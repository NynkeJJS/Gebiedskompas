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
    print("Inspecting Data Sources for Smallingerland (0090)...")
    db = SessionLocal()
    
    muni_code = '0090'
    
    try:
        # Check total count
        print("\n1. Total Data Count:")
        count = db.execute(text("""
            SELECT COUNT(*) 
            FROM gebied_data gd
            JOIN gebieden g ON gd.gebied_id = g.id
            WHERE g.gemeente_code = :code
        """), {"code": muni_code}).scalar()
        print(f"   Total records for {muni_code}: {count}")
        
        # Check source breakdown
        print("\n2. Data Source Breakdown (Top 20):")
        sources = db.execute(text("""
            SELECT gd.bron, COUNT(*) as cnt
            FROM gebied_data gd
            JOIN gebieden g ON gd.gebied_id = g.id
            WHERE g.gemeente_code = :code
            GROUP BY gd.bron
            ORDER BY cnt DESC
            LIMIT 20
        """), {"code": muni_code}).fetchall()
        
        for s in sources:
            print(f"   {s.bron}: {s.cnt}")
            
        # Check if any CBS data exists
        has_cbs = any('CBS_' in (s.bron or '') for s in sources)
        print(f"\n   Has CBS Data? {'YES' if has_cbs else 'NO'}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
