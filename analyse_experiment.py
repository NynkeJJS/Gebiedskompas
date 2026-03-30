# analysis.py
import os
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from factor_analyzer import FactorAnalyzer
import plotly.express as px


# -----------------------------------------------------
# Thema-boomstructuur functies
# -----------------------------------------------------

def build_loading_tree(loadings, threshold=0.40):
    absL = loadings.abs()
    tree = {}
    for feature in loadings.index:
        primary = absL.loc[feature].idxmax()
        if absL.loc[feature, primary] >= threshold:
            tree.setdefault(primary, []).append(feature)
    return tree


def normalize_loading_labels(tree, prefix="PC"):
    new_tree = {}
    for i, comp in enumerate(tree.keys(), start=1):
        new_comp = f"{prefix}{i}"
        new_tree[new_comp] = tree[comp]
    return new_tree


def print_loading_tree(tree):
    for comp, items in tree.items():
        print(f"{comp}: {len(items)} items")
        for it in items:
            print(f"   - {it}")


# -----------------------------------------------------
# Zonnestraalplot
# -----------------------------------------------------

def sunburst_from_tree(tree, title, filename, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    rows = []
    for comp, items in tree.items():
        for it in items:
            rows.append([comp, it])

    df = pd.DataFrame(rows, columns=["Component", "Item"])
    fig = px.sunburst(df, path=["Component", "Item"], title=title)

    file_path = os.path.join(output_dir, filename)
    fig.write_html(file_path, include_plotlyjs="cdn")
    print(f"[Plot] Sunburst opgeslagen: {file_path}")

    return fig


# -----------------------------------------------------
# PCA & FA functies
# -----------------------------------------------------

def run_pca_threshold(df_scaled, variance_threshold=0.80):
    """
    PCA uitvoeren en automatisch aantal componenten kiezen
    op basis van cumulatieve variantie (default = 80%).
    """

    #Fit PCA zonder max aantal componenten
    pca = PCA().fit(df_scaled)

    #Cumulatieve variantie
    cum_var = np.cumsum(pca.explained_variance_ratio_)

    #Aantal componenten dat threshold bereikt
    n_components = np.argmax(cum_var >= variance_threshold) + 1

    print(f"[PCA] Variantie-threshold = {variance_threshold*100:.0f}%")
    print(f"[PCA] Geselecteerde componenten = {n_components}")
    print(f"[PCA] Cumulatieve variantie = {cum_var[n_components-1]*100:.2f}%")

    #PCA opnieuw fitten met gekozen aantal componenten
    pca_final = PCA(n_components=n_components)
    pca_final.fit(df_scaled)

    #Loadings tabel
    loadings = pd.DataFrame(
        pca_final.components_.T,
        index=df_scaled.columns,
        columns=[f"PC{i+1}" for i in range(n_components)]
    )

    return pca_final, loadings, cum_var


def run_fa(df_scaled, n_factors=None):
    if n_factors is None:
        n_factors = min(5, df_scaled.shape[1] - 1)

    fa = FactorAnalyzer(n_factors=n_factors, rotation="oblimin")
    fa.fit(df_scaled)

    loadings = pd.DataFrame(
        fa.loadings_,
        index=df_scaled.columns,
        columns=[f"F{i+1}" for i in range(n_factors)]
    )
    return fa, loadings
