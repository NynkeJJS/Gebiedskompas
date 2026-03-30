#!/usr/bin/env python3
"""
Import CBS Data
Orchestrates the fetching and importing of CBS data based on configuration mapping.
"""

import sys
import os
import json
import psycopg2
import configparser
from datetime import datetime
import glob

# Fetcher is in same directory
# etl_scripts_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ETL_Scripts', 'CBS')
# sys.path.append(etl_scripts_path)

try:
    from cbs_data_fetcher import CBSDataFetcher
except ImportError as e:
    print(f"❌ Critical: Could not import CBSDataFetcher: {e}")
    print(f"   Path: {etl_scripts_path}")
    sys.exit(1)

def get_db_connection():
    """Create database connection"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config = configparser.ConfigParser()
    print("Zoekt config op:", config_path)

    read_files = config.read(config_path)
    print("Bestanden die echt gelezen zijn:", read_files)

    print("Secties gevonden:", config.sections())
    config.read(config_path)
    config.read(config_path)
    
    return psycopg2.connect(
        host=config['DATABASE']['host'],
        port=config['DATABASE']['port'],
        dbname=config['DATABASE']['dbname'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password']
    )

def load_json_file(filepath):
    """Safe load JSON file"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)



def ensure_indicator_exists(conn, naam, code=None, eenheid=None, omschrijving=None, bron=None):
    """
    Check if indicator exists, otherwise create it.
    Returns the UUID of the indicator.
    """
    try:
        with conn.cursor() as cur:
            # Check by code first if provided (more reliable)
            if code:
                cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
                result = cur.fetchone()
                if result:
                    return result[0]

            # Check by name
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (naam,))
            result = cur.fetchone()
            
            if result:
                return result[0]
            
            # Create new indicator
            print(f"✨ Creating new indicator: {naam}")
            try:
                cur.execute("""
                    INSERT INTO indicatoren (naam, code, eenheid, omschrijving, status, bron)
                    VALUES (%s, %s, %s, %s, 'O', %s)
                    RETURNING uuid
                """, (naam, code, eenheid, omschrijving, bron))
                new_uuid = cur.fetchone()[0]
                conn.commit()
                return new_uuid
            except psycopg2.errors.UniqueViolation:
                # Race condition or it existed by code/name but we missed it?
                conn.rollback()
                print(f"⚠️  Indicator {naam} ({code}) already exists (caught UniqueViolation), retrieving...")
                with conn.cursor() as cur2:
                     if code:
                        cur2.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
                     else:
                        cur2.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (naam,))
                     return cur2.fetchone()[0]
                     
    except Exception as e:
        conn.rollback()
        print(f"❌ Error in ensure_indicator_exists: {e}")
        raise

def get_gebied_id_by_code(conn, code):
    """Resolve CBS code (e.g., GM1900) to internal gebied_id"""
    if not code:
        return None
        
    # Formatting: CBS often uses 'GM1900' but sometimes just '1900' or 'WK190012'
    # Check if 'code' column in gebieden table matches
    # Usually in current setup 'id' IS the code (e.g. BU1900xxxx)
    # But filtering often happens on 'GM1900'.
    
    # Logic: We are importing data for WIJKEN and BUURTEN mostly.
    # The record usually contains 'WijkenEnBuurten' code like 'BU19000101'
    # Our 'gebieden.id' column stores this code directly.
    
    # Just return the code if it looks valid? 
    # Let's verify if it exists in DB to be safe.
    clean_code = code.strip()
    
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM gebieden WHERE id = %s", (clean_code,))
        res = cur.fetchone()
        if res:
            return res[0]
            
        # Try finding by 'code' column if id doesn't match
        # (Assuming 'code' might be alternative identifier)
        # For now, simplistic check
        return None

def process_dataset(mapping, dataset_id, output_dir, conn, gemeente_code=None, endpoint='opendata.cbs.nl'):
    """
    Process a single dataset defined in the mapping.
    
    Args:
        gemeente_code: Optional gemeente code filter (e.g. "1900"). 
                       If None, fetches all data (slower but complete).
        endpoint: API endpoint to use (default opendata.cbs.nl)
    """
    table_name = mapping.get('table_name')
    columns_map = mapping.get('columns', []) # List of column names
    indicator_names = mapping.get('indicator_name', [])
    
    if len(columns_map) != len(indicator_names):
        print(f"⚠️  Mismatch in columns/indicators length for {table_name}")
        return

    filter_info = f"gemeente={gemeente_code}" if gemeente_code else "alle"
    print(f"\n🌊 Processing {table_name} (Dataset: {dataset_id}, Endpoint: {endpoint}, {filter_info})")
    
    # 1. Fetch Data
    fetcher = CBSDataFetcher(endpoint=endpoint)
    
    print("   Fetching data from CBS...")
    # This saves files to output_dir
    fetcher.fetch_and_save(dataset_id, output_dir=output_dir, gemeente_filter=gemeente_code)
    
    # ... (rest of function remains same until end)
    
    # Find the data file
    # Pattern: *_DATA.json
    # We need to find the specific file we just downloaded. 
    # Fetcher replaces spaces with underscores in short_title.
    # A bit risky to guess exact name, so we find the latest file in output_dir?
    # Or rely on fetcher return? Fetcher doesn't return path.
    # Let's search pattern in output_dir
    json_files = glob.glob(os.path.join(output_dir, "*_DATA.json"))
    # Sort by modification time
    json_files.sort(key=os.path.getmtime, reverse=True)
    
    if not json_files:
        print("❌ No data file found after fetch.")
        return

    data_file = json_files[0] # Take most recent
    print(f"   Reading {os.path.basename(data_file)}...")
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data_json = json.load(f)
        
    records = data_json.get('data', {}).get('records', [])
    print(f"   Found {len(records)} records. Importing...")
    
    
    # Check for metadata file to use Title-based mapping
    # Pattern: *_METADATA.json matching data_file
    metadata_file = data_file.replace('_DATA.json', '_METADATA.json')
    title_to_key = {}
    
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            meta_json = json.load(f)
            props = meta_json.get('metadata', {}).get('properties', [])
            for p in props:
                # Handle potential case variations in metadata keys
                p_title = p.get('Title') or p.get('title')
                p_key = p.get('Key') or p.get('key')
                
                if p_title and p_key:
                    title_to_key[p_title] = p_key
                    # Also strip whitespace just in case
                    title_to_key[p_title.strip()] = p_key
        
        # Extract year from dataset title if possible
        dataset_title = meta_json.get('dataset', {}).get('title', '')
        print(f"   ℹ️ Metadata Title: '{dataset_title}'")
        import re
        year_match = re.search(r'20\d{2}', dataset_title)
        if year_match:
            dataset_year = int(year_match.group(0))
            print(f"   📅 Detected year from metadata: {dataset_year}")
        else:
            dataset_year = 2023
            print(f"   ⚠️ Could not detect year from metadata title '{dataset_title}', defaulting to {dataset_year}")
    else:
        dataset_year = 2023
    
    # 2. Map & Import
    count_imported = 0
    count_skipped = 0
    
    use_titles = mapping.get('use_titles', False)
    
    # Resolve physical column keys
    physical_columns = []
    
    if use_titles:
        for col_title in columns_map:
            # Try exact match
            key = title_to_key.get(col_title)
            # If not found, check if it's already a key (fallback)
            if not key and col_title in [p.get('Key') for p in props]:
                 key = col_title
            
            if not key:
                print(f"⚠️  Could not find key for title '{col_title}' in metadata.")
                physical_columns.append(None)
            else:
                physical_columns.append(key)
    else:
        physical_columns = columns_map

    # Pre-resolve indicator UUIDs
    indicator_uuids = []
    for i, _ in enumerate(columns_map):
        ind_name = indicator_names[i]
        # Use physical column key for code if available, else name
        col_ref = physical_columns[i] if i < len(physical_columns) and physical_columns[i] else f"IND_{i}"
        ind_code = f"CBS_{col_ref.split('_')[0][:40].upper()}" 
        uuid = ensure_indicator_exists(conn, ind_name, code=ind_code, bron=f"CBS {dataset_id}")
        indicator_uuids.append(uuid)
    
    with conn.cursor() as cur:
        for rec in records:
            # Resolve Area
            area_code = rec.get('WijkenEnBuurten', '').strip()
            if not area_code:
                # Fallback to RegioS if available
                area_code = rec.get('RegioS', '').strip()
            
            # Allow GM, WK, BU, and maybe NL (though NL usually not in gebieden)
            if not (area_code.startswith('WK') or area_code.startswith('BU') or area_code.startswith('GM')):
                continue
                
            gebied_id = get_gebied_id_by_code(conn, area_code)
            if not gebied_id:
                count_skipped += 1
                continue
            
            # Insert values
            for i, phys_col in enumerate(physical_columns):
                if not phys_col:
                    continue
                    
                val = rec.get(phys_col)
                if val is None:
                    continue
                    
                try:
                    val_float = float(val)
                except (ValueError, TypeError):
                    continue
                    
                ind_uuid = indicator_uuids[i]
                
                periode = rec.get('Perioden')
                
                # Extract year from Perioden if possible
                jaar = dataset_year # Default to metadata year
                
                if periode and 'JJ' in periode:
                     try:
                        jaar = int(periode[:4])
                     except:
                        pass
                elif periode and len(periode) >= 4 and periode[:4].isdigit():
                     try:
                        jaar = int(periode[:4])
                     except:
                        pass

                # Normalization logic
                normalize_field = mapping.get('normalize')
                if normalize_field:
                    # If this is a Title-based map, we need to find the Key for the normalize field too
                    norm_key = normalize_field
                    if use_titles and normalize_field in title_to_key:
                        norm_key = title_to_key[normalize_field]
                    elif use_titles:
                        # Maybe normalize_field IS the key?
                        pass
                        
                    norm_val = rec.get(norm_key)
                    if norm_val:
                        try:
                            norm_float = float(norm_val)
                            if norm_float > 0:
                                val_float = (val_float / norm_float) * 100
                        except:
                            pass
                
                cur.execute("""
                    INSERT INTO gebied_data 
                        (gebied_id, indicator_uuid, waarde, jaar, bron, scenario_id)
                    VALUES (%s, %s, %s, %s, %s, 'current')
                    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
                    DO UPDATE SET 
                        waarde = EXCLUDED.waarde,
                        updated_at = CURRENT_TIMESTAMP
                """, (gebied_id, ind_uuid, val_float, jaar, f"CBS_{dataset_id}"))
                
                count_imported += 1
                
        conn.commit()
    
    print(f"   ✅ Imported {count_imported} values ({count_skipped} areas skipped/not found).")


def main():
    print("🚀 Starting CBS Bulk Import - FRYSLÂN")
    print("=" * 60)
    print("📌 Fetching data for all Friese gemeenten...")
    print()
    
    # Add project root to sys.path for src imports
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    
    base_path = os.path.dirname(__file__)
    # Mapping and config are now in the same directory (ETL/CBS)
    mapping_file = os.path.join(base_path, 'cbs_mapping_v2.json')
    config_file = os.path.join(base_path, 'cbs_dataset_config.json')
    # Output dir is in ../../data/temp_cbs_import
    output_dir = os.path.join(base_path, '..', '..', 'data', 'temp_cbs_import')
    
    # Make temp dir
    os.makedirs(output_dir, exist_ok=True)
    
    # Load configs
    mappings = load_json_file(mapping_file)
    dataset_config = load_json_file(config_file)
    
    if not mappings or not dataset_config:
        print("❌ Could not load configuration files.")
        sys.exit(1)
        
    conn = get_db_connection()
    print("✅ Database connected.")
    
    # Argument parsing
    import argparse
    parser = argparse.ArgumentParser(description='Import CBS Data')
    parser.add_argument('--table', help='Specific table name to import (e.g. KERNCIJFERS_WIJKEN_EN_BUURTEN)')
    parser.add_argument('--gemeente', help='Comma-separated list of municipality codes (e.g. 0090,1940)')
    parser.add_argument('--missing-only', action='store_true', help='Process only municipalities with NO data')
    args = parser.parse_args()

    try:
        for item in mappings:
            generic_name = item.get('table_name')
            
            # Filter if requested
            if args.table and args.table != generic_name:
                continue

            dataset_config_val = generic_name
            
            if not dataset_config_val:
                print(f"⚠️  No dataset ID found for {generic_name}, skipping.")
                continue
            
            # Normalize to list of objects with endpoint
            datasets_to_process = []
            if isinstance(dataset_config_val, str):
                datasets_to_process.append({"id": dataset_config_val, "endpoint": "opendata.cbs.nl"})
            elif isinstance(dataset_config_val, list):
                for v in dataset_config_val:
                    if isinstance(v, str):
                         datasets_to_process.append({"id": v, "endpoint": "opendata.cbs.nl"})
                    elif isinstance(v, dict):
                         datasets_to_process.append(v)
            elif isinstance(dataset_config_val, dict):
                datasets_to_process.append(dataset_config_val)
            
            # Get list of municipalities to process
            gemeente_codes = []
            
            if args.gemeente:
                # Explicit list
                gemeente_codes = [c.strip() for c in args.gemeente.split(',') if c.strip()]
                print(f"🎯 Targeting specific municipalities: {gemeente_codes}")
            
            elif args.missing_only:
                # Auto-detect missing data
                print("🔍 Detecting municipalities with NO data...")
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT g.code 
                        FROM gemeenten g
                        LEFT JOIN gebieden gb ON g.code = gb.gemeente_code
                        LEFT JOIN gebied_data gd ON gb.id = gd.gebied_id
                        GROUP BY g.code
                        HAVING COUNT(gd.id) = 0
                        ORDER BY g.code
                    """)
                    rows = cur.fetchall()
                    gemeente_codes = [r[0] for r in rows]
                print(f"🕵️ Found {len(gemeente_codes)} municipalities without data: {gemeente_codes}")
            
            else:
                # Default: All active
                with conn.cursor() as cur:
                    # Assuming gemeenten table has 'code' column which matches CBS 4-digit code
                    cur.execute("SELECT code FROM gemeenten ORDER BY code")
                    rows = cur.fetchall()
                    gemeente_codes = [r[0] for r in rows]
                print(f"ℹ️  Found {len(gemeente_codes)} active municipalities to process.")

            if not gemeente_codes:
                print("⚠️  No municipalities selected for processing.")
                continue

            for ds_info in datasets_to_process:
                dataset_id = ds_info['id']
                endpoint = ds_info.get('endpoint', 'opendata.cbs.nl')
                
                try:
                    for g_code in gemeente_codes:
                        process_dataset(item, dataset_id, output_dir, conn, gemeente_code=g_code, endpoint=endpoint)
                except Exception as e:
                    print(f"❌ Error processing dataset {dataset_id}: {e}")
                    conn.rollback() # Important: reset transaction state
                    # Continue to next dataset instead of crashing everything
                    continue
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n" + "="*60)
        print("🏁 Import finished.")

if __name__ == "__main__":
    main()
