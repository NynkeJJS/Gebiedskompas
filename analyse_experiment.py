import os
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from factor_analyzer import FactorAnalyzer
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime


from config_experiment import(
 FIGURE_DIR,_RENDER_TMP, hti
) 


# -----------------------------------------------------
# PNG save functie (Werkt altijd op macOS + Python 3.14)
# -----------------------------------------------------

from config_experiment import FIGURE_DIR, _RENDER_TMP, hti

def save_figure(fig, filename, output_dir=FIGURE_DIR):

    os.makedirs(output_dir, exist_ok=True)

    html_path = os.path.join(_RENDER_TMP, filename.replace(".png", ".html"))
    fig.write_html(html_path, include_plotlyjs="cdn")

    # screenshot via Chrome
    hti.screenshot(
        html_file=html_path,
        save_as=filename,
        size=(1600, 1200)
    )

    tmp_png = os.path.join(_RENDER_TMP, filename)
    final_png = os.path.join(output_dir, filename)

    os.replace(tmp_png, final_png)

    # Schoonmaken
    if os.path.exists(html_path):
        os.remove(html_path)

    print(f"[PNG opgeslagen] {final_png}")
    return final_png


# -----------------------------------------------------
# Thema-boomstructuur
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
    new = {}
    for i, comp in enumerate(tree.keys(), 1):
        new[f"{prefix}{i}"] = tree[comp]
    return new


def print_loading_tree(tree):
    for comp, items in tree.items():
        print(f"{comp}: {len(items)} items")
        for it in items:
            print(f"   - {it}")


# -----------------------------------------------------
# PCA functies
# -----------------------------------------------------

def run_pca_threshold(df_scaled, variance_threshold=0.80):

    pca = PCA().fit(df_scaled)
    cum_var = np.cumsum(pca.explained_variance_ratio_)
    n = np.argmax(cum_var >= variance_threshold) + 1

    print(f"[PCA] {variance_threshold*100:.0f}% → {n} componenten")

    pca_final = PCA(n_components=n).fit(df_scaled)

    loadings = pd.DataFrame(
        pca_final.components_.T,
        index=df_scaled.columns,
        columns=[f"PC{i+1}" for i in range(n)]
    )

    return pca_final, loadings, cum_var


def plot_pca_variance(cum_var, output_dir):
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=cum_var, mode="lines+markers"))
    fig.update_layout(
        title="Cumulatieve variantie PCA",
        xaxis_title="Component",
        yaxis_title="Cumulatieve variantie",
        template="plotly_white"
    )
    save_figure(fig, "pca_cumulatieve_variantie.png", output_dir)
    return fig


def plot_loadings_heatmap(loadings, output_dir):
    fig = px.imshow(
        loadings,
        color_continuous_scale="RdBu",
        aspect="auto",
        title="PCA Loadings Heatmap"
    )
    save_figure(fig, "pca_loadings_heatmap.png", output_dir)
    return fig


# -----------------------------------------------------
# Factoranalyse functies
# -----------------------------------------------------

def run_fa(df_scaled, n_factors=None):
    if n_factors is None:
        n_factors = min(5, df_scaled.shape[1]-1)

    fa = FactorAnalyzer(n_factors=n_factors, rotation="oblimin").fit(df_scaled)

    loadings = pd.DataFrame(
        fa.loadings_,
        index=df_scaled.columns,
        columns=[f"F{i+1}" for i in range(n_factors)]
    )

    return fa, loadings


def plot_fa_heatmap(loadings, output_dir):
    fig = px.imshow(
        loadings,
        color_continuous_scale="RdBu",
        aspect="auto",
        title="FA Loadings Heatmap"
    )
    save_figure(fig, "fa_loadings_heatmap.png", output_dir)
    return fig


# -----------------------------------------------------
# Sunburst plot (PNG)
# -----------------------------------------------------

def sunburst_from_tree(tree, title, filename_png, output_dir=FIGURE_DIR):

    rows = []
    for comp, items in tree.items():
        for it in items:
            rows.append([comp, it])

    df = pd.DataFrame(rows, columns=["Component", "Item"])

    fig = px.sunburst(df, path=["Component", "Item"], title=title)

    save_figure(fig, filename_png, output_dir)
    return fig

# -----------------------------------------------------
# PDF RAPPORT GENERATOR
# -----------------------------------------------------

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

def generate_pdf_report(figures_dir, output_pdf_path):
    """
    Professioneel PDF-rapport met:
    - Titelblad
    - Hoofdstukken
    - PNG-grafieken, volledig passend op pagina
    - Geen tabellen
    """

    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    # ---------------------------------------------------
    # TITELBLAD
    # ---------------------------------------------------
    c.setFont("Helvetica-Bold", 30)
    c.drawString(50, height - 100, "Analyse Rapport Fryslân")

    c.setFont("Helvetica", 16)
    c.drawString(50, height - 150, "Kerncijfers, Klimaatdata, PCA & FA")

    c.setFont("Helvetica-Oblique", 12)
    c.drawString(50, height - 200, f"Gegenereerd op: {datetime.now().strftime('%d-%m-%Y %H:%M')}")

    c.showPage()

    # ---------------------------------------------------
    # Functie om figuren netjes te plaatsen
    # ---------------------------------------------------
    def add_image(path, title, chapter=False):
        if chapter:
            c.setFont("Helvetica-Bold", 22)
            c.drawString(50, height - 80, title)
            y_pos = height - 120
        else:
            y_pos = height - 100

        # Afbeelding inladen
        img = ImageReader(path)
        iw, ih = img.getSize()

        # Max breedte en hoogte binnen marges
        max_w = width - 100
        max_h = height - 200

        # Schaalfactor bepalen
        scale = min(max_w / iw, max_h / ih)

        new_w = iw * scale
        new_h = ih * scale

        # Gecentreerd plaatsen
        x = (width - new_w) / 2
        y = (height - new_h) / 2 - 40  # iets lager op de pagina

        c.drawImage(img, x, y, width=new_w, height=new_h)
        c.showPage()

    # ---------------------------------------------------
    # HOOFDSTUK 1 – PCA
    # ---------------------------------------------------
    add_image(os.path.join(figures_dir, "pca_cumulatieve_variantie.png"),
              "Hoofdstuk 1 – PCA: Cumulatieve variantie",
              chapter=True)

    add_image(os.path.join(figures_dir, "pca_loadings_heatmap.png"),
              "PCA Loadings Heatmap")

    add_image(os.path.join(figures_dir, "pca_sunburst.png"),
              "PCA Zonnestraalplot")

    # ---------------------------------------------------
    # HOOFDSTUK 2 – FA
    # ---------------------------------------------------
    add_image(os.path.join(figures_dir, "fa_loadings_heatmap.png"),
              "Hoofdstuk 2 – Factor Analyse Loadings",
              chapter=True)

    add_image(os.path.join(figures_dir, "fa_sunburst.png"),
              "Factor Analyse Zonnestraalplot")

    # ---------------------------------------------------
    # EINDE
    # ---------------------------------------------------
    c.save()
    print(f"📄 PDF-rapport opgeslagen: {output_pdf_path}")


# # -----------------------------------------------------
# # Thema-boomstructuur functies
# # -----------------------------------------------------

# def build_loading_tree(loadings, threshold=0.40):
#     absL = loadings.abs()
#     tree = {}
#     for feature in loadings.index:
#         primary = absL.loc[feature].idxmax()
#         if absL.loc[feature, primary] >= threshold:
#             tree.setdefault(primary, []).append(feature)
#     return tree


# def normalize_loading_labels(tree, prefix="PC"):
#     new_tree = {}
#     for i, comp in enumerate(tree.keys(), start=1):
#         new_comp = f"{prefix}{i}"
#         new_tree[new_comp] = tree[comp]
#     return new_tree


# def print_loading_tree(tree):
#     for comp, items in tree.items():
#         print(f"{comp}: {len(items)} items")
#         for it in items:
#             print(f"   - {it}")



# # -----------------------------------------------------
# # PCA & FA functies
# # -----------------------------------------------------

# def run_pca_threshold(df_scaled, variance_threshold=0.80):
#     """
#     PCA uitvoeren en automatisch aantal componenten kiezen
#     op basis van cumulatieve variantie (default = 80%).
#     """

#     #Fit PCA zonder max aantal componenten
#     pca = PCA().fit(df_scaled)

#     #Cumulatieve variantie
#     cum_var = np.cumsum(pca.explained_variance_ratio_)

#     #Aantal componenten dat threshold bereikt
#     n_components = np.argmax(cum_var >= variance_threshold) + 1

#     print(f"[PCA] Variantie-threshold = {variance_threshold*100:.0f}%")
#     print(f"[PCA] Geselecteerde componenten = {n_components}")
#     print(f"[PCA] Cumulatieve variantie = {cum_var[n_components-1]*100:.2f}%")

#     #PCA opnieuw fitten met gekozen aantal componenten
#     pca_final = PCA(n_components=n_components)
#     pca_final.fit(df_scaled)

#     #Loadings tabel
#     loadings = pd.DataFrame(
#         pca_final.components_.T,
#         index=df_scaled.columns,
#         columns=[f"PC{i+1}" for i in range(n_components)]
#     )

#     return pca_final, loadings, cum_var


# def run_fa(df_scaled, n_factors=None):
#     if n_factors is None:
#         n_factors = min(5, df_scaled.shape[1] - 1)

#     fa = FactorAnalyzer(n_factors=n_factors, rotation="oblimin")
#     fa.fit(df_scaled)

#     loadings = pd.DataFrame(
#         fa.loadings_,
#         index=df_scaled.columns,
#         columns=[f"F{i+1}" for i in range(n_factors)]
#     )
#     return fa, loadings



# # -----------------------------------------------------
# # Figuren opslaan
# # -----------------------------------------------------

# def plot_pca_variance(cum_var, output_dir, filename="pca_cumulatieve_variantie.png"):
#     fig = go.Figure()
#     fig.add_trace(go.Scatter(y=cum_var, mode="lines+markers"))
#     fig.update_layout(
#         title="Cumulatieve variantie PCA",
#         xaxis_title="Component",
#         yaxis_title="Cumulatieve variantie",
#         template="plotly_white"
#     )
#     save_figure(fig, filename, output_dir)
#     return fig

# def plot_loadings_heatmap(loadings, output_dir, filename="pca_loadings_heatmap.png"):
#     fig = px.imshow(
#         loadings,
#         color_continuous_scale="RdBu",
#         aspect="auto",
#         title="PCA Loadings Heatmap"
#     )
#     save_figure(fig, filename, output_dir)
#     return fig

# def plot_fa_heatmap(loadings, output_dir, filename="fa_loadings_heatmap.png"):
#     fig = px.imshow(
#         loadings,
#         color_continuous_scale="RdBu",
#         aspect="auto",
#         title="Factor Analysis Loadings Heatmap"
#     )
#     save_figure(fig, filename, output_dir)
#     return fig

# # -----------------------------------------------------
# # Zonnestraalplot
# # -----------------------------------------------------

# def sunburst_from_tree(tree, title, filename_png, output_dir):
#     rows = []
#     for comp, items in tree.items():
#         for it in items:
#             rows.append([comp, it])

#     df = pd.DataFrame(rows, columns=["Component", "Item"])
#     fig = px.sunburst(df, path=["Component", "Item"], title=title)
#     return save_figure(fig, filename_png, output_dir)
