import os
import json
import csv
import psycopg2
from configparser import ConfigParser
from pathlib import Path

# Configuration
CONFIG_PATH = 'config.ini'
CSV_PATH = Path('data/voorbeeld_gebiedsmonitor/indicator_testlijst.csv')
JSON_DIR = Path('data/temp_cbs_import')

# Map of specific CSV Sources to JSON patterns (simple heuristic)
# We will just load ALL JSON metadata files found in the directory into a big lookup dictionary.

def get_db_config():
    config = ConfigParser()
    config.read(CONFIG_PATH)
    return config['DATABASE']

def load_json_metadata():
    """
    Loads all definition metadata from JSON files in the directory.
    Returns a dictionary: { "Title (lowercase)": { "description": ..., "unit": ... } }
    """
    metadata_lookup = {}
    
    files = list(JSON_DIR.glob('*METADATA.json'))
    print(f"Loading metadata from {len(files)} JSON files...")

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            properties = data.get('metadata', {}).get('properties', [])
            for prop in properties:
                title = prop.get('title')
                description = prop.get('description')
                unit = prop.get('unit')

                if title:
                    # Normalize key to lowercase for easier matching
                    key = title.strip().lower()
                    
                    # specific cleaning for units if needed
                    if unit == '%':
                        unit = 'percentage'
                    
                    if key not in metadata_lookup:
                        metadata_lookup[key] = {
                            'description': description,
                            'unit': unit,
                            'source_file': file_path.name
                        }
                    else:
                        # If already exists, we might want to prioritize newer files? 
                        # For now, first come first served or overwrite. 
                        # Let's overwrite if the new one has a description and the old one didn't.
                        if description and not metadata_lookup[key]['description']:
                            metadata_lookup[key]['description'] = description
                            metadata_lookup[key]['unit'] = unit
                            metadata_lookup[key]['source_file'] = file_path.name
                            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    print(f"Loaded {len(metadata_lookup)} unique definitions.")
    return metadata_lookup

def enrich_metadata():
    db_config = get_db_config()
    conn = None
    
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        
        # 1. Load Metadata Dictionary
        cbs_definitions = load_json_metadata()
        
        # 2. Process CSV to find matches
        print("\nProcessing CSV mapping...")
        updated_count = 0
        skipped_count = 0
        not_found_count = 0
        
        if not CSV_PATH.exists():
            print(f"Error: CSV file not found at {CSV_PATH}")
            return

        with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                indicator_name = row.get('Indicator', '').strip()
                indicator_swf = row.get('Indicator SWF', '').strip()
                
                # Determine which name to lookup in CBS data
                # Prefer Indicator SWF if available, otherwise Indicator
                lookup_name = indicator_swf if indicator_swf else indicator_name
                
                if not indicator_name:
                    continue

                lookup_key = lookup_name.lower()
                
                if lookup_key in cbs_definitions:
                    meta = cbs_definitions[lookup_key]
                    description = meta['description']
                    unit = meta['unit']
                    source_file = meta['source_file']
                    
                    # Update Database
                    # Only update if description is missing in DB? 
                    # Or force update? Let's check if it exists first to avoid overwriting custom texts if we had any.
                    # But user said "vrijwel alles ontbreekt", so force update of empty fields is safe.
                    # Let's overwrite for now to ensure consistency with CBS.
                    
                    if description:
                        # Handle potential empty units
                        unit_val = unit if unit else None
                        
                        # Update Logic: Try SWF Name first (as DB likely uses this), else Indicator Name
                        updated = False
                        
                        # 1. Try updating by SWF Name
                        if indicator_swf:
                            cursor.execute("""
                                UPDATE indicatoren 
                                SET omschrijving = %s, 
                                    eenheid = COALESCE(eenheid, %s),
                                    bron = COALESCE(bron, %s)
                                WHERE naam = %s
                            """, (description, unit_val, f"CBS ({source_file})", indicator_swf))
                            if cursor.rowcount > 0:
                                updated = True

                        # 2. If not updated (or no SWF), try basic Name
                        if not updated:
                             cursor.execute("""
                                UPDATE indicatoren 
                                SET omschrijving = %s, 
                                    eenheid = COALESCE(eenheid, %s),
                                    bron = COALESCE(bron, %s)
                                WHERE naam = %s
                            """, (description, unit_val, f"CBS ({source_file})", indicator_name))
                             if cursor.rowcount > 0:
                                updated = True
                        
                        if updated:
                            updated_count += 1
                        else:
                            # Indicator not found in DB under either name
                            pass
                else:
                    not_found_count += 1
                    # print(f"  No match for: {lookup_name} (DB Name: {indicator_name})")

        conn.commit()
        print(f"\nResults:")
        print(f"Updated {updated_count} indicators.")
        print(f"Could not find definitions for {not_found_count} items (from CSV).")
        
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    enrich_metadata()
