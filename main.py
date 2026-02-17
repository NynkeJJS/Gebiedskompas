# main.py
from functies import inlezen_json, toon_structuur, pretty_print_json, flatten_hierarchy, flatten_indicators
import pandas as pd

def main():
    pad_naar_json = "data/raw/kompas_hierarchie.json"

    try:
        data = inlezen_json(pad_naar_json)
        print("JSON succesvol ingelezen!\n")

        print("=== STRUCTUUR (hiërarchie) ===")
        toon_structuur(data)

        print("\n=== VOLLEDIGE JSON (netjes) ===")
        pretty_print_json(data)

        print("\n=== Platte data ===")
        root = data["hierarchie"]      # <-- JUISTE ingang
        df_nodes = flatten_hierarchy(root, extra_keys=["uuid", "value"])
        print(df_nodes.head())

        print("\n=== Kolommen per type (indicator/laag) ===")
        kolommen_per_type = (
            df_nodes
            .groupby("type", dropna=False)
            .apply(lambda g: g.columns[g.notna().any()].tolist())
            .rename("kolommen")
            .reset_index()
        )
        print(kolommen_per_type)

        print("\n=== Kolommen per depth (laagnummer) ===")
        kolommen_per_depth = (
            df_nodes
            .groupby("depth")
            .apply(lambda g: g.columns[g.notna().any()].tolist())
            .rename("kolommen")
            .reset_index()
        )
        print(kolommen_per_depth)

        print("\n=== Indicator-kolommen ===")
        df_ind = flatten_indicators(root)
        print("Indicator-kolommen:", df_ind.columns.tolist())
        print(df_ind.head())

    except Exception as e:
        print(f"Er ging iets mis bij het inlezen: {e}")


if __name__ == "__main__":
    main()