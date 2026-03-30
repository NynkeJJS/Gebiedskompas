import requests
import json

def search_datasets(keyword):
    print(f"🔎 Searching for datasets with '{keyword}'...")
    url = "https://opendata.cbs.nl/ODataCatalog/Tables?$format=json&$select=Identifier,Title,Period,Frequency"
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"❌ Failed to decode JSON. Response start: {response.text[:200]}")
            return
            
        tables = data.get('value', [])
        results = [t for t in tables if keyword.lower() in t.get('Title', '').lower() or keyword.lower() in t.get('Identifier', '').lower()]
        
        if results:
            print(f"✅ Found {len(results)} datasets:")
            for row in results:
                print(f"   - {row.get('Identifier')}: {row.get('Title')} ({row.get('Period')})")
        else:
            print("❌ No datasets found.")
            
    except Exception as e:
        print(f"⚠️ Error searching CBS: {e}")

if __name__ == "__main__":
    search_datasets("Gezondheid")
    print("-" * 40)
    search_datasets("Overlast")
    print("-" * 40)
    search_datasets("Veiligheid")
