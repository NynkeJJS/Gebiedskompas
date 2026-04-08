from config_experiment import (
    FIGURE_DIR,
    PDF_PATH,
    KERNCIJFERS_DATA, 
    KERNCIJFERS_META, 
    KLIMAAT_DATA_CSV, 
    KLIMAAT_META_CSV,
)

from data_inlezen_experiment import (
    vprint,
    get_metadata,
    get_provincie_gebieden,
    get_data_provincie,
    metadata_label_map,
    koppel_geo_info,
    sla_op, 
    lees_opgeslagen_data,
    read_data_csv,
    read_and_join_with_metadata,
    controleer_ahn_metadata,
    maak_suffix_tabel,
    maak_gelabelde_kopie_df_data,
    maak_gelabelde_kopie_df_klimaat,
    join_cbs_with_klimaat
)

from data_pipeline_experiment import (
    pca_check
)

from analyse_experiment import (
    plot_fa_heatmap,
    plot_pca_variance,
    plot_loadings_heatmap,
    run_pca_threshold,
    run_fa_auto_stable,
    build_loading_tree,
    normalize_loading_labels,
    print_loading_tree,
    sunburst_from_tree,
    generate_pdf_report
)


def main():

    # ------------------------------------------------------
    # Data en metadata kerncijfers buurt ophalen en voorbereiden
    # ------------------------------------------------------
    print("Data inlezen...")
    df_meta = get_metadata()                   # DataFrame
    df_meta_dict = metadata_label_map(df_meta)         # dict

    df_provincie = get_provincie_gebieden()
    provincie_codes = df_provincie['Key'].tolist()
    df_data = get_data_provincie(provincie_codes)

    df_data = koppel_geo_info(df_data, df_provincie)

    sla_op(df_data, df_meta)               
    print(f"\nKlaar! Shape kerncijfers: {df_data.shape}")
    vprint(df_data.head())

    # ------------------------------------------------------
    # Data en metadata kerncijfers buurt ophalen en voorbereiden met ETL
    # ------------------------------------------------------
    # run python cbs_data_ophalen_experiment.py in de terminal om een enriched json-bestand te krijgen met data + metadata gekoppeld. 
    

    # ------------------------------------------------------
    # Data inlezen vanaf schijf
    # ------------------------------------------------------
    df_data, df_meta = lees_opgeslagen_data(
        data_path=KERNCIJFERS_DATA,
        meta_path=KERNCIJFERS_META,
    )


    # ------------------------------------------------------
    # Klimaatatlasdata en metadata inlezen en koppelen
    # ------------------------------------------------------

    # MetadataKlimaateffectatlas_KEA_2025_12_v3.csv kan extra informatie bevatten over de indicatoren, maar kan niet eenvoudig gekoppeld worden.

    print(f"Data-bestand:      {KLIMAAT_DATA_CSV}")
    print(f"Metadata-bestand:  {KLIMAAT_META_CSV}")

    # Data en metadata inlezen ter controle + AHN-overzicht maken
    df_klimaat = read_data_csv(
        path=KLIMAAT_DATA_CSV
    )

    df_ahn_overzicht = maak_suffix_tabel(df_klimaat)
    
    print("\n---- Print tabel AHN overzicht ----")
    print(df_ahn_overzicht)

    print("\n---- Print AHN overzicht shape----")
    print(df_ahn_overzicht.shape)

    # Data en metadata inlezen en koppelen
    df_klimaat, meta_tidy, col_meta = read_and_join_with_metadata(
        data_path=KLIMAAT_DATA_CSV,
        metadata_path=KLIMAAT_META_CSV
    )

    # Geef overzicht van de AHN-gerelateerde metadata
    controleer_ahn_metadata(df_klimaat, meta_tidy)


    # Aantal kolommen met metadata vs. totaal
    meta_klimaat = df_klimaat.attrs.get("metadata", {})
    covered = len(set(df_klimaat.columns) & set(meta_klimaat.keys()))
    print(f"Kolommen met metadata: {covered}/{df_klimaat.shape[1]}")


    # ------------------------------------------------------
    # Kerncijfers en Klimaatatlasdata kopieren en koppelen aan labels
    # Beide datasets koppelen
    # ------------------------------------------------------

    df_data_labeled = maak_gelabelde_kopie_df_data(df_data, df_meta)    
    df_klimaat_labeled = maak_gelabelde_kopie_df_klimaat(df_klimaat, meta_tidy, label_field="Omschrijving kort")



    # Controleren op dubbele kolommen
    print("\n---- Dubbele kolommen df_data_labeled: ----")
    print(df_data_labeled.columns[df_data_labeled.columns.duplicated()].tolist())
    # Eventueel nog verder naar kijken


    print("\n---- Dubbele kolommen df_klimaat_labeled: ----")
    print(df_klimaat_labeled.columns[df_klimaat_labeled.columns.duplicated()].tolist())


    df_join = join_cbs_with_klimaat(
        df_data=df_data_labeled,
        df_klimaat=df_klimaat_labeled,
        left_key="Codering (code)",
        right_key="Buurtcode op basis van CBS wijk en buurtkaart 2024",
        strict_unique=False,
        verbose=True
    )


    print(df_join.shape)
    df_join.head()

    # ------------------------------------------------------
    # Data pipeline: clean, impute, scale
    # ------------------------------------------------------
    

    print("\n Check data vervolgens bewerk de data (imputeren + schalen + shape):")
    df_num, df_scaled, dq_summary = pca_check(df_join, verbose=True, impute_strategy="knn")


    # ------------------------------------------------------
    # PCA
    # ------------------------------------------------------
    print("\n[Running PCA...")
    pca, pca_loadings, cum_var = run_pca_threshold(    
        df_scaled,    
        variance_threshold=0.90 # Robuuste keuze
    )

    plot_pca_variance(cum_var, FIGURE_DIR)
    plot_loadings_heatmap(pca_loadings, FIGURE_DIR)

    pca_tree = build_loading_tree(pca_loadings, threshold=0.30)
    pca_tree = normalize_loading_labels(pca_tree, prefix="PCA")

    print("\n--- PCA Boomstructuur ---")
    print_loading_tree(pca_tree)

    sunburst_from_tree(pca_tree, "PCA Zonnestraalplot", "pca_sunburst.png", output_dir=FIGURE_DIR)

    # -------------------------------------------------
    # Factoranalyse
    # -------------------------------------------------

    fa, fa_loadings, fa_info = run_fa_auto_stable(
    df_scaled,
    max_factors=12,
    min_factors=2,
    verbose=True
    )

    print(f"[FA] Gekozen methode: {fa_info['method']}")
    print(f"[FA] Aantal factoren: {fa_info['n_factors']}")
    plot_fa_heatmap(fa_loadings, FIGURE_DIR)

    fa_tree = build_loading_tree(fa_loadings, threshold=0)
    fa_tree = normalize_loading_labels(fa_tree, prefix="FA")

    print("\n--- FA Boomstructuur ---")
    print_loading_tree(fa_tree)

    sunburst_from_tree(fa_tree, "FA Zonnestraalplot", "fa_sunburst.png", output_dir=FIGURE_DIR)

    # ------------------------------------------------------
    # PDF RAPPORT MAKEN
    # ------------------------------------------------------

    generate_pdf_report(
    figures_dir=FIGURE_DIR,
    output_pdf_path=PDF_PATH,
    dq_summary=dq_summary
)

# ------------------------------------------------------
# Uitvoeren main script
# ------------------------------------------------------
   

if __name__ == "__main__":
    main()