import pandas as pd
from pathlib import Path
import sys

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

excel_path = project_root / 'data' / 'gemeenten' / 'gemeenten-alfabetisch-2025.xlsx'

# Read first 100 rows
df = pd.read_excel(excel_path, header=None, nrows=100)

# Search for header row
header_row_idx = None
for idx, row in df.iterrows():
    row_values = [str(x) for x in row.values]
    if "Gemeentenaam" in row_values or "Gemeentecode" in row_values:
        header_row_idx = idx
        print(f"Found header at row {idx}")
        print(row_values)
        break

if header_row_idx is not None:
    # Read again with correct header
    df = pd.read_excel(excel_path, header=header_row_idx)
    print("\nColumns found:", df.columns.tolist())
    
    # Filter Fryslân
    if 'Provincienaam' in df.columns:
        fryslan = df[df['Provincienaam'] == 'Fryslân']
        print(f"\nFound {len(fryslan)} municipalities in Fryslân")
        print(fryslan[['Gemeentenaam', 'Gemeentecode', 'GemeentecodeGM']].head())
    else:
        print("Column 'Provincienaam' not found")
else:
    print("Header not found in first 100 rows")
