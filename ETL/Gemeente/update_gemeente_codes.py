import sys
import os
from pathlib import Path
from sqlalchemy import text

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from src.database import SessionLocal

def main():
    print("Starting Municipality Code Update...")
    db = SessionLocal()
    
    # Mappings to fix: Old Code -> New Code
    # Based on analysis:
    # Smallingerland: 0140 -> 0090
    # De Fryske Marren: 1921 -> 1940
    updates = [
        {"naam": "Smallingerland", "old_code": "0140", "new_code": "0090"},
        {"naam": "De Fryske Marren", "old_code": "1921", "new_code": "1940"}
    ]
    
    try:
        for update in updates:
            naam = update["naam"]
            old = update["old_code"]
            new = update["new_code"]
            
            print(f"\nProcessing {naam}: {old} -> {new}")
            
            # 1. Check if new code already exists
            existing_new = db.execute(text("SELECT code FROM gemeenten WHERE code = :code"), {"code": new}).fetchone()
            if existing_new:
                print(f"⚠️  Target code {new} already exists! Skipping creation.")
                # If it exists, we just need to move FKs and delete old
            else:
                # 2. Get old record data
                old_record = db.execute(text("SELECT * FROM gemeenten WHERE code = :code"), {"code": old}).fetchone()
                if not old_record:
                    print(f"❌ Old record {old} not found. Skipping.")
                    continue
                
                # 3. Insert new record
                print(f"   Creating new record with code {new}...")
                db.execute(
                    text("""
                        INSERT INTO gemeenten (code, naam, provincie, is_eiland, created_at, updated_at)
                        VALUES (:code, :naam, :provincie, :is_eiland, :created_at, NOW())
                    """),
                    {
                        "code": new,
                        "naam": old_record.naam,
                        "provincie": old_record.provincie,
                        "is_eiland": old_record.is_eiland,
                        "created_at": old_record.created_at
                    }
                )
            
            # 4. Update Foreign Keys in 'gebieden'
            print(f"   Updating Foreign Keys in 'gebieden'...")
            result = db.execute(
                text("UPDATE gebieden SET gemeente_code = :new_code WHERE gemeente_code = :old_code"),
                {"new_code": new, "old_code": old}
            )
            print(f"   ✅ Updated {result.rowcount} areas.")
            
            # 5. Delete old record
            print(f"   Deleting old record {old}...")
            db.execute(text("DELETE FROM gemeenten WHERE code = :code"), {"code": old})
            print("   ✅ Deleted old record.")
            
            db.commit()
            print(f"✅ Successfully updated {naam}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
