#!/usr/bin/env python3
"""
Import Geometrie Data
Importeert gebiedsgeometrieën uit GeoJSON (Welstandsgebieden) en GPKG (CBS Buurten).
"""
import json
import sqlite3
import psycopg2
import configparser
import os

def get_db_connection():
    """Maak database connectie op basis van config.ini"""
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

def import_welstandsgebieden(geojson_path, conn):
    """Import Welstandsgebieden uit GeoJSON"""
    print(f"🗺️  Verwerken GeoJSON: {os.path.basename(geojson_path)}")
    
    with open(geojson_path, encoding='utf-8') as f:
        geojson = json.load(f)
    
    gebiedstype_id = '29fc9f28-89d9-488b-bf68-2ed176187b21'  # Welstandsgebieden
    
    with conn.cursor() as cur:
        count = 0
        for feature in geojson['features']:
            props = feature['properties']
            geom = feature['geometry']
            
            cur.execute("""
                INSERT INTO gebieden 
                    (id, gebiedstype_id, naam, geom, metadata)
                VALUES (
                    %(code)s, %(type_id)s, %(naam)s, 
                    ST_Multi(ST_CollectionExtract(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 28992), 3)), 
                    %(metadata)s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    geom = EXCLUDED.geom,
                    metadata = EXCLUDED.metadata;
            """, {
                'code': str(props['gebieds_id']),
                'type_id': gebiedstype_id,
                'naam': props['gebieds_naam'],
                'geom': json.dumps(geom),
                'metadata': json.dumps({'aanduiding': props.get('aanduiding')})
            })
            count += 1
        
        conn.commit()
        print(f"✅ {count} welstandsgebieden geïmporteerd")

def import_cbs_buurten_gpkg(gpkg_path, conn):
    """Import CBS Buurten uit GeoPackage (SQLite)"""
    print(f"📦 Verwerken GPKG: {os.path.basename(gpkg_path)}")
    
    # Lees GPKG via SQLite
    gpkg_conn = sqlite3.connect(gpkg_path)
    cur_gpkg = gpkg_conn.cursor()
    
    # Haal kolomnamen op
    cur_gpkg.execute("PRAGMA table_info(frl_cbs_buurten)")
    columns = [col[1] for col in cur_gpkg.fetchall()]
    
    # Query alle data
    cur_gpkg.execute("SELECT * FROM frl_cbs_buurten")
    rows = cur_gpkg.fetchall()
    
    gebiedstype_id = 'afba67cb-6b38-4723-9c95-102a22d5b38a'  # CBS Buurten
    
    # Use autocommit mode for individual error handling
    conn.autocommit = True
    
    count = 0
    errors = 0
    for row in rows:
        try:
            row_dict = dict(zip(columns, row))
            
            # Extract kernwaarden
            buurt_code = row_dict.pop('buurtcode', None)
            buurt_naam = row_dict.pop('buurtnaam', 'Onbekend')
            geom_wkb = row_dict.pop('geom', None)
            
            if not buurt_code or not geom_wkb:
                errors += 1
                continue
            
            # Filter metadata
            metadata = {k: v for k, v in row_dict.items() 
                       if v is not None and k not in ['fid']}
            
            # Extract gemeente code (verwacht GMxxxx format)
            gm_code_raw = row_dict.get('gm_code') or row_dict.get('gemeentecode')
            gemeente_code = None
            if gm_code_raw:
                # Strip 'GM' prefix if present
                gemeente_code = gm_code_raw.replace('GM', '') if isinstance(gm_code_raw, str) else str(gm_code_raw)
            
            # Default provincie (TODO: eventueel uit data halen indien aanwezig)
            provincienaam = 'Fryslân'

            with conn.cursor() as cur_pg:
                # Insert met WKB - GPKG WKB starts with GP header, strip it
                # GPKG uses its own binary format, need to extract standard WKB
                if geom_wkb[:2] == b'GP':
                    # GeoPackage format - extract actual geometry
                    # Header: GP (2) + version (1) + flags (1) + srid (4) + envelope (varies)
                    flags = geom_wkb[3]
                    envelope_indicator = (flags >> 1) & 0x07
                    
                    envelope_len = 0
                    if envelope_indicator == 1:
                        envelope_len = 32
                    elif envelope_indicator == 2 or envelope_indicator == 3:
                        envelope_len = 48
                    elif envelope_indicator == 4:
                        envelope_len = 64
                        
                    wkb_start = 8 + envelope_len
                    actual_wkb = geom_wkb[wkb_start:]
                else:
                    actual_wkb = geom_wkb
                
                cur_pg.execute("""
                    INSERT INTO gebieden 
                        (id, gebiedstype_id, naam, geom, metadata, gemeente_code, provincienaam)
                    VALUES (
                        %(id)s, %(type_id)s, %(naam)s,
                        ST_Multi(ST_GeomFromWKB(%(geom_wkb)s, 28992)),
                        %(metadata)s::jsonb,
                        %(gemeente_code)s,
                        %(provincienaam)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        naam = EXCLUDED.naam,
                        geom = EXCLUDED.geom,
                        metadata = EXCLUDED.metadata,
                        gemeente_code = EXCLUDED.gemeente_code,
                        provincienaam = EXCLUDED.provincienaam;
                """, {
                    'id': buurt_code,
                    'type_id': gebiedstype_id,
                    'naam': buurt_naam,
                    'geom_wkb': actual_wkb,
                    'metadata': json.dumps(metadata),
                    'gemeente_code': gemeente_code,
                    'provincienaam': provincienaam
                })
            count += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"⚠️  Fout bij buurt {buurt_code if 'buurt_code' in dir() else '?'}: {e}")
    
    conn.autocommit = False
    gpkg_conn.close()
    print(f"✅ {count} CBS buurten geïmporteerd ({errors} fouten)")

def main():
    print("🚀 Start Geometrie Import")
    print("=" * 50)
    
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'voorbeeld_gebiedsmonitor')
    
    conn = get_db_connection()
    print("✅ Database verbinding gemaakt")
    
    # 1. Welstandsgebieden (GeoJSON)
    json_path = os.path.join(base_dir, 'Welstandsgebieden_buitengebied_per_buurt.json')
    if os.path.exists(json_path):
        import_welstandsgebieden(json_path, conn)
    else:
        print(f"⚠️  GeoJSON niet gevonden: {json_path}")
        
    # 2. CBS Buurten (GPKG)
    gpkg_path = os.path.join(base_dir, 'frl_cbs_buurten.gpkg')
    if os.path.exists(gpkg_path):
        import_cbs_buurten_gpkg(gpkg_path, conn)
    else:
        print(f"⚠️  GPKG niet gevonden: {gpkg_path}")
    
    conn.close()
    print("=" * 50)
    print("🎉 Geometrie import voltooid!")

if __name__ == "__main__":
    main()
