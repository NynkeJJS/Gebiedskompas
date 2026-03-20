
from numpy import rint
import pandas as pd
import os
from config_experiment import INPUT_DIR, DATA_CSV, META_CSV, OUTPUT_DIR, OUTPUT_DATA, OUTPUT_META

from functies_experiment import (
    get_metadata,
    get_provincie_gebieden,
    get_data_provincie,
    koppel_metadata,
    koppel_geo_info,
    sla_op, 
    lees_opgeslagen_data,
    read_and_join_with_metadata,
    join_cbs_with_klimaat
)

from analyse_experiment import (
    normalize_factor_labels,
    pca_check,
    run_pca,
    run_factor_analysis,
    factor_theme_map,
    build_factor_tree,
    normalize_factor_labels,
    print_factor_tree
)


def main():

    # ------------------------------------------------------
    # Data en metadata kerncijfers buurt ophalen en voorbereiden
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
    # Klimaatatlasdata en metadata inlezen en koppelen
    # ------------------------------------------------------

    data_path = os.path.join(INPUT_DIR, DATA_CSV)
    metadata_path = os.path.join(INPUT_DIR, META_CSV)

    print(f"Data-bestand:      {data_path}")
    print(f"Metadata-bestand:  {metadata_path}")

    # Inlezen + koppelen
    df_klimaat, meta_tidy, col_meta = read_and_join_with_metadata(
        data_path,
        metadata_path,
        sep=";",          # pas aan naar "\t" indien tab-separated
        decimal=",",
        encoding="utf-8-sig",
        auto_rename=False # zet True om kolomnamen te vervangen door Indicator/Label
    )

    # Voorbeeld checks
    print("\n Overzicht metadata")
    print(meta_tidy.head(10))

    print("\n Voorbeeld metadata van F18ErnstigZ:")
    print(col_meta.get("F18ErnstigZ", {}))

    print("\n Dtype-overzicht (eerste 10 kolommen):")
    print(df_klimaat.dtypes.head(10))

    print("\n Data ingelezen en gekoppeld. Eerste 5 rijen:")
    print(df_klimaat.head())

    # Aantal kolommen met metadata vs. totaal
    meta_dict = df_klimaat.attrs.get("metadata", {})
    covered = len(set(df_klimaat.columns) & set(meta_dict.keys()))
    print(f"Kolommen met metadata: {covered}/{df_klimaat.shape[1]}")

    print("\n---- df_data columns ----")
    print(df_data.columns.tolist())

    print("\n---- df_data metadata columns ----")
    print(df_meta.columns.tolist())

    print("\n---- df_klimaat columns ----")
    print(df_klimaat.columns.tolist())

   
    # ------------------------------------------------------
    # Kerncijfers en Klimaatatlasdata koppelen
    # ------------------------------------------------------
    # Stel: df_data heeft 'Codering', df_meta heeft 'buurtcode2024' (en/of andere jaren)
    df_join = join_cbs_with_klimaat(
        df_data=df_data,
        df_klimaat=df_klimaat,
        strict_unique=False,   # duplicaten toestaan + dedupe
        verbose=True
    )

    print(df_join.shape)
    df_join.head()



    # ------------------------------------------------------
    # PRECHECK EERST — alleen inspectie en keuzes bepalen
    # ------------------------------------------------------
    
    print("\n Check (imputeren + schalen + shape):")
    df_num, df_scaled = pca_check(df_join, min_rows_warning=10)

    # → Op basis van deze output kies je bewust je aantallen:
    #    - Voor PCA laten we in deze main sklearn zelf bepalen (alle componenten) en kijken we naar cumulatieve variantie.
    #    - Voor FA kun je hier je n_factors kiezen. Start bijvoorbeeld met 4.
    n_factors = 10  # pas aan na je preflight-inzicht



    # ------------------------------------------------------
    # PCA
    # ------------------------------------------------------
    print("\n[Running PCA...")
    pca, pca_loadings, explained = run_pca(df_num, df_scaled)

    print("\nEerste PCA loadings:")
    print(pca_loadings.head())

    print("\nVerklaarde variantie (eerste 10 componenten):")
    print(explained[:10])

    # ------------------------------------------------------
    # FACTORANALYSE
    # ------------------------------------------------------
    print("\nRunning Factor Analysis...")
    fa, fa_loadings = run_factor_analysis(df_scaled, n_factors=n_factors)

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
    factor_tree = normalize_factor_labels(factor_tree)
    print_factor_tree(factor_tree)

# ------------------------------------------------------
# Uitvoeren main script
# ------------------------------------------------------
   

if __name__ == "__main__":
    main()