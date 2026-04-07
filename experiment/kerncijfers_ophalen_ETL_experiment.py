import os
import subprocess
import sys
import json


# --- AUTODETECT PROJECT ROOT ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
while not (
    os.path.isdir(os.path.join(PROJECT_ROOT, "ETL"))
    and os.path.isdir(os.path.join(PROJECT_ROOT, "data"))
):
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

print("📁 PROJECT_ROOT:", PROJECT_ROOT)

# Pad naar fetcher
FETCHER = os.path.join(PROJECT_ROOT, "ETL", "CBS", "cbs_data_fetcher.py")
print(" FETCHER:", FETCHER)

# Waar opslaan
OUTPUT = os.path.join(PROJECT_ROOT, "data", "bewerkt")
os.makedirs(OUTPUT, exist_ok=True)
print("📂OUTPUT:", OUTPUT)

# Gemeenten
GEMEENTEN = [
    "0059","0060","0040","1940","0072","0074","0080","1970",
    "0085","0086","0099","0090","1900","0093","0737","1949","0098"
]

DATASET = "86165NED"

def main():

    print("\n==============================")
    print(" CBS Downloader — dataset", DATASET)
    print("==============================")

    temp_files = []  # hier bewaren we alle tijdelijke GM‑bestanden

    # DOWNLOAD PER GEMEENTE
    for gm in GEMEENTEN:
        print(f"\n➡️ Ophalen gemeente GM{gm} ...")

        cmd = [
            sys.executable,
            FETCHER,
            "-ds", DATASET,
            "-gm", gm,
            "-o", OUTPUT
        ]

        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        # BESTANDEN RENAMEN NA DOWNLOAD
        base = f"GM{gm}_{DATASET}"

        src_data = os.path.join(OUTPUT, "Kerncijfers_wijken_en_buurten_2025_DATA.json")
        src_meta = os.path.join(OUTPUT, "Kerncijfers_wijken_en_buurten_2025_METADATA.json")

        dst_data = os.path.join(OUTPUT, f"{base}_DATA.json")
        dst_meta = os.path.join(OUTPUT, f"{base}_METADATA.json")

        if os.path.exists(src_data):
            os.rename(src_data, dst_data)
            temp_files.append(dst_data)

        if os.path.exists(src_meta):
            os.rename(src_meta, dst_meta)
            temp_files.append(dst_meta)

    print("\n Alle downloads voltooid.")

    # 3️⃣ VERWERK ALLE BESTANDEN + METADATA
    print("\n🔎 Metadata koppelen...")

    data_files = sorted([f for f in temp_files if f.endswith("_DATA.json")])

    enriched_all = []

    for data_path in data_files:
        meta_path = data_path.replace("_DATA.json", "_METADATA.json")

        print(f"   ➕ Verwerken: {os.path.basename(data_path)}")

        with open(data_path, "r", encoding="utf-8") as f:
            data_json = json.load(f)

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_json = json.load(f)

        records = data_json["data"]["records"]
        properties = meta_json["metadata"]["properties"]

        meta_map = {
            p["key"]: {
                "title": p.get("title"),
                "description": p.get("description"),
                "unit": p.get("unit")
            }
            for p in properties
        }

        # verrijk
        for rec in records:
            enriched = {}
            for key, value in rec.items():
                if key in meta_map:
                    enriched[key] = {
                        "value": value,
                        "title": meta_map[key]["title"],
                        "description": meta_map[key]["description"],
                        "unit": meta_map[key]["unit"]
                    }
                else:
                    enriched[key] = value
            enriched_all.append(enriched)

    # OPSLAAN VAN 1 GROOT ENRICHED BESTAND
    enriched_file = os.path.join(OUTPUT, f"{DATASET}_enriched.json")

    with open(enriched_file, "w", encoding="utf-8") as f:
        json.dump(enriched_all, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Verrijking voltooid → {enriched_file}")

    # VERWIJDER ALLE TIJDELIJKE GEMEENTE-BESTANDEN
    print("\n🧹 Opruimen: verwijderen tijdelijke gemeente-bestanden...")

    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass

    print(" Alle tijdelijke GM-bestanden verwijderd.")

if __name__ == "__main__":
    main()