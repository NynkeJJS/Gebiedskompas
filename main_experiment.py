
import pandas as pd
import os
from config_experiment import OUTPUT_DIR, OUTPUT_DATA, OUTPUT_META

from functies_experiment import (
    get_metadata,
    get_provincie_gebieden,
    get_data_provincie,
    koppel_metadata,
    koppel_geo_info,
    sla_op, 
    lees_opgeslagen_data
)

from analyse_experiment import (
    preflight_check,
    run_pca,
    run_factor_analysis,
    factor_theme_map,
    build_factor_tree,
    print_factor_tree
)


def main():

    # ------------------------------------------------------
    # Data en metadata ophalen en voorbereiden
    # ------------------------------------------------------
    # print("Data inlezen...")
    # df_meta = get_metadata()
    # df_provincie = get_provincie_gebieden()
    # provincie_codes = df_provincie['Key'].tolist()
    # df_data = get_data_provincie(provincie_codes)
    # df_data = koppel_metadata(df_data, df_meta)
    # df_data = koppel_geo_info(df_data, df_provincie)
    # sla_op(df_data, df_meta)
    # print(f"\nKlaar! Shape: {df_data.shape}")
    # print(df_data.head())

    # ------------------------------------------------------
    # Data inlezen vanaf schijf (CSV)
    # ------------------------------------------------------
# ------------------------------------------------------
# Data inlezen vanaf schijf (CSV uit data/output)
# ------------------------------------------------------

    # Bouw paden op
    data_path = os.path.join(OUTPUT_DIR, OUTPUT_DATA)
    meta_path = os.path.join(OUTPUT_DIR, OUTPUT_META)

    print("Data vanaf schijf inlezen...")

    # Controleer of bestanden bestaan
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Kon {data_path} niet vinden. "
            f"Zorg dat je eerst hebt weggeschreven of pas OUTPUT_DIR/OUTPUT_DATA aan."
        )

    # Inlezen
    df_data = pd.read_csv(data_path, low_memory=False)
    df_meta = pd.read_csv(meta_path, low_memory=False) if os.path.exists(meta_path) else None

    print(f"Klaar! df_data shape: {df_data.shape}")
    print(df_data.head(3))

    # ------------------------------------------------------
    # PRECHECK EERST — alleen inspectie en keuzes bepalen
    # ------------------------------------------------------
    
    print("\n[Stap 0] Preflight check (imputeren + schalen + shape):")
    df_num, df_scaled = preflight_check(df_data, min_rows_warning=10)

    # → Op basis van deze output kies je bewust je aantallen:
    #    - Voor PCA laten we in deze main sklearn zelf bepalen (alle componenten) en kijken we naar cumulatieve variantie.
    #    - Voor FA kun je hier je n_factors kiezen. Start bijvoorbeeld met 4.
    n_factors = 4  # pas aan na je preflight-inzicht

    # ------------------------------------------------------
    # PCA
    # ------------------------------------------------------
    print("\n[Running PCA...")
    pca, pca_loadings, explained = run_pca(df_data)

    print("\nEerste PCA loadings:")
    print(pca_loadings.head())

    print("\nVerklaarde variantie (eerste 10 componenten):")
    print(explained[:10])

    # (optioneel) PCA-scores berekenen en opslaan/terugkoppelen:
    # from sklearn.preprocessing import StandardScaler
    # scores = pca.transform(df_scaled.values)
    # scores_df = pd.DataFrame(scores, index=df_scaled.index,
    #                          columns=[f"PC{i+1}" for i in range(scores.shape[1])])
    # scores_df.to_csv("data/output/pca_scores.csv", index=True)

    # ------------------------------------------------------
    # FACTORANALYSE
    # ------------------------------------------------------
    print("\nRunning Factor Analysis...")
    fa, fa_loadings = run_factor_analysis(df_data, n_factors=n_factors)

    print("\nFactor loadings (eerste variabelen):")
    print(fa_loadings.head())

    # (optioneel) Factor-scores:
    # try:
    #     fa_scores = fa.transform(df_scaled.values)  # sommige versies bieden transform()
    #     fa_scores_df = pd.DataFrame(fa_scores, index=df_scaled.index,
    #                                 columns=[f"F{i+1}" for i in range(fa_scores.shape[1])])
    #     fa_scores_df.to_csv("data/output/factor_scores.csv", index=True)
    # except Exception:
    #     pass  # transform() is niet in alle factor_analyzer-versies aanwezig


    print("fa_loadings.shape:", fa_loadings.shape)
    print("fa_loadings.index[:5]:", fa_loadings.index[:5].tolist())
    print("fa_loadings.columns[:5]:", fa_loadings.columns[:5].tolist())
    print(fa_loadings.head(3))

    # ------------------------------------------------------
    # Automatische thema‑indeling
    # ------------------------------------------------------

    print("\nThema‑indeling op basis van factor loadings...")
    thema_indeling = factor_theme_map(fa_loadings, threshold=0.40)

    print(thema_indeling.head())

    # (optioneel) wegschrijven:
    # thema_indeling.to_csv("data/output/thema_indeling.csv", header=True)


    # ------------------------------------------------------
    # Boomstructuur tonen
    # ------------------------------------------------------

    print("\nBoomstructuur van factoren:")
    factor_tree = build_factor_tree(fa_loadings, threshold=0.40)
    print_factor_tree(factor_tree)

# ------------------------------------------------------
# Uitvoeren main script
# ------------------------------------------------------
   

if __name__ == "__main__":
    main()