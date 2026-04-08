import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler
from config_experiment import (EXCLUDE,
                               VERBOSE)

def vprint(msg: str):
    """Print alleen als VERBOSE=True."""
    if VERBOSE:
        print(msg)


def is_code_column(col: str) -> bool:
    """Herken GM/WK/BU codes (gebiedscodes)."""
    c = col.lower()
    return c.startswith("gm") or c.startswith("wk") or c.startswith("bu")


# =============================================
# DATA QUALITY CHECK
# =============================================

def report_data_quality(df, top_n=15, verbose=True):
    """Uitgebreide datakwaliteit-check vóór PCA."""

    df_num = df.select_dtypes(include="number")

    # Missing
    missing_pct = df_num.isna().mean()
    full_missing = missing_pct[missing_pct == 1.0]
    non_full_missing_pct = missing_pct[missing_pct < 1.0].sort_values(ascending=False)

    # Variantie
    variance = df_num.var(numeric_only=True)
    zero_var = variance[variance == 0].index.tolist()
    low_var  = variance[(variance < 1e-6) & (variance > 0)].index.tolist()

    # Maak ALTIJD de volledige dictionary aan
    dq = {
        "n_rows": df_num.shape[0],
        "n_cols": df_num.shape[1],

        "full_missing_cols": list(full_missing.index),
        "n_full_missing": len(full_missing),

        "non_full_missing_pct": non_full_missing_pct,

        "zero_var_cols": zero_var,
        "n_zero_var": len(zero_var),

        "low_var_cols": low_var,
        "n_low_var": len(low_var),

        # Deze worden later door pca_check() aangevuld
        "removed_cols": 0,
        "remaining_missing": None,
    }

    if verbose:
        vprint("\n======================")
        vprint(" DATA QUALITY CHECK")
        vprint("======================")
        vprint(f"Rijen: {dq['n_rows']}")
        vprint(f"Kolommen: {dq['n_cols']}")
        vprint(f"Zero variantie: {dq['zero_var_cols']}")
        vprint(f"Volledig missing: {dq['full_missing_cols']}")

    return dq

# =============================================
# PCA FEATURE SELECTIE (AUTOMATISCHE UITSUITING)
# =============================================

def select_pca_features(df: pd.DataFrame):
    """
    Selecteert numerieke PCA-variabelen en verwijdert:
    - ID/sleutels
    - GM/WK/BU codes
    - constanten
    """
    vprint("[PCA] Selecteer PCA-geschikte variabelen...")

    df_num = df.select_dtypes(include="number").copy()

    to_drop = set()
    
    # Verwijder dubbele kolommen (behoud eerste)
    if not df_num.columns.is_unique:        
        vprint("[PCA] Waarschuwing: dubbele kolomnamen gevonden → dedupliceren")        
        df_num = df_num.loc[:, ~df_num.columns.duplicated()]

    for col in df_num.columns:
        if col in EXCLUDE:
            to_drop.add(col)
        elif is_code_column(col):
            to_drop.add(col)
        elif df_num[col].nunique() <= 1:
            to_drop.add(col)

    if to_drop:
        vprint(f"[PCA] Drop {len(to_drop)} kolommen: {sorted(to_drop)}")
        df_num = df_num.drop(columns=sorted(to_drop))

    vprint(f"[PCA] Overblijvende PCA-variabelen: {df_num.shape[1]}")
    return df_num


# =============================================
# CLEAN + IMPUTE + SCALE
# =============================================

def clean_numeric(df, verbose=True):
    """Vervang inf → NaN en verwijder volledig-NaN kolommen."""
    df_num = df.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)
    nan_cols = df_num.columns[df_num.isna().all()]

    if verbose and len(nan_cols):
        vprint(f"[Clean] Drop volledig NaN: {list(nan_cols)}")

    return df_num.drop(columns=nan_cols)


def impute_numeric(df_num, strategy="knn", verbose=True):
    """Imputeer numerieke data via median/mean of KNN."""
    imputer = KNNImputer(n_neighbors=5) if strategy == "knn" else SimpleImputer(strategy=strategy)
    arr = imputer.fit_transform(df_num)

    df_imp = pd.DataFrame(arr, index=df_num.index, columns=df_num.columns)

    if verbose:
        vprint(f"[Impute] Missing na imputatie: {df_imp.isna().sum().sum()}")

    return df_imp


def scale_numeric(df_imp):
    """Z-score scaling voor PCA."""
    scaler = StandardScaler()
    arr = scaler.fit_transform(df_imp)
    return pd.DataFrame(arr, index=df_imp.index, columns=df_imp.columns)


# =============================================
# PCA PREPROCESSING PIPELINE (HOOFDFUNCTIE)
# =============================================

def pca_check(df_data, impute_strategy="knn", verbose=True):
    """
    End-to-end PCA-preprocessing + quality metrics.
    """
    # 1) Data quality
    dq = report_data_quality(df_data, verbose=verbose)

    # 2) Selecteer PCA variabelen
    df_pca = select_pca_features(df_data)

    # Aantal verwijderde kolommen (moet in PDF!)
    original = df_data.select_dtypes(include="number").shape[1]
    cleaned  = df_pca.shape[1]
    dq["removed_cols"] = original - cleaned

    # 3) Clean → Impute → Scale
    df_clean = clean_numeric(df_pca, verbose=verbose)
    df_imp   = impute_numeric(df_clean, strategy=impute_strategy, verbose=verbose)
    df_scaled = scale_numeric(df_imp)

    # Missing na imputatie (moet in PDF!)
    dq["remaining_missing"] = int(df_imp.isna().sum().sum())

    # PCA kolomnamen
    dq["pca_features"] = list(df_scaled.columns)

    return df_clean, df_scaled, dq