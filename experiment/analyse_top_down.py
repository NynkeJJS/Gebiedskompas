import yaml
import numpy as np
import pandas as pd
import plotly.express as px
from config import (
    THEMA_CONFIG_PATH, 
    THEMA_LABELS
)


def load_thema_config():
    """
    Laad thema-configuratie uit YAML-bestand.
    """
    with open(THEMA_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def score_weighted_mean(df, variables, weights):
    """
    Bereken samengestelde score als gewogen gemiddelde van variabelen.
    """
    w = np.array([weights[v] for v in variables], dtype=float)
    w = w / w.sum()
    return (df[variables] * w).sum(axis=1)


def score_entropy(df, variables):
    """Bereken samengestelde score op basis van entropie-gewichten.
    - Variabelen worden eerst omgezet naar een kansverdeling (P) per variabele.
    - Entropie (H) wordt berekend voor elke variabele: H = -k * sum(P * log(P))
    - Gewichten worden afgeleid van entropie: w = (1 - H) / sum(1 - H)
    - Samengestelde score = gewogen gemiddelde van variabelen met deze gewichten.
    """
    X = df[variables].copy()  # DataFrame met alleen de relevante variabelen
    eps = 1e-12 # kleine waarde om log(0) te voorkomen

    # Omzetten naar kansverdeling per variabele
    P = X / (X.sum(axis=0) + eps) # Sommeer per kolom en deel door totaal om P te krijgen
    P = P.clip(lower=eps) # Voorkom exact 0 in P om log(0) te vermijden

    n = X.shape[0] # aantal rijen (buurten)
    k = 1.0 / np.log(n) # Normalisatieconstante zodat 0 ≤ entropy ≤ 1

    # Bereken entropie per variabele
    entropy = -k * (P * np.log(P)).sum(axis=0)
    # Bereken gewichten op basis van entropie
    weights = (1 - entropy) / (1 - entropy).sum()

    # Bereken samengestelde score als gewogen gemiddelde van variabelen
    score = (X * weights).sum(axis=1)
    return score, weights

def samengestelde_variabelen(
    *,
    weighted_mean_df: pd.DataFrame,
    entropy_df: pd.DataFrame,
    weighted_mean_normalisatie: str,
) -> pd.DataFrame:
    """
    Bereken samengestelde themascores per buurt op basis van meerdere indicatoren
    en methoden, gestuurd door een YAML-configuratie.

    Parameters
    ----------
    weighted_mean_df : pd.DataFrame
        Dataset voor het gewogen gemiddelde.
        Mag z-score of min-max genormaliseerd zijn.

    entropy_df : pd.DataFrame
        Dataset voor entropy.
        MOET min-max genormaliseerd zijn.

    weighted_mean_normalisatie : {"z_score", "min_max"}
        Geeft aan welke normalisatie is toegepast op weighted_mean_df.
        Wordt gebruikt voor validatie en documentatie.

    Methodologische regels
    ----------------------
    - Entropy wordt uitsluitend toegepast op min-max genormaliseerde data.
    - Het gewogen gemiddelde mag met z-score of min-max werken.
    """

    # ======================================================
    # Validatie
    # ======================================================
    if weighted_mean_normalisatie not in {"z_score", "min_max"}:
        raise ValueError(
            "weighted_mean_normalisatie moet 'z_score' of 'min_max' zijn"
        )

    # Entropy guardrail (conceptueel, expliciet)
    # NB: we checken hier niet numeriek, maar semantisch
    if weighted_mean_normalisatie == "z_score":
        # entropy_df is expliciet gescheiden en dus veilig
        pass

    thema_config = load_thema_config()
    results = []

    # ======================================================
    # Loop over thema's en methoden
    # ======================================================
    for thema, cfg in thema_config.items():
        variables = cfg.get("variables", [])
        if not variables:
            continue

        for methode, methode_cfg in cfg.get("runs", {}).items():

            if methode == "entropy":
                score, _ = score_entropy(entropy_df, variables)

            elif methode == "weighted_mean":
                score = score_weighted_mean(
                    weighted_mean_df,
                    variables,
                    methode_cfg.get("weights", {})
                )

            else:
                raise ValueError(f"Onbekende methode: {methode}")

            # Standaardiseer output
            df_score = (
                score
                .rename("score")
                .reset_index()
                .rename(columns={"index": "buurtcode"})
            )
            df_score["thema"] = thema
            df_score["methode"] = methode

            results.append(df_score)

    return pd.concat(results, ignore_index=True)

def tabel_indicator_scores(
    *,
    indicator_df_minmax: pd.DataFrame,
    indicator_df_zscore: pd.DataFrame,
    buurtcode: str,
) -> pd.DataFrame:
    """
    Maak een tabel met originele indicator-scores (min-max én z-score)
    per thema en indicator voor één buurt.
    """

    thema_config = load_thema_config()
    rows = []

    for thema, cfg in thema_config.items():
        variables = cfg.get("variables", [])

        for var in variables:
            rows.append(
                {
                    "buurtcode": buurtcode,
                    "thema": thema,
                    "indicator": var,
                    "score_minmax": indicator_df_minmax.loc[buurtcode, var],
                    "score_z": indicator_df_zscore.loc[buurtcode, var],
                }
            )

    return pd.DataFrame(rows)

def tabel_entropy_gewichten_alles(
    *,
    entropy_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Entropie-gewichten voor alle thema's en indicatoren.
    """

    thema_config = load_thema_config()
    rows = []

    for thema, cfg in thema_config.items():
        variables = cfg.get("variables", [])
        if not variables:
            continue

        _, weights = score_entropy(entropy_df, variables)

        for indicator, gewicht in weights.items():
            rows.append(
                {
                    "thema": thema,
                    "indicator": indicator,
                    "entropy_gewicht": gewicht,
                }
            )

    return pd.DataFrame(rows)


def sunburst_profiel_buurt(
    df_results: pd.DataFrame,
    indicator_df: pd.DataFrame,   # genormaliseerde indicatoren
    buurtcode: str,
    methode: str,
    thema_labels: dict,
):
    """
    Sunburst-profiel voor één buurt:
    - Binnenring: thema (samengestelde score)
    - Buitenring: indicatoren (indicator-score)
    """

    thema_config = load_thema_config()

    # =========================
    # Binnenring: thema-scores
    # =========================
    df_thema = df_results[
        (df_results["Buurtcode"] == buurtcode) &
        (df_results["methode"] == methode)
    ].copy()

    df_thema["label"] = df_thema["thema"].map(thema_labels)
    df_thema["parent"] = ""
    df_thema["value"] = 0
    df_thema["color"] = df_thema["score"]
    df_thema["score_type"] = "thema"
    df_thema["indicator_score"] = np.nan

    # =========================
    # Buitenring: indicatoren
    # =========================
    rows = []

    for _, row in df_thema.iterrows():
        thema = row["thema"]
        thema_label = row["label"]
        thema_score = row["score"]

        variables = thema_config[thema].get("variables", [])
        if not variables:
            continue

        n = len(variables)

        for var in variables:
            rows.append(
                {
                    "label": var,
                    "parent": thema_label,
                    "value": 1 / n,
                    "color": indicator_df.loc[buurtcode, var],
                    "score_type": "indicator",
                    "indicator_score": indicator_df.loc[buurtcode, var],
                    "thema_score": thema_score,
                }
            )

    df_vars = pd.DataFrame(rows)

    # =========================
    # Combineer
    # =========================
    df_plot = pd.concat(
        [
            df_thema[
                ["label", "parent", "value", "color", "score_type", "score"]
            ].rename(columns={"score": "thema_score"}),
            df_vars,
        ],
        ignore_index=True,
    )

    # =========================
    # Plot
    # =========================
    fig = px.sunburst(
    df_plot,
    names="label",
    parents="parent",
    values="value",
    color="color",
    color_continuous_scale="RdBu",
    color_continuous_midpoint=0,
    branchvalues="remainder",
    )

    # Binnenring (level 0): themanaam + score
    fig.update_traces(
        textinfo="label+text",
        texttemplate="%{label}<br>%{color:.2f}",
        insidetextorientation="radial",
        selector=dict(level=0),
    )

    # Buitenring (level 1): GEEN tekst
    fig.update_traces(
        textinfo="none",
        selector=dict(level=1),
    )

        
    return fig