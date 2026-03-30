#!/bin/bash
# Bulk fetch RIVM data for Groningen and Drenthe
# Using the .venv as requested

GEMEENTEN=("0014" "0037" "0047" "0085" "0086" "0098" "0106" "0109" "0114" "0118" "0119" "0160" "0180" "1680" "1681" "1690" "1699" "1701" "1708" "1730" "1731" "1950" "1952" "1969" "0765" "1895" "1966" "1979")

# Activate venv
source .venv/bin/activate

for GM in "${GEMEENTEN[@]}"; do
    echo "------------------------------------------------------------"
    echo "📥 Fetching RIVM data for Gemeente $GM..."
    python3 ETL/run_etl.py -ds 50150NED -gm "$GM" --derden --extract-only
done

echo "✅ Bulk extraction finished."
