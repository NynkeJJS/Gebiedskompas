#!/bin/bash
# Bulk fetch and import RIVM and CBS data for Groningen and Drenthe

GEMEENTEN=("0014" "0037" "0047" "0085" "0086" "0098" "0106" "0109" "0114" "0118" "0119" "0160" "0180" "1680" "1681" "1690" "1699" "1701" "1708" "1730" "1731" "1950" "1952" "1969" "0765" "1895" "1966" "1979")

# Activate venv
source .venv/bin/activate

for GM in "${GEMEENTEN[@]}"; do
    echo "============================================================"
    echo "📊 Processing Gemeente $GM..."
    
    # RIVM
    echo "📥 RIVM (50150NED):"
    python3 ETL/run_etl.py -ds 50150NED -gm "$GM" --derden
    
    # CBS Kerncijfers (usually 83739NED for 2023, or 85 something for 2024/2025)
    # The mapping currently points to 83739NED in cbs_dataset_config.json
    echo "📥 CBS Kerncijfers (83739NED):"
    python3 ETL/run_etl.py -ds 83739NED -gm "$GM"
done

echo "✅ Bulk import for Groningen and Drenthe finished."
