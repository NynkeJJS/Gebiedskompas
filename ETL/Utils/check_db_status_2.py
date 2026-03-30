#!/usr/bin/env python3
"""Deel 2: EP-Online coverage + BAG data inspectie"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def get_conn():
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=os.getenv('DATABASE_PORT', '5432'),
        dbname=os.getenv('DATABASE_NAME', 'omnitwin_db'),
        user=os.getenv('DATABASE_USER', 'omnitwin_user'),
        password=os.getenv('DATABASE_PASSWORD', ''),
        sslmode=os.getenv('DATABASE_SSLMODE', 'prefer')
    )

def main():
    conn = get_conn()
    cur = conn.cursor()

    # EP-Online details
    print("=== EP-ONLINE DETAIL ===")
    cur.execute("""
        SELECT i.naam, i.uuid, COUNT(gd.id) as cnt, 
               AVG(gd.waarde)::numeric(10,2), MIN(gd.waarde), MAX(gd.waarde),
               MIN(gd.jaar), MAX(gd.jaar),
               gd.bron
        FROM indicatoren i
        JOIN gebied_data gd ON gd.indicator_uuid = i.uuid
        WHERE i.naam ILIKE '%energi%' OR i.naam ILIKE '%label%'
        GROUP BY i.naam, i.uuid, gd.bron
    """)
    for r in cur.fetchall():
        print(f"  {r[0]}")
        print(f"    UUID: {r[1]}")
        print(f"    Datapunten: {r[2]}, AVG={r[3]}, MIN={r[4]}, MAX={r[5]}")
        print(f"    Jaar: {r[6]}-{r[7]}")
        print(f"    Bron: {r[8]}")

    # Sample EP-Online data
    print("\n=== SAMPLE EP-ONLINE DATA (5 rijen) ===")
    cur.execute("""
        SELECT gd.gebied_id, g.naam, gd.waarde, gd.jaar, gd.bron
        FROM gebied_data gd
        JOIN indicatoren i ON i.uuid = gd.indicator_uuid
        LEFT JOIN gebieden g ON g.id = gd.gebied_id
        WHERE i.naam = 'Gemiddeld energielabel'
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r[0]} | {r[1]} | waarde={r[2]} | jaar={r[3]} | bron={r[4]}")

    # Gebieden schema check - heeft het geometrie?
    print("\n=== GEBIEDEN KOLOMMEN ===")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'gebieden' 
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:30s} | {r[1]}")

    # PC6 mapping check
    print("\n=== PC6 MAPPING CHECK ===")
    pc6_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                            'data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json')
    if os.path.exists(pc6_path):
        import json
        with open(pc6_path) as f:
            mapping = json.load(f)
        print(f"  ✅ PC6 mapping gevonden: {len(mapping)} entries")
        # Check Fryslân coverage
        frl_codes = [k for k,v in mapping.items() if v.startswith('0')]
        print(f"  Fryslân PC6 codes (starts with 0): {len(frl_codes)}")
    else:
        print(f"  ❌ PC6 mapping NIET gevonden op: {pc6_path}")

    # BAG bestanden check
    print("\n=== BAG BESTANDEN CHECK ===")
    bag_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/bag_frl')
    if os.path.exists(bag_dir):
        for f in os.listdir(bag_dir):
            fpath = os.path.join(bag_dir, f)
            size_mb = os.path.getsize(fpath) / (1024*1024)
            print(f"  {f}: {size_mb:.1f} MB")
    else:
        print(f"  ❌ BAG directory niet gevonden: {bag_dir}")

    # EP-Online bestanden check
    print("\n=== EP-ONLINE BESTANDEN CHECK ===")
    ep_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/ep-online')
    if os.path.exists(ep_dir):
        for root, dirs, files in os.walk(ep_dir):
            for f in files:
                fpath = os.path.join(root, f)
                size_mb = os.path.getsize(fpath) / (1024*1024)
                rel = os.path.relpath(fpath, ep_dir)
                print(f"  {rel}: {size_mb:.1f} MB")
    else:
        print(f"  ❌ EP-Online directory niet gevonden: {ep_dir}")

    cur.close()
    conn.close()
    print("\n✅ Check voltooid")

if __name__ == "__main__":
    main()
