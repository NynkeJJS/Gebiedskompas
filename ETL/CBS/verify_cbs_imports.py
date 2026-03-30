#!/usr/bin/env python3
"""
Verify CBS Data Imports
Checks database for coverage of CBS indicators across Friese gemeenten.
"""
import os
import psycopg2
import configparser
from collections import defaultdict

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
    print("🔎 Verifying CBS Data Imports...")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Total records per source
        print("\n📊 Records per Source:")
        cur.execute("""
            SELECT i.bron, COUNT(*) 
            FROM gebied_data gd
            JOIN indicatoren i ON gd.indicator_uuid = i.uuid
            GROUP BY i.bron
            ORDER BY i.bron
        """)
        for row in cur.fetchall():
            print(f"   {row[0] or 'Onbekend'}: {row[1]} records")
            
        # 2. Coverage per Gemeente (Top 5 + Bottom 5)
        # 2. Coverage per Gemeente (Top 5 + Bottom 5)
        print("\n🗺️  Coverage per Gemeente (records count):")
        cur.execute("""
            SELECT gem.naam, g.gemeente_code, COUNT(*) 
            FROM gebied_data gd
            JOIN gebieden g ON gd.gebied_id = g.id
            LEFT JOIN gemeenten gem ON g.gemeente_code = gem.code
            WHERE g.gemeente_code IS NOT NULL
            GROUP BY gem.naam, g.gemeente_code
            ORDER BY COUNT(*) DESC
        """)
        rows = cur.fetchall()
        
        print(f"   Found {len(rows)} gemeenten with data.")
        for i, row in enumerate(rows):
            # row: (naam, code, count)
            gem_naam = row[0] if row[0] else f"Code {row[1]}"
            count = row[2]
            
            if i < 5 or i >= len(rows) - 5:
                print(f"   {gem_naam}: {count}")
            elif i == 5:
                print("   ...")
             
        # 3. Specific Indicators check (Health & Overlast)
        print("\n🏥 Health & Safety Indicators check:")
        health_indicators = [
            'Roker', 'Overgewicht', 'Eenzaam', 
            'Geregistreerde overlast', 'Moeite met rondkomen'
        ]
        
        for ind_name in health_indicators:
            cur.execute("""
                SELECT COUNT(*) 
                FROM gebied_data gd
                JOIN indicatoren i ON gd.indicator_uuid = i.uuid
                WHERE i.naam LIKE %s
            """, (f'%{ind_name}%',))
            count = cur.fetchone()[0]
            print(f"   {ind_name}: {count} records")

        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
