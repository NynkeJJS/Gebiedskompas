import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy import text
from src.database import engine
import json

def inspect_data():
    with engine.connect() as conn:
        # Get one row to see columns and metadata structure
        query = text("SELECT id, naam, metadata FROM gebieden LIMIT 5")
        result = conn.execute(query)
        
        print("--- Sample Metadata ---")
        for row in result:
            print(f"Gebied: {row.naam}")
            if row.metadata:
                print(f"Metadata keys: {list(row.metadata.keys())}")
                # Check for common water keys
                for key in ['water', 'WATER', 'is_water', 'HeeftWater']:
                    if key in row.metadata:
                        print(f"  FOUND {key}: {row.metadata[key]}")
            else:
                print("  No metadata")
        
        # Check distinct values for a 'water' key if we found one, or guess
        # CBS often uses 'water' = 'JA' / 'NEE'
        print("\n--- Checking for 'water' in metadata ---")
        q2 = text("""
            SELECT 
                metadata->>'water' as water_val,
                COUNT(*) as count
            FROM gebieden 
            WHERE metadata ? 'water'
            GROUP BY metadata->>'water'
        """)
        res2 = conn.execute(q2).fetchall()
        if res2:
            print("Values for metadata->'water':")
            for r in res2:
                print(f"  '{r[0]}': {r[1]}")
        else:
            print("Key 'water' not found in metadata jsonb.")

if __name__ == "__main__":
    inspect_data()
