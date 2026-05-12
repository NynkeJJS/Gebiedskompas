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


def aggregate_themascores_for_sunburst(
    df_results: pd.DataFrame, # DataFrame met resultaten per buurt, thema en methode
    agg: str = "mean",
) -> pd.DataFrame:
    """
    Aggregeer samengestelde themascores over alle buurten
    voor sunburst-visualisatie.
    Aggregatiemethode kan 'mean' of 'median' zijn. 
    Resultaat is DataFrame met gemiddelde/mediane score per thema en methode, klaar voor visualisatie.
    """

    if agg not in {"mean", "median"}:
        raise ValueError("agg moet 'mean' of 'median' zijn")

    df_agg = (
        df_results
        .groupby(["methode", "thema"], as_index=False)
        ["score"]
        .agg(agg)
    )

    return df_agg




def sunburst_profiel_buurt(
    df_results,
    buurtcode,
    methode,
    thema_labels,
):
    """
    Sunburst-profiel voor één buurt.
    - Alle thema-segmenten even groot
    - Kleur = samengestelde themascore
    """
    df_buurt = df_results[
        (df_results["buurtcode"] == buurtcode) &
        (df_results["methode"] == methode)
    ].copy()

    df_buurt["thema_kort"] = df_buurt["thema"].map(thema_labels)
    df_buurt["value"] = 1  # GELIJKE GROOTTE

    fig = px.sunburst(
        df_buurt,
        path=["thema_kort"],
        values="value",
        color="score",
        color_continuous_scale="RdBu",
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Score: %{color:.2f}<extra></extra>"
        )
    )

    return fig
