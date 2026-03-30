import geopandas as gpd
import pandas as pd
import sys

bag_vbo_path = 'data/bag_frl/cleaned_bag_data_verblijfsobject.gpkg'
bag_pand_path = 'data/bag_frl/bag_data_bag_pand.gpkg'

print("--- GEBRUIKSDOELEN ANALYSE (VBO) ---")
try:
    gdf_vbo = gpd.read_file(bag_vbo_path)
    if 'gebruiksdoel' in gdf_vbo.columns:
        print(f"Unieke waarden in 'gebruiksdoel':")
        counts = gdf_vbo['gebruiksdoel'].value_counts()
        for doel, count in counts.items():
            print(f"- {doel}: {count}")
    else:
        print("Kolom 'gebruiksdoel' niet gevonden! Beschikbare kolommen:", gdf_vbo.columns.tolist())
        
    print("\n--- MEERVOUDIGE FUNCTIES CHECK ---")
    # Check if any value contains multiple functions (e.g. comma separated)
    multi = gdf_vbo[gdf_vbo['gebruiksdoel'].str.contains(',', na=False)]
    if not multi.empty:
        print(f"Gevonden records met meervoudige doelen: {len(multi)}")
        print(multi['gebruiksdoel'].head())
    else:
        print("Geen comma-separated waarden gevonden in 'gebruiksdoel'.")

except Exception as e:
    print(f"Fout bij lezen VBO: {e}")

print("\n--- BOUWJAAR ANALYSE (PAND) ---")
try:
    gdf_pand = gpd.read_file(bag_pand_path)
    if 'bouwjaar' in gdf_pand.columns:
        print(f"Bouwjaar stats:")
        print(gdf_pand['bouwjaar'].describe())
        
        # Test categories
        voor_1915 = len(gdf_pand[gdf_pand['bouwjaar'] < 1915])
        p_1915_1945 = len(gdf_pand[(gdf_pand['bouwjaar'] >= 1915) & (gdf_pand['bouwjaar'] <= 1945)])
        p_1945_1984 = len(gdf_pand[(gdf_pand['bouwjaar'] > 1945) & (gdf_pand['bouwjaar'] <= 1984)])
        vanaf_1985 = len(gdf_pand[gdf_pand['bouwjaar'] >= 1985])
        
        print(f"\nVerdeling:")
        print(f"- Voor 1915: {voor_1915}")
        print(f"- 1915-1945: {p_1915_1945}")
        print(f"- 1945-1984: {p_1945_1984}")
        print(f"- Vanaf 1985: {vanaf_1985}")
    else:
         print("Kolom 'bouwjaar' niet gevonden!")

except Exception as e:
    print(f"Fout bij lezen Pand: {e}")
