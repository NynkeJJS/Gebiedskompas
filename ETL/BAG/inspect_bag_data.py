#!/usr/bin/env python3
"""Inspecteer BAG GPKG bestanden - kolommen, datatypes, sample data"""
import geopandas as gpd
import os

bag_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/bag_frl')

print("=" * 80)
print("BAG FRYSLÂN DATA INSPECTIE")
print("=" * 80)

# 1. Verblijfsobjecten
print("\n=== 1. VERBLIJFSOBJECTEN ===")
vbo = gpd.read_file(os.path.join(bag_dir, 'cleaned_bag_data_verblijfsobject.gpkg'))
print(f"Records: {len(vbo)}")
print(f"Kolommen: {list(vbo.columns)}")
print(f"\nDtypes:")
for col in vbo.columns:
    if col != 'geometry':
        print(f"  {col:30s} | {vbo[col].dtype} | nulls={vbo[col].isna().sum()} | unique={vbo[col].nunique()}")
print(f"\nSample (eerste 5, geen geometry):")
print(vbo.drop(columns='geometry').head(5).to_string())

# Check gebruiksdoel waarden
print(f"\n--- Gebruiksdoel verdeling ---")
if 'gebruiksdoel' in vbo.columns:
    print(vbo['gebruiksdoel'].value_counts().head(15))
elif 'gebruiksdoelen' in vbo.columns:
    print(vbo['gebruiksdoelen'].value_counts().head(15))
else:
    # Zoek naar kolommen die 'gebruik' bevatten
    gebruik_cols = [c for c in vbo.columns if 'gebruik' in c.lower()]
    print(f"  Geen 'gebruiksdoel' kolom. Gerelateerde kolommen: {gebruik_cols}")

# Check status waarden
if 'status' in vbo.columns:
    print(f"\n--- Status verdeling ---")
    print(vbo['status'].value_counts())

# 2. Panden
print("\n\n=== 2. PANDEN ===")
pnd = gpd.read_file(os.path.join(bag_dir, 'bag_data_bag_pand.gpkg'))
print(f"Records: {len(pnd)}")
print(f"Kolommen: {list(pnd.columns)}")
print(f"\nDtypes:")
for col in pnd.columns:
    if col != 'geometry':
        print(f"  {col:30s} | {pnd[col].dtype} | nulls={pnd[col].isna().sum()} | unique={pnd[col].nunique()}")
print(f"\nSample (eerste 5, geen geometry):")
print(pnd.drop(columns='geometry').head(5).to_string())

# Bouwjaar stats
if 'bouwjaar' in pnd.columns:
    print(f"\n--- Bouwjaar statistieken ---")
    print(f"  Min: {pnd['bouwjaar'].min()}")
    print(f"  Max: {pnd['bouwjaar'].max()}")
    print(f"  Mean: {pnd['bouwjaar'].mean():.0f}")
    print(f"  Median: {pnd['bouwjaar'].median():.0f}")
    print(f"  < 1945: {(pnd['bouwjaar'] < 1945).sum()} ({(pnd['bouwjaar'] < 1945).mean()*100:.1f}%)")
    print(f"  > 2000: {(pnd['bouwjaar'] > 2000).sum()} ({(pnd['bouwjaar'] > 2000).mean()*100:.1f}%)")
elif 'oorspronkelijkBouwjaar' in pnd.columns:
    col = 'oorspronkelijkBouwjaar'
    print(f"\n--- {col} statistieken ---")
    print(f"  Min: {pnd[col].min()}")
    print(f"  Max: {pnd[col].max()}")
    print(f"  Mean: {pnd[col].mean():.0f}")
else:
    bouwjaar_cols = [c for c in pnd.columns if 'bouw' in c.lower() or 'jaar' in c.lower()]
    print(f"  Geen 'bouwjaar' kolom. Gerelateerde: {bouwjaar_cols}")

# CRS info
print(f"\n=== CRS INFO ===")
print(f"VBO CRS: {vbo.crs}")
print(f"Panden CRS: {pnd.crs}")

print("\n✅ Inspectie voltooid")
