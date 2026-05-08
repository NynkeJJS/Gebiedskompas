import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from config import (
    EXCLUDE,
    vprint
)


def is_code_column(col: str) -> bool:
    """
    Herken GM/WK/BU codes (gebiedscodes).
    """
    c = col.lower()
    return c.startswith("gm") or c.startswith("wk") or c.startswith("bu")


# =============================================
# DATA QUALITY CHECK
# =============================================

def report_data_quality(df, top_n=15):
    """
    Uitgebreide datakwaliteit-check vóór analyses.
    """

    # Selecteer alleen numerieke kolommen.
    df_num = df.select_dtypes(include="number").copy()


    # Missing
    missing_pct = df_num.isna().mean() # berekent percentage missing per kolom
    full_missing = missing_pct[missing_pct == 1.0] 
    non_full_missing_pct = missing_pct[missing_pct < 1.0].sort_values(ascending=False) 

    # Variantie
    variance = df_num.var(numeric_only=True) # berekent variantie per kolom
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

        # Deze worden later door check aangevuld
        "removed_cols": 0,
        "remaining_missing": None,
    }

    vprint("\n======================")
    vprint(" DATA QUALITY CHECK")
    vprint("======================")
    vprint(f"Rijen: {dq['n_rows']}")
    vprint(f"Kolommen: {dq['n_cols']}")
    vprint(f"Zero variantie: {dq['zero_var_cols']}")
    vprint(f"Volledig missing: {dq['full_missing_cols']}")

    return dq

# =============================================
# FEATURE SELECTIE (AUTOMATISCHE UITSUITING)
# =============================================

def select_features(df: pd.DataFrame):
    """
    Deze functie selecteert geschikte numerieke variabelen uit een DataFrame en 
    verwijdert kolommen die niet bruikbaar zijn voor statistische analyse of modellering 
    De functie sluit automatisch de volgende typen kolommen uit:
    - ID/sleutels
    - GM/WK/BU codes
    - constanten
    """
    vprint("Selecteer geschikte variabelen...")

    # Selecteer alleen numerieke kolommen 
    df_num = df.select_dtypes(include="number").copy()

    to_drop = set()
    
    # Verwijder dubbele kolommen 
    if not df_num.columns.is_unique:        
        vprint("Waarschuwing: dubbele kolomnamen gevonden → dedupliceren")        
        df_num = df_num.loc[:, ~df_num.columns.duplicated()] # behoud eerste keer een kolomnaam, verwijder volgende duplicaten


    for col in df_num.columns:
        # Kolommen die aan één van deze voorwaarden voldoen, worden toegevoegd aan to_drop.
        if col in EXCLUDE:
            # ID/sleutelkolommen
            to_drop.add(col)
        elif is_code_column(col):
            # GM/WK/BU codes
            to_drop.add(col)
        elif df_num[col].nunique() <= 1:
            # Constante waarden
            to_drop.add(col)

    if to_drop:
        vprint(f"Drop {len(to_drop)} kolommen: {sorted(to_drop)}")
        df_num = df_num.drop(columns=sorted(to_drop))

    vprint(f"Overblijvende variabelen: {df_num.shape[1]}")
    return df_num


# =============================================
# CLEAN + IMPUTE + SCALE
# =============================================

def clean_numeric(df):
    """
    Vervang inf → NaN en verwijder volledig-NaN kolommen.
    """
    df_num = df.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)
    nan_cols = df_num.columns[df_num.isna().all()] # kolommen waar alle waarden NaN zijn

    vprint(f"[Clean] Drop volledig NaN: {list(nan_cols)}")

    return df_num.drop(columns=nan_cols)


def impute_numeric(df_num, strategy="median"):
    """
    Imputeer numerieke data via KNN of median.
    """
    imputer = KNNImputer(n_neighbors=5) if strategy == "knn" else SimpleImputer(strategy=strategy) # KNN is default, maar kan worden aangepast naar 'strategy' 
    arr = imputer.fit_transform(df_num)

    df_imp = pd.DataFrame(arr, index=df_num.index, columns=df_num.columns) # DataFrame terugvormen met originele index en kolomnamen

    vprint(f"[Impute] Missing na imputatie: {df_imp.isna().sum().sum()}") # Totaal aantal missing in de gehele dataframe (gesommeerd over alle kolommen)

    return df_imp


def scale_zscore(df_imp: pd.DataFrame
                 ) -> pd.DataFrame:
    """
    Z-score scaling: (x - mean) / std
    """
    scaler = StandardScaler()
    arr = scaler.fit_transform(df_imp)

    return pd.DataFrame(
        arr,
        index=df_imp.index,
        columns=df_imp.columns,
    )


def scale_minmax(
                df_imp: pd.DataFrame,
                feature_range: tuple = (0, 1),
                ) -> pd.DataFrame:
    """
    Min-max scaling naar opgegeven bereik (default 0-1)
    """
    scaler = MinMaxScaler(feature_range=feature_range)
    arr = scaler.fit_transform(df_imp)

    return pd.DataFrame(
        arr,
        index=df_imp.index,
        columns=df_imp.columns,
    )


# =============================================
# PREPROCESSING PIPELINE (HOOFDFUNCTIE)
# =============================================
def data_check(df_data, impute_strategy="knn"):
    """
    Preprocessing pipeline die de volgende stappen uitvoert:
    1. Data quality check (missing, variance)
    2. Feature selectie (automatische uitsluiting van ID/sleutels, codes, constanten)
    3. Clean (inf → NaN) + Impute (KNN of median)
    4. Scaling (z-score en min-max)


    Returns:
    - df_clean: opgeschoonde numerieke data
    - df_scaled_z: z-score geschaalde data (PCA / FA)
    - df_scaled_minmax: min-max geschaalde data (entropie)
    - dq: data quality samenvatting
    """
    # ======================================================
    # 1. Data quality
    # ======================================================
    dq = report_data_quality(df_data)

    # ======================================================
    # 2. Feature selectie
    # ======================================================
    df_analyse = select_features(df_data)

    original = df_data.select_dtypes(include="number").shape[1] # Aantal oorspronkelijke numerieke kolommen
    cleaned = df_analyse.shape[1]
    dq["removed_cols"] = original - cleaned # Aantal verwijderde kolommen tijdens feature selectie

    # ======================================================
    # 3. Clean → Impute
    # ======================================================
    df_clean = clean_numeric(df_analyse) # Volledige NaN kolommen worden hier verwijderd, overige NaN blijven staan voor imputatie
    df_imp = impute_numeric(df_clean, strategy=impute_strategy) # KNN of median imputatie (default KNN)

    dq["remaining_missing"] = int(df_imp.isna().sum().sum()) # Totaal aantal missing na imputatie (zou 0 moeten zijn bij KNN/median)

    # ======================================================
    # 4. Scaling (twee varianten)
    # ======================================================
    df_scaled_z = scale_zscore(df_imp) # Z-score scaling (voor PCA / FA en gewogen gemiddelden) 
    df_scaled_minmax = scale_minmax(df_imp) # Min-max scaling (voor entropie, omdat deze gevoelig is voor schaalverschillen)

    # ======================================================
    # 5. Metadata voor downstream analyses
    # ======================================================
    dq["analyse_features"] = list(df_scaled_z.columns) # Overzicht van de variabelen die uiteindelijk in de analyses worden gebruikt (na selectie, clean, impute)
    dq["n_features"] = df_scaled_z.shape[1] # Aantal variabelen dat uiteindelijk in de analyses wordt gebruikt

    return df_clean, df_scaled_z, df_scaled_minmax, dq
