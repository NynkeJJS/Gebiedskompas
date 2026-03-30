#!/usr/bin/env python3
"""
Import BAG Fryslân indicatoren: huishoudens (woonfunctie), bouwjaar, oppervlakte.
Plus nieuwe indicatoren voor Kompas: Bouwperiodes (4) en Gebruiksfuncties (11).

Strategie:
1. Laad PC6 → Buurt mapping (JSON)
2. Laad BAG VBO GPKG
3. Match VBO postcode (PC6) → Buurtcode → Gebied_id
4. Aggregeer per buurt: 
   - Bestaand: huishoudens, gem. bouwjaar, % voor-1945, gem. oppervlakte
   - Nieuw: Aantal per bouwperiode (<1915, 1915-1945, 1945-1984, >1984)
   - Nieuw: Aantal per gebruiksfunctie (11 cats, meervoudig gesplitst)
5. Insert in gebied_data tabel

Resultaat: ~20 indicatoren per buurt
"""
import os, sys, json, uuid
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import psycopg2
import geopandas as gpd
import pandas as pd
import numpy as np

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Configuratie
# Bepaal project root (D-OmniTwin)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BAG_VBO_PATH = os.path.join(PROJECT_ROOT,
                            'data/bag_frl/cleaned_bag_data_verblijfsobject.gpkg')
PC6_MAPPING_PATH = os.path.join(PROJECT_ROOT,
                                'data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json')
JAAR = 2025
BRON = 'Kadaster BAG Fryslân 2026'

# Indicator definities
INDICATORS = {
    # Bestaande indicatoren
    'bag_huishoudens': {
        'naam': 'Huishoudens (BAG woonfunctie)',
        'eenheid': 'aantal',
        'omschrijving': 'Aantal verblijfsobjecten met woonfunctie per buurt.',
        'categorie': 'Wonen'
    },
    'bag_gemiddeld_bouwjaar': {
        'naam': 'Gemiddeld bouwjaar woningen (BAG)',
        'eenheid': 'jaar',
        'omschrijving': 'Gemiddeld bouwjaar van verblijfsobjecten met woonfunctie.',
        'categorie': 'Wonen'
    },
    'bag_pct_voor_1945': {
        'naam': 'Woningen gebouwd vóór 1945 (BAG)',
        'eenheid': '%',
        'omschrijving': 'Percentage woonfunctie VBO\'s met bouwjaar vóór 1945.',
        'categorie': 'Wonen'
    },
    'bag_gem_oppervlakte': {
        'naam': 'Gemiddelde woonoppervlakte (BAG)',
        'eenheid': 'm²',
        'omschrijving': 'Gemiddelde oppervlakte van verblijfsobjecten met woonfunctie per buurt.',
        'categorie': 'Wonen'
    },
    'bag_pct_woonfunctie': {
        'naam': 'Percentage woonfunctie (BAG)',
        'eenheid': '%',
        'omschrijving': 'Percentage verblijfsobjecten met woonfunctie ten opzichte van totaal aantal VBO\'s.',
        'categorie': 'Wonen'
    },
    
    # Nieuw: Bouwperiodes (Kompas: Samenstelling > Bebouwing > Bouwperiode)
    'bag_bouwjaar_voor_1915': {
        'naam': 'Bouwjaar voor 1915',
        'eenheid': 'aantal',
        'omschrijving': 'Aantal panden gebouwd voor 1915.',
        'categorie': 'Bebouwing'
    },
    'bag_bouwjaar_1915_1945': {
        'naam': 'Bouwjaar 1915-1945',
        'eenheid': 'aantal',
        'omschrijving': 'Aantal panden gebouwd tussen 1915 en 1945.',
        'categorie': 'Bebouwing'
    },
    'bag_bouwjaar_1945_1984': {
        'naam': 'Bouwjaar 1945-1984',
        'eenheid': 'aantal',
        'omschrijving': 'Aantal panden gebouwd tussen 1945 en 1984.',
        'categorie': 'Bebouwing'
    },
    'bag_bouwjaar_vanaf_1985': {
        'naam': 'Bouwjaar vanaf 1985',
        'eenheid': 'aantal',
        'omschrijving': 'Aantal panden gebouwd vanaf 1985.',
        'categorie': 'Bebouwing'
    },

    # Nieuw: Gebruiksfuncties (Kompas: Samenstelling > Bebouwing > Gebruik omgeving)
    'bag_functie_woon': { 'naam': 'Woonfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met woonfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_bijeenkomst': { 'naam': 'Bijeenkomstfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met bijeenkomstfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_cel': { 'naam': 'Celfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met celfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_gezondheid': { 'naam': 'Gezondheidszorgfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met gezondheidszorgfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_industrie': { 'naam': 'Industriefunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met industriefunctie.', 'categorie': 'Gebruik' },
    'bag_functie_kantoor': { 'naam': 'Kantoorfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met kantoorfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_logies': { 'naam': 'Logiesfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met logiesfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_onderwijs': { 'naam': 'Onderwijsfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met onderwijsfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_sport': { 'naam': 'Sportfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met sportfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_winkel': { 'naam': 'Winkelfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met winkelfunctie.', 'categorie': 'Gebruik' },
    'bag_functie_overige': { 'naam': 'Overige gebruiksfunctie', 'eenheid': 'aantal', 'omschrijving': 'Aantal VBO\'s met overige gebruiksfunctie.', 'categorie': 'Gebruik' }
}


def get_conn():
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=os.getenv('DATABASE_PORT', '5432'),
        dbname=os.getenv('DATABASE_NAME', 'omnitwin_db'),
        user=os.getenv('DATABASE_USER', 'omnitwin_user'),
        password=os.getenv('DATABASE_PASSWORD', ''),
        sslmode=os.getenv('DATABASE_SSLMODE', 'prefer')
    )


def load_pc6_mapping():
    """Laad PC6 → Buurtcode mapping"""
    print(f"📂 Laden PC6 mapping: {PC6_MAPPING_PATH}")
    with open(PC6_MAPPING_PATH, 'r') as f:
        mapping = json.load(f)
    print(f"   ✅ {len(mapping)} PC6 codes geladen")
    return mapping


def load_buurt_to_gebied(conn):
    """Haal mapping buurtcode → gebied_id uit database"""
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM gebieden 
        WHERE id LIKE 'BU%'
    """)
    mapping = {}
    for row in cur.fetchall():
        # BU00810001 → 00810001
        buurtcode = row[0].replace('BU', '')
        mapping[buurtcode] = row[0]
    cur.close()
    print(f"   ✅ {len(mapping)} buurten in database")
    return mapping


def load_bag_vbo():
    """Laad BAG Verblijfsobjecten (zonder geometrie voor snelheid)"""
    print(f"\n📂 Laden BAG VBO: {BAG_VBO_PATH}")
    print(f"   (dit kan 1-2 minuten duren voor 380k records...)")
    
    # We hoeven geen geometrie te laden - we matchen via postcode
    vbo = gpd.read_file(BAG_VBO_PATH, ignore_geometry=True)
    print(f"   ✅ {len(vbo)} verblijfsobjecten geladen")
    
    # Filter op actieve objecten
    actief_statussen = [
        'Verblijfsobject in gebruik',
        'Verblijfsobject in gebruik (niet ingemeten)'
    ]
    vbo_actief = vbo[vbo['status'].isin(actief_statussen)].copy()
    print(f"   ✅ {len(vbo_actief)} actieve VBO's ({len(vbo) - len(vbo_actief)} niet-actief gefilterd)")
    
    # Bepaal woonfunctie (kan in combinatie voorkomen: "industriefunctie,woonfunctie")
    vbo_actief['is_woonfunctie'] = vbo_actief['gebruiksdoel'].str.contains('woonfunctie', case=False, na=False)
    woon_count = vbo_actief['is_woonfunctie'].sum()
    print(f"   ✅ {woon_count} VBO's met woonfunctie ({woon_count/len(vbo_actief)*100:.1f}%)")
    
    # Filter bouwjaar uitschieters
    vbo_actief['bouwjaar_valid'] = vbo_actief['bouwjaar'].between(1600, 2026)
    invalid = (~vbo_actief['bouwjaar_valid']).sum()
    if invalid > 0:
        print(f"   ⚠️  {invalid} VBO's met onrealistisch bouwjaar (buiten 1600-2026), worden uitgesloten van bouwjaar berekening")
    
    return vbo_actief


def match_vbo_to_buurt(vbo, pc6_mapping, buurt_to_gebied):
    """Match VBO postcode → Buurtcode → Gebied_id (vectorized voor snelheid)"""
    print(f"\n🔗 Matching VBO's aan buurten via postcode (vectorized)...")
    
    # Stap 1: PC6 → Buurtcode
    vbo['buurtcode'] = vbo['postcode'].map(pc6_mapping)
    matched_pc6 = vbo['buurtcode'].notna().sum()
    print(f"   PC6 → Buurt: {matched_pc6} / {len(vbo)} gematcht ({matched_pc6/len(vbo)*100:.1f}%)")
    
    # Stap 2: Buurtcode → Gebied_id
    vbo['gebied_id'] = vbo['buurtcode'].map(buurt_to_gebied)
    matched_gebied = vbo['gebied_id'].notna().sum()
    print(f"   Buurt → Gebied: {matched_gebied} / {len(vbo)} gematcht ({matched_gebied/len(vbo)*100:.1f}%)")
    
    unmatched = len(vbo) - matched_gebied
    if unmatched > 0:
        print(f"   ⚠️  {unmatched} VBO's niet gematcht aan buurt in database")
    
    return vbo[vbo['gebied_id'].notna()].copy()


def aggregate_per_buurt(vbo_matched):
    """Bereken indicatoren per buurt, inclusief nieuwe Kompas indicatoren"""
    print(f"\n📊 Aggregeren per buurt...")
    
    results = {}
    
    # Mapping functies naar interne ID's
    func_map = {
        'woonfunctie': 'bag_functie_woon',
        'bijeenkomstfunctie': 'bag_functie_bijeenkomst',
        'celfunctie': 'bag_functie_cel',
        'gezondheidszorgfunctie': 'bag_functie_gezondheid',
        'industriefunctie': 'bag_functie_industrie',
        'kantoorfunctie': 'bag_functie_kantoor',
        'logiesfunctie': 'bag_functie_logies',
        'onderwijsfunctie': 'bag_functie_onderwijs',
        'sportfunctie': 'bag_functie_sport',
        'winkelfunctie': 'bag_functie_winkel',
        'overige gebruiksfunctie': 'bag_functie_overige'
    }

    for gebied_id, group in vbo_matched.groupby('gebied_id'):
        totaal = len(group)
        
        # 1. Bestaande indicatoren (woon)
        woon = group['is_woonfunctie'].sum()
        woningen = group[group['is_woonfunctie']]
        woningen_valid_bouwjaar = woningen[woningen['bouwjaar_valid']]
        
        # 2. Bouwjaarklassen (alleen voor geldige bouwjaren)
        # We kijken hier naar *alle* panden/vbo's, niet alleen woningen (zoals in Kompas chart staat 'Bebouwing')
        # Of alleen woningen? In Kompas 'Bebouwing' kan breder zijn.
        # User zei: "check afbeelding 1 m.i. kunnen we de bouwjaren hier aan verbinden" 
        # Meestal gaat bouwjaar over alle panden. We gebruiken alle VBO's met valide bouwjaar.
        group_valid_bouwjaar = group[group['bouwjaar_valid']]
        bj = group_valid_bouwjaar['bouwjaar']
        
        bj_voor_1915 = (bj < 1915).sum()
        bj_1915_1945 = ((bj >= 1915) & (bj <= 1945)).sum()
        bj_1945_1984 = ((bj > 1945) & (bj <= 1984)).sum() # Let op: <= 1984 (user zei 1945-1984)
        bj_vanaf_1985 = (bj >= 1985).sum()
        
        # 3. Gebruiksfuncties
        # Gebruiksdoel is comma-separated string, dus we joinen alles en splitten dan voor telling
        # Of itereren. Pandas vectorize is sneller.
        # We maken dummy columns voor elke functie
        func_counts = defaultdict(int)
        
        # Dit is de string kolom
        doelen = group['gebruiksdoel'].dropna().astype(str)
        
        # Simpele en snelle manier: concat all strings en count substrings?
        # Nee, want 'woonfunctie' zit niet in 'kantoorfunctie' maar wel uniek.
        # We kunnen stacken.
        all_funcs = doelen.str.split(',').explode().str.strip()
        counts = all_funcs.value_counts()
        
        for func_naam, count in counts.items():
            mapped_key = func_map.get(func_naam)
            if mapped_key:
                func_counts[mapped_key] = count
            
        
        results[gebied_id] = {
            # Bestaand
            'bag_huishoudens': int(woon),
            'bag_pct_woonfunctie': round(woon / totaal * 100, 1) if totaal > 0 else 0,
            'bag_gemiddeld_bouwjaar': round(woningen_valid_bouwjaar['bouwjaar'].mean(), 0)
                if len(woningen_valid_bouwjaar) > 0 else None,
            'bag_pct_voor_1945': round(
                (woningen_valid_bouwjaar['bouwjaar'] < 1945).sum() / len(woningen_valid_bouwjaar) * 100, 1
            ) if len(woningen_valid_bouwjaar) > 0 else None,
            'bag_gem_oppervlakte': round(woningen['oppervlakte'].mean(), 1)
                if len(woningen) > 0 and woningen['oppervlakte'].notna().any() else None,
            
            # Nieuw: Bouwperiodes
            'bag_bouwjaar_voor_1915': int(bj_voor_1915),
            'bag_bouwjaar_1915_1945': int(bj_1915_1945),
            'bag_bouwjaar_1945_1984': int(bj_1945_1984),
            'bag_bouwjaar_vanaf_1985': int(bj_vanaf_1985),
            
            # Nieuw: Functies
            'bag_functie_woon': int(func_counts['bag_functie_woon']),
            'bag_functie_bijeenkomst': int(func_counts['bag_functie_bijeenkomst']),
            'bag_functie_cel': int(func_counts['bag_functie_cel']),
            'bag_functie_gezondheid': int(func_counts['bag_functie_gezondheid']),
            'bag_functie_industrie': int(func_counts['bag_functie_industrie']),
            'bag_functie_kantoor': int(func_counts['bag_functie_kantoor']),
            'bag_functie_logies': int(func_counts['bag_functie_logies']),
            'bag_functie_onderwijs': int(func_counts['bag_functie_onderwijs']),
            'bag_functie_sport': int(func_counts['bag_functie_sport']),
            'bag_functie_winkel': int(func_counts['bag_functie_winkel']),
            'bag_functie_overige': int(func_counts['bag_functie_overige']),
        }
    
    print(f"   ✅ {len(results)} buurten met BAG data")
    
    # Quick sanity check
    if results:
        sample_id = list(results.keys())[0]
        print(f"\n   --- Sample ({sample_id}) ---")
        for k, v in results[sample_id].items():
            if 'functie' in k or 'bouwjaar_' in k:
                print(f"   {k}: {v}")
    
    return results


def ensure_indicators(conn):
    """Maak indicatoren aan als ze niet bestaan, return UUID mapping"""
    cur = conn.cursor()
    indicator_uuids = {}
    
    for code, info in INDICATORS.items():
        # Check of indicator al bestaat
        cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (info['naam'],))
        row = cur.fetchone()
        
        if row:
            indicator_uuids[code] = str(row[0])
            # print(f"   ✅ Indicator bestaat: {info['naam']} ({row[0]})") # Verbose
        else:
            new_uuid = str(uuid.uuid4())
            try:
                cur.execute("""
                    INSERT INTO indicatoren (uuid, naam, code, eenheid, omschrijving, categorie, bron)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (code) DO UPDATE SET naam=EXCLUDED.naam
                    RETURNING uuid
                """, (new_uuid, info['naam'], code, info['eenheid'], info['omschrijving'], 
                      info['categorie'], BRON))
                
                # Check if insert returned something (if update happened RETURNING might not work as expected in older pg versions without WHERE, but here Insert or Update)
                # Actually, standard ON CONFLICT RETURNING works.
                res = cur.fetchone()
                if res:
                    indicator_uuids[code] = str(res[0])
                    print(f"   🆕 Indicator aangemaakt/updated: {info['naam']}")
                else:
                    # Fallback
                    cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
                    indicator_uuids[code] = str(cur.fetchone()[0])
                    
            except Exception as e:
                print(f"Error creating indicator {code}: {e}")
                conn.rollback()
                continue
                
    conn.commit()
    cur.close()
    return indicator_uuids


def import_to_database(conn, buurt_aggregates, indicator_uuids):
    """Import aggregaties naar gebied_data tabel"""
    print(f"\n💾 Importeren naar database...")
    cur = conn.cursor()
    
    inserted = 0
    updated = 0
    errors = 0
    
    # Batch parameters? No, simple loop is fine for < 1000 buurten * 20 indicators
    for gebied_id, values in buurt_aggregates.items():
        for ind_code, waarde in values.items():
            if waarde is None or (isinstance(waarde, float) and np.isnan(waarde)):
                continue
            
            ind_uuid = indicator_uuids.get(ind_code)
            if not ind_uuid:
                continue
            
            try:
                cur.execute("""
                    INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
                    DO UPDATE SET waarde = EXCLUDED.waarde, bron = EXCLUDED.bron
                """, (gebied_id, ind_uuid, float(waarde), JAAR, 'current', BRON))
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"   ⚠️  Error {gebied_id}/{ind_code}: {e}")
    
    conn.commit()
    cur.close()
    print(f"   ✅ {inserted} datapunten geïmporteerd/bijgewerkt ({errors} fouten)")
    return inserted


def print_summary(conn, indicator_uuids):
    """Print samenvatting van geïmporteerde data"""
    cur = conn.cursor()
    print(f"\n{'='*60}")
    print(f"IMPORT SAMENVATTING")
    print(f"{'='*60}")
    
    # Groepeer op category voor netter overzicht
    cats = defaultdict(list)
    for code, uuid in indicator_uuids.items():
        cats[INDICATORS[code]['categorie']].append((code, uuid))
        
    for cat, items in cats.items():
        print(f"\n[{cat}]")
        for code, ind_uuid in items:
            cur.execute("""
                SELECT COUNT(*), AVG(waarde)::numeric(10,1), SUM(waarde)::numeric(10,0)
                FROM gebied_data WHERE indicator_uuid = %s AND bron = %s
            """, (ind_uuid, BRON))
            row = cur.fetchone()
            info = INDICATORS[code]
            if info['eenheid'] == 'aantal':
                print(f"  - {info['naam']:<35}: Totaal {row[2]:>8} {info['eenheid']}")
            else:
                print(f"  - {info['naam']:<35}: Gem. {row[1]:>8} {info['eenheid']}")
    
    cur.close()


def main():
    start_time = datetime.now()
    print(f"{'='*60}")
    print(f"BAG FRYSLÂN IMPORT - Huishoudens & Bouwjaar Indicatoren")
    print(f"Gestart: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 1. Database connectie
    print(f"\n1️⃣  Database connectie...")
    conn = get_conn()
    buurt_to_gebied = load_buurt_to_gebied(conn)
    
    # 2. PC6 mapping laden
    print(f"\n2️⃣  PC6 mapping laden...")
    pc6_mapping = load_pc6_mapping()
    
    # 3. BAG VBO laden
    print(f"\n3️⃣  BAG Verblijfsobjecten laden...")
    vbo = load_bag_vbo()
    
    # 4. Match via postcode → buurt
    print(f"\n4️⃣  Matching VBO → Buurt...")
    vbo_matched = match_vbo_to_buurt(vbo, pc6_mapping, buurt_to_gebied)
    
    # 5. Aggregeren per buurt
    print(f"\n5️⃣  Aggregeren per buurt...")
    buurt_aggregates = aggregate_per_buurt(vbo_matched)
    
    # 6. Indicatoren aanmaken/ophalen
    print(f"\n6️⃣  Indicatoren configuratie...")
    indicator_uuids = ensure_indicators(conn)
    
    # 7. Import naar database
    print(f"\n7️⃣  Import naar database...")
    count = import_to_database(conn, buurt_aggregates, indicator_uuids)
    
    # 8. Samenvatting
    print_summary(conn, indicator_uuids)
    
    conn.close()
    
    elapsed = datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"✅ Import voltooid in {elapsed.total_seconds():.0f} seconden")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
