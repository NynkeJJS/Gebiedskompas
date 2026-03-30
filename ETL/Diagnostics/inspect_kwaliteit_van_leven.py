import sys
import os
from pathlib import Path
from sqlalchemy import text
import pandas as pd

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from src.database import SessionLocal

def main():
    print("Inspecting 'Kwaliteit van leven' Data Coverage...")
    db = SessionLocal()
    
    try:
        # 1. Identify "Kwaliteit van leven" IDs in hierarchy
        print("\n1. Finding Theme/Topic IDs...")
        query_hier = text("""
            SELECT DISTINCT titel_naam, thema_naam, onderdeel_naam, indicator_naam, indicator_uuid
            FROM v_kompas_hierarchie
            WHERE titel_naam ILIKE '%Kwaliteit van leven%'
               OR thema_naam ILIKE '%Kwaliteit van leven%' 
               OR onderdeel_naam ILIKE '%Kwaliteit van leven%'
            ORDER BY thema_naam, onderdeel_naam, indicator_naam
        """)
        hier_rows = db.execute(query_hier).fetchall()
        
        if not hier_rows:
            print("⚠️  No indicators found for 'Kwaliteit van leven' in v_kompas_hierarchie.")
            # Fallback: list themes
            themes = db.execute(text("SELECT DISTINCT thema_naam FROM v_kompas_hierarchie")).fetchall()
            print("Available themes:", [r[0] for r in themes])
            return

        print(f"   Found {len(hier_rows)} indicators linked to 'Kwaliteit van leven'.")
        # Collect UUIDs
        ind_uuids = [row.indicator_uuid for row in hier_rows]
        
        # 2. Check Data Counts by Municipality
        print("\n2. Checking Data Counts per Municipality...")
        
        # We start with the 3 municipalities of interest
        municipalities = ['Súdwest-Fryslân', 'Smallingerland', 'De Fryske Marren']
        
        for muni in municipalities:
            print(f"\n   --- {muni} ---")
            # Get Areas (Buurten) for this municipality
            # Note: We query 'gebieden' directly. 
            # We assume 'gemeente_code' is now correct or we join via spatial/name if needed?
            # We just updated codes, so we should rely on the link 'gebieden.gemeente_code' -> 'gemeenten.code'
            
            # Find the municipality code first to be sure
            muni_row = db.execute(text("SELECT code FROM gemeenten WHERE naam = :naam"), {"naam": muni}).fetchone()
            if not muni_row:
                print(f"   ❌ Municipality {muni} not found in DB.")
                continue
                
            muni_code = muni_row.code
            print(f"   Code: {muni_code}")
            
            # Count data points for these indicators in areas belonging to this municipality
            query_count = text("""
                SELECT COUNT(*) 
                FROM gebied_data gd
                JOIN gebieden g ON gd.gebied_id = g.id
                WHERE g.gemeente_code = :muni_code
                  AND gd.indicator_uuid IN :uuids
            """)
            
            count = db.execute(query_count, {"muni_code": muni_code, "uuids": tuple(ind_uuids)}).scalar()
            
            # Also calculate coverage % ?
            # Total areas
            area_count = db.execute(text("SELECT COUNT(*) FROM gebieden WHERE gemeente_code = :code"), {"code": muni_code}).scalar()
            
            if area_count > 0:
                avg_per_area = count / area_count
                expected = len(ind_uuids)
                print(f"   Total Data Points: {count}")
                print(f"   Total Areas: {area_count}")
                print(f"   Avg Indicators per Area: {avg_per_area:.1f} / {expected}")
            else:
                 print(f"   Total Data Points: {count}")
                 print(f"   ⚠️ No areas found for this municipality code.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
