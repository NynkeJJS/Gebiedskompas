import sys
import os
import json
import pandas as pd
from sqlalchemy import text
from pathlib import Path

# Add project root to path to import src and services
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from src.database import SessionLocal
from services.kompas_service import KompasService

def main():
    print("Starting Kompas Hierarchy Export...")
    
    # 1. Setup DB
    db = SessionLocal()
    try:
        service = KompasService(db)
        
        # 2. Get Config ID
        # Default to standard config (usually id=1)
        config_id = service.get_standaard_config_id()
        print(f"Using Config ID: {config_id}")
        
        # 3. Fetch Hierarchy JSON (Nested structure)
        print("Fetching JSON hierarchy...")
        hierarchy_data = service.get_hierarchie(config_id)
        
        # 4. Save JSON
        export_dir = project_root / 'exports'
        export_dir.mkdir(exist_ok=True)
        
        json_path = export_dir / 'kompas_hierarchie.json'
        
        # Helper to convert datetime to string for JSON serialization
        def json_serial(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            raise TypeError (f"Type {type(obj)} not serializable")

        with open(json_path, 'w') as f:
            json.dump(hierarchy_data, f, indent=2, default=json_serial)
        print(f"JSON exported to: {json_path}")
        
        # 5. Fetch Flat Data for Excel
        # We join with indicatoren table to get metadata like eenheid and bron
        print("Fetching flat data for Excel...")
        query = text("""
            SELECT 
                v.titel_naam AS "Titel",
                v.thema_naam AS "Thema",
                v.onderdeel_naam AS "Onderdeel",
                v.indicator_naam AS "Indicator",
                i.eenheid AS "Eenheid",
                i.bron AS "Bron",
                i.omschrijving AS "Omschrijving",
                v.weging AS "Weging"
            FROM v_kompas_hierarchie v
            LEFT JOIN indicatoren i ON v.indicator_uuid = i.uuid
            WHERE v.config_id = :config_id
            ORDER BY v.titel_id, v.thema_id, v.onderdeel_id, v.indicator_naam
        """)
        
        # Use pandas to read sql
        df = pd.read_sql(query, db.bind, params={"config_id": config_id})
        
        excel_path = export_dir / 'kompas_hierarchie.xlsx'
        df.to_excel(excel_path, index=False)
        print(f"Excel exported to: {excel_path}")
        
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
