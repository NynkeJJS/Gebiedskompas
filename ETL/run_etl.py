#!/usr/bin/env python3
"""
D-OmniTwin ETL Runner
Een unificerend stuurscript voor het ophalen en importeren van CBS, RIVM en Politie datasets via OData.
"""

import sys
import os
import argparse
import subprocess
import textwrap

# Definieer de paden naar de onderliggende modules
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CBS_DIR = os.path.join(BASE_DIR, 'CBS')
RIVM_DIR = os.path.join(BASE_DIR, 'RIVM')

# We gebruiken tijdelijk de bestaande scripts als "modules" totdat we ze volledig ombouwen.
CBS_FETCHER = os.path.join(CBS_DIR, 'cbs_data_fetcher.py')
CBS_IMPORTER = os.path.join(CBS_DIR, 'import_cbs_data.py')

def print_header(title):
    print(f"\n{'='*70}")
    print(f"🚀 D-OmniTwin ETL: {title}")
    print(f"{'='*70}\n")

def run_extraction(dataset_id, endpoint, gemeente, output_dir):
    """Fase 1: Extractie (Ophalen via OData en opslaan als JSON)"""
    print_header(f"Fase 1: Extractie van {dataset_id}")
    
    cmd = [sys.executable, CBS_FETCHER, '-ds', dataset_id, '-o', output_dir]
    if endpoint:
        cmd.extend(['-e', endpoint])
    if gemeente:
        cmd.extend(['-gm', gemeente])
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Extractie gefaald (Code: {e.returncode}). Zie logs hierboven.")
        sys.exit(1)

def run_import(metadata_only=False, gemeente=None):
    """Fase 2: Importeren in PostgreSQL (Load & Transform)"""
    print_header("Fase 2: Database Import & Transformatie")
    
    if metadata_only:
        print("⚠️ Let op: Enkel metadata (zoals RIVM) enrichment wordt uitgevoerd.")
        cmd = [sys.executable, os.path.join(RIVM_DIR, 'enrich_rivm_metadata.py')]
    else:
        # Dit script zoekt automatisch in de data/temp_cbs_import of output mappen 
        # op basis van de configuration in CBS/cbs_mapping_v3.json
        cmd = [sys.executable, CBS_IMPORTER]
        if gemeente:
            cmd.extend(['--gemeente', gemeente])
        
    print(f"Running command: {' '.join(cmd)}")
    try:
        # De environment moet wel ingesteld zijn (config.ini of .env)
        subprocess.run(cmd, check=True)
        print("\n✅ Import succesvol afgerond.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Import gefaald (Code: {e.returncode}). Zie logs hierboven.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Unified ETL Runner voor D-OmniTwin (CBS, RIVM, Politie)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent('''\
        Voorbeelden:
          1. Run de volledige pijplijn voor CBS dataset Kerncijfers (83739NED) in gemeente Súdwest-Fryslân (1900):
             python run_etl.py -ds 83739NED -gm 1900
             
          2. Haal een RIVM dataset op (DataDerden endpoint):
             python run_etl.py -ds 50150NED -gm 1900 --derden
             
          3. Alleen de import stap draaien (handig na bulk fetching):
             python run_etl.py --import-only
        ''')
    )
    
    parser.add_argument('-ds', '--dataset', type=str, help='Dataset ID (bijv. "83739NED").')
    parser.add_argument('-gm', '--gemeente', type=str, help='Gemeente code (bijv. "1900" voor SWF).')
    parser.add_argument('--derden', action='store_true', help='Gebruik het dataderden.cbs.nl endpoint (nodig voor RIVM/Politie).')
    parser.add_argument('--extract-only', action='store_true', help='Alleen data ophalen, niet direct importeren in DB.')
    parser.add_argument('--import-only', action='store_true', help='Sla ophalen over, start direct de import/database stap.')
    parser.add_argument('-o', '--output', type=str, default=os.path.join(BASE_DIR, '..', 'data', 'temp_cbs_import'), help='Output map voor ruwe JSON.')

    args = parser.parse_args()

    endpoint = "dataderden.cbs.nl" if args.derden else "opendata.cbs.nl"

    # Validaties
    if not args.import_only and not args.dataset:
        print("❌ Fout: De flag '--dataset' is vereist voor extractie.")
        parser.print_help()
        sys.exit(1)

    # Zorg dat temp map bestaat
    os.makedirs(args.output, exist_ok=True)

    if not args.import_only:
        run_extraction(args.dataset, endpoint, args.gemeente, args.output)
        
    if not args.extract_only:
        run_import(metadata_only=False, gemeente=args.gemeente)

if __name__ == "__main__":
    main()
