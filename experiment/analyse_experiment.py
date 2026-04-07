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


def generate_pdf_report(figures_dir, output_pdf_path, dq_summary):
    """
    Professioneel PDF-rapport met:
    - Titelblad
    - Hoofdstuk 0: Data kwaliteit
    - Hoofdstukken met PNG-grafieken (PCA en FA)
    - Geen tabellen
    - Perfect geschaalde figuren zonder afsnijden
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
    c.drawString(50, height - 200,
        f"Gegenereerd op: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )

    c.showPage()

    # ---------------------------------------------------
    # HOOFDSTUK 1 – Datakwaliteit
    # ---------------------------------------------------
    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, height - 80, "Hoofdstuk 1 – Datakwaliteit")

    c.setFont("Helvetica", 12)
    y = height - 130

    # Basisgegevens
    c.drawString(50, y, f"Aantal rijen: {dq_summary['n_rows']}")
    y -= 20
    c.drawString(50, y, f"Aantal numerieke kolommen: {dq_summary['n_cols']}")
    y -= 40

    # 1) Volledig missing
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"1. Kolommen met 100% missing ({dq_summary['n_full_missing']}):")
    y -= 25

    c.setFont("Helvetica", 11)
    if dq_summary["n_full_missing"] == 0:
        c.drawString(60, y, "Geen.")
        y -= 20
    else:
        for col in dq_summary["full_missing_cols"][:20]:
            c.drawString(60, y, f"- {col}")
            y -= 15
            if y < 80:
                c.showPage()
                y = height - 80

    c.showPage()

    # 2) Missing percentages
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 80, "2. Missing-percentage (excl. volledig missing) – Top 15")

    y = height - 120
    c.setFont("Helvetica", 11)

    for col, pct in dq_summary["non_full_missing_pct"].head(15).items():
        c.drawString(60, y, f"{col}: {pct:.2%}")
        y -= 15
        if y < 80:
            c.showPage()
            y = height - 80

    c.showPage()

    # 3) Zero-variantie
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 80, f"3. Zero-variantie kolommen ({dq_summary['n_zero_var']}):")

    y = height - 120
    c.setFont("Helvetica", 11)

    if dq_summary["n_zero_var"] == 0:
        c.drawString(60, y, "Geen.")
    else:
        for col in dq_summary["zero_var_cols"]:
            c.drawString(60, y, f"- {col}")
            y -= 15
            if y < 80:
                c.showPage()
                y = height - 80

    c.showPage()

    # 4) Extreem lage variatie
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 80,
                f"4. Kolommen met extreem lage variatie (<1e-6): {dq_summary['n_low_var']}")

    y = height - 120
    c.setFont("Helvetica", 11)

    if dq_summary["n_low_var"] == 0:
        c.drawString(60, y, "Geen.")
    else:
        for col in dq_summary["low_var_cols"][:25]:
            c.drawString(60, y, f"- {col}")
            y -= 15
            if y < 80:
                c.showPage()
                y = height - 80

    c.showPage()

    # 5) Verwijderde kolommen & resterende missings
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 80, "5. Overige datakwaliteit-statistieken")

    y = height - 120
    c.setFont("Helvetica", 11)

    c.drawString(60, y, f"Aantal verwijderde kolommen (volledig missing): {dq_summary['removed_cols']}")
    y -= 20

    c.drawString(60, y, f"Missende waarden NA imputatie: {dq_summary['remaining_missing']}")
    y -= 20

    if dq_summary["remaining_missing"] == 0:
        c.drawString(60, y, "✔ Alle missing values succesvol geïmpteerd.")
    else:
        c.drawString(60, y, "⚠ Er zijn nog missende waarden na imputatie!")

    c.showPage()
    # ---------------------------------------------------
    # HELPER FUNCTIE: FIGUUR PLAATSEN
    # ---------------------------------------------------
    def add_image(path, title, chapter=False):
        if not os.path.exists(path):
            return

        # Titel bovenaan pagina
        if chapter:
            c.setFont("Helvetica-Bold", 22)
            c.drawString(50, height - 80, title)
            margin_top = 140
        else:
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 80, title)
            margin_top = 120

        # Afbeelding inladen
        img = ImageReader(path)
        iw, ih = img.getSize()

        # Pagina marges
        margin_bottom = 60
        margin_side = 60

        avail_w = width - 2 * margin_side
        avail_h = height - margin_top - margin_bottom

        # Schaalfactor
        scale = min(avail_w / iw, avail_h / ih)

        new_w = iw * scale
        new_h = ih * scale

        # Gecentreerd plaatsen
        x = (width - new_w) / 2
        y = margin_bottom + (avail_h - new_h) / 2

        c.drawImage(img, x, y, width=new_w, height=new_h)
        c.showPage()

    # ---------------------------------------------------
    # HOOFDSTUK 2 – PCA
    # ---------------------------------------------------
    add_image(
        os.path.join(figures_dir, "pca_cumulatieve_variantie.png"),
        "Hoofdstuk 2 – PCA: Cumulatieve variantie",
        chapter=True
    )

    add_image(
        os.path.join(figures_dir, "pca_loadings_heatmap.png"),
        "PCA Loadings Heatmap"
    )

    add_image(
        os.path.join(figures_dir, "pca_sunburst.png"),
        "PCA Zonnestraalplot"
    )

    # ---------------------------------------------------
    # HOOFDSTUK 3 – Factoranalyse
    # ---------------------------------------------------
    add_image(
        os.path.join(figures_dir, "fa_loadings_heatmap.png"),
        "Hoofdstuk 3 – FA Loadings",
        chapter=True
    )

    add_image(
        os.path.join(figures_dir, "fa_sunburst.png"),
        "FA Zonnestraalplot"
    )

    # ---------------------------------------------------
    # EINDE RAPPORT
    # ---------------------------------------------------
    c.save()
    print(f"📄 PDF-rapport opgeslagen: {output_pdf_path}")