import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler

def report_data_quality(df, top_n=15, verbose=True):
    """
    Uitgebreide datakwaliteit-check vóór imputatie of scaling.
    Return: dictionary met alle kernresultaten voor PDF-rapport.
    """

    if not verbose:
        return None

    print("\n======================")
    print("📊 ALGEMENE DATA-INFORMATIE")
    print("======================")

    print(f"Aantal rijen       : {df.shape[0]}")
    print(f"Aantal kolommen    : {df.shape[1]}")

    df_num = df.select_dtypes(include='number')
    print(f"Numerieke kolommen : {df_num.shape[1]}")

    # -----------------------------
    # Missing analyse
    # -----------------------------
    missing_count = df_num.isna().sum()
    missing_pct = missing_count / len(df_num)

    # 1) volledig missing
    full_missing_cols = missing_pct[missing_pct == 1.0].sort_values(ascending=False)

    print("\n🔍 Kolommen die 100% missing zijn:")
    if len(full_missing_cols) > 0:
        print(full_missing_cols)
    else:
        print("Geen volledig missende kolommen.")

    # 2) overige kolommen
    non_full_missing_pct = missing_pct[missing_pct < 1.0]

    print("\n🔍 Missing-percentage van overige kolommen:")
    print(non_full_missing_pct.sort_values(ascending=False).head(top_n))


    # Variantie
    variance = df_num.var(numeric_only=True)
    zero_var_cols = variance[variance == 0].index.tolist()
    low_var_cols = variance[(variance < 1e-6) & (variance > 0)].index.tolist()

    print("\n⚠ Zero-variantie kolommen:")
    print(zero_var_cols if zero_var_cols else "Geen.")

    print("\n⚠ Extreem lage variatie (<1e-6):")
    print(low_var_cols[:top_n] if low_var_cols else "Geen.")

    print("\n— Data Quality Check klaar —\n")

    return {
        "n_rows": df_num.shape[0],
        "n_cols": df_num.shape[1],
        "full_missing_cols": list(full_missing_cols.index),
        "n_full_missing": len(full_missing_cols),
        "non_full_missing_pct": non_full_missing_pct.sort_values(ascending=False),
        "zero_var_cols": zero_var_cols,
        "n_zero_var": len(zero_var_cols),
        "low_var_cols": low_var_cols,
        "n_low_var": len(low_var_cols),
    }


def clean_numeric(df, verbose=True, drop_all_nan_cols=True):
    """
    Selecteert numerieke variabelen, vervangt inf met NaN,
    en dropt kolommen die volledig NaN zijn.
    """
    df_num = df.select_dtypes(include='number').replace([np.inf, -np.inf], np.nan)

    if drop_all_nan_cols:
        all_nan_cols = df_num.columns[df_num.isna().all(axis=0)]
        if verbose and len(all_nan_cols) > 0:
            print(f"[Clean] Drop {len(all_nan_cols)} volledig-NaN kolommen: {list(all_nan_cols)}")
        df_num = df_num.drop(columns=all_nan_cols)

    return df_num



def impute_numeric(df_num, strategy="median", verbose=True):
    """
    Imputeer kolommen met KNN of median/mean.
    """
    if strategy == "knn":
        imputer = KNNImputer(n_neighbors=5)
    else:
        imputer = SimpleImputer(strategy=strategy)

    X_imputed = imputer.fit_transform(df_num)

    try:
        kept_cols = imputer.get_feature_names_out(df_num.columns)
    except AttributeError:
        kept_cols = df_num.columns.to_numpy()

    df_imputed = pd.DataFrame(X_imputed, index=df_num.index, columns=kept_cols)

    if verbose:
        missing_after = df_imputed.isna().sum().sum()
        print(f"[Impute] Missing na imputatie: {missing_after}")

    return df_imputed



def scale_numeric(df_imputed):
    """
    Schaal numerieke data met StandardScaler (Z-score).
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(df_imputed)
    df_scaled = pd.DataFrame(X, index=df_imputed.index, columns=df_imputed.columns)
    return df_scaled



def preprocess_numeric(df, impute_strategy="knn", verbose=True):
    """
    Pipeline combineert:
    - clean
    - impute
    - scale
    """
    df_num = clean_numeric(df, verbose=verbose)
    df_imputed = impute_numeric(df_num, strategy=impute_strategy, verbose=verbose)
    df_scaled = scale_numeric(df_imputed)
    return df_num, df_imputed, df_scaled

def pca_check(df_data, min_rows_warning=10, verbose=True, impute_strategy="knn"):
    """
    Wrapper voor preprocessing met extra checks voor PCA/FA.
    Geeft behalve df_num en df_scaled nu óók uitgebreide dq_summary terug:
    - datakwaliteit uit report_data_quality
    - aantal verwijderde kolommen
    - aantal resterende missings na imputatie
    """

    # 1️⃣ Data kwaliteit rapporteren
    dq_summary = report_data_quality(df_data, verbose=verbose)

    # 2️⃣ Preprocessing pipeline
    df_num_clean = clean_numeric(df_data, verbose=verbose)

    # kolommen verwijderd?
    original_cols = df_data.select_dtypes(include='number').shape[1]
    cleaned_cols  = df_num_clean.shape[1]
    removed_cols  = original_cols - cleaned_cols

    # Imputeren
    df_imputed = impute_numeric(df_num_clean, strategy=impute_strategy, verbose=verbose)

    # missings NA imputatie
    remaining_missing = int(df_imputed.isna().sum().sum())

    # Continue met scaling
    df_scaled = scale_numeric(df_imputed)

    # 3️⃣ technische PCA checks
    n_samples, n_features = df_scaled.shape

    if verbose:
        print("\n======================")
        print("📏 CHECKS VOOR PCA")
        print("======================")
        print(f"[Check] Geschaalde shape    : {df_scaled.shape}")
        print(f"[Check] Aantal observaties  : {n_samples}")
        print(f"[Check] Aantal variabelen   : {n_features}")
        print(f"[Check] Verwijderde kolommen: {removed_cols}")
        print(f"[Check] Missings NA imputatie: {remaining_missing}")

    # 4️⃣ Voeg deze extra info toe aan dq_summary
    dq_summary["removed_cols"] = removed_cols
    dq_summary["remaining_missing"] = remaining_missing

    return df_num_clean, df_scaled, dq_summary