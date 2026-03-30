#!/usr/bin/env python3
"""
Bereken EP-Online coverage: percentage huishoudens met energielabel.
Koppeling: 'Aantal energielabels' / 'Huishoudens (BAG woonfunctie)' * 100
"""
import os, sys, uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

JAAR = 2025
BRON = 'Berekend: EP-Online / BAG Fryslân'

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
    
    # 1. Vind BAG huishoudens indicator
    cur.execute("SELECT uuid FROM indicatoren WHERE naam = 'Huishoudens (BAG woonfunctie)'")
    row = cur.fetchone()
    if not row:
        print("❌ BAG huishoudens indicator niet gevonden! Draai eerst import_bag_indicators.py")
        return
    bag_uuid = str(row[0])
    print(f"✅ BAG huishoudens indicator: {bag_uuid}")
    
    # 2. Vind EP-Online 'Aantal energielabels (definitief)' indicator
    # We berekenen coverage op basis van DEFINITIEVE labels
    cur.execute("SELECT uuid FROM indicatoren WHERE naam = 'Aantal energielabels (definitief)'")
    row = cur.fetchone()
    if not row:
        print("❌ 'Aantal energielabels (definitief)' indicator niet gevonden! Draai eerst import_energielabels.py (nieuwe versie)")
        return
    ep_uuid = str(row[0])
    print(f"✅ Aantal energielabels (definitief) indicator: {ep_uuid}")
    
    # 3. Join: buurten met BEIDE datasets
    cur.execute("""
        SELECT bag.gebied_id, bag.waarde AS huishoudens, ep.waarde AS labels
        FROM gebied_data bag
        JOIN gebied_data ep ON ep.gebied_id = bag.gebied_id
        WHERE bag.indicator_uuid = %s AND ep.indicator_uuid = %s
          AND bag.waarde > 0
    """, (bag_uuid, ep_uuid))
    
    rows = cur.fetchall()
    print(f"\n📊 {len(rows)} buurten met zowel BAG huishoudens als EP-Online aantallen")
    
    if not rows:
        print("❌ Geen overlap gevonden")
        return
    
    # 4. Maak coverage indicator aan
    cur.execute("SELECT uuid FROM indicatoren WHERE naam = 'Energielabel coverage'")
    existing = cur.fetchone()
    if existing:
        coverage_uuid = str(existing[0])
        print(f"✅ Coverage indicator bestaat: {coverage_uuid}")
    else:
        coverage_uuid = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO indicatoren (uuid, naam, code, eenheid, omschrijving, categorie, bron)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (coverage_uuid,
              'Energielabel coverage',
              'pct_energielabel_coverage',
              '%',
              'Percentage huishoudens met een definitief energielabel. Berekend als: aantal energielabels EP-Online / huishoudens BAG woonfunctie * 100.',
              'Wonen',
              BRON))
        conn.commit()
        print(f"🆕 Coverage indicator aangemaakt: {coverage_uuid}")
    
    # 5. Bereken en insert coverage data
    inserted = 0
    for gebied_id, huishoudens, labels in rows:
        pct = min(labels / huishoudens * 100, 100)  # Cap at 100%
        cur.execute("""
            INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
            VALUES (%s, %s, %s, %s, 'current', %s)
            ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
            DO UPDATE SET waarde = EXCLUDED.waarde, bron = EXCLUDED.bron
        """, (gebied_id, coverage_uuid, round(pct, 1), JAAR, BRON))
        inserted += 1
    
    conn.commit()
    
    # 6. Samenvatting
    cur.execute("""
        SELECT COUNT(*), AVG(waarde)::numeric(5,1), MIN(waarde)::numeric(5,1), MAX(waarde)::numeric(5,1)
        FROM gebied_data WHERE indicator_uuid = %s
    """, (coverage_uuid,))
    stats = cur.fetchone()
    
    print(f"\n{'='*50}")
    print(f"✅ Energielabel Coverage berekend:")
    print(f"   Buurten: {stats[0]}")
    print(f"   Gemiddelde: {stats[1]}%")
    print(f"   Bereik: {stats[2]}% - {stats[3]}%")
    print(f"{'='*50}")
    
    # Top/bottom 5
    cur.execute("""
        SELECT g.naam, gd.waarde 
        FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
        WHERE gd.indicator_uuid = %s
        ORDER BY gd.waarde DESC LIMIT 5
    """, (coverage_uuid,))
    print(f"\n   Top 5 hoogste coverage:")
    for r in cur.fetchall():
        print(f"     {r[0]}: {r[1]}%")
    
    cur.execute("""
        SELECT g.naam, gd.waarde 
        FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
        WHERE gd.indicator_uuid = %s AND gd.waarde > 0
        ORDER BY gd.waarde ASC LIMIT 5
    """, (coverage_uuid,))
    print(f"\n   Top 5 laagste coverage (>0%):")
    for r in cur.fetchall():
        print(f"     {r[0]}: {r[1]}%")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
