import os
import sys
import configparser
import psycopg2
from pathlib import Path

# Add project root to path for imports if needed
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def load_config():
    config = configparser.ConfigParser()
    config_path = project_root / 'config.ini'
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    config.read(config_path)
    return config

def init_db():
    config = load_config()
    
    try:
        db_config = config['DATABASE']
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected to database.")
        
        schema_path = project_root / 'data' / 'schema.sql'
        if not schema_path.exists():
            print(f"Error: Schema file not found at {schema_path}")
            sys.exit(1)
            
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        print("Executing schema...")
        cursor.execute(schema_sql)
        
        print("Database initialized successfully.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
