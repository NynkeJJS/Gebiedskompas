import pandas as pd
import plotly.express as px

from config import (
    vprint, 
    FIGURE_DIR,
    PDF_PATH,
    KLIMAAT_DATA_CSV, 
    KLIMAAT_META_CSV,
    VARIANCE_THRESHOLD,
    THEMA_LABELS,
    BUURTEN_VOOR_PROFIEL
)

from data_inlezen import (
    get_metadata,
    get_provincie_gebieden,
    get_data_provincie,
    koppel_geo_info,
    sla_op, 
    read_data_csv,
    read_and_join_with_metadata,
    controleer_ahn_metadata,
    maak_suffix_tabel,
    maak_gelabelde_kopie_df_data,
    maak_gelabelde_kopie_df_klimaat,
    join_cbs_with_klimaat
)

from data_pipeline import (
    data_check
)

from analyse_bottom_up import (
    plot_fa_heatmap,
    plot_pca_variance,
    plot_loadings_heatmap,
    run_pca_threshold,
    run_fa_auto_stable,
    build_loading_tree,
    normalize_loading_labels,
    print_loading_tree,
    sunburst_from_tree,
    generate_pdf_report,
    save_figure,
)
from analyse_top_down import (
    samengestelde_variabelen,
    aggregate_themascores_for_sunburst,
    sunburst_profiel_buurt,
)


def main_data():
    """
    Stappen 1-4:
    - kerncijfers
    - klimaatdata
    - labels + joins
    - cleaning / scaling
    """
    # ======================================================
    # 1. Kerncijfers
    # ======================================================
    print("Data inlezen...")
    df_meta = get_metadata()
    #df_meta_dict = metadata_label_map(df_meta)

    df_prov = get_provincie_gebieden()
    provincie_codes = df_prov["Key"].tolist()

    df_data = get_data_provincie(provincie_codes)
    df_data = koppel_geo_info(df_data, df_prov)

    sla_op(df_data, df_meta)
    print(f"Kerncijfers shape: {df_data.shape}")
    vprint(df_data.head())



    # ======================================================
    # 2. Klimaatdata + metadata
    # ======================================================
   
    """ Klimaatdata inlezen en overzicht tonen van de AHN gegevens. 
    Dit is een cruciale stap om te zorgen dat de klimaatdata correct gelabeld
    en bruikbaar is voor verdere analyse."""

    print(f"\nKlimaatdata: {KLIMAAT_DATA_CSV}")
    print(f"Metadata:    {KLIMAAT_META_CSV}")

    df_klimaat_raw = read_data_csv(KLIMAAT_DATA_CSV)
    df_ahn_overzicht = maak_suffix_tabel(df_klimaat_raw)

    print("\n---- AHN-overzicht ----")
    print(df_ahn_overzicht)

    """ 
    Klimaatdata inlezen en koppelen met metadata. 
    Bij het inlezen van de klimaatdata wordt ook gecontroleerd of de AHN-gegevens correct gelabeld zijn.
    """

    df_klimaat, df_klimaat_meta, col_meta = read_and_join_with_metadata(
        data_path=KLIMAAT_DATA_CSV,
        metadata_path=KLIMAAT_META_CSV,
    )

    controleer_ahn_metadata(df_klimaat, df_klimaat_meta)

    # ======================================================
    # 3. Labels + koppelen
    # ======================================================
    """ 
    Labelt CBS- en klimaatdata met behulp van metadata en combineert beide datasets 
    tot één samenhangende dataset op buurtniveau voor verdere analyse
    """

    df_data_labeled = maak_gelabelde_kopie_df_data(df_data, df_meta)
    df_klimaat_labeled = maak_gelabelde_kopie_df_klimaat(
        df_klimaat, df_klimaat_meta, label_field="Omschrijving kort"
    )

    df_join = join_cbs_with_klimaat(
        df_data=df_data_labeled,
        df_klimaat=df_klimaat_labeled,
        left_key="Codering (code)",
        right_key="Buurtcode op basis van CBS wijk en buurtkaart 2024",
        strict_unique=False,
    )

    # Maak expliciet een kopie om veilig kolommen en index aan te passendf_join = df_join.copy()
    df_join = df_join.copy()

    # Neem de CBS-buurtcode expliciet op
    df_join["Buurtcode"] = df_join["Codering (code)"]

    # Zet 'm ook als index (handig, maar kolom blijft bestaan)
    df_join = df_join.set_index("Buurtcode", drop=False)


    print("Gecombineerde dataset:", df_join.shape)

    # ======================================================
    # 4. Cleaning / imputatie / schalen
    # ======================================================

    print("\nData controleren en voorbereiden...")

    df_clean, df_scaled_z, df_scaled_minmax, dq_summary = data_check(
        df_join,
        impute_strategy="knn",
    )

    return {
        "df_scaled_z": df_scaled_z,             # voor PCA, FA en gewogen gemiddelde
        "df_scaled_minmax": df_scaled_minmax,   # voor entropy
        "dq_summary": dq_summary,
    }

def main_analyse_experiment(df_scaled_z, dq_summary):
    """
    Stappen 1-3:
    - PCA
    - Factoranalyse
    - Rapportage
    """
    # ======================================================
    # 1. PCA
    # ======================================================
    print("\n[PCA]")
    pca, pca_loadings, cum_var = run_pca_threshold(
        df_scaled_z,
        variance_threshold=VARIANCE_THRESHOLD,
    )

    plot_pca_variance(cum_var, FIGURE_DIR, VARIANCE_THRESHOLD)
    plot_loadings_heatmap(pca_loadings, FIGURE_DIR)

    pca_tree = normalize_loading_labels(
        build_loading_tree(pca_loadings, threshold=0.30),
        prefix="PCA",
    )

    print_loading_tree(pca_tree)

    sunburst_from_tree(
        pca_tree,
        "PCA Zonnestraalplot",
        "pca_sunburst.png",
        FIGURE_DIR,
    )

    # ======================================================
    # 2. Factoranalyse
    # ======================================================
    print("\n[FA]")
    fa, fa_loadings, fa_info = run_fa_auto_stable(
        df_scaled_z,
        rotation="oblimin",
        max_factors=12,
        min_factors=2,
    )

    plot_fa_heatmap(fa_loadings, FIGURE_DIR)

    fa_tree = normalize_loading_labels(
        build_loading_tree(fa_loadings, threshold=0),
        prefix="FA",
    )

    print_loading_tree(fa_tree)

    sunburst_from_tree(
        fa_tree,
        "FA Zonnestraalplot",
        "fa_sunburst.png",
        FIGURE_DIR,
    )




    # ======================================================
    # 3. PDF rapport
    # ======================================================
    generate_pdf_report(
        figures_dir=FIGURE_DIR,
        output_pdf_path=PDF_PATH,
        dq_summary=dq_summary,
    )



def main_analyse_samengestelde_variabelen(weighted_mean, entropy):
    
    """
    Structurering van de analyse van samengestelde variabelen


    - Bereken themascores per buurt (entropy & weighted mean)
    - Maak geaggregeerde sunbursts (over alle buurten)
    - Maak profiel-sunbursts per geselecteerde buurt
      (gelijke grootte, kleur = score)
    """

    print("\n[Analyse samengestelde variabelen]")
    print("Start berekening thema-scores (entropy & weighted mean)")

    # ======================================================
    # 1. Per buurt × thema × methode
    # ======================================================
    df_results = samengestelde_variabelen(weighted_mean=weighted_mean, entropy=entropy)
    # Thema-labels inkorten
    df_results["thema_kort"] = df_results["thema"].map(THEMA_LABELS)

    print(f"Resultaten berekend: {df_results.shape[0]} rijen")
    print("Thema's:", df_results["thema_kort"].unique())
    print("Methodes:", df_results["methode"].unique())

    # ======================================================
    # 2. Opslaan detailresultaten (per buurt)
    # ======================================================
    output_scores = "../data/output/samengestelde_themascores.csv"
    df_results.to_csv(output_scores, index=False)
    print(f"Detailresultaten opgeslagen in: {output_scores}")

    # ======================================================
    # 3. Aggregatie over buurten (voor overzicht)
    # ======================================================
    df_agg = (
        df_results
        .groupby(["methode", "thema_kort"], as_index=False)["score"]
        .mean()
    )

    # ======================================================
    # 4. Geaggregeerde sunburst: entropy
    # ======================================================
    df_entropy = df_agg[df_agg["methode"] == "entropy"]

    fig_entropy = px.sunburst(
        df_entropy,
        path=["thema_kort"],
        values="score",
        color="score",
        color_continuous_scale="RdBu",
        title="Samengestelde themascores - Entropy (gemiddeld over buurten)",
    )

    save_figure(
        fig_entropy,
        filename="themascores_sunburst_entropy.png",
    )

    # ======================================================
    # 5. Geaggregeerde sunburst: weighted mean
    # ======================================================
    df_weighted = df_agg[df_agg["methode"] == "weighted_mean"]

    fig_weighted = px.sunburst(
        df_weighted,
        path=["thema_kort"],
        values="score",
        color="score",
        color_continuous_scale="RdBu",
        title="Samengestelde themascores – Gewogen gemiddelde (gemiddeld over buurten)",
    )

    save_figure(
        fig_weighted,
        filename="themascores_sunburst_weighted_mean.png",
    )

    # ======================================================
    # 6. Sunbursts per buurt (gelijke grootte, kleur = score)
    # ======================================================
    for buurt in BUURTEN_VOOR_PROFIEL:

        df_buurt = df_results[df_results["Buurtcode"] == buurt].copy()

        if df_buurt.empty:
            print(f"[Waarschuwing] Geen data voor buurt {buurt}")
            continue

        # Alle thema's even groot
        df_buurt["value"] = 1

        # ------------------------------
        # 6a. Entropy (profiel)
        # ------------------------------
        df_entropy_buurt = df_buurt[df_buurt["methode"] == "entropy"]

        fig_entropy_buurt = px.sunburst(
            df_entropy_buurt,
            path=["thema_kort"],
            values="value",
            color="score",
            color_continuous_scale="RdBu",
            title=f"Buurt {buurt} – thematisch profiel (entropy)",
        )

        fig_entropy_buurt.update_traces(
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Score: %{color:.2f}<extra></extra>"
            )
        )

        save_figure(
            fig_entropy_buurt,
            filename=f"buurt_{buurt}_sunburst_entropy.png",
        )

        # ------------------------------
        # 6b. Weighted mean (profiel)
        # ------------------------------
        df_weighted_buurt = df_buurt[df_buurt["methode"] == "weighted_mean"]

        fig_weighted_buurt = px.sunburst(
            df_weighted_buurt,
            path=["thema_kort"],
            values="value",
            color="score",
            color_continuous_scale="RdBu",
            title=f"Buurt {buurt} – thematisch profiel (gewogen gemiddelde)",
        )

        fig_weighted_buurt.update_traces(
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Score: %{color:.2f}<extra></extra>"
            )
        )

        save_figure(
            fig_weighted_buurt,
            filename=f"buurt_{buurt}_sunburst_weighted_mean.png",
        )

    # ======================================================
    # 7. Return (altijd als laatste)
    # ======================================================
    return df_results, df_agg




def main(run_experiment=True, run_samengesteld=True):

    data_out = main_data()

    print(sorted(data_out["df_scaled_minmax"].columns.tolist()))

    if run_experiment:
        main_analyse_experiment(
            df_scaled_z=data_out["df_scaled_z"],
            dq_summary=data_out["dq_summary"],
        )

    if run_samengesteld:
        main_analyse_samengestelde_variabelen(
            weighted_mean=data_out["df_scaled_z"],
            entropy=data_out["df_scaled_minmax"]
        )




if __name__ == "__main__":
    main(run_experiment=True, run_samengesteld=True)
