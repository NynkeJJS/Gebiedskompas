from config_experiment import (
    vprint, 
    FIGURE_DIR,
    PDF_PATH,
    KERNCIJFERS_DATA, 
    KERNCIJFERS_META, 
    KLIMAAT_DATA_CSV, 
    KLIMAAT_META_CSV,
    VARIANCE_THRESHOLD,
)

from data_inlezen_experiment import (
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

    # ======================================================
    # 1. Kerncijfers: data + metadata ophalen / inlezen
    # ======================================================
    print("Data inlezen...")
    df_meta = get_metadata()
    df_meta_dict = metadata_label_map(df_meta)

    df_prov = get_provincie_gebieden()
    provincie_codes = df_prov["Key"].tolist()

    df_data = get_data_provincie(provincie_codes)
    df_data = koppel_geo_info(df_data, df_prov)

    sla_op(df_data, df_meta)
    print(f"Kerncijfers shape: {df_data.shape}")
    vprint(df_data.head())

    # # Inlezen vanaf schijf
    # df_data, df_meta = lees_opgeslagen_data(
    #     data_path=KERNCIJFERS_DATA,
    #     meta_path=KERNCIJFERS_META,
    # )

    # ======================================================
    # 2. Klimaatatlasdata + metadata koppelen
    # ======================================================
    print(f"\nKlimaatdata: {KLIMAAT_DATA_CSV}")
    print(f"Metadata:    {KLIMAAT_META_CSV}")

    df_klimaat_raw = read_data_csv(KLIMAAT_DATA_CSV)
    df_ahn_overzicht = maak_suffix_tabel(df_klimaat_raw)

    print("\n---- AHN-overzicht ----")
    print(df_ahn_overzicht)
    print("Shape:", df_ahn_overzicht.shape)

    df_klimaat, meta_tidy, col_meta = read_and_join_with_metadata(
        data_path=KLIMAAT_DATA_CSV,
        metadata_path=KLIMAAT_META_CSV,
    )

    controleer_ahn_metadata(df_klimaat, meta_tidy)

    meta_klimaat = df_klimaat.attrs.get("metadata", {})
    covered = len(set(df_klimaat.columns) & set(meta_klimaat.keys()))
    print(f"Kolommen met metadata: {covered}/{df_klimaat.shape[1]}")

    # ======================================================
    # 3. Labels toepassen + datasets koppelen
    # ======================================================
    df_data_labeled = maak_gelabelde_kopie_df_data(df_data, df_meta)
    df_klimaat_labeled = maak_gelabelde_kopie_df_klimaat(
        df_klimaat, meta_tidy, label_field="Omschrijving kort"
    )

    print("\nDubbele kolommen kerncijfers:",
          df_data_labeled.columns[df_data_labeled.columns.duplicated()].tolist())
    print("Dubbele kolommen klimaat:",
          df_klimaat_labeled.columns[df_klimaat_labeled.columns.duplicated()].tolist())

    df_join = join_cbs_with_klimaat(
        df_data=df_data_labeled,
        df_klimaat=df_klimaat_labeled,
        left_key="Codering (code)",
        right_key="Buurtcode op basis van CBS wijk en buurtkaart 2024",
        strict_unique=False,
    )

    print("Gecombineerde dataset:", df_join.shape)

    # ======================================================
    # 4. Data pipeline: cleaning, imputatie, schalen
    # ======================================================
    print("\nData controleren en voorbereiden...")
    df_num, df_scaled, dq_summary = pca_check(
        df_join,
        impute_strategy="knn",
    )

    # ======================================================
    # 5. PCA
    # ======================================================
    print("\n[PCA]")
    pca, pca_loadings, cum_var = run_pca_threshold(
        df_scaled,
        variance_threshold=VARIANCE_THRESHOLD,
    )

    plot_pca_variance(cum_var, FIGURE_DIR, VARIANCE_THRESHOLD)
    plot_loadings_heatmap(pca_loadings, FIGURE_DIR)

    pca_tree = normalize_loading_labels(
        build_loading_tree(pca_loadings, threshold=0.30),
        prefix="PCA",
    )

    print("\n--- PCA boom ---")
    print_loading_tree(pca_tree)

    sunburst_from_tree(
        pca_tree,
        "PCA Zonnestraalplot",
        "pca_sunburst.png",
        FIGURE_DIR,
    )

    # ======================================================
    # 6. Factoranalyse (met expliciete rotatie)
    # ======================================================
    print("\n[FA]")
    fa, fa_loadings, fa_info = run_fa_auto_stable(
        df_scaled,
        rotation="oblimin",   
        max_factors=12,
        min_factors=2,
    )

    print(f"Methode: {fa_info['method']}")
    print(f"Aantal factoren: {fa_info['n_factors']}")

    plot_fa_heatmap(fa_loadings, FIGURE_DIR)

    fa_tree = normalize_loading_labels(
        build_loading_tree(fa_loadings, threshold=0),
        prefix="FA",
    )

    print("\n--- FA boom ---")
    print_loading_tree(fa_tree)

    sunburst_from_tree(
        fa_tree,
        "FA Zonnestraalplot",
        "fa_sunburst.png",
        FIGURE_DIR,
    )

    # ======================================================
    # 7. PDF-rapport
    # ======================================================
    generate_pdf_report(
        figures_dir=FIGURE_DIR,
        output_pdf_path=PDF_PATH,
        dq_summary=dq_summary,
    )


# ------------------------------------------------------
# Uitvoeren main script
# ------------------------------------------------------
   

if __name__ == "__main__":
    main()