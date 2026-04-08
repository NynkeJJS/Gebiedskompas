from __future__ import annotations
import re
import os
from typing import Tuple, Dict, Any, Iterable, Optional, List
import requests
import pandas as pd
from tqdm import tqdm
from collections import defaultdict


from config_experiment import (
    VERBOSE,
    BASE_URL,
    PROVINCIE,
    BATCH_SIZE,
    FRIESE_GEMEENTEN,
    KERNCIJFERS_DATA,
    KERNCIJFERS_META,
)

__all__ = [
    "vprint",
    "get_metadata",
    "get_provincie_gebieden",
    "get_data_provincie",
    "koppel_geo_info",
    "sla_op",
    "lees_opgeslagen_data",
    "read_data_csv",
    "read_metadata_to_tidy",
    "metadata_label_map",
    "maak_suffix_tabel",
    "attach_and_apply_metadata",
    "read_and_join_with_metadata",
    "controleer_ahn_metadata",
    "maak_gelabelde_kopie_df_data",
    "maak_gelabelde_kopie_df_klimaat",
    "join_cbs_with_klimaat",
]

# ------------------------------------------------------
# Debug helpers
# ------------------------------------------------------

def vprint(msg: str):
    if VERBOSE:
        print(msg)


# ------------------------------------------------------
# OData helpers
# ------------------------------------------------------

def get_all_pages(url: str, params: Dict[str, Any] | None = None) -> list[dict]:
    """Haalt automatisch alle OData-pagina’s op totdat er geen vervolgpagina meer is."""
    results: list[dict] = []
    while url:
        resp = requests.get(url, params=params) # api aanroepen
        resp.raise_for_status() # stop bij fout
        data = resp.json() # JSON omzetten naar dictionary
        results.extend(data.get("value", [])) # data toevoegen aan resultaten
        url = data.get("odata.nextLink") # volgende pagina URL
        params = None  # alleen bij eerste request params meesturen, volgende pagina's bevatten al de juiste query in nextLink
    return results


def get_metadata() -> pd.DataFrame:
    """Haalt alle metadata op van de API en retourneert dit als DataFrame."""
    vprint("Metadata ophalen...")
    meta_data = get_all_pages(f"{BASE_URL}/DataProperties")
    df_meta = pd.DataFrame(meta_data)
    vprint(f"  {len(df_meta)} indicatoren gevonden")
    return df_meta

def metadata_label_map(df_meta: pd.DataFrame) -> dict[str, str]:
    """
    Bouwt een mapping van indicatorcode -> 'Titel (eenheid)'
    """
    vprint("Metadata labels voorbereiden (met eenheid)...")

    label_map = {}

    for _, row in df_meta.iterrows():
        key = row.get("Key")
        title = row.get("Title")
        unit = row.get("Unit") or row.get("Eenheid")

        if not isinstance(key, str) or not isinstance(title, str):
            continue

        title = title.strip()

        if isinstance(unit, str) and unit.strip():
            label = f"{title} ({unit.strip()})"
        else:
            label = title

        label_map[key] = label

    # Sleutelveld eruit
    label_map.pop("WijkenEnBuurten", None)

    vprint(f"  {len(label_map)} labels met eenheid aangemaakt")
    return label_map


def get_provincie_gebieden() -> pd.DataFrame:
    """Haalt alle wijken/buurten/gemeenten op en filtert ze zodat alleen de gebieden die binnen Friesland vallen overblijven."""
    vprint(f"Wijken en buurten ophalen voor {PROVINCIE}...")
    
    geo_data = get_all_pages(f"{BASE_URL}/WijkenEnBuurten")
    df_geo = pd.DataFrame(geo_data)

    friese_gemeenten = FRIESE_GEMEENTEN
    vprint(f"  Friese gemeenten: {friese_gemeenten}")

    df_provincie = df_geo[
        (df_geo["Key"].isin(friese_gemeenten))
        | (df_geo["Municipality"].isin(friese_gemeenten))
    ]

    vprint(f"  {len(df_provincie)} gebieden gevonden in {PROVINCIE}")
    vprint(f"  Voorbeeld gebieden:\n{df_provincie[['Key', 'Title', 'Municipality']].head(10)}")
    return df_provincie


def get_data_provincie(provincie_codes: list[str]) -> pd.DataFrame:
    """Haalt indicatorgegevens op voor een provincie en toont een progress bar."""
    vprint(f"Data ophalen voor {PROVINCIE}...")

    all_data: list[dict] = []
    total_batches = (len(provincie_codes) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in tqdm(
        range(0, len(provincie_codes), BATCH_SIZE),
        total=total_batches,
        disable=not VERBOSE,                # progress bar automatisch UIT als VERBOSE=False
        desc="Batches verwerken"
    ):
        batch = provincie_codes[i : i + BATCH_SIZE]
        filter_str = " or ".join([f"WijkenEnBuurten eq '{code}'" for code in batch])
        params = {"$filter": filter_str, "$top": 10000}

        batch_data = get_all_pages(f"{BASE_URL}/TypedDataSet", params=params)
        all_data.extend(batch_data)

        vprint(f"  Batch {i // BATCH_SIZE + 1} geladen ({len(batch_data)} rijen)")

    df_data = pd.DataFrame(all_data)
    vprint(f"  Totaal {len(df_data)} rijen opgehaald")

    return df_data



def koppel_geo_info(df_data: pd.DataFrame, df_provincie: pd.DataFrame) -> pd.DataFrame:
    """Voegt gebiedsnaam toe door te koppelen op de gebiedscode."""
    vprint("Geografische info koppelen...")

    df_geo_info = df_provincie[["Key", "Title"]].rename(
        columns={"Title": "Naam_gebied", "Key": "WijkenEnBuurten"}
    )
    return df_data.merge(df_geo_info, on="WijkenEnBuurten", how="left")


def sla_op(df_data: pd.DataFrame, df_meta: pd.DataFrame) -> None:
    """Slaat data en metadata op als CSV op schijf."""
    vprint("Bestanden opslaan...")

    vprint(f"  Data opgeslagen op: {os.path.abspath(KERNCIJFERS_DATA)}")
    vprint(f"  Meta opgeslagen op: {os.path.abspath(KERNCIJFERS_META)}")

    df_data.to_csv(KERNCIJFERS_DATA, index=False)
    df_meta.to_csv(KERNCIJFERS_META, index=False)


def lees_opgeslagen_data(data_path, meta_path):
    """leest data en metadata van schijf."""
    vprint("Data vanaf schijf inlezen...")

    df_data = pd.read_csv(data_path, low_memory=False)
    df_meta = pd.read_csv(meta_path, low_memory=False) if os.path.exists(meta_path) else None

    vprint(f"Klaar! Shape: {df_data.shape}")
    return df_data, df_meta

# ------------------------------------------------------
# CSV + metadata helpers met encoding-fallback
# ------------------------------------------------------

def read_data_csv(
    path: str,
    sep: str = ";",
    decimal: str = ",",
    encoding: str = "utf-8-sig",
    na_values: Iterable = ("-9995", -9995, "", "NA", "N/A"),
    low_memory: bool = False,
) -> pd.DataFrame:
    """Leest een CSV‑bestand met automatische encoding‑controle en opgeschoonde kolomnamen."""

    encodings = (encoding, "utf-8", "cp1252", "latin-1") 
    last_err = None

    # Inlezen csv met verschillende encodings 
    for enc in encodings:
        try:
            vprint(f"[CSV] Proberen met encoding: {enc}")
            df = pd.read_csv(
                path,
                sep=sep,
                decimal=decimal,
                encoding=enc,
                na_values=list(na_values),
                low_memory=low_memory,
            )
            break
        except Exception as e:
            last_err = e
    else:
        raise UnicodeError(
            f"Kon '{path}' niet lezen. "
            f"Encodings geprobeerd: {encodings}. "
            f"Laatste fout: {last_err}"
        )

    df.columns = df.columns.str.strip()
    return df

def read_metadata_to_tidy(
    path: str,
    sep: str = ";",
    decimal: str = ",",
    encoding: str = "utf-8-sig",
    indicator_key: str = "Attribuutnaam",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Leest metadata en levert (meta_raw, meta_tidy).
    - Rij-oriëntatie: 
    Als er een kolom `indicator_key` (=default: 'Attribuutnaam') bestaat:
        * meta_tidy = zelfde rijen, indicator_key hernoemd naar 'column_name'
        * één rij per indicator (kolomnaam in dataset)
    - Kolom-oriëntatie:
        * Eerste kolom is lijst met meta-velden -> transpose naar tidy.
    """
    
    # CSV inlezen
    meta_raw = read_data_csv(path, sep=sep, decimal=decimal, encoding=encoding)
    # Kolomnamen opschonen
    meta_raw.columns = meta_raw.columns.map(lambda c: str(c).strip())

    # Vind indicator_key case-insensitive
    attr_col = next(
        (c for c in meta_raw.columns if c.strip().lower() == indicator_key.strip().lower()),
        None
    )

    if attr_col is not None:
        # Rij-oriëntatie (één rij per indicator)

        # Indicatornaam-kolom opschonen
        meta_raw[attr_col] = meta_raw[attr_col].astype(str).str.strip()

        # Duplicaten signaleren
        dup_mask = meta_raw[attr_col].duplicated(keep=False)
        if dup_mask.any():
            dup_vals = meta_raw.loc[dup_mask, attr_col].value_counts().to_dict()
            print(f"[WAARSCHUWING] Dubbele {attr_col}-waarden: {dup_vals}")

        # Hernoem indicator_key-kolom naar 'column_name'
        meta_tidy = meta_raw.rename(columns={attr_col: "column_name"}).copy()

        # Opschonen + index zetten 
        meta_tidy["column_name"] = meta_tidy["column_name"].astype(str).str.strip()
        meta_tidy.index = meta_tidy["column_name"]
        meta_tidy = meta_tidy.drop(columns=["column_name"])

        return meta_raw, meta_tidy


    else:
        # Kolom-oriëntatie (oude breed-naar-tidy transpose)
        # Eerste kolom geeft naam van indicator. Deze opschonen en daarna transponeren.
        first_col_name = meta_raw.columns[0]
        meta_raw[first_col_name] = meta_raw[first_col_name].astype(str).str.strip()
        meta_tidy = (
            meta_raw.set_index(first_col_name).T.reset_index().rename(columns={"index": "column_name"})
        )
        meta_tidy["column_name"] = meta_tidy["column_name"].astype(str).str.strip()
        return meta_raw, meta_tidy



# ------------------------------------------------------
# Hulpfuncties voor omgaan met AHN en BK suffixen
# ------------------------------------------------------

# regex patroon om AHN/BK-kolommen te herkennen en basisnaam + suffix te extraheren

PATTERN_SUFFIX = re.compile(
    r"^(?P<base>.*?)(?:_(?P<suffix>AHN(?P<nr>\d+)(?:_[A-Za-z0-9]+)?|BK))?$",
    re.IGNORECASE
)

def parse_suffix(col: str) -> dict[str, object]:
    """
    Ontleedt een kolomnaam in basisnaam en suffix-informatie.
    """
    m = PATTERN_SUFFIX.match(col)
    if not m:
        return {"base": col, "suffix": None, "ahn_nr": None}

    return {
        "base": m.group("base"),
        "suffix": m.group("suffix"),
        "ahn_nr": int(m.group("nr")) if m.group("nr") else None,
    }


# ------------------------------------------------------
# Hulpfuncties voor het inzichtelijk maken van welke AHN/BK-suffixen er zijn per basisvariabele
# ------------------------------------------------------

def maak_suffix_tabel(df_klimaat: pd.DataFrame) -> pd.DataFrame:
    """
    Geeft een tabel:
    - variabele (basisnaam zonder suffix)
    - alle gevonden suffixen (AHN*, AHN*_BK, BK)
    """
    rows = []

    for col in df_klimaat.columns:
        info = parse_suffix(col)

        # Geen suffix → niet opnemen in overzicht
        if info["suffix"] is None:
            continue

        rows.append({
            "variabele": info["base"],
            "suffix": info["suffix"],
        })

    # Geen AHN/BK-kolommen gevonden → lege tabel met juiste kolommen teruggeven
    if not rows:
        return pd.DataFrame(columns=["variabele", "alle_suffixen"])

    df_long = pd.DataFrame(rows)

    df_wide = (
        df_long
        .groupby("variabele")["suffix"]
        .apply(lambda s: ", ".join(sorted(set(s))))
        .reset_index(name="alle_suffixen")
    )

    return df_wide



def attach_and_apply_metadata(
    df: pd.DataFrame,
    meta_tidy: pd.DataFrame,
    label_fields: Iterable[str] = ("Indicator", "Label", "Omschrijving"),
    unit_fields: Iterable[str] = ("Eenheid", "Unit"),
    dtype_field: str = "dtype",
    dayfirst: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    - Koppelt metadata aan df (in df.attrs['metadata']).
    - Past dtypes toe als 'dtype' in metadata aanwezig is.
    - (Optioneel) hernoemt kolommen o.b.v. eerste gevonden veld in label_fields.
    - Retourneert dict: {kolomnaam: {meta_field: waarde, ...}}.
    """
    # strip kolomnamen
    df_cols_stripped = {c: parse_suffix(c)["base"] for c in df.columns}

    col_meta: Dict[str, Dict[str, Any]] = {}

    for original_col, base in df_cols_stripped.items():
        if base in meta_tidy.index: # Controleren of er metadata beschikbaar is
            col_meta[original_col] = meta_tidy.loc[base].to_dict() # metadata ophalen en omzetten naar dict

    # ---------------------------
    # Dtypes toepassen (per df-kolom)
    # ---------------------------
    if dtype_field in meta_tidy.columns:

        # Maak en dictionary aan met basisnaam en dtype
        dtype_map = meta_tidy[dtype_field].dropna().to_dict()

        for col in df.columns:
            base = parse_suffix(col)["base"]

            if base not in dtype_map:
                continue
            
            # Alleen geldige dtype-specificaties toepassen
            dtype_spec = dtype_map[base]
            if not isinstance(dtype_spec, str):
                continue

            d_lower = dtype_spec.lower()

            try:
                if d_lower.startswith("datetime"):
                    df[col] = pd.to_datetime(
                        df[col], errors="coerce", dayfirst=dayfirst
                    )
                elif d_lower in ("string", "category"):
                    df[col] = df[col].astype(d_lower)
                elif d_lower.startswith("float"):
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif d_lower.startswith(("int", "uint")):
                    df[col] = (
                        pd.to_numeric(df[col], errors="coerce")
                        .astype("Int64")
                    )
                elif d_lower in ("bool", "boolean"):
                    df[col] = df[col].astype("boolean")
                else:
                    df[col] = pd.to_numeric(df[col], errors="ignore")

            except Exception:
                # Veilige fallback: kolom ongewijzigd laten
                pass

    df.attrs["metadata"] = col_meta
    return col_meta


def read_and_join_with_metadata(
    data_path: str,
    metadata_path: str,
    sep: str = ";",
    decimal: str = ",",
    encoding: str = "utf-8-sig",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict]]:
    """
    Leest data + metadata in, koppelt ze, en behoudt per basisvariabele
    alleen de hoogste AHN-versie (incl. AHN*_BK).
    """

    # ---------------------------------------------------------
    # Data en metadata inlezen
    # ---------------------------------------------------------
    
    df = read_data_csv(data_path, sep=sep, decimal=decimal, encoding=encoding)
    _, meta_tidy = read_metadata_to_tidy(
        metadata_path,
        sep=sep,
        decimal=decimal,
        encoding=encoding,
        indicator_key="Attribuutnaam"
    )

    # Metadata koppelen
    col_meta = attach_and_apply_metadata(df, meta_tidy)

    # ---------------------------------------------------------
    # AHN-informatie verzamelen
    # ---------------------------------------------------------
    ahn_cols = []

    for col in df.columns:
        info = parse_suffix(col)

        # Alleen kolommen met een AHN-nummer
        if info["ahn_nr"] is None:
            continue

        # Lijst van AHN-kolommen bijhouden met basisnaam en AHN-nummer
        ahn_cols.append({
            "col": col,
            "base": info["base"],
            "ahn_nr": info["ahn_nr"],
        })

    # Geen AHN-kolommen
    if not ahn_cols:
        return df, meta_tidy, col_meta

    # ---------------------------------------------------------
    # Hoogste AHN per basisvariabele bepalen
    # ---------------------------------------------------------
    max_ahn_per_base = defaultdict(int)

    # Dcitionary maken van basisnaam → hoogste AHN-nummer
    for row in ahn_cols:
        max_ahn_per_base[row["base"]] = max(
            max_ahn_per_base[row["base"]],
            row["ahn_nr"],
        )

    # ---------------------------------------------------------
    # Oudere AHN-kolommen verwijderen
    # ---------------------------------------------------------
    to_drop = [
        row["col"]
        for row in ahn_cols
        if row["ahn_nr"] < max_ahn_per_base[row["base"]]
    ]

    # Kolommen verwijderen die een oudere AHN-versie hebben dan de hoogste gevonden voor die basisvariabele
    if to_drop:
        vprint(f"[AHN] Verwijderen {len(to_drop)} oudere AHN-kolommen:")
        for col in to_drop:
            vprint(f"   - {col}")
        df = df.drop(columns=to_drop)

    return df, meta_tidy, col_meta

import pandas as pd


import pandas as pd


def controleer_ahn_metadata(
    df: pd.DataFrame,
    meta_tidy: pd.DataFrame,
) -> pd.DataFrame:
    """
    Controleert voor AHN/BK-kolommen:
    - of metadata exact bestaat in meta_tidy
    - of metadata via de basisnaam bestaat
    - waar de metadata inhoudelijk vandaan komt 
    """

    rows = []

    for col in df.columns:
        info = parse_suffix(col)

        # Alleen AHN of BK-varianten inspecteren
        if info["suffix"] is None:
            continue

        base = info["base"]
        suffix = info["suffix"]
        ahn_nr = info["ahn_nr"]

        # Bronnen van metadata
        has_meta_exact = col in meta_tidy.index
        has_meta_base = base in meta_tidy.index

        # Resolutie bepalen (zonder expliciete 'geërfd'-kolom)
        if has_meta_exact:
            resolution = "exact"
        elif has_meta_base:
            resolution = "basis"
        else:
            resolution = "geen"

        rows.append({
            "kolom": col,
            "basisnaam": base,
            "suffix": suffix,
            "ahn_nr": ahn_nr,
            "metadata_exact": "ja" if has_meta_exact else "nee",
            "metadata_basis": "ja" if has_meta_base else "nee",
            "metadata_resolutie": resolution,
        })

    df_check = pd.DataFrame(rows)

    if df_check.empty:
        print("Geen AHN/BK-kolommen gevonden.")
        return df_check

    print("\n--- Controle metadata voor AHN/BK‑variabelen ---")
    print(df_check.to_string(index=False))

    return df_check


# ------------------------------------------------------------------------
# Helpers voor het het maken van unieke labels op basis van jaartallen
# ------------------------------------------------------------------------

def extract_year_from_column(col: str) -> Optional[str]:
    """
    Haalt een jaartal uit een kolomnaam zoals.
    Retourneert None als er geen jaar is.
    """
    # Zoek naar een suffix van een tweecijferig jaartal aan het einde van de kolomnaam, voorafgegaan door een underscore of het begin van de string
    m = re.search(r"(?:_|^)(\d{2})$", col)
    if not m:
        return None

    year = int(m.group(1))
    # Geeft een 4 cijferig jaartal terug.
    return f"20{year:02d}"

def build_label_with_unit_and_year(
    *,
    title: str,
    unit: str | None,
    year: str | None,
) -> str:
    """
    Bouwt een label als:
    - Titel (eenheid, jaar)
    - Titel (eenheid)
    - Titel (jaar)
    - Titel
    """
    parts = []

    if unit:
        parts.append(unit)

    if year:
        parts.append(year)

    if parts:
        return f"{title} ({', '.join(parts)})"

    return title

# ------------------------------------------------------------------------
# Functies voor het gebruik van labels in plaats van indicatornamen
# ------------------------------------------------------------------------


def maak_gelabelde_kopie_df_data(
    df: pd.DataFrame,
    df_meta: pd.DataFrame,
) -> pd.DataFrame:
    """
    Maakt een gelabelde kopie van df:
    Titel + eenheid + jaar (indien aanwezig).
    """
    df_labeled = df.copy()

    rename_map = {}

    # Zorg voor snelle lookup van metadata
    meta_lookup = df_meta.set_index("Key")

    for col in df.columns:
        if col not in meta_lookup.index:
            continue
        
        # Haal titel, eenheid en jaar op basis van metadata en kolomnaam
        title = meta_lookup.at[col, "Title"]
        unit = meta_lookup.at[col, "Unit"] if "Unit" in meta_lookup.columns else None
        year = extract_year_from_column(col)

        if not isinstance(title, str):
            continue
        
        # Bouwt een label op basis van titel, eenheid en jaar.
        label = build_label_with_unit_and_year(
            title=title.strip(),
            unit=unit.strip() if isinstance(unit, str) and unit.strip() else None,
            year=year,
        )

        rename_map[col] = label

    df_labeled = df_labeled.rename(columns=rename_map)
    return df_labeled


def maak_gelabelde_kopie_df_klimaat(
    df_klimaat: pd.DataFrame,
    meta_tidy: pd.DataFrame,
    label_field: str,
    *,
    keep_suffix: bool = False,
) -> pd.DataFrame:

    # Maakt een kopie van df_klimaat om labels aan toe te voegen zonder de originele data te wijzigen.
    df_klimaat_labels = df_klimaat.copy()

    # Controleert of het opgegeven label_field in de metadata aanwezig is.  
    if label_field not in meta_tidy.columns:
        vprint(
            f"[WAARSCHUWING] label_field '{label_field}' niet gevonden in metadata. "
            "Geen kolommen gelabeld."
        )
        return df_klimaat_labels


    rename_map = {}

    # Itereert over de kolommen van df_klimaat, probeert de basisnaam te matchen met metadata, en bouwt een label op basis van het opgegeven label_field.
    # Neemt automatisch ook indicatoren mee zonder suffix, zolang de basisnaam maar in de metadata staat.
    for col in df_klimaat_labels.columns:
        info = parse_suffix(col)
        base = info["base"]

        if base not in meta_tidy.index:
            continue

        label = meta_tidy.at[base, label_field]

        if not isinstance(label, str):
            continue

        label = label.strip()
        if label.lower() in {"", "nvt", "none"}:
            continue

        # Voeg suffix-informatie toe aan het label
        if info["suffix"] and info["suffix"].endswith("BK"):
            label = f"{label} (bebouwde kom)"
        elif keep_suffix and info["suffix"]:
            label = f"{label} ({info['suffix']})"

        rename_map[col] = label

    if rename_map:
        df_klimaat_labels = df_klimaat_labels.rename(columns=rename_map)

    vprint(f"[INFO] Kolommen gelabeld: {len(rename_map)}")

    return df_klimaat_labels


# ---------------------------------------------------------------------------------------
# Functievoor het koppelen van CBS-data aan klimaatdata op basis van gebiedscode.
# ---------------------------------------------------------------------------------------

def join_cbs_with_klimaat(
    df_data: pd.DataFrame,
    df_klimaat: pd.DataFrame,
    *,
    left_key: str,
    right_key: str,
    strict_unique: bool = False,   # True => error bij duplicaten, False => dedupe
    verbose: bool = True
) -> pd.DataFrame:
    """
    Koppel df_data (links) aan df_klimaat (rechts) op opgegeven sleutels.

    Parameters
    ----------
    left_key : str
        Kolomnaam in df_data (bijv. 'Codering')
    right_key : str
        Kolomnaam in df_klimaat (bijv. 'buurtcode2024')
    """

    # Controle of beide sleutels aanwezig zijn in de respectievelijke DataFrames
    if left_key not in df_data.columns:
        raise KeyError(f"df_data mist sleutelkolom '{left_key}'.")
    if right_key not in df_klimaat.columns:
        raise KeyError(f"df_klimaat mist sleutelkolom '{right_key}'.")

    # Maakt kopieën van de DataFrames om originele data ongewijzigd te laten.
    left = df_data.copy()
    right = df_klimaat.copy()

    # Normaliseer sleutels
    left[left_key] = left[left_key].astype(str).str.strip().str.upper()
    right[right_key] = right[right_key].astype(str).str.strip().str.upper()

    # Controleert duplicaten in de rechter DataFrame op basis van right_key.
    dup_mask = right.duplicated(subset=[right_key])
    dup_count = dup_mask.sum()

    if dup_count > 0:
        if strict_unique:
            dups = (
                right.loc[right.duplicated(subset=[right_key], keep=False), right_key]
                .value_counts()
                .head(20)
            )
            raise ValueError(
                f"'{right_key}' is niet uniek in df_klimaat ({dup_count} duplicaten).\n"
                f"Voorbeelden:\n{dups}"
            )
        else:
            if verbose:
                print(f"[WAARSCHUWING] {dup_count} duplicaten in df_klimaat['{right_key}'] gevonden.")
                print("→ Dedupliceren (keep='first'), alle kolommen verder intact.")

            right = (
                right.sort_values(right_key)
                .drop_duplicates(subset=[right_key], keep="first")
            )

    # Left join uitvoeren
    df_join = left.merge(
        right,
        left_on=left_key,
        right_on=right_key,
        how="left",
        validate="m:1"
    )

    # Logging
    if verbose:
        n_missing = df_join[right_key].isna().sum()
        coverage = 1 - n_missing / len(df_join)

        print(f"[INFO] Join afgerond op '{left_key}' ↔ '{right_key}'.")
        print(f"[INFO] Dekking: {coverage:.3f} | Niet-gematcht: {n_missing} rijen.")

        if n_missing > 0:
            print("Voorbeeld niet-gematchte sleutels (eerste 10):")
            print(df_join.loc[df_join[right_key].isna(), left_key].head(10))

    return df_join