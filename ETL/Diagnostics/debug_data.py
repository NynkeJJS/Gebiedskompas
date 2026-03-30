
from src.database import SessionLocal
from sqlalchemy import text

def debug_db():
    db = SessionLocal()
    try:
        print("Checking Database Content...\n")

        # 1. Check Indicatoren Metadata (Definition)
        print("--- 1. Indicatoren Metadata ---")
        result = db.execute(text("SELECT naam, definitie, bron FROM indicatoren LIMIT 5")).fetchall()
        for row in result:
            print(f"Name: {row.naam}")
            print(f"  Definitie: {row.definitie}")
            print(f"  Bron: {row.bron}")
        
        # 2. Check History Data (Gebied Data)
        print("\n--- 2. History Data Sample ---")
        # Find an indicator that has data
        indicator = db.execute(text("SELECT uuid, naam FROM indicatoren LIMIT 1")).fetchone()
        if indicator:
            uuid = indicator.uuid
            print(f"Checking history for indicator: {indicator.naam} ({uuid})")
            
            # Find a gebied that has data for this indicator
            data_row = db.execute(text(f"SELECT gebied_id FROM gebied_data WHERE indicator_uuid = '{uuid}' LIMIT 1")).fetchone()
            
            if data_row:
                gebied_id = data_row.gebied_id
                print(f"Found data for gebied: {gebied_id}")
                
                history = db.execute(text(f"""
                    SELECT jaar, waarde 
                    FROM gebied_data 
                    WHERE indicator_uuid = '{uuid}' AND gebied_id = '{gebied_id}'
                    ORDER BY jaar
                """)).fetchall()
                
                print(f"History entries found: {len(history)}")
                for h in history:
                    print(f"  - {h.jaar}: {h.waarde}")
            else:
                print("No data found for this indicator in any area.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_db()
