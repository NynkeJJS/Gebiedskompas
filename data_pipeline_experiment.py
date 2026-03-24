import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler


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



def preprocess_numeric(df, impute_strategy="median", verbose=True):
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



def pca_check(df_data, min_rows_warning=10, verbose=True, impute_strategy="median"):
    """
    Wrapper voor preprocessing met extra checks voor PCA/FA.
    """
    df_num, df_imputed, df_scaled = preprocess_numeric(
        df_data,
        impute_strategy=impute_strategy,
        verbose=verbose
    )

    n_samples, n_features = df_scaled.shape
    if verbose:
        print(f"[Check] Geschaalde shape: {df_scaled.shape}")
        print(f"[Check] n_samples={n_samples}, n_features={n_features}")

        if n_samples < min_rows_warning:
            print(f"[Check] ⚠ Weinig observaties (n={n_samples})")

        if n_samples < n_features:
            print(
                f"[Check] ⚠ Meer variabelen ({n_features}) dan observaties ({n_samples}). "
                f"PCA max components = {n_samples}, FA max = {max(1, n_samples-1)}"
            )

    return df_num, df_scaled
