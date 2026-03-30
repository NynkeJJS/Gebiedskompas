#!/usr/bin/env python3
"""
Enrich RIVM Metadata
Lees metadata uit 50150NED_metadata.csv en update de indicatoren tabel.
"""

import psycopg2
import configparser
import os
import json

def get_db_connection():
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

def main():
    print("🚀 Start Metadata Enrichment")
    
    # Pad naar CSV
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'metadata', 'rivm', '50150NED_metadata.csv')
    
    if not os.path.exists(csv_path):
        print(f"❌ Bestand niet gevonden: {csv_path}")
        return

    # Lees CSV - Let op: RIVM CSV is complex met secties
    # We zijn geïnteresseerd in de "DataProperties" sectie die begint rond regel 140
    # Maar pandas kan dit lastig parsen direct. We lezen het als text en zoeken de sectie.
    
    print(f"📖 Lezen van {csv_path}...")
    
    topics = []
    import csv
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip until we find "DataProperties"
        line = f.readline()
        while line and '"DataProperties"' not in line:
            line = f.readline()
            
        if not line:
            print("❌ Sectie 'DataProperties' niet gevonden")
            return

        # Now search for the header line of this section
        # It usually starts with ID;Position
        # We can just iterate until we find the header
        reader = csv.reader(f, delimiter=';')
        
        headers = []
        for row in reader:
            if not row: continue
            
            # Check if this is the header row
            if 'ID' in row and 'Key' in row:
                headers = row
                continue
                
            # If we have headers, process data
            if headers:
                # Map columns by index
                try:
                    key_idx = headers.index('Key')
                    title_idx = headers.index('Title')
                    desc_idx = headers.index('Description')
                    unit_idx = headers.index('Unit')
                    type_idx = headers.index('Type')
                    
                    if len(row) > title_idx and row[type_idx] == 'Topic':
                        topic = {
                            'Key': row[key_idx],
                            'Title': row[title_idx],
                            'Description': row[desc_idx],
                            'Unit': row[unit_idx] if len(row) > unit_idx else '%'
                        }
                        topics.append(topic)
                except ValueError:
                    continue

    print(f"🔍 {len(topics)} topics gevonden in metadata bestand.")

    # Maak DB connectie
    conn = get_db_connection()
    
    # Update loop
    count_updated = 0
    with conn.cursor() as cur:
        for topic in topics:
            # Zoek indicator in database
            # Zoek indicator in database
            cur.execute("""
                SELECT uuid, naam, omschrijving FROM indicatoren 
                WHERE naam ILIKE %s OR code ILIKE %s
            """, (topic['Title'], topic['Key']))
            
            matches = cur.fetchall()
            
            if matches:
                 for match in matches:
                    uuid = match[0]
                    # Update description/definition
                    description = topic['Description'].replace('/""/', '"')
                    
                    cur.execute("""
                        UPDATE indicatoren 
                        SET omschrijving = %s,
                            eenheid = %s,
                            bron = 'RIVM / GGD / CBS',
                            admin_notes = 'Metadata automatisch verrijkt uit 50150NED'
                        WHERE uuid = %s
                    """, (description, topic['Unit'], uuid))
                    count_updated += 1
                    # print(f"   ✅ Updated {topic['Title']}")

        conn.commit()
    
    conn.close()
    print(f"✅ Klaar! {count_updated} indicatoren bijgewerkt met metadata.")

if __name__ == "__main__":
    main()
