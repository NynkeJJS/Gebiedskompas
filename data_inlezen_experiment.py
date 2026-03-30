from __future__ import annotations

import os
from typing import Tuple, Dict, Any, Iterable, Optional, List
import requests
import pandas as pd

from config_experiment import (
    BASE_URL,
    PROVINCIE,
    BATCH_SIZE,
    FRIESE_GEMEENTEN,
    BEWERKT_DIR,
    KERNCIJFERS_DATA,
    KERNCIJFERS_META,
)

__all__ = [
    "get_all_pages",
    "get_metadata",
    "get_provincie_gebieden",
    "get_data_provincie",
    "koppel_metadata",
    "koppel_geo_info",
    "sla_op",
    "lees_opgeslagen_data",
    "read_data_csv",
    "read_metadata_wide_to_tidy",
    "attach_and_apply_metadata",
    "read_and_join_with_metadata",
]
# ------------------------------------------------------
# OData helpers
# ------------------------------------------------------
def get_all_pages(url: str, params: Dict[str, Any] | None = None) -> list[dict]:
    """Haal alle pagina's op via paginering (OData $skip/nextLink)."""
    results: list[dict] = []
    while url:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("value", []))
        url = data.get("odata.nextLink")
        params = None  # only on first call
    return results


def get_metadata() -> pd.DataFrame:
    print("Metadata ophalen...")
    meta_data = get_all_pages(f"{BASE_URL}/DataProperties")
    df_meta = pd.DataFrame(meta_data)
    print(f"  {len(df_meta)} indicatoren gevonden")
    return df_meta


def get_provincie_gebieden() -> pd.DataFrame:
    print(f"Wijken en buurten ophalen voor {PROVINCIE}...")
    geo_data = get_all_pages(f"{BASE_URL}/WijkenEnBuurten")
    df_geo = pd.DataFrame(geo_data)

    # 1. Selecteer Friese gemeenten (GM)
    friese_gemeenten = FRIESE_GEMEENTEN
    print(f"  Friese gemeenten: {friese_gemeenten}")

    # 2. Selecteer ALLE gebieden (GM, WK, BU) die tot Friesland behoren
    df_provincie = df_geo[
        (df_geo["Key"].isin(friese_gemeenten))  # GM-niveau
        | (df_geo["Municipality"].isin(friese_gemeenten))  # WK & BU niveau
    ]

    print(f"  {len(df_provincie)} gebieden gevonden in {PROVINCIE}")
    return df_provincie


def get_data_provincie(provincie_codes: list[str]) -> pd.DataFrame:
    print(f"Data ophalen voor {PROVINCIE}...")
    all_data: list[dict] = []

    for i in range(0, len(provincie_codes), BATCH_SIZE):
        batch = provincie_codes[i : i + BATCH_SIZE]
        filter_str = " or ".join([f"WijkenEnBuurten eq '{code}'" for code in batch])

        params = {"$filter": filter_str, "$top": 10000}
        batch_data = get_all_pages(f"{BASE_URL}/TypedDataSet", params=params)

        all_data.extend(batch_data)
        print(f"  Batch {i // BATCH_SIZE + 1} geladen ({len(batch_data)} rijen)")

    df_data = pd.DataFrame(all_data)
    print(f"  Totaal {len(df_data)} rijen opgehaald")
    return df_data


def koppel_metadata(df_data: pd.DataFrame, df_meta: pd.DataFrame) -> pd.DataFrame:
    print("Metadata koppelen...")
    meta_dict = df_meta.set_index("Key")["Title"].to_dict()

    # WijkenEnBuurten uitsluiten van hernoemen
    meta_dict.pop("WijkenEnBuurten", None)

    rename_map = {k: v for k, v in meta_dict.items() if k in df_data.columns}
    df_data_labeled = df_data.rename(columns=rename_map)
    print(f"  {len(rename_map)} kolommen hernoemd")
    return df_data_labeled


def koppel_geo_info(df_data: pd.DataFrame, df_provincie: pd.DataFrame) -> pd.DataFrame:
    print("Geografische info koppelen...")
    df_geo_info = df_provincie[["Key", "Title"]].rename(
        columns={"Title": "Naam_gebied", "Key": "WijkenEnBuurten"}
    )
    return df_data.merge(df_geo_info, on="WijkenEnBuurten", how="left")


def sla_op(df_data: pd.DataFrame, df_meta: pd.DataFrame) -> None:
    print("Bestanden opslaan...")
    os.makedirs(BEWERKT_DIR, exist_ok=True)

    data_path = os.path.join(BEWERKT_DIR, KERNCIJFERS_DATA)
    meta_path = os.path.join(BEWERKT_DIR, KERNCIJFERS_META)

    df_data.to_csv(data_path, index=False)
    df_meta.to_csv(meta_path, index=False)

    print(f"  Data opgeslagen op: {os.path.abspath(data_path)}")
    print(f"  Meta opgeslagen op: {os.path.abspath(meta_path)}")


def lees_opgeslagen_data(output_dir, output_data, output_meta, verbose=True):
    data_path = os.path.join(output_dir, output_data)
    meta_path = os.path.join(output_dir, output_meta)

    if verbose:
        print("Data vanaf schijf inlezen...")

    df_data = pd.read_csv(data_path, low_memory=False)
    df_meta = pd.read_csv(meta_path, low_memory=False) if os.path.exists(meta_path) else None

    if verbose:
        print(f"Klaar! Shape: {df_data.shape}")

    return df_data, df_meta


# ------------------------------------------------------
# CSV + metadata helpers met encoding-fallback
# ------------------------------------------------------
from typing import Iterable, Tuple, Dict, Any
import pandas as pd

def _read_csv_with_fallback(
    path: str,
    sep: str,
    decimal: str,
    encodings: Iterable[str],
    na_values: Iterable,
    low_memory: bool,
) -> pd.DataFrame:
    last_err: Exception | None = None
    for enc in encodings:
        try:
            return pd.read_csv(
                path,
                sep=sep,
                decimal=decimal,
                encoding=enc,
                na_values=list(na_values),
                low_memory=low_memory,
            )
        except UnicodeDecodeError as e:
            last_err = e
            continue
        except Exception as e:
            # ParserError of andere issues: bewaar en verbreek de fallback
            last_err = e
            break
    raise UnicodeError(
        f"Kon bestand '{path}' niet lezen met encodings {list(encodings)}. "
        f"Laatst ontvangen fout: {last_err}"
    )

def read_data_csv(
    path: str,
    sep: str = ";",
    decimal: str = ",",
    encoding: str = "utf-8-sig",
    na_values: Iterable = ("-9995", -9995, "", "NA", "N/A"),
    low_memory: bool = False,
) -> pd.DataFrame:
    encodings = (encoding, "cp1252", "latin-1")
    df = _read_csv_with_fallback(
        path=path,
        sep=sep,
        decimal=decimal,
        encodings=encodings,
        na_values=na_values,
        low_memory=low_memory,
    )
    df.columns = df.columns.map(lambda c: str(c).strip())
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
    - Als er een kolom `attribute_key` (default: 'Attribuutnaam') bestaat:
        * meta_tidy = zelfde rijen, hernoemd naar 'column_name'
        * één rij per attribuut (kolomnaam in dataset)
    - Anders:
        * Eerste kolom is lijst met meta-velden -> transpose naar tidy.
    """
    meta_raw = read_data_csv(path, sep=sep, decimal=decimal, encoding=encoding)
    meta_raw.columns = meta_raw.columns.map(lambda c: str(c).strip())

    # Vind attribute_key case-insensitive
    attr_col = next(
        (c for c in meta_raw.columns if c.strip().lower() == attribute_key.strip().lower()),
        None
    )

    if attr_col is not None:
        # Rij-oriëntatie (één rij per attribuut)
        meta_raw[attr_col] = meta_raw[attr_col].astype(str).str.strip()
        # Duplicaten signaleren
        dup_mask = meta_raw[attr_col].duplicated(keep=False)
        if dup_mask.any():
            dup_vals = meta_raw.loc[dup_mask, attr_col].value_counts().to_dict()
            print(f"[WAARSCHUWING] Dubbele {attr_col}-waarden: {dup_vals}")

        meta_tidy = meta_raw.rename(columns={attr_col: "column_name"}).copy()
        meta_tidy["column_name"] = meta_tidy["column_name"].astype(str).str.strip()
        return meta_raw, meta_tidy

    # Fallback: kolom-oriëntatie (oude breed-naar-tidy transpose)
    first_col_name = meta_raw.columns[0]
    meta_raw[first_col_name] = meta_raw[first_col_name].astype(str).str.strip()
    meta_tidy = (
        meta_raw.set_index(first_col_name).T.reset_index().rename(columns={"index": "column_name"})
    )
    meta_tidy["column_name"] = meta_tidy["column_name"].astype(str).str.strip()
    return meta_raw, meta_tidy



def attach_and_apply_metadata(
    df: pd.DataFrame,
    meta_tidy: pd.DataFrame,
    label_fields: Iterable[str] = ("Indicator", "Label", "Omschrijving"),
    unit_fields: Iterable[str] = ("Eenheid", "Unit"),
    dtype_field: str = "dtype",
    auto_rename: bool = False,
    dayfirst: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    - Koppelt metadata aan df (in df.attrs['metadata']).
    - Past dtypes toe als 'dtype' in metadata aanwezig is.
    - (Optioneel) hernoemt kolommen o.b.v. eerste gevonden veld in label_fields.
    - Retourneert dict: {kolomnaam: {meta_field: waarde, ...}}.
    """
    # Alleen metadata voor kolommen die in df zitten
    meta_tidy = meta_tidy[meta_tidy["column_name"].isin(df.columns)].copy()
    meta_tidy.index = meta_tidy["column_name"]
    meta_tidy = meta_tidy.drop(columns=["column_name"])

    # Dictionary per kolom
    col_meta: Dict[str, Dict[str, Any]] = meta_tidy.to_dict(orient="index")

    # Dtypes toepassen
    if dtype_field in meta_tidy.columns:
        dtype_map = meta_tidy[dtype_field].dropna().to_dict()

        # Splits datetime van overige hints
        datetime_cols = [
            col
            for col, hint in dtype_map.items()
            if isinstance(hint, str) and hint.lower().startswith("datetime")
        ]
        other_dtypes = {col: hint for col, hint in dtype_map.items() if col not in datetime_cols}

        for col, hint in other_dtypes.items():
            if col not in df.columns or not isinstance(hint, str):
                continue
            d_lower = hint.lower()
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
                    # Onbekende hint -> probeer numeriek, anders laat staan
                    df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                # Veilige fallback
                df[col] = pd.to_numeric(df[col], errors="ignore")

        for col in datetime_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=dayfirst)

    # (Optioneel) hernoemen aan de hand van labelvelden
    if auto_rename:
        label_col = next((f for f in label_fields if f in meta_tidy.columns), None)
        if label_col:
            rename_map = meta_tidy[label_col].dropna().to_dict()
            rename_map = {
                k: v for k, v in rename_map.items() if str(v).strip().lower() not in ("nvt", "", "none")
            }
            df.rename(columns=rename_map, inplace=True)

    # Units en overige metadata bewaren in attrs
    df.attrs["metadata"] = col_meta
    return col_meta

def read_and_join_with_metadata(
    data_path: str,
    metadata_path: str,
    sep: str = ";",
    decimal: str = ",",
    encoding: str = "utf-8-sig",
    auto_rename: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """
    Leest data + metadata en koppelt ze.
    Retourneert: (df, meta_tidy, col_meta)
    """
    df = read_data_csv(data_path, sep=sep, decimal=decimal, encoding=encoding)
    _, meta_tidy = read_metadata_to_tidy(metadata_path, sep=sep, decimal=decimal, encoding=encoding, attribute_key="Attribuutnaam")

    # Eventuele kolommen in df die niet in metadata staan
    missing_meta = [c for c in df.columns if c not in set(meta_tidy["column_name"])]
    if missing_meta:
        print(f"[INFO] {len(missing_meta)} kolommen zonder metadata (eerste 10): {missing_meta[:10]}")

    col_meta = attach_and_apply_metadata(df, meta_tidy, auto_rename=auto_rename)
    return df, meta_tidy, col_meta

def join_cbs_with_klimaat(
    df_data: pd.DataFrame,
    df_klimaat: pd.DataFrame,
    *,
    strict_unique: bool = False,   # True => error bij duplicaten, False => dedupe
    verbose: bool = True
) -> pd.DataFrame:
    """
    Koppel df_data (links, heeft 'Codering') aan df_klimaat (rechts, op 'buurtcode2024').
    - Behoudt ALLE rijen uit df_data (LEFT JOIN).
    - Neemt ALLE kolommen van df_klimaat mee.
    - Normaliseert sleutels (strip + upper).
    - Controleert of buurtcode2024 uniek is; indien niet uniek:
          strict_unique=False → dedupe + waarschuwing
          strict_unique=True  → error
    
    Returns:
        df_join : volledige linkerkant + alle klimaatatlasvelden
    """

    # --- 1. Controles ---
    if "Codering" not in df_data.columns:
        raise KeyError("df_data mist sleutelkolom 'Codering'.")
    if "buurtcode2024" not in df_klimaat.columns:
        raise KeyError("df_klimaat mist sleutelkolom 'buurtcode2024'.")

    # --- 2. Kopieën maken ---
    left = df_data.copy()
    right = df_klimaat.copy()

    # --- 3. Normaliseer sleutels ---
    left["Codering"] = left["Codering"].astype(str).str.strip().str.upper()
    right["buurtcode2024"] = right["buurtcode2024"].astype(str).str.strip().str.upper()

    # --- 4. Controleer uniciteit klimaatsleutel ---
    dup_mask = right.duplicated(subset=["buurtcode2024"])
    dup_count = dup_mask.sum()

    if dup_count > 0:
        if strict_unique:
            dups = (
                right.loc[right.duplicated(subset=["buurtcode2024"], keep=False), "buurtcode2024"]
                .value_counts()
                .head(20)
            )
            raise ValueError(
                f"'buurtcode2024' is niet uniek in df_klimaat ({dup_count} duplicaten).\n"
                f"Voorbeelden:\n{dups}"
            )
        else:
            if verbose:
                print(f"[WAARSCHUWING] {dup_count} duplicaten in df_klimaat['buurtcode2024'] gevonden.")
                print("→ Dedupliceren (keep='first'), alle kolommen verder intact.")
            
            # Dedup: behoud eerste voorkomen, inclusief ALLE klimaatatlas kolommen
            right = right.sort_values("buurtcode2024").drop_duplicates(subset=["buurtcode2024"], keep="first")

    # --- 5. Definitieve LEFT JOIN ---
    df_join = left.merge(
        right,
        left_on="Codering",
        right_on="buurtcode2024",
        how="left",
        validate="m:1"
    )

    # --- 6. Logging ---
    if verbose:
        n_missing = df_join["buurtcode2024"].isna().sum()
        coverage = 1 - n_missing / len(df_join)

        print(f"[INFO] Join afgerond op 'Codering' ↔ 'buurtcode2024'.")
        print(f"[INFO] Dekking: {coverage:.3f}  | Niet-gematcht: {n_missing} rijen.")

        if n_missing > 0:
            print("Voorbeeld niet-gematchte codes (eerste 10):")
            print(df_join.loc[df_join["buurtcode2024"].isna(), "Codering"].head(10))

    return df_join