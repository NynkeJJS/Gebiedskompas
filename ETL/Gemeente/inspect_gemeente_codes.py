import pandas as pd
import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from src.database import SessionLocal

def main():
    print("Reading Excel file...", flush=True)
    excel_path = project_root / 'data' / 'gemeenten' / 'gemeenten-alfabetisch-2025.xlsx'
    
    try:
        df = pd.read_excel(excel_path, sheet_name='Gemeenten_alfabetisch')
        
        # Normalize column names just in case
        df.columns = [c.strip() for c in df.columns]
        
        # Filter Fryslân (robust)
        if 'Provincienaam' in df.columns:
            fryslan = df[df['Provincienaam'].astype(str).str.strip() == 'Fryslân']
        else:
            print("Column 'Provincienaam' not found. Available:", df.columns.tolist(), flush=True)
            return
        
        print(f"Found {len(fryslan)} municipalities in Fryslân:", flush=True)
        print(fryslan[['Gemeentenaam', 'Gemeentecode', 'GemeentecodeGM']], flush=True)
        
        # Check DB
        print("\nChecking Database for existing municipalities...", flush=True)
        db = SessionLocal()
        
        # Check 'gebieden' table for GM codes
        query = text("SELECT id, naam FROM gebieden WHERE gebiedstype_id = 'GM' AND naam IN :names")
        db_rows = db.execute(query, {"names": tuple(fryslan['Gemeentenaam'].tolist())}).fetchall()
        
        found_in_db = {row.naam: row.id for row in db_rows}
        
        print("\nComparison:", flush=True)
        for _, row in fryslan.iterrows():
            naam = row['Gemeentenaam']
            code = f"GM{row['Gemeentecode']:04d}" # Format '80' -> 'GM0080'
            code_gm = row['GemeentecodeGM'] # 'GM0080'
            
            db_id = found_in_db.get(naam, "NOT FOUND")
            
            status = "OK" if db_id == code_gm else "MISMATCH/MISSING"
            print(f"{naam:<20} | Excel: {code_gm} | DB: {db_id:<10} | {status}", flush=True)

    except Exception as e:
        print(f"Error: {e}", flush=True)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()
