#!/usr/bin/env python3
"""
Import Kompas Hiërarchie uit indicator_testlijst.csv
=====================================================

Leest de CSV file met 5-niveau hiërarchie en vult de kompas_* tabellen:
1. kompas_titels      (Title kolom)
2. kompas_themas      (Thema kolom)
3. kompas_onderdelen  (Onderdeel kolom)
4. kompas_extra_onderdelen (Extra onderdeel kolom - JSON array tags)
5. kompas_indicator_mapping + kompas_indicator_extra_tags

Gebruik:
    python scripts/import_kompas_hierarchie.py

Datum: 2026-01-21
"""

import csv
import json
import re
import psycopg2
from pathlib import Path
import configparser

# ============================================================================
# Configuratie
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config.ini'
CSV_PATH = PROJECT_ROOT / 'data' / 'voorbeeld_gebiedsmonitor' / 'indicator_testlijst.csv'

def get_db_connection():
    """Haal database connectie op uit config.ini"""
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    
    db = config['DATABASE']
    return psycopg2.connect(
        host=db['host'],
        port=db['port'],
        dbname=db['dbname'],
        user=db['user'],
        password=db['password']
    )

def parse_extra_onderdeel(value: str) -> list:
    """
    Parse de 'Extra onderdeel' kolom die JSON arrays bevat.
    Voorbeelden:
      - '["Wateroverlast"]' → ['Wateroverlast']
      - '["Hitte","Wateroverlast"]' → ['Hitte', 'Wateroverlast']
      - '' of None → []
    """
    if not value or value.strip() == '':
        return []
    
    try:
        # Probeer JSON parse
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item]
        return []
    except json.JSONDecodeError:
        # Fallback: probeer als komma-gescheiden string
        return [item.strip().strip('"') for item in value.split(',') if item.strip()]

def get_or_create_titel(cursor, naam: str) -> int:
    """Haal titel ID op of maak nieuwe aan."""
    cursor.execute(
        "SELECT id FROM kompas_titels WHERE naam = %s",
        (naam,)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    
    cursor.execute(
        "INSERT INTO kompas_titels (naam) VALUES (%s) RETURNING id",
        (naam,)
    )
    return cursor.fetchone()[0]

def get_or_create_thema(cursor, naam: str, titel_id: int) -> int:
    """Haal thema ID op of maak nieuwe aan."""
    cursor.execute(
        "SELECT id FROM kompas_themas WHERE naam = %s AND titel_id = %s",
        (naam, titel_id)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    
    cursor.execute(
        "INSERT INTO kompas_themas (naam, titel_id) VALUES (%s, %s) RETURNING id",
        (naam, titel_id)
    )
    return cursor.fetchone()[0]

def get_or_create_onderdeel(cursor, naam: str, thema_id: int) -> int:
    """Haal onderdeel ID op of maak nieuwe aan."""
    if not naam or naam.strip() == '':
        # Als onderdeel leeg is, gebruik een placeholder
        naam = "(Algemeen)"
    
    cursor.execute(
        "SELECT id FROM kompas_onderdelen WHERE naam = %s AND thema_id = %s",
        (naam, thema_id)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    
    cursor.execute(
        "INSERT INTO kompas_onderdelen (naam, thema_id) VALUES (%s, %s) RETURNING id",
        (naam, thema_id)
    )
    return cursor.fetchone()[0]

def get_or_create_extra_onderdeel(cursor, naam: str) -> int:
    """Haal extra onderdeel ID op of maak nieuwe aan."""
    cursor.execute(
        "SELECT id FROM kompas_extra_onderdelen WHERE naam = %s",
        (naam,)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    
    cursor.execute(
        "INSERT INTO kompas_extra_onderdelen (naam) VALUES (%s) RETURNING id",
        (naam,)
    )
    return cursor.fetchone()[0]

def find_indicator_uuid(cursor, indicator_swf: str, indicator_naam: str) -> str:
    """
    Zoek indicator UUID in de database.
    Probeert eerst 'Indicator SWF' naam, daarna 'Indicator' naam.
    """
    # Probeer eerst de SWF naam
    if indicator_swf and indicator_swf.strip():
        cursor.execute(
            "SELECT uuid FROM indicatoren WHERE naam ILIKE %s LIMIT 1",
            (indicator_swf.strip(),)
        )
        result = cursor.fetchone()
        if result:
            return str(result[0])
    
    # Probeer de gewone indicator naam
    if indicator_naam and indicator_naam.strip():
        cursor.execute(
            "SELECT uuid FROM indicatoren WHERE naam ILIKE %s LIMIT 1",
            (indicator_naam.strip(),)
        )
        result = cursor.fetchone()
        if result:
            return str(result[0])
    
    return None

def import_kompas_hierarchie():
    """Hoofdfunctie: importeer de CSV naar de database."""
    print("=" * 60)
    print("KOMPAS HIËRARCHIE IMPORT")
    print("=" * 60)
    print(f"CSV: {CSV_PATH}")
    print()
    
    if not CSV_PATH.exists():
        print(f"❌ CSV bestand niet gevonden: {CSV_PATH}")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Statistieken
    stats = {
        'titels': set(),
        'themas': set(),
        'onderdelen': set(),
        'extra_onderdelen': set(),
        'indicators_linked': 0,
        'indicators_not_found': 0,
        'rows_processed': 0
    }
    
    try:
        # Lees CSV (utf-8-sig voor BOM handling)
        with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                stats['rows_processed'] += 1
                
                # Haal kolommen op (let op spatie na 'Onderdeel ')
                titel_naam = row.get('Title', '').strip()
                thema_naam = row.get('Thema', '').strip()
                onderdeel_naam = row.get('Onderdeel ', '').strip()  # Let op spatie!
                extra_onderdeel_raw = row.get('Extra onderdeel', '')
                indicator_naam = row.get('Indicator', '').strip()
                indicator_actueel = row.get('Indicator actueel', '').strip().upper() == 'J'
                indicator_swf = row.get('Indicator SWF', '').strip()
                
                # Skip lege/test rijen
                if not titel_naam or titel_naam.lower() == 'test3':
                    continue
                if not thema_naam:
                    continue
                
                # Niveau 1: Titel
                titel_id = get_or_create_titel(cursor, titel_naam)
                stats['titels'].add(titel_naam)
                
                # Niveau 2: Thema
                thema_id = get_or_create_thema(cursor, thema_naam, titel_id)
                stats['themas'].add(f"{titel_naam} > {thema_naam}")
                
                # Niveau 3: Onderdeel
                onderdeel_id = get_or_create_onderdeel(cursor, onderdeel_naam, thema_id)
                stats['onderdelen'].add(f"{thema_naam} > {onderdeel_naam}")
                
                # Niveau 4: Extra onderdelen (tags)
                extra_tags = parse_extra_onderdeel(extra_onderdeel_raw)
                extra_ids = []
                for tag in extra_tags:
                    if tag:
                        extra_id = get_or_create_extra_onderdeel(cursor, tag)
                        extra_ids.append(extra_id)
                        stats['extra_onderdelen'].add(tag)
                
                # Niveau 5: Indicator koppeling
                indicator_uuid = find_indicator_uuid(cursor, indicator_swf, indicator_naam)
                
                if indicator_uuid:
                    # Insert mapping (ignore if exists)
                    cursor.execute("""
                        INSERT INTO kompas_indicator_mapping 
                            (indicator_uuid, onderdeel_id, is_actueel, indicator_swf, config_id)
                        VALUES (%s, %s, %s, %s, 1)
                        ON CONFLICT (indicator_uuid, onderdeel_id, config_id) DO UPDATE SET
                            is_actueel = EXCLUDED.is_actueel,
                            indicator_swf = EXCLUDED.indicator_swf
                    """, (indicator_uuid, onderdeel_id, indicator_actueel, indicator_swf or indicator_naam))
                    
                    # Link extra tags
                    for extra_id in extra_ids:
                        cursor.execute("""
                            INSERT INTO kompas_indicator_extra_tags 
                                (indicator_uuid, extra_onderdeel_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                        """, (indicator_uuid, extra_id))
                    
                    stats['indicators_linked'] += 1
                else:
                    stats['indicators_not_found'] += 1
                    if indicator_actueel:  # Log alleen als indicator "actueel" is
                        print(f"  ⚠️  Indicator niet gevonden: '{indicator_swf or indicator_naam}'")
        
        conn.commit()
        
        # Print resultaten
        print()
        print("✅ IMPORT VOLTOOID")
        print("-" * 40)
        print(f"📊 Rijen verwerkt:        {stats['rows_processed']}")
        print(f"📁 Titels aangemaakt:     {len(stats['titels'])}")
        print(f"📂 Thema's aangemaakt:    {len(stats['themas'])}")
        print(f"📄 Onderdelen aangemaakt: {len(stats['onderdelen'])}")
        print(f"🏷️  Extra tags aangemaakt: {len(stats['extra_onderdelen'])}")
        print(f"🔗 Indicatoren gekoppeld: {stats['indicators_linked']}")
        print(f"❓ Indicatoren niet gevonden: {stats['indicators_not_found']}")
        print()
        
        # Toon hiërarchie samenvatting
        print("📋 TITELS:")
        for titel in sorted(stats['titels']):
            print(f"   • {titel}")
        
        print()
        print("🏷️  EXTRA ONDERDEEL TAGS:")
        for tag in sorted(stats['extra_onderdelen']):
            print(f"   • {tag}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Fout tijdens import: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    import_kompas_hierarchie()
