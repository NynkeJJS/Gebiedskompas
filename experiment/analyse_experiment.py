import os
import numpy as np
import pandas as pd
from pyparsing import warnings
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


# -----------------------------------------------------------------
# Parallel Analysis functie of aantal factoren bij FA te bepalen
# -----------------------------------------------------------------


def parallel_analysis_fa(
    df_scaled,
    n_iter: int = 200,
    percentile: float = 95,
    random_state: int = 0,
):
    """
    Parallel Analysis voor Factoranalyse.
    Bepaalt het maximale aantal factoren dat boven ruis uitstijgt.

    Parameters
    ----------
    df_scaled : pd.DataFrame
        Gestandaardiseerde data.
    n_iter : int
        Aantal random simulaties.
    percentile : float
        Percentiel van random eigenwaarden (meestal 95).
    """

    rng = np.random.default_rng(random_state)

    n_samples, n_features = df_scaled.shape

    # 1) Eigenwaarden van de echte data (correlatiematrix)
    corr = np.corrcoef(df_scaled.T)
    eig_data = np.linalg.eigvalsh(corr)[::-1]

    # 2) Eigenwaarden van random data
    rand_eigs = np.zeros((n_iter, n_features))

    for i in range(n_iter):
        rand = rng.standard_normal((n_samples, n_features))
        rand_corr = np.corrcoef(rand.T)
        rand_eigs[i] = np.linalg.eigvalsh(rand_corr)[::-1]

    # 3) Percentiel van random eigenwaarden
    eig_random = np.percentile(rand_eigs, percentile, axis=0)

    # 4) Aantal factoren = data > random
    n_factors = int(np.sum(eig_data > eig_random))

    return n_factors, eig_data, eig_random


# -----------------------------------------------------
# Factoranalyse functies
# -----------------------------------------------------


def run_fa_auto_stable(
    df_scaled,
    *,
    rotation: str = "oblimin",
    max_factors: int | None = None,
    min_factors: int = 2,
    verbose: bool = True,
):
    """
    Automatische factoranalyse met:
    - Parallel Analysis als bovengrens
    - aflopend aantal factoren
    - strikte stabiliteitscriteria
    - automatische fallback van ML → principal

    Retourneert
    ----------
    fa : FactorAnalyzer
    loadings : pd.DataFrame
    info : dict (gekozen methode, n_factors)
    """

    # --------------------------------------------------
    # 1. Parallel Analysis
    # --------------------------------------------------
    n_pa, eig_data, eig_rand = parallel_analysis_fa(df_scaled)

    start = min(n_pa, max_factors) if max_factors else n_pa

    if verbose:
        print(f"[FA] Parallel Analysis bovengrens: {n_pa}")
        print(f"[FA] Start bij {start} factoren")

    # --------------------------------------------------
    # 2. Interne helper: probeer FA
    # --------------------------------------------------
    def try_fa(n_factors: int, method: str):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            fa = FactorAnalyzer(
                n_factors=n_factors,
                rotation=rotation,
                method=method,
            )
            fa.fit(df_scaled)

            # Waarschuwingen analyseren
            messages = [str(x.message).lower() for x in w]
            bad = any(
                ("invalid value" in m or "converge" in m)
                for m in messages
            )

            if bad:
                raise RuntimeError(f"FA warning: {messages}")

            loadings = fa.loadings_

            if (
                np.isnan(loadings).any()
                or np.isinf(loadings).any()
            ):
                raise RuntimeError("NaN/inf in loadings")

            return fa, loadings

    # --------------------------------------------------
    # 3. Eerst proberen: ML‑FA
    # --------------------------------------------------
    last_error = None

    for k in range(start, min_factors - 1, -1):
        if verbose:
            print(f"[FA] ML‑FA proberen met {k} factoren…")

        try:
            fa, loadings = try_fa(k, method="ml")

            loadings_df = pd.DataFrame(
                loadings,
                index=df_scaled.columns,
                columns=[f"F{i+1}" for i in range(k)],
            )

            if verbose:
                print(f"[FA] ML‑FA stabiel bij {k} factoren")

            return fa, loadings_df, {
                "method": "ml",
                "n_factors": k,
                "pa_upper_bound": n_pa,
            }

        except Exception as e:
            last_error = e
            if verbose:
                print(f"[FA] ML‑FA afgekeurd ({k}): {e}")

    # --------------------------------------------------
    # 4. Fallback: principal FA
    # --------------------------------------------------
    if verbose:
        print("[FA] ML‑FA faalt volledig → overschakelen op principal FA")

    for k in range(start, min_factors - 1, -1):
        if verbose:
            print(f"[FA] Principal FA proberen met {k} factoren…")

        try:
            fa, loadings = try_fa(k, method="principal")

            loadings_df = pd.DataFrame(
                loadings,
                index=df_scaled.columns,
                columns=[f"F{i+1}" for i in range(k)],
            )

            if verbose:
                print(f"[FA] Principal FA stabiel bij {k} factoren")

            return fa, loadings_df, {
                "method": "principal",
                "n_factors": k,
                "pa_upper_bound": n_pa,
            }

        except Exception as e:
            last_error = e
            if verbose:
                print(f"[FA] Principal FA afgekeurd ({k}): {e}")

    # --------------------------------------------------
    # 5. Niets werkt
    # --------------------------------------------------
    raise RuntimeError(
        "Geen stabiele factoranalyse gevonden.\n"
        f"Laatst waargenomen probleem: {last_error}"
    )


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