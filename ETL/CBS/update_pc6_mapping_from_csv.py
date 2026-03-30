import pandas as pd
import json
import os
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
zip_path = os.path.join(PROJECT_ROOT, 'data/cbs_pc6_huisnr_buurt/2025-cbs-pc6huisnr20250801_buurt.zip')
json_path = os.path.join(PROJECT_ROOT, 'data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json')

print(f"Laden zipfile {zip_path}")
with zipfile.ZipFile(zip_path, 'r') as z:
    with z.open('pc6hnr20250801_gwb.csv') as f:
        # De PC6 -> Buurt dataset van CBS (2025)
        df = pd.read_csv(f, sep=';', dtype=str)

df.columns = df.columns.str.lower().str.strip()
print(f"Columns: {df.columns.tolist()}")

# De verwachte structuur van CBS: pc6, huisnummer, buurt2025, wijk2025, gem2025
# We willen een unique mapping van pc6 naar buurtcode
# Let op: Soms ligt 1 pc6 over meerdere buurten. We pakken de meest voorkomende (mode) of de eerste.
df_grouped = df.groupby('pc6')['buurt2025'].first().reset_index()

with open(json_path, 'r') as f:
    mapping = json.load(f)

print(f"Bestaande mapping: {len(mapping)} records")

updates = 0
for idx, row in df_grouped.iterrows():
    pc6 = row['pc6']
    # CBS levert waarschijnlijk alleen de laatste 4 cijfers '0001', of 'BU00900001'.
    # We slaan de structuur zonder 'BU' op, of controleren even wat we in de DF hebben:
    # df weggelaten BU? Soms levert CBS "BU00900001", soms "00900001".
    # pc6_buurt_mapping.json verwacht bijvoorbeeld "00981101".
    b25 = row['buurt2025']
    if pd.isna(b25): continue
    if b25.startswith('BU'):
        b25 = b25[2:]
        
    if mapping.get(pc6) != b25:
        mapping[pc6] = b25
        updates += 1

print(f"✅ {updates} PC6 mapping codes geupdate!")

if updates > 0:
    with open(json_path, 'w') as f:
        json.dump(mapping, f, separators=(',', ':'))
    print("Mapping opgeslagen!")
    
