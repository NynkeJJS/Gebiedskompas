
from numpy import rint
import pandas as pd
import os
from config_experiment import INPUT_DIR, DATA_CSV, META_CSV, OUTPUT_DIR, OUTPUT_DATA, OUTPUT_META

from data_inlezen_experiment import (
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

from data_pipeline_experiment import pca_check

from analyse_experiment import (
    run_pca_threshold,
    run_fa,
    build_loading_tree,
    normalize_loading_labels,
    print_loading_tree,
    sunburst_from_tree
)


def main():

    # ------------------------------------------------------
    # Data en metadata kerncijfers buurt ophalen en voorbereiden
    # ------------------------------------------------------
    print("Data inlezen...")
    df_meta = get_metadata()
    df_provincie = get_provincie_gebieden()
    provincie_codes = df_provincie['Key'].tolist()
    df_data = get_data_provincie(provincie_codes)
    df_data = koppel_metadata(df_data, df_meta)
    df_data = koppel_geo_info(df_data, df_provincie)
    sla_op(df_data, df_meta)
    print(f"\nKlaar! Shape: {df_data.shape}")
    print(df_data.head())

    # ------------------------------------------------------
    # Data inlezen vanaf schijf
    # ------------------------------------------------------
    df_data, df_meta = lees_opgeslagen_data(
        output_dir=OUTPUT_DIR,
        output_data=OUTPUT_DATA,
        output_meta=OUTPUT_META,
        verbose=True
    )


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

    df_join = join_cbs_with_klimaat(
        df_data=df_data,
        df_klimaat=df_klimaat,
        strict_unique=False,   # duplicaten toestaan + dedupe
        verbose=True
    )

    print(df_join.shape)
    df_join.head()

    # ------------------------------------------------------
    # Data pipeline: clean, impute, scale
    # ------------------------------------------------------
    
    print("\n Check (imputeren + schalen + shape):")
    df_num, df_scaled = pca_check(df_join, verbose=True, impute_strategy="median")
    # → Op basis van deze output kies je bewust je aantallen:
    #    - Voor PCA laten we in deze main sklearn zelf bepalen (alle componenten) en kijken we naar cumulatieve variantie.
    #    - Voor FA kun je hier je n_factors kiezen. Start bijvoorbeeld met 4.
    n_factors = 10  # pas aan na je preflight-inzicht
    variance_threshold=0.90


    # ------------------------------------------------------
    # PCA
    # ------------------------------------------------------
    print("\n[Running PCA...")
    pca, pca_loadings, cum_var = run_pca_threshold(    
        df_scaled,    
        variance_threshold=0.80 
    )
    pca_tree = build_loading_tree(pca_loadings, threshold=0.40)
    pca_tree = normalize_loading_labels(pca_tree, prefix="PC")

    print("\n--- PCA Boomstructuur ---")
    print_loading_tree(pca_tree)

    sunburst_from_tree(pca_tree, "PCA Zonnestraalplot", "pca_sunburst.html")

    # -------------------------------------------------
    # Factoranalyse
    # -------------------------------------------------
    fa, fa_loadings = run_fa(df_scaled)

    fa_tree = build_loading_tree(fa_loadings, threshold=0.40)
    fa_tree = normalize_loading_labels(fa_tree, prefix="FA")

    print("\n--- FA Boomstructuur ---")
    print_loading_tree(fa_tree)

    sunburst_from_tree(fa_tree, "FA Zonnestraalplot", "fa_sunburst.html")


# ------------------------------------------------------
# Uitvoeren main script
# ------------------------------------------------------
   

if __name__ == "__main__":
    main()