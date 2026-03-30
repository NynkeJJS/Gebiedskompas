#!/bin/bash
# Targeted fetch and import for missing Groningen municipalities
# Using .venv

GEMEENTEN=("0047" "1952" "1969" "1966" "0765" "1950" "1895" "1979")

source .venv/bin/activate

for GM in "${GEMEENTEN[@]}"; do
    echo "============================================================"
    echo "📊 Finalizing Groningen: Gemeente $GM..."
    
    # RIVM
    python3 ETL/run_etl.py -ds 50150NED -gm "$GM" --derden
    
    # CBS
    python3 ETL/run_etl.py -ds 83739NED -gm "$GM"
done

echo "✅ Final sweep for Groningen finished."
