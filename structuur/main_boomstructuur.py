# main.py
from functies_boomstructuur import inlezen_json, toon_structuur, print_json, flatten_hierarchy, depth_type_kolommen
import pandas as pd

def main():
    pad_naar_json = "../data/raw/kompas_hierarchie.json" 

    try:
        data = inlezen_json(pad_naar_json)
        print("JSON succesvol ingelezen!\n")

        print("=== STRUCTUUR (hiërarchie) ===")
        toon_structuur(data)

        print("\n=== VOLLEDIGE JSON ===")
        print_json(data)

        print("\n=== Platte data ===")
        # Haalt de hierarchie uit de JSON
        root = data["hierarchie"]   
        df_nodes = flatten_hierarchy(root, extra_keys=["uuid", "value"])
        print(df_nodes.head())

        print("\n=== Kolommen per depth en type ===")
        df_overzicht = depth_type_kolommen(df_nodes)
        print(df_overzicht.to_string(index=False))
  
    except Exception as e:
        print(f"Er ging iets mis bij het inlezen: {e}")


if __name__ == "__main__":
    main()