#!/usr/bin/env python3
"""
CBS Batch Fetcher
Haal meerdere CBS datasets op in één run

Usage:
    python batch_fetch.py datasets.txt
    python batch_fetch.py datasets.txt -gm 1900
"""

import subprocess
import sys
import argparse
from pathlib import Path


def read_dataset_list(filepath):
    """Lees dataset IDs uit bestand"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Parse dataset IDs (whitespace separated)
    datasets = content.split()
    # Filter out lege strings en comments
    datasets = [d for d in datasets if d and not d.startswith('#')]
    return datasets


def fetch_dataset(dataset_id, output_dir, gemeente=None, endpoint='opendata.cbs.nl'):
    """Haal één dataset op"""
    cmd = [
        sys.executable,  # Gebruik dezelfde Python interpreter
        'cbs_data_fetcher.py',
        '-ds', dataset_id,
        '-o', output_dir,
        '-e', endpoint
    ]
    
    if gemeente:
        cmd.extend(['-gm', gemeente])
    
    print(f"\n{'='*60}")
    print(f"Dataset: {dataset_id} (endpoint: {endpoint})")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Fout bij dataset {dataset_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Batch fetch meerdere CBS datasets',
        epilog="""
Voorbeelden:
  python batch_fetch.py datasets_cbs.txt
  python batch_fetch.py datasets_cbs.txt -gm 1900
  python batch_fetch.py datasets_rivm.txt -e dataderden.cbs.nl
        """
    )
    
    parser.add_argument('dataset_file', help='Bestand met dataset IDs (één per regel of space-separated)')
    parser.add_argument('-o', '--output', default='./output', help='Output directory')
    parser.add_argument('-gm', '--gemeente', help='Gemeente code voor filtering')
    parser.add_argument('-e', '--endpoint', default='opendata.cbs.nl', 
                       help='CBS API endpoint')
    
    args = parser.parse_args()
    
    # Lees dataset lijst
    try:
        datasets = read_dataset_list(args.dataset_file)
    except FileNotFoundError:
        print(f"❌ Bestand niet gevonden: {args.dataset_file}")
        sys.exit(1)
    
    if not datasets:
        print("❌ Geen datasets gevonden in bestand")
        sys.exit(1)
    
    print(f"\n🎯 Batch Fetch: {len(datasets)} datasets")
    print(f"📂 Output: {args.output}")
    if args.gemeente:
        print(f"🏘️  Gemeente filter: {args.gemeente}")
    print(f"🌐 Endpoint: {args.endpoint}\n")
    
    # Maak output directory
    Path(args.output).mkdir(parents=True, exist_ok=True)
    
    # Fetch alle datasets
    success_count = 0
    failed = []
    
    for i, dataset_id in enumerate(datasets, 1):
        print(f"\n[{i}/{len(datasets)}] Ophalen: {dataset_id}")
        
        if fetch_dataset(dataset_id, args.output, args.gemeente, args.endpoint):
            success_count += 1
        else:
            failed.append(dataset_id)
    
    # Samenvatting
    print(f"\n{'='*60}")
    print(f"🏁 BATCH VOLTOOID")
    print(f"{'='*60}")
    print(f"✅ Succesvol: {success_count}/{len(datasets)}")
    
    if failed:
        print(f"❌ Gefaald: {len(failed)}")
        print(f"   Datasets: {', '.join(failed)}")
    
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
