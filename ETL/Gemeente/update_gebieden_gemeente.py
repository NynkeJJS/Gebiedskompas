#!/usr/bin/env python3
"""
Update gebieden tabel met gemeente informatie uit CBS GeoPackage

Dit script leest de 'gemeentenaam' kolom uit de CBS buurten GeoPackage
en werkt de gebieden tabel bij met de juiste gemeente_code en provincienaam.

Gebruik:
    .venv/bin/python scripts/update_gebieden_gemeente.py

Vereisten:
    - psycopg2 (database connectie)
    - geopandas (GeoPackage lezen)
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from configparser import ConfigParser

# ============================================================================
# CONFIGURATIE
# ============================================================================

# GeoPackage bronbestand
GPKG_PATH = project_root / "data" / "voorbeeld_gebiedsmonitor" / "frl_cbs_buurten.gpkg"

# Mapping van gemeentenaam (uit brondata) naar gemeente_code (CBS)
# Bron: CBS gemeentecodes per 1 januari 2026
FRIESE_GEMEENTEN = {
    'Achtkarspelen': '0059',
    'Ameland': '0060',
    'Dantumadiel': '1891',
    'De Fryske Marren': '1921',
    'Harlingen': '0072',
    'Heerenveen': '0074',
    'Leeuwarden': '0080',
    'Noardeast-Fryslân': '1970',
    'Ooststellingwerf': '0085',
    'Opsterland': '0086',
    'Schiermonnikoog': '0088',
    'Smallingerland': '0140',
    'Súdwest-Fryslân': '1900',
    'Terschelling': '0093',
    'Tytsjerksteradiel': '0737',
    'Vlieland': '0096',
    'Waadhoeke': '1949',
    'Weststellingwerf': '0098',
}

# Alle Friese gemeenten krijgen provincie 'Fryslân'
PROVINCIE = 'Fryslân'


def get_db_config():
    """Lees database configuratie uit config.ini of .env"""
    config_path = project_root / "config.ini"
    
    if config_path.exists():
        config = ConfigParser()
        config.read(config_path)
        
        return {
            'host': config.get('DATABASE', 'host', fallback='localhost'),
            'port': config.get('DATABASE', 'port', fallback='5432'),
            'database': config.get('DATABASE', 'dbname', fallback='omnitwin_db'),
            'user': config.get('DATABASE', 'user', fallback='omnitwin_user'),
            'password': config.get('DATABASE', 'password', fallback=''),
        }
    else:
        # Fallback naar environment variables
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'omnitwin_db'),
            'user': os.getenv('DB_USER', 'omnitwin_user'),
            'password': os.getenv('DB_PASSWORD', ''),
        }


def load_gemeente_mapping_from_gpkg():
    """
    Laad buurtcode -> gemeentenaam mapping uit GeoPackage
    
    Returns:
        dict: {buurtcode: gemeentenaam}
    """
    try:
        import geopandas as gpd
        
        print(f"📂 Laden: {GPKG_PATH}")
        gdf = gpd.read_file(GPKG_PATH)
        
        # Maak mapping: buurtcode -> gemeentenaam
        mapping = {}
        for _, row in gdf.iterrows():
            buurtcode = row.get('buurtcode') or row.get('statcode')
            gemeentenaam = row.get('gemeentenaam')
            
            if buurtcode and gemeentenaam:
                mapping[buurtcode] = gemeentenaam
        
        print(f"✅ {len(mapping)} buurten geladen")
        return mapping
        
    except Exception as e:
        print(f"❌ Fout bij laden GeoPackage: {e}")
        return {}


def update_gebieden(buurt_gemeente_mapping):
    """
    Update gebieden tabel met gemeente informatie
    
    Args:
        buurt_gemeente_mapping: dict {buurtcode: gemeentenaam}
    """
    db_config = get_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Haal ALLE gebieden op (update alles, niet alleen NULL)
        cursor.execute("""
            SELECT id, naam 
            FROM gebieden 
        """)
        gebieden = cursor.fetchall()
        
        print(f"📋 {len(gebieden)} gebieden te checken")
        
        updated = 0
        skipped = 0
        not_found = 0
        
        for gebied_id, gebied_naam in gebieden:
            # Zoek gemeentenaam op basis van buurtcode (gebied_id)
            gemeentenaam = buurt_gemeente_mapping.get(gebied_id)
            
            if gemeentenaam and gemeentenaam in FRIESE_GEMEENTEN:
                gemeente_code = FRIESE_GEMEENTEN[gemeentenaam]
                
                cursor.execute("""
                    UPDATE gebieden 
                    SET gemeente_code = %s, provincienaam = %s
                    WHERE id = %s
                """, (gemeente_code, PROVINCIE, gebied_id))
                
                updated += 1
            elif gemeentenaam:
                # Gemeente niet in Fryslân, zet naar NULL
                cursor.execute("""
                    UPDATE gebieden 
                    SET gemeente_code = NULL, provincienaam = NULL
                    WHERE id = %s
                """, (gebied_id,))
                skipped += 1
            else:
                not_found += 1
        
        conn.commit()
        
        print(f"✅ {updated} gebieden geüpdatet met Friese gemeente")
        print(f"⏭️  {skipped} gebieden buiten Fryslân (NULL gezet)")
        print(f"❓ {not_found} gebieden niet gevonden in brondata")
        
        # Verificatie
        cursor.execute("""
            SELECT gemeente_code, COUNT(*) 
            FROM gebieden 
            GROUP BY gemeente_code
            ORDER BY COUNT(*) DESC
        """)
        stats = cursor.fetchall()
        
        print("\n📊 Gemeente verdeling:") 
        for code, count in stats:
            if code:
                # Lookup naam
                naam = next((k for k, v in FRIESE_GEMEENTEN.items() if v == code), code)
                print(f"   {naam} ({code}): {count} gebieden")
            else:
                print(f"   NULL (buiten Fryslân): {count} gebieden")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database fout: {e}")
        raise


def main():
    print("=" * 60)
    print("UPDATE GEBIEDEN MET GEMEENTE INFORMATIE")
    print("=" * 60)
    
    # Stap 1: Laad mapping uit GeoPackage
    buurt_mapping = load_gemeente_mapping_from_gpkg()
    
    if not buurt_mapping:
        print("⚠️  Geen mapping geladen, exit")
        return
    
    # Toon gevonden gemeenten
    unique_gemeenten = set(buurt_mapping.values())
    print(f"\n🏘️  Gevonden gemeenten ({len(unique_gemeenten)}):")
    for g in sorted(unique_gemeenten):
        code = FRIESE_GEMEENTEN.get(g, '???')
        print(f"   {g}: {code}")
    
    # Stap 2: Update database
    print("\n📝 Updaten gebieden...")
    update_gebieden(buurt_mapping)
    
    print("\n✅ Klaar!")


if __name__ == "__main__":
    main()
