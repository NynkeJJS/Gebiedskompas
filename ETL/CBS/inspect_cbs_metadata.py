import sys
import os
import json
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
# Add ETL_Scripts to path
sys.path.append(str(project_root / 'data' / 'ETL_Scripts' / 'CBS'))

from cbs_data_fetcher import CBSDataFetcher

def main():
    print("Inspecting Metadata for 50140NED...")
    
    # Use the endpoint provided by user/config
    endpoint = "dataderden.cbs.nl" 
    dataset_id = "50140NED"
    
    fetcher = CBSDataFetcher(endpoint=endpoint)
    
    try:
        data_props = fetcher.fetch_data_properties(dataset_id)
        print(f"\nFound {len(data_props)} properties. Searching for 'rondkomen'...")
        
        found = []
        for p in data_props:
            title = p.get('Title', '') or p.get('title', '')
            key = p.get('Key', '') or p.get('key', '')
            desc = p.get('Description', '') or p.get('description', '')
            
            if 'rondkomen' in title.lower() or 'rondkomen' in desc.lower():
                found.append(f"Title: {title} | Key: {key}")
                
        if found:
            print("\n✅ Matches found:")
            for f in found:
                print(f"   - {f}")
        else:
            print("\n❌ No matches found for 'rondkomen'.")
            print("Listing first 10 properties as sample:")
            for p in data_props[:10]:
                print(f"   - {p.get('Title')} ({p.get('Key')})")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
