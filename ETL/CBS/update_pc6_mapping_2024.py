import pandas as pd
import geopandas as gpd
import json
import os
import psycopg2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db():
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=os.getenv('DATABASE_PORT', '5432'),
        dbname=os.getenv('DATABASE_NAME', 'omnitwin_db'),
        user=os.getenv('DATABASE_USER', 'omnitwin_user'),
        password=os.getenv('DATABASE_PASSWORD', 'admin_omnitwin2026')
    )

print("Laden bestaande pc6 mapping...")
mapping_path = os.path.join(PROJECT_ROOT, 'data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json')
with open(mapping_path, 'r') as f:
    mapping = json.load(f)

print(f"Bestaande map: {len(mapping)} PC6 codes")

# Lees alle geometrieën van de nieuwe actieve buurten uit de database 
print("Laden 2024 (actieve) buurten uit database in geopandas...")
conn = get_db()
query = "SELECT id as buurt_id, id as statcode, geom as geometry FROM gebieden WHERE actief = true AND id LIKE 'BU%' AND geom IS NOT NULL"
buurten = gpd.read_postgis(query, conn, geom_col='geometry', crs=28992)
conn.close()

buurten['buurtcode'] = buurten['statcode'].str.replace('BU', '')
print(f"Loaded {len(buurten)} actieve buurten.")

# We moeten de locaties van de postcodes hebben. Eerder werden die verzameld uit PC6_HUISNR. 
pc6_path = os.path.join(PROJECT_ROOT, 'data/cbs_pc6_huisnr_buurt/cbs_pc6_2023.gpkg')
if not os.path.exists(pc6_path):
    print(f"⚠️ {pc6_path} niet gevonden, we controleren pc6_huisnr_2023.gpkg")
    pc6_path = os.path.join(PROJECT_ROOT, 'data/cbs_pc6_huisnr_buurt/cbs_pc6_huisnr_2023.gpkg')

print(f"Laden {pc6_path}...")
try:
    pc_gdf = gpd.read_file(pc6_path)
    
    if 'geometry' in pc_gdf.columns and not pc_gdf.geometry.is_empty.all():
        print("Spatial join pc6 -> buurten_2024 (intersects)...")
        # Ensure CRS match
        if pc_gdf.crs != buurten.crs:
            pc_gdf = pc_gdf.to_crs(buurten.crs)
            
        joined = gpd.sjoin(pc_gdf, buurten[['buurtcode', 'geometry']], how='inner', predicate='intersects')

        print("Updaten mapping (bijwerken voor deze PC6)...")
        updates = 0
        for idx, row in joined.iterrows():
            # CBS levert pc6 per huishouden of aggregated, find pc6 col
            pc6_col = [c for c in row.index if 'pc6' in c.lower() or 'postcode' in c.lower()][0]
            pc6 = str(row[pc6_col])
            buurt_code = str(row['buurtcode'])
            if mapping.get(pc6) != buurt_code:
                mapping[pc6] = buurt_code
                updates += 1

        print(f"✅ {updates} PC6 mapping codes geupdate!")
        temp_path = os.path.join(PROJECT_ROOT, 'data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping_2024.json')
        with open(temp_path, 'w') as f:
            json.dump(mapping, f, separators=(',', ':'))

        print(f"Nieuwe mapping opgeslagen in {temp_path}. Hernoem manueel als geslaagd.")
    else:
        print("Geen geometrie in PC6 file, kan geen spatial join doen.")
except Exception as e:
    print(f"Failed: {e}")

