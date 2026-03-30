#!/usr/bin/env python3
"""Quick database status check - welke data zit er al in?"""
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

    # 1. Gebiedstypes
    print("=== GEBIEDSTYPES ===")
    cur.execute("SELECT id, naam, niveau, (SELECT COUNT(*) FROM gebieden g WHERE g.gebiedstype_id = gt.id) as aantal FROM gebiedstypes gt ORDER BY niveau")
    for r in cur.fetchall():
        print(f"  {r[0]:6s} | {r[1]:30s} | niveau={r[2]} | {r[3]} gebieden")

    # 2. Totaal gebied_data
    print("\n=== GEBIED_DATA TOTAAL ===")
    cur.execute("SELECT COUNT(*) FROM gebied_data")
    print(f"  Totaal datapunten: {cur.fetchone()[0]}")

    # 3. Indicatoren met data
    print("\n=== INDICATOREN MET DATA (top 20) ===")
    cur.execute("""
        SELECT i.naam, COUNT(gd.id) as cnt, 
               COUNT(DISTINCT gd.gebied_id) as gebieden,
               MIN(gd.jaar) as min_jaar, MAX(gd.jaar) as max_jaar,
               AVG(gd.waarde)::numeric(10,2) as avg_val
        FROM indicatoren i
        JOIN gebied_data gd ON gd.indicator_uuid = i.uuid
        GROUP BY i.naam
        ORDER BY cnt DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {r[0]:45s} | datapunten={r[1]:>5d} | gebieden={r[2]:>4d} | jaar={r[3]}-{r[4]} | avg={r[5]}")
    else:
        print("  ❌ GEEN enkel datapunt gevonden in gebied_data!")

    # 4. Energielabel specific check
    print("\n=== ENERGIELABEL CHECK ===")
    cur.execute("""
        SELECT i.naam, i.uuid, i.code
        FROM indicatoren i
        WHERE i.naam ILIKE '%energi%' OR i.naam ILIKE '%label%' OR i.code ILIKE '%energ%'
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            cur.execute("SELECT COUNT(*) FROM gebied_data WHERE indicator_uuid = %s", (r[1],))
            cnt = cur.fetchone()[0]
            print(f"  {'✅' if cnt > 0 else '⚠️'} {r[0]} (code={r[2]}) → {cnt} datapunten")
    else:
        print("  ❌ Geen energielabel indicatoren aanwezig in indicatoren tabel")

    # 5. Totaal indicatoren
    print("\n=== INDICATOREN TOTAAL ===")
    cur.execute("SELECT COUNT(*) FROM indicatoren")
    totaal = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT indicator_uuid) FROM gebied_data")
    met_data = cur.fetchone()[0]
    print(f"  Totaal indicatoren: {totaal}")
    print(f"  Indicatoren met data: {met_data}")
    print(f"  Indicatoren zonder data: {totaal - met_data}")

    cur.close()
    conn.close()
    print("\n✅ Database check voltooid")

if __name__ == "__main__":
    main()
