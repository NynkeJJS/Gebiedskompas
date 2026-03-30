#!/usr/bin/env python3
"""
Enrich Indicator Metadata
Reads CBS metadata files and updates indicator omschrijving/eenheid in database.
"""

import os
import sys
import json
import glob
import psycopg2
import configparser

def get_db_connection():
    """Create database connection"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config.read(config_path)
    
    return psycopg2.connect(
        host=config['DATABASE']['host'],
        port=config['DATABASE']['port'],
        dbname=config['DATABASE']['dbname'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password']
    )

def load_metadata_from_files(metadata_dir):
    """Load all metadata from CBS JSON files"""
    metadata_map = {}  # title -> {description, unit}
    
    # Find all metadata files
    pattern = os.path.join(metadata_dir, "*_METADATA.json")
    files = glob.glob(pattern)
    
    print(f"📂 Found {len(files)} metadata files")
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            props = data.get('metadata', {}).get('properties', [])
            
            for p in props:
                title = p.get('title', '').strip()
                if not title:
                    continue
                    
                metadata_map[title] = {
                    'description': p.get('description', ''),
                    'unit': p.get('unit', ''),
                    'key': p.get('key', '')
                }
                
                # Also map by cleaned title (for fuzzy matching)
                clean_title = title.replace(' ', '').lower()
                metadata_map[clean_title] = metadata_map[title]
                
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")
    
    print(f"📊 Loaded metadata for {len(metadata_map)} properties")
    return metadata_map

def find_best_match(indicator_naam, metadata_map):
    """Find best matching metadata for an indicator name"""
    # Try exact match
    if indicator_naam in metadata_map:
        return metadata_map[indicator_naam]
    
    # Try cleaned match
    clean_name = indicator_naam.replace(' ', '').lower()
    if clean_name in metadata_map:
        return metadata_map[clean_name]
    
    # Try partial match
    for title, meta in metadata_map.items():
        if isinstance(title, str):
            if indicator_naam.lower() in title.lower() or title.lower() in indicator_naam.lower():
                return meta
    
    return None

# Mapping van onze indicator namen naar CBS titels
INDICATOR_MAPPING = {
    'Koopwoningen': 'Koopwoningen',
    'Woningcorporatie bezit': 'In bezit woningcorporatie',
    'Particulier huurbezit': 'In bezit overige verhuurders',
    'Gemiddelde WOZ-waarde': 'Gemiddelde WOZ-waarde van woningen',
    'Bevolkingsdichtheid': 'Bevolkingsdichtheid',
    'Inkomen per inwoner': 'Gemiddeld inkomen per inwoner',
    'Huishoudens met laag inkomen': 'Huishoudens met een laag inkomen',
    'Afstand tot huisarts': 'Afstand tot huisartsenpraktijk',
    'Afstand tot kinderdagverblijf': 'Afstand tot kinderdagverblijf',
    'Afstand tot school': 'Afstand tot school',
    'Afstand tot grote supermarkt': 'Afstand tot grote supermarkt',
    'Huishoudens totaal': 'Huishoudens totaal',
    'Huishoudens met kind': 'Huishoudens met kinderen',
    'Huishoudens zonder kind': 'Huishoudens zonder kinderen',
    "Personenauto's per huishouden": "Personenauto's per huishouden",
    "Personenauto's naar oppervlakte": "Personenauto's naar oppervlakte",
    # RIVM indicatoren
    'Roker': 'Rookt',
    'Overgewicht': 'Overgewicht',
    'Obesitas': 'Ernstig overgewicht (obesitas)',
    'Eenzaam': 'Eenzaam',
    'Ervaren gezondheid': 'Goed ervaren gezondheid',
    'Overmatig alcoholgebruik': 'Overmatig drinken',
    'Moeite met rondkomen': 'Moeite met rondkomen',
}

def main():
    print("🔄 Enriching Indicator Metadata")
    print("=" * 60)
    
    # Load metadata from files
    base_path = os.path.dirname(__file__)
    metadata_dirs = [
        os.path.join(base_path, '..', 'data', 'temp_cbs_import'),
        os.path.join(base_path, '..', 'data', 'ETL_Scripts', 'CBS', 'output'),
    ]
    
    metadata_map = {}
    for d in metadata_dirs:
        if os.path.exists(d):
            metadata_map.update(load_metadata_from_files(d))
    
    if not metadata_map:
        print("❌ No metadata found!")
        return
    
    # Connect to database
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    # Get all indicators without omschrijving
    cur.execute("""
        SELECT uuid, naam, code, omschrijving, eenheid 
        FROM indicatoren
        WHERE omschrijving IS NULL OR eenheid IS NULL
    """)
    
    indicators = cur.fetchall()
    print(f"\n📋 Found {len(indicators)} indicators to update")
    
    updated = 0
    
    for ind_uuid, naam, code, current_omschr, current_eenheid in indicators:
        # Try mapping first
        cbs_title = INDICATOR_MAPPING.get(naam, naam)
        
        meta = find_best_match(cbs_title, metadata_map)
        
        if not meta:
            continue
        
        # Build update
        updates = []
        params = []
        
        if not current_omschr and meta.get('description'):
            updates.append("omschrijving = %s")
            params.append(meta['description'][:2000])  # Limit length
        
        if not current_eenheid and meta.get('unit'):
            updates.append("eenheid = %s")
            params.append(meta['unit'])
        
        if updates:
            params.append(ind_uuid)
            query = f"UPDATE indicatoren SET {', '.join(updates)} WHERE uuid = %s"
            cur.execute(query, params)
            print(f"✅ Updated: {naam}")
            updated += 1
    
    print(f"\n{'='*60}")
    print(f"🏁 Updated {updated} indicators with metadata")
    
    conn.close()

if __name__ == "__main__":
    main()
