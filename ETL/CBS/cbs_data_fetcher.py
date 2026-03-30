#!/usr/bin/env python3
"""
CBS Data Fetcher - Integrated Script
Combineert beste practices van CBS_API_V4.py en cbs_omschrijvingen_ophalen.py
Output: 2 JSON files (data + metadata)

Author: Based on A. Wolters scripts
Last modified: 19-01-2026
"""

import requests
import pandas as pd
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from tqdm import tqdm


class CBSDataFetcher:
    """Integrated CBS data and metadata fetcher with JSON output"""
    
    def __init__(self, endpoint: str = 'opendata.cbs.nl', timeout: int = 30):
        """
        Initialize CBS Data Fetcher
        
        Args:
            endpoint: CBS API endpoint (default: opendata.cbs.nl)
            timeout: Request timeout in seconds
        """
        if 'dataderden' in endpoint:
             self.base_url = f'https://{endpoint}/ODataApi/odata'
        else:
             self.base_url = f'https://{endpoint}/ODataFeed/OData'
             
        self.endpoint = endpoint
        self.timeout = timeout
        self.session = requests.Session()
        
    def fetch_table_info(self, dataset_id: str) -> Dict[str, Any]:
        """
        Haal TableInfos op voor dataset metadata
        
        Args:
            dataset_id: CBS dataset code (bijv. '83739NED')
            
        Returns:
            Dictionary met table info
        """
        url = f'{self.base_url}/{dataset_id}/TableInfos'
        params = {'$format': 'json'}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.encoding = response.apparent_encoding
            response.raise_for_status()
            data = response.json()
            
            if data.get('value'):
                return data['value'][0]
            return {}
        except Exception as e:
            print(f"⚠️  Waarschuwing: Kon TableInfos niet ophalen: {e}")
            return {}
    
    def fetch_data_properties(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        Haal DataProperties op voor metadata/beschrijvingen
        
        Args:
            dataset_id: CBS dataset code
            
        Returns:
            List van property dictionaries
        """
        url = f'{self.base_url}/{dataset_id}/DataProperties'
        params = {'$format': 'json'}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.encoding = response.apparent_encoding
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except Exception as e:
            print(f"⚠️  Waarschuwing: Kon DataProperties niet ophalen: {e}")
            return []
    
    def get_available_tables(self, dataset_id: str) -> List[str]:
        """
        Haal lijst van beschikbare tabellen op
        
        Args:
            dataset_id: CBS dataset code
            
        Returns:
            List van table namen
        """
        url = f'{self.base_url}/{dataset_id}'
        params = {'$format': 'json'}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.encoding = response.apparent_encoding
            response.raise_for_status()
            data = response.json()
            
            tables = []
            for item in data.get('value', []):
                table_name = item['url'].split('/')[-1].split('?')[0]
                tables.append(table_name)
            
            # Prefer TypedDataSet over UntypedDataSet
            if 'TypedDataSet' in tables and 'UntypedDataSet' in tables:
                tables.remove('UntypedDataSet')
                
            return tables
        except Exception as e:
            print(f"❌ Fout bij ophalen tabellen: {e}")
            raise
    
    def fetch_table_data(self, dataset_id: str, table_name: str, 
                        gemeente_filter: Optional[str] = None,
                        available_columns: List[str] = None) -> List[Dict[str, Any]]:
        """
        Haal data op van specifieke tabel (met paginering)
        
        Args:
            dataset_id: CBS dataset code
            table_name: Naam van de tabel
            gemeente_filter: Optionele gemeente code voor filtering
            available_columns: Lijst van beschikbare kolomnamen (keys)
            
        Returns:
            List van data records
        """
        all_data = []
        url = f'{self.base_url}/{dataset_id}/{table_name}'
        params = {'$format': 'json'}
        
        # Optionele filtering op gemeente
        if gemeente_filter and table_name in ['TypedDataSet', 'UntypedDataSet']:
            filters = []
            
            # Check which region columns exist and filter on them
            # Default columns often used in CBS data
            region_cols = ['WijkenEnBuurten', 'Wijken', 'RegioS']
            
            # If available_columns matches known structure, use it. 
            # Otherwise fall back to trying them all (historical behavior) 
            # or better: only check if we know they exist.
            
            for col in region_cols:
                if available_columns and col not in available_columns:
                    continue
                
                # Construct filter part for this column
                # Logic: startswith(Col, 'GMxxxx') or 'WKxxxx' or 'BUxxxx' or 'NL'
                # This is safer than substring and works on dataderden.cbs.nl
                filters.append(
                    f"("
                    f"(startswith({col},'GM{gemeente_filter}')) or "
                    f"(startswith({col},'WK{gemeente_filter}')) or "
                    f"(startswith({col},'BU{gemeente_filter}')) or "
                    f"(startswith({col},'NL'))"
                    f")"
                )
            
            if filters:
                params["$filter"] = " and ".join(filters)
            else:
                 # If no region columns found but filter requested? 
                 # Maybe it's a dataset without region cols?
                 print(f"⚠️  Waarschuwing: Gemeente filter negeerd omdat geen regio kolommen ({region_cols}) gevonden zijn.")
        
        print(f"  📥 Ophalen: {table_name}...")
        
        # Paginering met progress bar
        with tqdm(desc=f"    {table_name}", unit=" rijen") as pbar:
            while url:
                try:
                    response = self.session.get(url, params=params, timeout=self.timeout)
                    response.encoding = response.apparent_encoding
                    response.raise_for_status()
                    data_json = response.json()
                    
                    batch = data_json.get('value', [])
                    all_data.extend(batch)
                    pbar.update(len(batch))
                    
                    # Volgende pagina
                    url = data_json.get('odata.nextLink')
                    params = {}  # Clear params for next link
                    
                except Exception as e:
                    print(f"\n❌ Fout bij ophalen data: {e}")
                    raise
        
        print(f"  ✅ {len(all_data)} rijen opgehaald")
        return all_data
    
    def create_metadata_json(self, dataset_id: str, table_info: Dict, 
                            data_properties: List[Dict]) -> Dict[str, Any]:
        """
        Creëer gestructureerd metadata JSON object
        
        Args:
            dataset_id: CBS dataset code
            table_info: TableInfos data
            data_properties: DataProperties data
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "dataset": {
                "id": dataset_id,
                "title": table_info.get('Title', ''),
                "short_title": table_info.get('ShortTitle', ''),
                "description": table_info.get('Description', ''),
                "summary": table_info.get('Summary', ''),
                "source": "CBS",
                "endpoint": self.endpoint,
                "retrieved_at": datetime.utcnow().isoformat() + 'Z'
            },
            "metadata": {
                "properties": []
            },
            "additional_info": {
                "modified": table_info.get('Modified', ''),
                "catalog_frequency": table_info.get('CatalogFrequency', ''),
                "default_presentation": table_info.get('DefaultPresentation', ''),
                "graph_types": table_info.get('GraphTypes', '')
            }
        }
        
        # Process properties
        for prop in data_properties:
            prop_info = {
                "key": prop.get('Key', ''),
                "title": prop.get('Title', ''),
                "description": prop.get('Description', ''),
                "datatype": prop.get('Datatype', ''),
                "unit": prop.get('Unit', ''),
                "decimals": prop.get('Decimals'),
                "default_value": prop.get('DefaultValue', '')
            }
            metadata["metadata"]["properties"].append(prop_info)
        
        return metadata
    
    def create_data_json(self, dataset_id: str, table_name: str, 
                        data_records: List[Dict], filters_applied: Dict) -> Dict[str, Any]:
        """
        Creëer gestructureerd data JSON object
        
        Args:
            dataset_id: CBS dataset code
            table_name: Naam van de tabel
            data_records: Lijst met data records
            filters_applied: Toegepaste filters
            
        Returns:
            Data dictionary
        """
        data_json = {
            "dataset": {
                "id": dataset_id,
                "table": table_name,
                "source": "CBS",
                "endpoint": self.endpoint,
                "retrieved_at": datetime.utcnow().isoformat() + 'Z',
                "filters_applied": filters_applied
            },
            "data": {
                "records": data_records,
                "record_count": len(data_records)
            },
            "quality": {
                "completeness": self._calculate_completeness(data_records)
            }
        }
        
        return data_json
    
    def _calculate_completeness(self, records: List[Dict]) -> float:
        """
        Bereken data completeness percentage
        
        Args:
            records: Data records
            
        Returns:
            Completeness percentage (0-100)
        """
        if not records:
            return 0.0
        
        total_values = 0
        non_null_values = 0
        
        for record in records:
            for value in record.values():
                total_values += 1
                if value is not None and value != '':
                    non_null_values += 1
        
        if total_values == 0:
            return 0.0
            
        return round((non_null_values / total_values) * 100, 2)
    
    def save_json(self, data: Dict[str, Any], filepath: str, pretty: bool = True):
        """
        Sla JSON data op naar bestand
        
        Args:
            data: Dictionary om op te slaan
            filepath: Output bestandspad
            pretty: Pretty print met indentation
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)
        
        print(f"  💾 Opgeslagen: {filepath}")
    
    def fetch_and_save(self, dataset_id: str, output_dir: str = './output', 
                      gemeente_filter: Optional[str] = None):
        """
        Hoofd workflow: haal data en metadata op en sla op als JSON
        
        Args:
            dataset_id: CBS dataset code
            output_dir: Output directory
            gemeente_filter: Optionele gemeente code
        """
        print(f"\n{'='*60}")
        print(f"📊 CBS Dataset: {dataset_id}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Stap 1: Haal metadata op
        print("1️⃣  Metadata ophalen...")
        table_info = self.fetch_table_info(dataset_id)
        data_properties = self.fetch_data_properties(dataset_id)
        
        # Stap 2: Haal beschikbare tabellen op
        print("\n2️⃣  Beschikbare tabellen ophalen...")
        tables = self.get_available_tables(dataset_id)
        print(f"  📋 Gevonden: {', '.join(tables)}")
        
        # Stap 3: Haal data op (alleen TypedDataSet of eerste data tabel)
        print("\n3️⃣  Data ophalen...")
        data_table = 'TypedDataSet' if 'TypedDataSet' in tables else (
            next((t for t in tables if 'DataSet' in t or not t.endswith('s')), tables[0])
        )
        
        filters = {}
        if gemeente_filter:
            filters['gemeente_code'] = gemeente_filter
        
        # Extract available keys from properties
        available_keys = [p.get('Key') for p in data_properties]
        data_records = self.fetch_table_data(dataset_id, data_table, gemeente_filter, available_columns=available_keys)
        
        # Stap 4: Creëer JSON structures
        print("\n4️⃣  JSON objecten creëren...")
        metadata_json = self.create_metadata_json(dataset_id, table_info, data_properties)
        data_json = self.create_data_json(dataset_id, data_table, data_records, filters)
        
        # Stap 5: Sla op
        print("\n5️⃣  JSON bestanden opslaan...")
        short_title = table_info.get('ShortTitle', dataset_id).replace(':', '').replace(' ', '_').replace('/', '_')
        
        metadata_file = f"{output_dir}/{short_title}_METADATA.json"
        data_file = f"{output_dir}/{short_title}_DATA.json"
        
        self.save_json(metadata_json, metadata_file)
        self.save_json(data_json, data_file)
        
        # Samenvatting
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ Voltooid in {elapsed:.2f} seconden")
        print(f"{'='*60}")
        print(f"📄 Metadata: {metadata_file}")
        print(f"📄 Data:     {data_file}")
        print(f"📊 Records:  {len(data_records)}")
        print(f"{'='*60}\n")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='CBS Data Fetcher - Haal CBS data en metadata op en sla op als JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  # Basis gebruik
  python cbs_data_fetcher.py -ds 83739NED
  
  # Met gemeente filter (Súdwest-Fryslân)
  python cbs_data_fetcher.py -ds 83739NED -gm 1900
  
  # Aangepaste output directory
  python cbs_data_fetcher.py -ds 84417NED -o ./mijn_output
  
  # Politie data (ander endpoint)
  python cbs_data_fetcher.py -ds 47026NED -e dataderden.cbs.nl
        """
    )
    
    parser.add_argument('-ds', '--dataset', required=True,
                       help='CBS dataset code (formaat: "12345NED")')
    parser.add_argument('-o', '--output', default='./output',
                       help='Output directory (default: ./output)')
    parser.add_argument('-gm', '--gemeente', 
                       help='Gemeente code voor filtering (bijv. "1900" voor SWF)')
    parser.add_argument('-e', '--endpoint', default='opendata.cbs.nl',
                       help='CBS API endpoint (default: opendata.cbs.nl, alternatief: dataderden.cbs.nl)')
    parser.add_argument('-t', '--timeout', type=int, default=30,
                       help='Request timeout in seconden (default: 30)')
    
    args = parser.parse_args()
    
    # Initialiseer fetcher
    fetcher = CBSDataFetcher(endpoint=args.endpoint, timeout=args.timeout)
    
    # Haal data op en sla op
    try:
        fetcher.fetch_and_save(
            dataset_id=args.dataset,
            output_dir=args.output,
            gemeente_filter=args.gemeente
        )
    except Exception as e:
        print(f"\n❌ Fout: {e}")
        exit(1)


if __name__ == "__main__":
    main()
