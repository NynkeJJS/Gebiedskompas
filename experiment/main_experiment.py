import pandas as pd
import plotly.express as px

from config import (
    KERNCIJFERS_DATA,
    KERNCIJFERS_META,
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
    # print("Data inlezen...")
    # df_meta = get_metadata()
    # #df_meta_dict = metadata_label_map(df_meta)

    # df_prov = get_provincie_gebieden()
    # provincie_codes = df_prov["Key"].tolist()

    # df_data = get_data_provincie(provincie_codes)
    # df_data = koppel_geo_info(df_data, df_prov)

    # sla_op(df_data, df_meta)
    # print(f"Kerncijfers shape: {df_data.shape}")
    # vprint(df_data.head())

    df_data, df_meta = pd.read_csv(KERNCIJFERS_DATA), pd.read_csv(KERNCIJFERS_META)

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


def main_analyse_samengestelde_variabelen(
    *,
    df_minmax,
    df_zscore,
    normalisatie_weighted_mean_buurt: str = "z_score",
    weighted_mean_norm_gemiddelde_label: str,
    entropy_norm_gemiddelde_label: str,
    entropy_norm_buurt_label: str,
):

    print("\n[Analyse samengestelde variabelen]")
    print("Start berekening thema-scores (entropy & weighted mean)")

    # ======================================================
    # 1. Resultaten berekenen
    # ======================================================

    # Aggregatie → ALTIJD min-max
    df_results_gemiddelde = samengestelde_variabelen(
        weighted_mean_df=df_minmax,
        entropy_df=df_minmax,
        weighted_mean_normalisatie="min_max",
    )

    # Buurtprofielen
    if normalisatie_weighted_mean_buurt == "z_score":
        weighted_mean_norm_buurt_label = "z-score normalisatie"
        subtitle_weighted = ("Afwijking van deze buurt ten opzichte van het gemiddelde van alle buurten.")
        df_results_buurt = samengestelde_variabelen(
            weighted_mean_df=df_zscore,
            entropy_df=df_minmax,
            weighted_mean_normalisatie="z_score",
        )

    elif normalisatie_weighted_mean_buurt == "min_max":
        weighted_mean_norm_buurt_label = "min-max normalisatie"
        subtitle_weighted = ("Relatief niveau van thema's binnen deze buurt (0-1 schaal).")
        df_results_buurt = samengestelde_variabelen(
            weighted_mean_df=df_minmax,
            entropy_df=df_minmax,
            weighted_mean_normalisatie="min_max",
        )

    else:
        raise ValueError("normalisatie_weighted_mean_buurt moet 'z_score' of 'min_max' zijn")

    # Thema‑labels
    for df in (df_results_gemiddelde, df_results_buurt):
        df["thema_kort"] = df["thema"].map(THEMA_LABELS)

    # ======================================================
    # 2. Aggregatie over buurten
    # ======================================================

    df_agg = (
        df_results_gemiddelde
        .groupby(["methode", "thema_kort"], as_index=False)["score"]
        .mean()
    )

    # ======================================================
    # 3. Opslaan resultaten
    # ======================================================

    df_agg.to_csv(
        "../data/output/samengestelde_themascores_gemiddelde_agg.csv",
        index=False,
    )

    df_results_gemiddelde.to_csv(
        "../data/output/samengestelde_themascores_gemiddelde.csv",
        index=False,
    )


    df_results_buurt.to_csv(
        "../data/output/samengestelde_themascores_buurt.csv",
        index=False,
    )



    # ======================================================
    # 4. Geaggregeerde sunbursts
    # ======================================================

    fig_entropy = px.sunburst(
        df_agg[df_agg["methode"] == "entropy"],
        path=["thema_kort"],
        values="score",
        color="score",
        color_continuous_scale="RdBu",
    )

    fig_entropy.update_layout(
    title="Samengestelde themascores - Entropy "
            f"(gemiddeld over buurten, {entropy_norm_gemiddelde_label})",
        )
    

    fig_entropy.add_annotation(
        text="Gemiddelde bijdrage van thema's aan verschillen tussen buurten.",
        x=0.0,
        y=0.95,
        xref="paper",
        yref="paper",
        xanchor="left",
        showarrow=False,
        font=dict(size=14, color="black"),
    )

    save_figure(fig_entropy, "themascores_sunburst_entropy.png")

    fig_weighted = px.sunburst(
        df_agg[df_agg["methode"] == "weighted_mean"],
        path=["thema_kort"],
        values="score",
        color="score",
        color_continuous_scale="RdBu",
    )

    fig_weighted.update_layout(
    title="Samengestelde themascores - Gewogen gemiddelde "
            f"(gemiddeld over buurten, {weighted_mean_norm_gemiddelde_label})",
        )
    

    fig_weighted.add_annotation(
        text="Gemiddeld niveau van thema's over alle buurten.",
        x=0.0,
        y=0.95,
        xref="paper",
        yref="paper",
        xanchor="left",
        showarrow=False,
        font=dict(size=14, color="black"),
    )
    save_figure(fig_weighted, "themascores_sunburst_weighted_mean.png")

    # ======================================================
    # 5. Buurtprofielen
    # ======================================================

    for buurt in BUURTEN_VOOR_PROFIEL:

        df_buurt = df_results_buurt[
            df_results_buurt["Buurtcode"] == buurt
        ].copy()

        if df_buurt.empty:
            continue

        df_buurt["value"] = 1

        fig_entropy_buurt = px.sunburst(
            df_buurt[df_buurt["methode"] == "entropy"],
            path=["thema_kort"],
            values="value",
            color="score",
            color_continuous_scale="RdBu",
        )

        fig_entropy_buurt.update_layout(
        title=f"Buurt {buurt} - entropy ({entropy_norm_buurt_label})"
        )
        
        

        fig_entropy_buurt.add_annotation(
            text="Onderscheidend vermogen van thema's binnen deze buurt.",
            x=0.0,
            y=0.95,
            xref="paper",
            yref="paper",
            xanchor="left",
            showarrow=False,
            font=dict(size=14, color="black"),
)
        save_figure(fig_entropy_buurt, f"buurt_{buurt}_sunburst_entropy.png")

        fig_weighted_buurt = px.sunburst(
            df_buurt[df_buurt["methode"] == "weighted_mean"],
            path=["thema_kort"],
            values="value",
            color="score",
            color_continuous_scale="RdBu",
        )

        fig_weighted_buurt.update_layout(
        title=f"Buurt {buurt} - gewogen gemiddelde ({weighted_mean_norm_buurt_label})"
        )

        fig_weighted_buurt.add_annotation(
            text=subtitle_weighted,
            x=0.0,
            y=0.95,
            xref="paper",
            yref="paper",
            xanchor="left",
            showarrow=False,
            font=dict(size=14, color="black"),
        )
        save_figure(fig_weighted_buurt, f"buurt_{buurt}_sunburst_weighted_mean.png")

    return df_results_gemiddelde, df_results_buurt, df_agg


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
            df_minmax=data_out["df_scaled_minmax"],
            df_zscore=data_out["df_scaled_z"],
            normalisatie_weighted_mean_buurt="z_score",
            weighted_mean_norm_gemiddelde_label="min-max normalisatie",
            entropy_norm_gemiddelde_label="min-max normalisatie",
            entropy_norm_buurt_label="min-max normalisatie",
        )






if __name__ == "__main__":
    main(run_experiment=True, run_samengesteld=True)
