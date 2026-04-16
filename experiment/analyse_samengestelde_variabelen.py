import yaml
import numpy as np
import pandas as pd
import plotly.express as px
from config import (
    THEMA_CONFIG_PATH, 
    THEMA_LABELS
)


def load_thema_config():
    with open(THEMA_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def score_weighted_mean(df, variables, weights):
    w = np.array([weights[v] for v in variables], dtype=float)
    w = w / w.sum()
    return (df[variables] * w).sum(axis=1)


def score_entropy(df, variables):
    X = df[variables].copy()
    eps = 1e-12

    P = X / (X.sum(axis=0) + eps)
    P = P.clip(lower=eps)

    n = X.shape[0]
    k = 1.0 / np.log(n)

    entropy = -k * (P * np.log(P)).sum(axis=0)
    weights = (1 - entropy) / (1 - entropy).sum()

    score = (X * weights).sum(axis=1)
    return score, weights


def samengestelde_variabelen(weighted_mean, entropy):
    """
    Combineert indicatoren tot samengestelde scores per thema.
    
    Parameters
    ----------
    weighted_mean : pd.DataFrame
        Dataset met z-score geschaalde variabelen (voor weighted mean).
    entropy : pd.DataFrame
        Dataset met min-max geschaalde variabelen (voor entropy).
    
    Returns
    -------
    pd.DataFrame
        Tabel met kolommen:
        [buurtcode, thema, methode, score]
    """
    thema_config = load_thema_config()
    results = []

    for thema, cfg in thema_config.items():
        variables = cfg.get("variables", [])
        if not variables:
            continue

        for methode, methode_cfg in cfg.get("runs", {}).items():

            if methode == "entropy":
                score, _ = score_entropy(entropy, variables)

            elif methode == "weighted_mean":
                score = score_weighted_mean(
                    weighted_mean,
                    variables,
                    methode_cfg.get("weights", {})
                )

            else:
                raise ValueError(f"Onbekende methode: {methode}")

            df_score = score.rename("score").reset_index()
            df_score = df_score.rename(columns={"index": "buurtcode"})
            df_score["thema"] = thema
            df_score["methode"] = methode
            results.append(df_score)

    return pd.concat(results, ignore_index=True)


def aggregate_themascores_for_sunburst(
    df_results: pd.DataFrame,
    agg: str = "mean",
) -> pd.DataFrame:
    """
    Aggregeer samengestelde themascores over alle buurten
    voor sunburst-visualisatie (optie 1).

    Parameters
    ----------
    df_results : DataFrame
        Kolommen: [buurtcode, thema, methode, score]
    agg : str
        'mean' of 'median'

    Returns
    -------
    DataFrame met kolommen:
        [methode, thema, score]
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


import plotly.express as px

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
