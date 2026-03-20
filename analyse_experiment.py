# analyse.py

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from factor_analyzer import FactorAnalyzer


# ------------------------------------------------------
# Data voorbereiden door missende waardes te imputeren en de variabelen te schalen
# Controle toevoegen om te waarschuwen als er weinig observaties zijn of als er meer variabelen dan observaties zijn
# ------------------------------------------------------

def pca_check(df_data, min_rows_warning=10):
    """Imputeer + schaal één keer, print shapes, en geef zowel df_num als X terug."""
    df_num = df_data.select_dtypes(include='number')
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler

    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(df_num)

    scaler = StandardScaler()
    X = scaler.fit_transform(X_imputed)

    n_samples, n_features = X.shape
    print(f"[Check] n_samples={n_samples}, n_features={n_features}")

    if n_samples < min_rows_warning:
        print(f"[Check] Waarschuwing: weinig observaties (n={n_samples})."
              " Overweeg agressiever imputeren/aggregatie.")
    if n_samples < n_features:
        print(f"[Check] Let op: meer variabelen ({n_features}) dan observaties ({n_samples}). "
              f"Maximaal aantal PCA‑componenten = {n_samples} en voor FA moet n_factors ≤ {max(1, n_samples-1)}.")

    # Handig: ook een geschaalde DataFrame teruggeven voor FA
    df_scaled = pd.DataFrame(X, columns=df_num.columns, index=df_num.index)
    return df_num, df_scaled


# ------------------------------------------------------
# PCA
# ------------------------------------------------------

def run_pca(df_num, df_scaled, output_dir="data/output"):

    X = df_scaled.values

    pca = PCA()  # laat sklearn zelf het aantal componenten bepalen
    pca.fit(X)

    explained = pca.explained_variance_ratio_

    # Plot cumulatieve variantie
    plt.figure(figsize=(10,5))
    plt.plot(explained.cumsum(), marker='o')
    plt.title("Cumulatieve verklaarde variantie")
    plt.xlabel("Aantal componenten")
    plt.ylabel("Cumulatieve variantie")
    plt.grid(True)

    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, "pca_cumulatieve_variantie.png"), dpi=150)
    plt.close()

    # Loadings met correct aantal componenten
    n_components = pca.n_components_
    loadings = pd.DataFrame(
        pca.components_.T,
        columns=[f"PC{i+1}" for i in range(n_components)],
        index=df_num.columns
    )
    loadings.to_csv(os.path.join(output_dir, "pca_loadings.csv"))
    return pca, loadings, explained


# ------------------------------------------------------
# Factoranalyse (EFA)
# ------------------------------------------------------

def run_factor_analysis(df_scaled, n_factors=4, output_dir="data/output"):

    n_samples, n_features = df_scaled.shape
    max_factors = max(1, min(n_features, n_samples - 1))
    if n_factors > max_factors:
        print(f"[FA] n_factors verlaagd van {n_factors} naar {max_factors} (beperkt door data).")
        n_factors = max_factors

    fa = FactorAnalyzer(n_factors=n_factors, rotation='varimax')
    fa.fit(df_scaled)  # let op: geschaalde, geimputeerde data

    loadings = pd.DataFrame(
        fa.loadings_,
        columns=[f"Factor{i+1}" for i in range(n_factors)],
        index=df_scaled.columns
    )

    os.makedirs(output_dir, exist_ok=True)
    loadings.to_csv(os.path.join(output_dir, "factor_loadings.csv"))
    return fa, loadings

# ------------------------------------------------------
# Automatische thema-indeling op basis van factor loadings
# ------------------------------------------------------

def factor_theme_map(loadings, threshold=0.4):
    mapping = {}
    for col in loadings.index:
        row = loadings.loc[col]
        factor = row.abs().idxmax()
        if abs(row[factor]) >= threshold:
            mapping[col] = factor
        else:
            mapping[col] = None
    return pd.Series(mapping, name="Thema")


def build_factor_tree(loadings, threshold=0.4):
    tree = {}
    for indicator in loadings.index:
        row = loadings.loc[indicator]
        factor = row.abs().idxmax()
        if abs(row[factor]) < threshold:
            continue
        tree.setdefault(factor, []).append(indicator)
    return tree


def normalize_factor_labels(tree):
    new_tree = {}
    for i, key in enumerate(sorted(tree.keys()), start=1):
        new_tree[f"Factor {i}"] = tree[key]
    return new_tree


def print_factor_tree(tree):
    for factor, indicators in tree.items():
        print(f"\n{factor}:")
        for ind in indicators:
            print(f"   - {ind}")