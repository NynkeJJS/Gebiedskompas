#!/bin/bash
# Optimized bulk ETK for Groningen and Drenthe
# 1. Fetch all data first (extract-only)
# 2. Import everything in one go

GEMEENTEN=("0014" "0037" "0047" "0085" "0086" "0098" "0106" "0109" "0114" "0118" "0119" "0160" "0180" "1680" "1681" "1690" "1699" "1701" "1708" "1730" "1731" "1950" "1952" "1969" "0765" "1895" "1966" "1979")

source .venv/bin/activate

echo "🚀 Starting optimized bulk extraction..."

for GM in "${GEMEENTEN[@]}"; do
    echo "📥 Fetching for Gemeente $GM..."
    
    # RIVM (Extract only)
    python3 ETL/run_etl.py -ds 50150NED -gm "$GM" --derden --extract-only > /dev/null 2>&1
    
    # CBS Kerncijfers (Extract only)
    # We loop through several years that we know are in the mapping
    # 83739NED (2023), 84799NED (2020), 85039NED (2021), 85318NED (2022), 85618NED (2023), 85984NED (2024), 86165NED (2025)
    # Actually run_etl only takes one DS. 
    # Just fetch the most important ones for now (2023-2025)
    python3 ETL/run_etl.py -ds 85984NED -gm "$GM" --extract-only > /dev/null 2>&1
    python3 ETL/run_etl.py -ds 86165NED -gm "$GM" --extract-only > /dev/null 2>&1
done

echo "⚙️  Starting bulk import for allFetched data..."
# Run import-only once (it will process ALL municipalities by default)
python3 ETL/run_etl.py --import-only

echo "✅ Optimized Bulk ETL finished."
