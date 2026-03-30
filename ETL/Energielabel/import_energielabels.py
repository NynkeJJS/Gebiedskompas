#!/usr/bin/env python3
"""
Import EP-Online Energielabel Data
Parses the large XML file and aggregates per buurt for Friese gemeenten.
Uses streaming parser to handle the 8GB file.
"""

import xml.etree.ElementTree as ET
from collections import defaultdict
import psycopg2
import os, sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))


# Energieklasse naar numerieke waarde (lagere waarde = beter label)
ENERGIEKLASSE_MAP = {
    'A+++++': 1.0,
    'A++++': 1.5,
    'A+++': 2.0,
    'A++': 2.5,
    'A+': 3.0,
    'A': 3.5,
    'B': 4.0,
    'C': 5.0,
    'D': 6.0,
    'E': 7.0,
    'F': 8.0,
    'G': 9.0,
}

# Numerieke waarde terug naar label
def value_to_label(value):
    if value <= 1.25: return 'A+++++'
    elif value <= 1.75: return 'A++++'
    elif value <= 2.25: return 'A+++'
    elif value <= 2.75: return 'A++'
    elif value <= 3.25: return 'A+'
    elif value <= 3.75: return 'A'
    elif value <= 4.5: return 'B'
    elif value <= 5.5: return 'C'
    elif value <= 6.5: return 'D'
    elif value <= 7.5: return 'E'
    elif value <= 8.5: return 'F'
    else: return 'G'

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=os.getenv('DATABASE_PORT', '5432'),
        dbname=os.getenv('DATABASE_NAME', 'omnitwin_db'),
        user=os.getenv('DATABASE_USER', 'omnitwin_user'),
        password=os.getenv('DATABASE_PASSWORD', ''),
        sslmode=os.getenv('DATABASE_SSLMODE', 'prefer')
    )

def load_pc6_buurt_mapping():
    """Load PC6 to Buurt mapping from JSON"""
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mapping_path = os.path.join(PROJECT_ROOT, 
                                'data', 'cbs_pc6_huisnr_buurt', 'pc6_buurt_mapping.json')
    with open(mapping_path, 'r') as f:
        return json.load(f)

def load_buurt_to_gebied_mapping(conn):
    """Map CBS buurtcode (00981101) to our gebied_id (BU00981101)"""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, REPLACE(id, 'BU', '') as cbs_code
        FROM gebieden 
        WHERE id LIKE 'BU%'
    """)
    return {row[1]: row[0] for row in cur.fetchall()}

def parse_energielabels_streaming(xml_path, pc6_to_buurt, limit=None):
    """
    Parse the large XML file using iterparse (streaming).
    Aggregates directly per buurt.
    """
    print(f"📖 Parsing {xml_path} (streaming)...")
    
    # definities voor aggregatie
    buurt_data = defaultdict(lambda: {
        'definitief_waarden': [],
        'voorlopig_count': 0,
        'totaal_count': 0
    })
    
    count = 0
    matched_count = 0
    
    context = ET.iterparse(xml_path, events=('end',))
    
    for event, elem in context:
        if 'Pandcertificaat' in elem.tag:
            try:
                # Extract properties
                postcode = None
                energieklasse = None
                gebouwklasse = None
                status = None
                
                for child in elem:
                    tag = child.tag.split('}')[-1]  # Remove namespace
                    if tag == 'Postcode':
                        postcode = child.text
                    elif tag == 'Energieklasse':
                        energieklasse = child.text
                    elif tag == 'Gebouwklasse':
                        gebouwklasse = child.text
                    elif tag == 'Status':
                        status = child.text
                
                # Filter op Gebouwklasse 'W' (Woningbouw)
                # En we hebben een postcode en energieklasse nodig
                if postcode and energieklasse and gebouwklasse == 'W' and postcode in pc6_to_buurt:
                    buurtcode = pc6_to_buurt[postcode]
                    numeric_val = ENERGIEKLASSE_MAP.get(energieklasse)
                    
                    if numeric_val is not None:
                        is_voorlopig = status and 'vergunning' in status.lower()
                        is_definitief = status and status.lower() in ['bestaand', 'oplevering']
                        
                        buurt_data[buurtcode]['totaal_count'] += 1
                        
                        if is_voorlopig:
                            buurt_data[buurtcode]['voorlopig_count'] += 1
                        elif is_definitief: # of gewoon else? Laten we strikt zijn en 'Bestaand'/'Oplevering' als definitief tellen
                            buurt_data[buurtcode]['definitief_waarden'].append(numeric_val)
                        
                        matched_count += 1
                
                count += 1
                if count % 500000 == 0:
                    print(f"   Processed {count:,} records, matched to buurten: {matched_count:,}")
                
                if limit and count >= limit:
                    break
                    
            except Exception as e:
                pass
            
            elem.clear()
    
    print(f"✅ Parsed {count:,} records total, {matched_count:,} matched to Friese buurten")
    return buurt_data

def import_to_database(buurt_aggregates, buurt_to_gebied, conn):
    """Import aggregated data to database"""
    cur = conn.cursor()
    
    # Get or create indicator UUIDs
    indicators = {
        'Gemiddeld energielabel': None,
        'Aantal energielabels (definitief)': None,
        'Aantal energielabels (voorlopig)': None,
        'Aantal energielabels (totaal)': None,
    }
    
    # Definities voor nieuwe indicatoren
    definities = {
        'Gemiddeld energielabel': {
            'code': 'gemiddeld_energielabel',
            'eenheid': 'labelklasse',
            'omschrijving': 'Gemiddeld energielabel van definitieve labels (Bestaand/Oplevering)'
        },
        'Aantal energielabels (definitief)': {
            'code': 'aantal_energielabels_definitief',
            'eenheid': 'aantal',
            'omschrijving': 'Aantal definitieve energielabels (Status: Bestaand of Oplevering)'
        },
        'Aantal energielabels (voorlopig)': {
            'code': 'aantal_energielabels_voorlopig',
            'eenheid': 'aantal',
            'omschrijving': 'Aantal voorlopige energielabels (Status: Vergunningsaanvraag)'
        },
        'Aantal energielabels (totaal)': {
            'code': 'aantal_energielabels',
            'eenheid': 'aantal',
            'omschrijving': 'Totaal aantal geregistreerde energielabels (Definitief + Voorlopig)'
        }
    }
    
    for name in indicators:
        cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (name,))
        result = cur.fetchone()
        if result:
            indicators[name] = result[0]
            print(f"ℹ️  Indicator exists: {name}")
        else:
            # Create indicator (or get existing) safely with SQL
            definitie = definities.get(name, {})
            
            # 1. Try insert with ON CONFLICT DO NOTHING on unique constraint (code)
            # Note: code implies uniqueness in schema
            cur.execute("""
                INSERT INTO indicatoren (naam, code, eenheid, omschrijving, bron, interpretatie_logica)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING
            """, (name, definitie.get('code'), 
                  definitie.get('eenheid'), 
                  definitie.get('omschrijving'),
                  'RVO EP-Online',
                  'N/A'))
            
            # 2. Retrieve UUID (whether inserted or existing)
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (name,))
            res = cur.fetchone()
            if res:
                indicators[name] = res[0]
                print(f"✅ Indicator ready: {name}")
            else:
                print(f"❌ Failed to get UUID for {name} - check definitions!")
                continue
                
    conn.commit() # Commit indicators immediately!
    sys.stdout.flush()
    
    # Import data per buurt
    inserted = 0
    updated = 0
    
    for cbs_buurt, stats in buurt_aggregates.items():
        if cbs_buurt not in buurt_to_gebied:
            continue
        
        gebied_id = buurt_to_gebied[cbs_buurt]
        
        # Extract values
        def_waarden = stats['definitief_waarden']
        count_voorlopig = stats['voorlopig_count']
        count_totaal = stats['totaal_count']
        count_definitief = len(def_waarden)
        
        avg_definitief = sum(def_waarden) / len(def_waarden) if def_waarden else 0
        
        # Data points to insert
        data_points = [
            ('Aantal energielabels (definitief)', count_definitief),
            ('Aantal energielabels (voorlopig)', count_voorlopig),
            ('Aantal energielabels (totaal)', count_totaal)
        ]
        
        if avg_definitief > 0:
            data_points.append(('Gemiddeld energielabel', avg_definitief))
        
        for ind_name, val in data_points:
            ind_uuid = indicators.get(ind_name)
            if not ind_uuid: 
                continue # Should not happen if indicators dict is correct
            
            # Check if exists
            cur.execute("""
                SELECT id FROM gebied_data 
                WHERE gebied_id = %s AND indicator_uuid = %s AND jaar = 2025
            """, (gebied_id, ind_uuid))
            
            if cur.fetchone():
                cur.execute("""
                    UPDATE gebied_data 
                    SET waarde = %s, bron = %s
                    WHERE gebied_id = %s AND indicator_uuid = %s AND jaar = 2025
                """, (val, 'RVO EP-Online 2026-02', gebied_id, ind_uuid))
                updated += 1
            else:
                cur.execute("""
                    INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron)
                    VALUES (%s, %s, %s, %s, %s)
                """, (gebied_id, ind_uuid, val, 2025, 'RVO EP-Online 2026-02'))
                inserted += 1
    
    conn.commit()
    print(f"✅ Inserted {inserted}, updated {updated} records")
    return inserted + updated

def main():
    print("🚀 EP-Online Energielabel Import (Full Version)")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    xml_path = os.path.join(PROJECT_ROOT, 
                           'data', 'ep-online', 'extracted_v20260202_v4_xml', 'v20260202_v4_xml.xml')
    
    if not os.path.exists(xml_path):
        print(f"❌ File not found: {xml_path}")
        return
    
    # Load mappings
    print("\n📂 Loading mappings...")
    pc6_to_buurt = load_pc6_buurt_mapping()
    print(f"   PC6 -> Buurt: {len(pc6_to_buurt)} postcodes")
    
    conn = get_db_connection()
    buurt_to_gebied = load_buurt_to_gebied_mapping(conn)
    print(f"   Buurt -> Gebied: {len(buurt_to_gebied)} buurten")
    
    # Parse XML (streaming) - FULL DATASET
    buurt_data = parse_energielabels_streaming(xml_path, pc6_to_buurt, limit=None)
    
    print(f"\n📊 Buurten with data: {len(buurt_data)}")
    
    # Show sample
    print("\n=== SAMPLE DATA (first 10 buurten) ===")
    for buurt, stats in list(buurt_data.items())[:10]:
        def_waarden = stats['definitief_waarden']
        count_totaal = stats['totaal_count']
        avg = sum(def_waarden) / len(def_waarden) if def_waarden else 0
        label = value_to_label(avg)
        print(f"  {buurt}: {count_totaal} labels (def={len(def_waarden)}, voorlopig={stats['voorlopig_count']}), avg {avg:.2f} = {label}")
    
    # Import to database
    print("\n📥 Importing to database...")
    total = import_to_database(buurt_data, buurt_to_gebied, conn)
    
    conn.close()
    print(f"\n✅ Done: {datetime.now()}")
    print(f"📊 Total records: {total}")

if __name__ == "__main__":
    main()
