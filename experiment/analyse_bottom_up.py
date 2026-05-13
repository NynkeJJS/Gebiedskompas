import os
import numpy as np
import pandas as pd
import warnings
from sklearn.decomposition import PCA
from factor_analyzer import FactorAnalyzer
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime


from config import(
                                FIGURE_DIR,
                                _RENDER_TMP, 
                                hti, 
                                vprint,
                                VARIANCE_THRESHOLD
) 

"""
- Principel Component Analysis (PCA) is gebruikt om de globale structuur van de data te verkennen.
    - Aantal componenten is automatisch bepaald op basis van cumulatieve variantie (drempel 90%).
- Factoranalyse om latente (onderliggende) factoren te modelleren. 
    - Parallel Analysis om gebruikt om een theoretische bovengrens voor het aantal factoren vast te stellen.
    - De Factoranalyse (FA) is eerst uitgevoerd met Maximum Likelihood (ML) optimalisatie, vanwege de sterke statistische eigenschappen, 
        - Multivariate normaliteit en voldoende grote steekproef zijn aannames van ML, maar als deze niet voldaan zijn can ML instabiel worden (numerieke problemen, niet-convergeren).
    - Wanneer de ML Factoranalyse niet stabiel bleek te zijn is er automatisch een Principal Factoranalyse uitgevoerd. 
        - Principal Factoranalyse is robuuster en werkt vaak ook als ML faalt, maar heeft zwakkere statistische aannames.
        - Geen normaliteits- of steekproefgroottevereisten, maar minder krachtige statistische eigenschappen.
"""

# -----------------------------------------------------
# PNG save functie
# -----------------------------------------------------


def save_figure(fig, filename, output_dir=FIGURE_DIR):
    """
    Exporteert een Plotly-figuur naar PNG
    Gebruikt een tijdelijke HTML-render
    Maakt een headless browser screenshot
    Slaat het resultaat op in een vaste outputmap
    Ruimt tijdelijke bestanden netjes op
    """
    os.makedirs(output_dir, exist_ok=True)

    # HTML tijdelijk opslaan
    html_path = os.path.join(_RENDER_TMP, filename.replace(".png", ".html"))
    fig.write_html(html_path, include_plotlyjs="cdn")

    # Screenshot maken met HTML2Image (headless Chrome)
    hti.screenshot(
        html_file=html_path,
        save_as=filename,
        size=(1600, 1200)
    )

    # Verplaats van tijdelijke render-map naar definitieve output
    tmp_png = os.path.join(_RENDER_TMP, filename)
    final_png = os.path.join(output_dir, filename)
    os.replace(tmp_png, final_png) 

    # Opruimen
    if os.path.exists(html_path):
        os.remove(html_path)

    vprint(f"[PNG opgeslagen] {final_png}")
    return final_png


# -----------------------------------------------------
# Thema-boomstructuur
# -----------------------------------------------------

def build_loading_tree(loadings, threshold=0.4): 
    """
    Variabelen (features) toewijzen aan hun “belangrijkste” component of factor, 
    op basis van de sterkste loading, mits die loading groot genoeg is (threshold). 
    """
    
    # Absolute loadings
    absL = loadings.abs() 

    tree = {}
    for feature in loadings.index:
        # Component met hoogste absolute loading voor deze feature
        primary = absL.loc[feature].idxmax()
        # Alleen toewijzen als de loading boven de drempel ligt
        if absL.loc[feature, primary] >= threshold:
            # Toevoegen aan boomstructuur: component → lijst van features
            tree.setdefault(primary, []).append(feature)
    return tree


def normalize_loading_labels(tree, prefix):
    """
    Component- of factorlabels omzetten naar een vaste volgorde.
    """
    new = {}
    for i, comp in enumerate(tree.keys(), 1):
        new[f"{prefix}{i}"] = tree[comp]
    return new


def print_loading_tree(tree):
    """
    Boomstructuur van componenten/factoren en hun belangrijkste variabelen printen.
    """
    for comp, items in tree.items():
        print(f"{comp}: {len(items)} items")
        for it in items:
            print(f"   - {it}")


# -----------------------------------------------------
# PCA functies
# -----------------------------------------------------

def run_pca_threshold(df_scaled, variance_threshold=VARIANCE_THRESHOLD):
    """ 
    PCA uitvoeren en automatisch aantal componenten kiezen op basis van cumulatieve variantie. 
    De functie retourneert het PCA-model, de loadings en de cumulatieve variantie.
    """

    # Volledige PCA uitvoeren om cumulatieve variantie te berekenen
    pca = PCA().fit(df_scaled)
    # Cumulatieve variantie berekenen en bepalen hoeveel componenten nodig zijn voor de drempel
    cum_var = np.cumsum(pca.explained_variance_ratio_)
    n = np.argmax(cum_var >= variance_threshold) + 1 

    print(f"[PCA] {variance_threshold*100:.0f}% → {n} componenten")

    # Finale PCA met gekozen aantal componenten
    pca_final = PCA(n_components=n).fit(df_scaled)

    # Loadings in DataFrame-vorm met duidelijke labels
    loadings = pd.DataFrame(
        pca_final.components_.T, # Transponeren zodat variabelen als rijen en componenten als kolommen
        index=df_scaled.columns, # Variabelen als index
        columns=[f"PC{i+1}" for i in range(n)] 
    )

    return pca_final, loadings, cum_var


def plot_pca_variance(cum_var, output_dir, variance_threshold=VARIANCE_THRESHOLD):
    """ 
    Visualiseert de cumulatieve verklaarde variantie van de PCA-componenten. 
    """
    fig = go.Figure() 

    fig.add_trace(
        go.Scatter(
            x=list(range(1, len(cum_var) + 1)), # Componentnummers
            y=cum_var, # Cumulatieve variantie
            mode="lines+markers"
        )
    )

    fig.update_layout(
        title="Cumulatieve variantie PCA",
        xaxis_title="Component",
        yaxis_title="Cumulatieve variantie",
        template="plotly_white"
    )

    if variance_threshold is not None:
        fig.add_hline(
            y=variance_threshold, # Horizontale lijn bij de drempel
            line_dash="dash",
            annotation_text=f"{variance_threshold:.0%}",
            annotation_position="bottom right"
        )

    save_figure(fig, "pca_cumulatieve_variantie.png", output_dir)
    return fig


def plot_loadings_heatmap(loadings, output_dir):
    """    
    Visualiseert de PCA-loadings als een heatmap, waarbij per variabele wordt getoond hoe sterk deze bijdraagt aan elke PCA-component.    
    """    
    fig = px.imshow(
        loadings, # DataFrame met variabelen als rijen en componenten als kolommen
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
    df_scaled, # Gestandaardiseerde data voor FA
    n_iter: int = 200, # Aantal random simulaties voor de ruis-eigenwaarden
    percentile: float = 95, # Percentiel van random eigenwaarden als drempel
    random_state: int = 0,
):
    """
    Parallel Analysis voor Factoranalyse.
    Welke factoren verklaren meer variantie dan je zou verwachten door puur toeval?
    Bepaalt hoeveel factoren statistisch “echte structuur” bevatten,
    door eigenwaarden van de data te vergelijken met eigenwaarden uit willekeurige data.
    Alles boven de ruis → potentiële factor.

    Parallel Analysis geeft een bovengrens voor het aantal factoren (wat statistisch boven ruis uitstijgt), 
    maar dat aantal is geen garantie dat een factoranalyse met zoveel factoren ook convergeert, 
    stabiel is of inhoudelijk interpreteerbaar.
    """
    # Random generator met vaste seed voor reproduceerbaarheid
    rng = np.random.default_rng(random_state)

    # Data dimensies, rijen = samples, kolommen = features
    n_samples, n_features = df_scaled.shape

    # Bereken de eigenwaarden van de correlatiematrix van de geschaalde data.
    # Deze eigenwaarden representeren de hoeveelheid variantie per PCA-component
    # en bevatten zowel het echte signaal als de ruis.
    corr = np.corrcoef(df_scaled.T) # Correlatiematrix van de data
    eig_data = np.linalg.eigvalsh(corr)[::-1] # Eigenwaarden van de data, gesorteerd van hoog naar laag

    # Simuleer eigenwaarden van random data (alleen ruis)
    # Deze worden gebruikt als referentie om te bepalen welke PCA-componenten significant zijn ten opzichte van toeval.
    
    eig_random = np.zeros((n_iter, n_features)) # Matrix om eigenwaarden van random data op te slaan

    for i in range(n_iter):
        # Genereer random normaal verdeelde data met dezelfde dimensies
        rand = rng.standard_normal((n_samples, n_features)) 
        rand_corr = np.corrcoef(rand.T) 

        # Bereken en sorteer de eigenwaarden van de correlatiematrix (aflopend)
        eig_random[i] = np.linalg.eigvalsh(rand_corr)[::-1] 

    # Bepaal per component het gekozen percentiel van de random eigenwaarden
    # (bijv. 95e percentiel als conservatieve ruisdrempel)
    eig_random = np.percentile(eig_random, percentile, axis=0)

    # Aantal significante factoren: eigenwaarden van de echte data
    # die groter zijn dan die van de random (ruis) data
    n_factors = int(np.sum(eig_data > eig_random))

    return n_factors, eig_data, eig_random

# -----------------------------------------------------
# Factoranalyse functies
# -----------------------------------------------------

def try_fa(df_scaled, n_factors: int, method: str, rotation: str = "oblimin"):
    """
    Probeert een factoranalyse (FA) uit te voeren met een opgegeven methode
    en aantal factoren, en controleert of de oplossing numeriek stabiel is.

    De functie vangt waarschuwingen tijdens het fitten (zoals niet-convergeren
    of invalid values) en controleert of de resulterende loadings geen NaN- of
    oneindige waarden bevatten. 

    Methodes:
        - "ml": Maximum Likelihood FA (sterke statistische eigenschappen, maar gevoelig voor instabiliteit)
        - "principal": Principal Factor Analysis (robuster, maar zwakkere statistische aannames)

    Rotatatie:
        - "oblimin": oblique rotatie, waarbij factoren onderling gecorreleerd mogen zijn. Dit is de standaard aanname

    Bij instabiliteit wordt een RuntimeError opgegooid.
    """

    # Vang alle warnings op tijdens het fitten in w, zodat ook subtiele numerieke of convergentieproblemen niet gemist worden
    with warnings.catch_warnings(record=True) as w: 
        # Zet alle warnings op "always" zodat we ze kunnen bekijken, in plaats van dat ze worden onderdrukt of samengevoegd
        warnings.simplefilter("always")

        # Initialiseer het FactorAnalyzer-model met de opgegeven
        # methode, rotatie en het aantal factoren
        fa = FactorAnalyzer(
            n_factors=n_factors,
            rotation=rotation, 
            method=method,
        )

        # Fit het FA-model op de geschaalde inputdata
        fa.fit(df_scaled)

        # Verzamel alle waarschuwingsteksten
        messages = [str(x.message).lower() for x in w]

        # Controleer op bekende problematische signalen in warnings:
        # - 'invalid value' wijst vaak op numerieke instabiliteit
        # - 'converge' duidt op slechte of mislukte convergentie
        bad = any(
            ("invalid value" in m or "converge" in m)
            for m in messages
        )

        # Breek expliciet af als de FA-oplossing onbetrouwbaar lijkt
        if bad:
            raise RuntimeError(f"FA warning: {messages}")

        # Haal de factorloadings uit het gefitte model
        loadings = fa.loadings_

        # Extra veiligheidscheck: NaN- of oneindige waarden
        # betekenen vrijwel altijd een instabiele oplossing
        if (
            np.isnan(loadings).any()
            or np.isinf(loadings).any()
        ):
            raise RuntimeError("NaN/inf in loadings")

        # FA is succesvol gefit en heeft valide, stabiele loadings
        return fa, loadings


def run_fa_auto_stable(
    df_scaled,
    *,
    rotation: str = "oblimin", # Standaard rotatie waarbij factoren onderling gecorreleerd mogen zijn
    max_factors: int | None = None,
    min_factors: int = 2,
):
    """
    Voert automatisch een stabiele exploratieve factoranalyse (EFA) uit.

    Strategie:
    - Bepaal een bovengrens voor het aantal factoren via Parallel Analysis
    - Start bij dit maximum en verlaag het aantal factoren stapsgewijs
    - Vereis strikte numerieke en convergentiestabiliteit
    - Probeer eerst Maximum Likelihood (ML), met fallback naar principal FA
    - Gebruik één consistente rotatie (oblimin) voor alle pogingen

    Retourneert
    ----------
  
        Metadata over de gekozen oplossing (methode, n_factors, PA-bovengrens).
    """

    # --------------------------------------------------
    # Parallel Analysis
    # --------------------------------------------------
    # Bepaal het maximaal onderbouwde aantal factoren
    # via vergelijking met random (ruis) eigenwaarden
    n_pa, eig_data, eig_rand = parallel_analysis_fa(df_scaled)

    # Bepaal het startpunt:
    # - maximaal toegestaan door Parallel Analysis
    # - optioneel begrensd door max_factors
    start = min(n_pa, max_factors) if max_factors is not None else n_pa

    print(f"[FA] Parallel Analysis bovengrens: {n_pa}")
    print(f"[FA] Start bij {start} factoren")

    # --------------------------------------------------
    # Probeer eerst Maximum Likelihood FA
    # --------------------------------------------------
    # ML heeft sterke statistische eigenschappen, maar is gevoelig voor instabiliteit en niet-convergentie
    last_error = None

    # Loop aflopend om de meest doelmatige stabiele oplossing te vinden
    # We beginnen bij de maximale bovengrens en gaan omlaag tot een minimum (2 factoren)

    for k in range(start, min_factors - 1, -1):
        vprint(f"[FA] ML-FA proberen met {k} factoren…")

        try:
            # Probeer FA met ML-optimalisatie
            fa, loadings = try_fa(
                df_scaled,
                n_factors=k,
                method="ml",
                rotation=rotation,
            )

            # Zet loadings om naar een netjes gelabelde DataFrame
            loadings_df = pd.DataFrame(
                loadings,
                index=df_scaled.columns,
                columns=[f"F{i+1}" for i in range(k)],
            )

            vprint(f"[FA] ML-FA stabiel bij {k} factoren")

            # Eerste stabiele oplossing = direct teruggeven
            return fa, loadings_df, {
                "method": "ml",
                "n_factors": k,
                "rotation": rotation,
                "pa_upper_bound": n_pa,
            }

        except Exception as e:
            # Opslaan van het laatst waargenomen probleem
            last_error = e
            vprint(f"[FA] ML-FA afgekeurd ({k}): {e}")

    # --------------------------------------------------
    # Fallback naar principal factor analysis
    # --------------------------------------------------
    # Principal FA is robuuster en werkt vaak ook als ML faalt,
    # maar heeft zwakkere statistische aannames
    vprint("[FA] ML-FA faalt volledig → fallback naar principal FA")

    for k in range(start, min_factors - 1, -1):
        vprint(f"[FA] Principal FA proberen met {k} factoren…")

        try:
            fa, loadings = try_fa(
                df_scaled,
                n_factors=k,
                method="principal",
                rotation=rotation,
            )

            loadings_df = pd.DataFrame(
                loadings,
                index=df_scaled.columns,
                columns=[f"F{i+1}" for i in range(k)],
            )

            vprint(f"[FA] Principal FA stabiel bij {k} factoren")

            return fa, loadings_df, {
                "method": "principal",
                "n_factors": k,
                "rotation": rotation,
                "pa_upper_bound": n_pa,
            }

        except Exception as e:
            last_error = e
            vprint(f"[FA] Principal FA afgekeurd ({k}): {e}")

    # --------------------------------------------------
    # Geen enkele configuratie is stabiel
    # --------------------------------------------------
    # Expliciet falen met het laatst gedetecteerde probleem
    raise RuntimeError(
        "Geen stabiele factoranalyse gevonden.\n"
        f"Laatst waargenomen probleem: {last_error}"
    )

def plot_fa_heatmap(loadings_df, output_dir):
    """
    Visualiseert de factorloadings van een factoranalyse als heatmap
    en slaat de figuur op.
    """
    fig = px.imshow(
        loadings_df,
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
    """ 
    Maakt een sunburst-visualisatie van een hiërarchische structuur    
    (component → items) en slaat de figuur op als PNG. 
    """
    # Zet de boomstructuur om in een DataFrame met kolommen: Component, Item
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
    - Hoofdstuk 1: Data kwaliteit
    - Hoofdstukken met PNG-grafieken (PCA en FA)
    - Geen tabellen
    - Perfect geschaalde figuren zonder afsnijden
    """

    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

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
    # TITELBLAD
    # ---------------------------------------------------
    c.setFont("Helvetica-Bold", 30)
    c.drawString(50, height - 100, "Analyse Rapport Fryslân")

    c.setFont("Helvetica", 16)
    c.drawString(50, height - 150, "Kerncijfers CBS, Klimaatdata, PCA & FA")

    c.setFont("Helvetica-Oblique", 12)
    c.drawString(50, height - 200,
        f"Gegenereerd op: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )

    c.showPage()

    # ---------------------------------------------------
    # HOOFDSTUK 1 – Datakwaliteit
    # ---------------------------------------------------
    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, height - 80, "Hoofdstuk 1 - Datakwaliteit")

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
    c.drawString(50, height - 80, "2. Missing-percentage (excl. volledig missing) - Top 15")

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
    # HOOFDSTUK 2 – PCA
    # ---------------------------------------------------
    add_image(
        os.path.join(figures_dir, "pca_cumulatieve_variantie.png"),
        "Hoofdstuk 2 - PCA: Cumulatieve variantie",
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
        "Hoofdstuk 3 - FA Loadings",
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
    print(f"PDF-rapport opgeslagen: {output_pdf_path}")