from __future__ import annotations
import re
import os
from typing import Tuple, Dict, Any, Iterable, Optional, List
from pyparsing import col
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
    "koppel_metadata",
    "koppel_geo_info",
    "sla_op",
    "lees_opgeslagen_data",
    "read_metadata_wide_to_tidy",
    "attach_and_apply_metadata",
    "metadata_dict",
    "read_and_join_with_metadata",
    "maak_gelabelde_kopie_df_data",
    "maak_gelabelde_kopie_df_klimaat",
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
        disable=not VERBOSE,                # <<< progress bar automatisch UIT als VERBOSE=False
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

def metadata_dict(df_meta: pd.DataFrame) -> dict[str, str]:
    """
    Bouwt een mapping van indicatorcode -> leesbare titel
    op basis van metadata.
    """
    vprint("Metadata voorbereiden...")

    meta_dict = df_meta.set_index("Key")["Title"].to_dict()
    meta_dict.pop("WijkenEnBuurten", None)

    vprint(f"  {len(meta_dict)} metadata-items beschikbaar")
    return meta_dict

def maak_gelabelde_kopie_df_data(
    df: pd.DataFrame,
    meta_dict: dict[str, str],
) -> pd.DataFrame:
    """
    Maakt een gelabelde kopie van df op basis van meta_dict.
    Originele df blijft onaangetast.
    """
    rename_map = {
        k: v
        for k, v in meta_dict.items()
        if k in df.columns
    }

    df_labeled = df.rename(columns=rename_map)

    vprint(f"  {len(rename_map)} kolommen hernoemd (gelabelde kopie)")
    return df_labeled



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
    """Lees CSV-bestand met encoding-fallback en opgeschoonde kolomnamen."""

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
    attribute_key: str = "Attribuutnaam",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Leest metadata en levert (meta_raw, meta_tidy).
    - Rij-oriëntatie: 
    Als er een kolom `attribute_key` (=default: 'Attribuutnaam') bestaat:
        * meta_tidy = zelfde rijen, hernoemd naar 'column_name'
        * één rij per attribuut (kolomnaam in dataset)
    - Kolom-oriëntatie:
        * Eerste kolom is lijst met meta-velden -> transpose naar tidy.
    """
    
    # CSV inlezen
    meta_raw = read_data_csv(path, sep=sep, decimal=decimal, encoding=encoding)
    # Kolomnamen opschonen
    meta_raw.columns = meta_raw.columns.map(lambda c: str(c).strip())

    # Vind attribute_key case-insensitive
    attr_col = next(
        (c for c in meta_raw.columns if c.strip().lower() == attribute_key.strip().lower()),
        None
    )

    if attr_col is not None:
        # Rij-oriëntatie (één rij per attribuut)

        # Attribuutnaam-kolom opschonen
        meta_raw[attr_col] = meta_raw[attr_col].astype(str).str.strip()

        # Duplicaten signaleren
        dup_mask = meta_raw[attr_col].duplicated(keep=False)
        if dup_mask.any():
            dup_vals = meta_raw.loc[dup_mask, attr_col].value_counts().to_dict()
            print(f"[WAARSCHUWING] Dubbele {attr_col}-waarden: {dup_vals}")

        # Hernoem attribuut_key-kolom naar 'column_name'
        meta_tidy = meta_raw.rename(columns={attr_col: "column_name"}).copy()

        # Opschonen + index zetten (CRUCIAAL)
        meta_tidy["column_name"] = meta_tidy["column_name"].astype(str).str.strip()
        meta_tidy.index = meta_tidy["column_name"]
        meta_tidy = meta_tidy.drop(columns=["column_name"])

        return meta_raw, meta_tidy


    else:
        # Kolom-oriëntatie (oude breed-naar-tidy transpose)
        # Eerste kolom geeft naam van meta_veld. Deze opschonen en daarna transponeren.
        first_col_name = meta_raw.columns[0]
        meta_raw[first_col_name] = meta_raw[first_col_name].astype(str).str.strip()
        meta_tidy = (
            meta_raw.set_index(first_col_name).T.reset_index().rename(columns={"index": "column_name"})
        )
        meta_tidy["column_name"] = meta_tidy["column_name"].astype(str).str.strip()
        return meta_raw, meta_tidy



def maak_suffix_tabel(df_klimaat: pd.DataFrame) -> pd.DataFrame:
    """
    Geeft een tabel:
    - variabele (basisnaam zonder suffix)
    - alle gevonden AHN-suffixen (_AHN3, _AHN3_BK, _AHN4_X etc.)
    """
    # regex patroon om AHN-kolommen te herkennen en basisnaam + suffix te extraheren
    pattern = re.compile(
        r"^(?P<base>.*?)(?:_(?P<suffix>AHN\d+(?:_[A-Za-z0-9]+)?|BK))$",
        re.IGNORECASE
    )

    rows = []

    # Gaat door alle kolommen en zoekt naar AHN-suffixen. Als gevonden, splitst in basisnaam + suffix.
    for col in df_klimaat.columns:
        m = pattern.match(col)
        if not m:
            continue

        base = m.group(1)
        suffix = m.group(2)

        rows.append({"variabele": base, "suffix": suffix})
    # Zet om naar DataFrame 
    df_long = pd.DataFrame(rows)

    # Groepeert op basisnaam
    df_wide = (
        df_long.groupby("variabele")["suffix"]
        .apply(lambda s: ", ".join(sorted(s)))
        .reset_index(name="alle_suffixen")
    )

    return df_wide


PATTERN_SUFFIX = re.compile(
    r"^(?P<base>.*?)(?:_(?P<suffix>AHN\d+(?:_[A-Za-z0-9]+)?|BK))?$",
    re.IGNORECASE
)

def strip_suffix(col: str) -> str:
    m = PATTERN_SUFFIX.match(col)
    return m.group("base") if m else col

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
    # Alleen metadata voor kolommen die in df zitten
    

    df_cols_stripped = {c: strip_suffix(c) for c in df.columns}

    reverse_map: Dict[str, list[str]] = {}
    for original, base in df_cols_stripped.items():
        reverse_map.setdefault(base, []).append(original)

    # meta_tidy.index bevat AL de basisindicatornamen
    valid_meta_rows = meta_tidy.index.isin(reverse_map.keys())
    meta_tidy = meta_tidy.loc[valid_meta_rows].copy()



    # Maakt een dictionary met een dictionary per kolom met metadata, 
    col_meta: Dict[str, Dict[str, Any]] = meta_tidy.to_dict(orient="index")

    # Dtypes toepassen

    # Controleert of dtype_field aanwezig is in meta_tidy, en of het veld niet leeg is,
    if dtype_field in meta_tidy.columns:
        dtype_map = meta_tidy[dtype_field].dropna().to_dict()

        # Splits datetime van overige dtypes
        datetime_cols = [
            col
            for col, dtype_spec in dtype_map.items()
            if isinstance(dtype_spec, str) and dtype_spec.lower().startswith("datetime")
        ]
        other_dtypes = {col: dtype_spec for col, dtype_spec in dtype_map.items() if col not in datetime_cols}

        for col, dtype_spec in other_dtypes.items():
            # Alleen bestaande kolommen proberen te converteren, en alleen als dtype_spec een string is
            if col not in df.columns or not isinstance(dtype_spec, str):
                continue
            d_lower = dtype_spec.lower()
            # Dtypes toepassen
            try:
                if d_lower in ("string", "category"):
                    df[col] = df[col].astype(d_lower)
                elif d_lower in ("float", "float64", "float32"):
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif d_lower in ("int", "int64", "int32", "int16", "int8"):
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                elif d_lower in ("boolean", "bool"):
                    df[col] = df[col].astype("boolean")
                else:
                    # Onbekende dtype -> probeer numeriek, anders laat staan
                    df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                # Veilige fallback
                df[col] = pd.to_numeric(df[col], errors="ignore")
        # Dtypes toepassen voor datetime-kolommen apart.
        for col in datetime_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=dayfirst) # dayfirst--> dag-maand-jaar 

    df.attrs["metadata"] = col_meta
    return col_meta

def read_and_join_with_metadata(
    data_path: str,
    metadata_path: str,
    sep: str = ";",
    decimal: str = ",",
    encoding: str = "utf-8-sig",
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """
    Leest data + metadata in, koppelt ze, en verwijdert ALLE AHN3- en AHN4-
    variabelen inclusief suffixvarianten (_AHN3, _AHN3_*, _AHN4, _AHN4_*).
    """
    # Data en metadata inlezen
    df = read_data_csv(data_path, sep=sep, decimal=decimal, encoding=encoding)
    _, meta_tidy = read_metadata_to_tidy(
        metadata_path,
        sep=sep,
        decimal=decimal,
        encoding=encoding,
        attribute_key="Attribuutnaam"
    )

    # Metadata koppelen
    col_meta = attach_and_apply_metadata(df, meta_tidy)

    # ---------------------------------------------------------
    # Alleen recente AHN-variabelen behouden.
    # ---------------------------------------------------------
    
    # Herken AHN-suffixen en splits basis + AHN-nummer
    pattern_ahn = re.compile(
        r"^(?P<base>.*?)(?:_)?AHN(?P<nr>\d+)(?P<rest>.*)$",
        flags=re.IGNORECASE,
    )

    ahn_cols = []

    # Verzamel AHN-informatie per kolom
    for col in df.columns:
        m = pattern_ahn.match(col)
        if not m:
            continue

        ahn_cols.append({
            "col": col,
            "base": m.group("base"),
            "ahn_nr": int(m.group("nr")),
        })

    # Bepaal per basisnaam het hoogste AHN-nummer
    max_ahn_per_base = defaultdict(int)
    for row in ahn_cols:
        max_ahn_per_base[row["base"]] = max(
            max_ahn_per_base[row["base"]],
            row["ahn_nr"],
        )

    # Te verwijderen: alle kolommen met een lager AHN-nummer
    to_drop = [
        row["col"]
        for row in ahn_cols
        if row["ahn_nr"] < max_ahn_per_base[row["base"]]
    ]

    # Verwijderen + logging
    if to_drop:
        vprint(f"[AHN] Verwijderen {len(to_drop)} oudere AHN-kolommen:")
        for col in to_drop:
            vprint(f"   - {col}")
        df = df.drop(columns=to_drop)
    return df, meta_tidy, col_meta

def controleer_ahn_metadata(df: pd.DataFrame):
    print("\n--- Controle metadata voor AHN‑variabelen na verwijderen oudere AHN kolommen---")

    meta = df.attrs.get("metadata", {})
    if not meta:
        print(" Geen metadata gevonden in df.attrs['metadata']")
        return

    # patroon om AHN‑kolommen te herkennen
    pattern = re.compile(
        r"^(.*?)(?:_)?(AHN\d(?:_[A-Za-z0-9]+)?)$",
        re.IGNORECASE
    )
    rows = []
    for col in df.columns:
        m = pattern.match(col)
        if not m:
            continue
        
        base = m.group(1)
        suffix = m.group(2)

        # metadata kan gekoppeld zijn op exacte naam of op basisnaam
        has_meta_exact = col in meta
        has_meta_base  = base in meta

        rows.append({
            "kolom": col,
            "basisnaam": base,
            "suffix": suffix,
            "metadata_op_exacte_kolom": "ja" if has_meta_exact else "nee",
            "metadata_op_basisnaam": "ja" if has_meta_base else "nee",
        })

    df_check = pd.DataFrame(rows)
    print(df_check.to_string(index=False))  # mooi geformatteerd printen

    return df_check

def maak_gelabelde_kopie_df_klimaat(
    df_klimaat: pd.DataFrame,
    meta_tidy: pd.DataFrame,
    label_field: str, 
    suffix_scheider: str = "_AHN",
) -> pd.DataFrame:
    """
    Maakt een gelabelde kopie van df_klimaat op basis van metadata.
    De originele df_klimaat blijft onaangetast.

    Parameters
    ----------
    df_klimaat : pd.DataFrame
        Bron-dataframe met technische kolomnamen.
    meta_tidy : pd.DataFrame
        Metadata met index = basisnaam van de indicator.
    label_field : str
        Metadata-kolom die het label bevat (default: 'Omschrijving').
    suffix_scheider : str
        Scheider waarmee AHN-suffixen worden herkend (default: '_AHN').

    Returns
    -------
    pd.DataFrame
        Een nieuwe DataFrame met gelabelde kolommen.
    """
    df_klimaat_labels = df_klimaat.copy()

    if label_field not in meta_tidy.columns:
        vprint(f"[WAARSCHUWING] label_field '{label_field}' niet gevonden in metadata. Geen kolommen gelabeld.")
        return df_klimaat_labels
    print("Voorbeeld meta_tidy.index:")
    print(meta_tidy.index[:20].tolist())

    print("Voorbeeld df_klimaat kolommen:")
    print(df_klimaat_labels.columns[:20].tolist())

    rename_map = {}

    for col in df_klimaat_labels.columns:
        base = strip_suffix(col)
        if base in meta_tidy.index:
            label = meta_tidy.at[base, label_field]
            if isinstance(label, str) and label.strip().lower() not in {"", "nvt", "none"}:
                rename_map[col] = label


    if rename_map:
        df_klimaat_labels = df_klimaat_labels.rename(columns=rename_map)
    
    vprint(f"[INFO] Kolommen gelabeld: {len(rename_map)}")
    print(rename_map)

    return df_klimaat_labels

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

    # --- 1. Controles ---
    if left_key not in df_data.columns:
        raise KeyError(f"df_data mist sleutelkolom '{left_key}'.")
    if right_key not in df_klimaat.columns:
        raise KeyError(f"df_klimaat mist sleutelkolom '{right_key}'.")

    # --- 2. Kopieën maken ---
    left = df_data.copy()
    right = df_klimaat.copy()

    # --- 3. Normaliseer sleutels ---
    left[left_key] = left[left_key].astype(str).str.strip().str.upper()
    right[right_key] = right[right_key].astype(str).str.strip().str.upper()

    # --- 4. Controleer uniciteit rechts ---
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

    # --- 5. Definitieve LEFT JOIN ---
    df_join = left.merge(
        right,
        left_on=left_key,
        right_on=right_key,
        how="left",
        validate="m:1"
    )

    # --- 6. Logging ---
    if verbose:
        n_missing = df_join[right_key].isna().sum()
        coverage = 1 - n_missing / len(df_join)

        print(f"[INFO] Join afgerond op '{left_key}' ↔ '{right_key}'.")
        print(f"[INFO] Dekking: {coverage:.3f} | Niet-gematcht: {n_missing} rijen.")

        if n_missing > 0:
            print("Voorbeeld niet-gematchte sleutels (eerste 10):")
            print(df_join.loc[df_join[right_key].isna(), left_key].head(10))

    return df_join