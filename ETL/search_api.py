#!/usr/bin/env python3
"""
Unified Search API voor D-OmniTwin ETL
Helpt bij het vinden en inspecteren van datasets van CBS, RIVM en Politie.
"""

import requests
import json
import argparse
import textwrap

ENDPOINTS = {
    "CBS": "https://opendata.cbs.nl/ODataCatalog",
    "RIVM/Politie (Derden)": "https://dataderden.cbs.nl/ODataCatalog"
}

def search_datasets(keyword):
    print(f"\n🔎 Zoeken naar datasets met '{keyword}'...\n" + "="*60)
    
    for naam, basis_url in ENDPOINTS.items():
        url = f"{basis_url}/Tables?$format=json&$select=Identifier,Title,Period,Frequency,ShortDescription"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            tables = data.get('value', [])
            # Filter op keyword in Title of Identifier
            results = [t for t in tables if keyword.lower() in t.get('Title', '').lower() or keyword.lower() in t.get('Identifier', '').lower()]
            
            if results:
                print(f"✅ Gevonden op {naam} ({len(results)} resultaten):")
                for row in results:
                    print(f"   [{row.get('Identifier')}] {row.get('Title')} ({row.get('Period')})")
            else:
                print(f"❌ Geen resultaten gevonden op {naam}.")
                
        except Exception as e:
            print(f"⚠️ Fout bij zoeken op {naam}: {e}")
    print("=" * 60 + "\n")

def inspect_dataset(dataset_id, is_derden=False):
    """Haal de DataProperties (kolommen) op van een specifieke dataset."""
    basis_url = ENDPOINTS["RIVM/Politie (Derden)"] if is_derden else ENDPOINTS["CBS"]
    
    # We moeten de echte ODataFeed endpoint hebben voor de DataProperties
    feed_url = basis_url.replace("ODataCatalog", "ODataFeed/OData") if not is_derden else basis_url.replace("ODataCatalog", "ODataApi/odata")
    url = f"{feed_url}/{dataset_id}/DataProperties?$format=json"
    
    print(f"📊 Inspectie van kolommen (DataProperties) voor dataset '{dataset_id}'...\n" + "="*60)
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        properties = data.get('value', [])
        if properties:
            print(f"{'Sleutel (Key)':<40} | {'Titel (Title)':<40} | {'Type'}")
            print("-" * 100)
            for prop in properties:
                # Alleen metrics of interessante dimensies tonen, IDs en algemene meta iets verbergen indien gewenst
                # maar voor mapping is alles handig.
                key = str(prop.get('Key', ''))
                title = str(prop.get('Title', ''))
                datatype = str(prop.get('Datatype', ''))
                print(f"{key:<40} | {title[:38]:<40} | {datatype}")
        else:
            print("❌ Geen kolommen gevonden. Controleer of de dataset ID correct is en of de juiste endpoint (-d) wordt gebruikt.")
    except Exception as e:
        print(f"⚠️ Fout bij inspecteren van dataset {dataset_id}: {e}")
        print("Tip: Probeer de -d flag te gebruiken als dit een RIVM of Politie dataset is (dataderden.cbs.nl).")
    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin ETL Search - Vind en inspecteer datasets voor mapping.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent('''\
        Voorbeelden:
          1. Zoek naar het woord 'Gezondheid' over alle OData API's:
             python search_api.py -q Gezondheid
             
          2. Inspecteer de kolommen van de CBS dataset '83739NED' voor mapping in kompas:
             python search_api.py -i 83739NED
             
          3. Inspecteer een de kolommen van een RIVM/Politie dataset (Dataderden):
             python search_api.py -i 50150NED -d
        ''')
    )
    
    parser.add_argument('-q', '--query', type=str, help='Zoekterm voor datasets (bijv. "Veiligheid").')
    parser.add_argument('-i', '--inspect', type=str, help='Dataset ID (bijv. "83739NED") om de beschikbare kolommen te zien.')
    parser.add_argument('-d', '--derden', action='store_true', help='Als je -i gebruikt: vink dit aan als het een RIVM/Politie bron is op dataderden.cbs.nl.')

    args = parser.parse_args()

    if args.query:
        search_datasets(args.query)
    elif args.inspect:
        inspect_dataset(args.inspect, is_derden=args.derden)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
