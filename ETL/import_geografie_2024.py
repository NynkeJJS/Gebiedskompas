#!/usr/bin/env python3
"""
Import CBS Gebiedsindeling 2024: Provincies + Buurten
=====================================================
Leest provincies.gpkg en CBS_BUURTEN2024.gpkg in.
Filtert buurten op de noordelijke provincies (Friesland, Groningen, Drenthe)
met een 100 meter buffer rondom de provinciegrenzen.
Voegt provincie_naam toe aan elke buurt.

Gebruik:
    python import_geografie_2024.py --stap provincies   # Stap 1: Provincies laden
    python import_geografie_2024.py --stap gemeenten    # Stap 2: Gemeenten aanvullen
    python import_geografie_2024.py --stap buurten      # Stap 3: Buurten 2024 laden
    python import_geografie_2024.py --stap alles        # Alle stappen

Vereisten:
    pip install geopandas fiona psycopg2 shapely
"""

import argparse
import sys
import os
import time

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values
from shapely import wkb
from shapely.ops import unary_union

# ── Configuratie ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVINCIES_GPKG = os.path.join(BASE_DIR, "data", "cbs_pc6_huisnr_buurt", "provincies.gpkg")
BUURTEN_GPKG = os.path.join(BASE_DIR, "data", "cbs_pc6_huisnr_buurt", "CBS_BUURTEN2024.gpkg")

NOORD_PROVINCIES = ["Fryslân", "Groningen", "Drenthe"]
BUFFER_METERS = 100  # 100m buffer rondom provinciegrenzen

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "omnitwin_db"),
    "user": os.getenv("DB_USER", "omnitwin_user"),
    "password": os.getenv("DB_PASSWORD", "admin_omnitwin2026"),
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


# ── Stap 1: Provincies importeren ──────────────────────────────
def import_provincies():
    """Importeer alle provincies naar de gebieden tabel."""
    print("\n" + "=" * 60)
    print("STAP 1: Provincies importeren")
    print("=" * 60)

    gdf = gpd.read_file(PROVINCIES_GPKG, layer="provincies", engine="pyogrio")
    print(f"  📂 Geladen: {len(gdf)} provincies uit {PROVINCIES_GPKG}")
    print(f"  📐 CRS: {gdf.crs}")

    # Zorg dat CRS = EPSG:28992 (RD New)
    if gdf.crs and gdf.crs.to_epsg() != 28992:
        gdf = gdf.to_crs(epsg=28992)
        print("  🔄 Getransformeerd naar EPSG:28992")

    conn = get_conn()
    cur = conn.cursor()

    # Haal of maak gebiedstype 'Provincie'
    cur.execute("SELECT id FROM gebiedstypes WHERE code = 'PROVINCIE' OR naam = 'Provincie' LIMIT 1;")
    row = cur.fetchone()
    if row:
        prov_type_id = row[0]
        print(f"  ✅ Gebiedstype 'Provincie' bestaat al: {prov_type_id}")
    else:
        cur.execute("""
            INSERT INTO gebiedstypes (id, naam, code, beschrijving, bron, niveau)
            VALUES (gen_random_uuid(), 'Provincie', 'PROVINCIE', 'Provincies van Nederland', 'CBS', 'Provincie')
            RETURNING id;
        """)
        prov_type_id = cur.fetchone()[0]
        print(f"  🆕 Gebiedstype 'Provincie' aangemaakt: {prov_type_id}")

    inserted = 0
    updated = 0

    for _, row in gdf.iterrows():
        prov_code = row.get("code", "")
        prov_naam = row.get("naam", "")
        geom = row.geometry

        if not prov_code or not prov_naam:
            continue

        # Maak een ID aan: PV + code (bv. PV20 voor Groningen)
        prov_id = f"PV{prov_code.replace('PV', '')}"

        # Converteer geometrie naar MultiPolygon WKB
        if geom.geom_type == "Polygon":
            from shapely.geometry import MultiPolygon
            geom = MultiPolygon([geom])

        geom_bytes = psycopg2.Binary(geom.wkb)

        cur.execute("""
            INSERT INTO gebieden (id, gebiedstype_id, naam, geom, provincienaam, actief)
            VALUES (%s, %s, %s, ST_SetSRID(ST_GeomFromWKB(%s), 28992), %s, true)
            ON CONFLICT (id) DO UPDATE SET
                naam = EXCLUDED.naam,
                geom = EXCLUDED.geom,
                provincienaam = EXCLUDED.provincienaam,
                updated_at = CURRENT_TIMESTAMP;
        """, (prov_id, str(prov_type_id), prov_naam, geom_bytes, prov_naam))

        if cur.rowcount > 0:
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n  📊 Resultaat: {inserted} provincies ingevoegd/bijgewerkt")
    return True


# ── Stap 2: Gemeenten aanvullen ────────────────────────────────
def import_gemeenten(gdf_buurten):
    """Vul de gemeenten tabel aan met gemeenten die nog ontbreken."""
    print("\n" + "=" * 60)
    print("STAP 2: Gemeenten aanvullen")
    print("=" * 60)

    # Unieke gemeenten uit de buurt-data
    gemeenten = gdf_buurten[["gemeentecode", "gemeentenaam"]].drop_duplicates()
    print(f"  📋 {len(gemeenten)} unieke gemeenten in de buurt-data")

    conn = get_conn()
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for _, row in gemeenten.iterrows():
        gm_code = str(row["gemeentecode"]).replace("GM", "").strip()
        gm_naam = str(row["gemeentenaam"]).strip()

        if not gm_code or not gm_naam:
            continue

        # Pad de code op naar 4 tekens
        gm_code = gm_code.zfill(4)

        # Bepaal provincie op basis van de buurten die erbij horen
        buurt_subset = gdf_buurten[gdf_buurten["gemeentecode"] == row["gemeentecode"]]
        # De provincie is al bepaald via de buffer join (zie stap 3)
        prov_naam = buurt_subset["provincie_naam"].iloc[0] if "provincie_naam" in buurt_subset.columns else "Onbekend"

        # Check of gemeente al bestaat
        cur.execute("SELECT code FROM gemeenten WHERE code = %s;", (gm_code,))
        if cur.fetchone():
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO gemeenten (code, naam, provincie)
            VALUES (%s, %s, %s)
            ON CONFLICT (code) DO NOTHING;
        """, (gm_code, gm_naam, prov_naam))

        if cur.rowcount > 0:
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"  🆕 {inserted} nieuwe gemeenten, ⏭️ {skipped} reeds aanwezig")
    return True


# ── Stap 3: Buurten 2024 importeren ───────────────────────────
def import_buurten():
    """Importeer CBS buurten 2024 gefilterd op noordelijke provincies (100m buffer)."""
    print("\n" + "=" * 60)
    print("STAP 3: Buurten 2024 importeren (Noord-Nederland)")
    print("=" * 60)

    t0 = time.time()

    # 1. Laad provincies en maak buffer
    print("  📂 Provincies laden...")
    prov_gdf = gpd.read_file(PROVINCIES_GPKG, layer="provincies", engine="pyogrio")
    if prov_gdf.crs and prov_gdf.crs.to_epsg() != 28992:
        prov_gdf = prov_gdf.to_crs(epsg=28992)

    noord = prov_gdf[prov_gdf["naam"].isin(NOORD_PROVINCIES)].copy()
    print(f"  🗺️  Geselecteerde provincies: {', '.join(noord['naam'].tolist())}")

    # Buffer van 100m rondom de provinciegrenzen
    noord_buffered = noord.copy()
    noord_buffered["geometry"] = noord_buffered.geometry.buffer(BUFFER_METERS)
    print(f"  🔲 Buffer van {BUFFER_METERS}m toegepast")

    # 2. Laad alle buurten
    print("  📂 Buurten 2024 laden (dit kan even duren bij 99MB)...")
    buurten_gdf = gpd.read_file(BUURTEN_GPKG, layer="buurten", engine="pyogrio")
    print(f"  📊 Totaal: {len(buurten_gdf)} buurten in heel NL")

    if buurten_gdf.crs and buurten_gdf.crs.to_epsg() != 28992:
        buurten_gdf = buurten_gdf.to_crs(epsg=28992)

    # 3. Spatial join: buurten binnen de gebufferde provincies
    print("  🔍 Spatial join uitvoeren (buurten × gebufferde provincies)...")
    buurten_noord = gpd.sjoin(
        buurten_gdf,
        noord_buffered[["naam", "geometry"]],
        how="inner",
        predicate="intersects"
    )
    # Hernoem de provincie kolom
    buurten_noord = buurten_noord.rename(columns={"naam": "provincie_naam"})
    # Verwijder duplicaten (een buurt kan door meerdere buffers geraakt worden)
    buurten_noord = buurten_noord.drop_duplicates(subset=["buurtcode"])
    print(f"  ✅ {len(buurten_noord)} buurten in noord-buffer gevonden (na dedup)")

    t_load = time.time() - t0
    print(f"  ⏱️  Data geladen in {t_load:.1f}s")

    # 4. Gemeenten aanvullen
    import_gemeenten(buurten_noord)

    # 5. Database insert
    print("\n  📝 Buurten naar database schrijven...")
    conn = get_conn()
    cur = conn.cursor()

    # Haal het gebiedstype ID voor CBS Buurt
    cur.execute("SELECT id FROM gebiedstypes WHERE code = 'CBS_BUURT' LIMIT 1;")
    buurt_type_row = cur.fetchone()
    if not buurt_type_row:
        print("  ❌ Gebiedstype CBS_BUURT niet gevonden!")
        return False
    buurt_type_id = str(buurt_type_row[0])

    # Haal het gebiedstype ID voor Gemeente
    cur.execute("SELECT id FROM gebiedstypes WHERE naam = 'Gemeente' LIMIT 1;")
    gm_type_row = cur.fetchone()
    gm_type_id = str(gm_type_row[0]) if gm_type_row else None

    inserted_bu = 0
    updated_bu = 0
    inserted_wk = 0
    inserted_gm = 0
    skipped = 0
    errors = 0

    # Track welke wijken en gemeenten we al gemaakt hebben
    seen_wijken = set()
    seen_gemeenten = set()

    for idx, row in buurten_noord.iterrows():
        try:
            bu_code = str(row["buurtcode"]).strip()
            bu_naam = str(row["buurtnaam"]).strip()
            wk_code = str(row["wijkcode"]).strip() if row.get("wijkcode") else None
            gm_code_raw = str(row["gemeentecode"]).strip()
            gm_naam = str(row["gemeentenaam"]).strip()
            prov_naam = str(row["provincie_naam"]).strip()
            geom = row.geometry

            # Buurt ID: BU + buurtcode (bv. BU00900101)
            bu_id = f"BU{bu_code.replace('BU', '')}"
            gm_code = gm_code_raw.replace("GM", "").zfill(4)

            # Converteer geometrie
            if geom is None or geom.is_empty:
                skipped += 1
                continue

            if geom.geom_type == "Polygon":
                from shapely.geometry import MultiPolygon
                geom = MultiPolygon([geom])

            geom_bytes = psycopg2.Binary(geom.wkb)

            # Insert GM record als dat nog niet bestaat
            gm_id = f"GM{gm_code}"
            if gm_id not in seen_gemeenten and gm_type_id:
                cur.execute("""
                    INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, provincienaam, actief)
                    VALUES (%s, %s, %s, %s, %s, true)
                    ON CONFLICT (id) DO UPDATE SET
                        provincienaam = EXCLUDED.provincienaam,
                        updated_at = CURRENT_TIMESTAMP;
                """, (gm_id, gm_type_id, gm_naam, gm_code, prov_naam))
                if cur.rowcount > 0:
                    inserted_gm += 1
                seen_gemeenten.add(gm_id)

            # Insert WK record als dat nog niet bestaat
            if wk_code and wk_code not in seen_wijken:
                wk_id = f"WK{wk_code.replace('WK', '')}"
                cur.execute("""
                    INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, provincienaam, actief)
                    VALUES (%s, %s, %s, %s, %s, true)
                    ON CONFLICT (id) DO UPDATE SET
                        provincienaam = EXCLUDED.provincienaam,
                        updated_at = CURRENT_TIMESTAMP;
                """, (wk_id, buurt_type_id, f"Wijk {wk_code}", gm_code, prov_naam))
                if cur.rowcount > 0:
                    inserted_wk += 1
                seen_wijken.add(wk_code)

            # Insert buurt
            cur.execute("""
                INSERT INTO gebieden (id, gebiedstype_id, naam, geom, gemeente_code, provincienaam, actief)
                VALUES (%s, %s, %s, ST_SetSRID(ST_GeomFromWKB(%s), 28992), %s, %s, true)
                ON CONFLICT (id) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    geom = EXCLUDED.geom,
                    gemeente_code = EXCLUDED.gemeente_code,
                    provincienaam = EXCLUDED.provincienaam,
                    updated_at = CURRENT_TIMESTAMP;
            """, (bu_id, buurt_type_id, bu_naam, geom_bytes, gm_code, prov_naam))

            if cur.rowcount > 0:
                inserted_bu += 1

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ⚠️ Error bij {bu_code}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    t_total = time.time() - t0
    print(f"\n  📊 Resultaat:")
    print(f"     🏘️  Buurten:    {inserted_bu} ingevoegd/bijgewerkt")
    print(f"     🏗️  Wijken:     {inserted_wk} ingevoegd/bijgewerkt")
    print(f"     🏛️  Gemeenten:  {inserted_gm} ingevoegd/bijgewerkt")
    print(f"     ⏭️  Overgeslagen: {skipped} (lege geometrie)")
    print(f"     ❌ Fouten:      {errors}")
    print(f"     ⏱️  Totale tijd: {t_total:.1f}s")

    return True


# ── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Import CBS Gebiedsindeling 2024")
    parser.add_argument("--stap", choices=["provincies", "gemeenten", "buurten", "alles"],
                        default="alles", help="Welke stap uitvoeren")
    args = parser.parse_args()

    print("=" * 60)
    print("🗺️  CBS Gebiedsindeling 2024 Import")
    print(f"   Focus: {', '.join(NOORD_PROVINCIES)}")
    print(f"   Buffer: {BUFFER_METERS}m")
    print("=" * 60)

    if args.stap in ("provincies", "alles"):
        import_provincies()

    if args.stap in ("buurten", "alles"):
        import_buurten()  # Dit roept intern ook import_gemeenten() aan

    if args.stap == "gemeenten":
        print("  ℹ️  Gemeenten worden automatisch bij de buurten-stap aangevuld.")
        print("     Gebruik --stap buurten of --stap alles.")

    print("\n" + "=" * 60)
    print("✅ Import voltooid!")
    print("=" * 60)


if __name__ == "__main__":
    main()
