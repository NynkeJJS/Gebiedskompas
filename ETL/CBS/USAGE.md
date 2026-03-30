# CBS Data Fetcher - Gebruikshandleiding

## Overzicht

`cbs_data_fetcher.py` is een geïntegreerd script dat CBS data en metadata ophaalt en opslaat als gestructureerde JSON bestanden.

**Belangrijkste features**:
- ✅ Combineert beste practices van beide bestaande scripts
- ✅ Haalt zowel data als metadata op in één run
- ✅ Output naar 2 aparte JSON files (data + metadata)
- ✅ Ondersteuning voor gemeente filtering
- ✅ Progress bars tijdens download
- ✅ Automatische paginering
- ✅ Meerdere endpoints (CBS, Politie, RIVM)

## Installatie

Zorg dat de virtual environment geactiveerd is:
```bash
source .venv/bin/activate  # Linux/Mac
# of
.venv\Scripts\activate     # Windows
```

Dependencies zijn al geïnstalleerd via `requirements.txt`.

## Basis Gebruik

### Simpelste vorm
```bash
python cbs_data_fetcher.py -ds 83739NED
```

Dit haalt dataset `83739NED` op en schrijft naar `./output/`:
- `Kerncijfers_wijken_en_buurten_2023_METADATA.json`
- `Kerncijfers_wijken_en_buurten_2023_DATA.json`

### Met gemeente filter
```bash
# Data alleen voor Súdwest-Fryslân (code 1900)
python cbs_data_fetcher.py -ds 83739NED -gm 1900
```

### Custom output directory
```bash
python cbs_data_fetcher.py -ds 84417NED -o ./mijn_data
```

### Politie data (ander endpoint)
```bash
python cbs_data_fetcher.py -ds 47026NED -e dataderden.cbs.nl
```

## Command-line Opties

| Optie | Verkorting | Beschrijving | Vereist |
|-------|------------|--------------|---------|
| `--dataset` | `-ds` | CBS dataset code (bijv. "83739NED") | ✅ Ja |
| `--output` | `-o` | Output directory (default: ./output) | ❌ Nee |
| `--gemeente` | `-gm` | Gemeente code voor filtering (bijv. "1900") | ❌ Nee |
| `--endpoint` | `-e` | CBS API endpoint (default: opendata.cbs.nl) | ❌ Nee |
| `--timeout` | `-t` | Request timeout in seconden (default: 30) | ❌ Nee |

---

## Batch Processing - Meerdere Datasets

### Quick Start: Alles Ophalen

**Makkelijkste methode - run één commando voor alle data**:

```bash
# Activeer virtual environment
source .venv/bin/activate

# Haal ALLE datasets op (CBS + RIVM + Politie)
bash fetch_all.sh
```

Dit haalt 50+ datasets op en organiseert ze netjes:
```
output/
├── cbs/        # 47 CBS datasets
├── rivm/       # 1 RIVM dataset  
└── politie/    # 2 Politie datasets
```

### Stap-voor-Stap Batch Processing

#### 1. Dataset Lijsten

Je hebt 3 dataset list bestanden:

**`datasets_cbs.txt`** - CBS datasets (47 datasets):
```
82964NED  # Jeugdzorg
83563NED
...
85618NED
```

**`datasets_rivm.txt`** - RIVM datasets (1 dataset):
```
50120NED
```

**`datasets_politie.txt`** - Politie datasets (2 datasets):
```
47018NED
47024NED
```

#### 2. Batch Script Gebruik

**Optie A: Per categorie** (aanbevolen voor grote batches)

```bash
# CBS datasets (47x)
python batch_fetch.py datasets_cbs.txt -gm 1900 -o output/cbs

# RIVM datasets (1x) - LET OP: ander endpoint!
python batch_fetch.py datasets_rivm.txt -gm 1900 -e dataderden.cbs.nl -o output/rivm

# Politie datasets (2x) - LET OP: ander endpoint!
python batch_fetch.py datasets_politie.txt -gm 1900 -e dataderden.cbs.nl -o output/politie
```

**Optie B: Alles in één keer**

```bash
# Simpelweg dit runnen:
bash fetch_all.sh
```

#### 3. Custom Dataset Lijst

Maak je eigen lijst:

```bash
# Maak nieuw bestand
cat > mijn_datasets.txt << EOF
83739NED  # Kerncijfers wijken
84417NED  # Kerncijfers 2022
85217NED  # Woningvoorraad
EOF

# Run batch
python batch_fetch.py mijn_datasets.txt -gm 1900
```

### Batch Output Structuur

Na `fetch_all.sh` heb je deze structuur:

```
output/
├── cbs/
│   ├── Jeugdzorg_met_jeugdbescherming_METADATA.json
│   ├── Jeugdzorg_met_jeugdbescherming_DATA.json
│   ├── Kerncijfers_wijken_en_buurten_2023_METADATA.json
│   ├── Kerncijfers_wijken_en_buurten_2023_DATA.json
│   └── ... (94 JSON files - 47 datasets × 2)
├── rivm/
│   ├── RIVM_Dataset_METADATA.json
│   └── RIVM_Dataset_DATA.json
└── politie/
    ├── Geregistreerde_misdrijven_METADATA.json
    ├── Geregistreerde_misdrijven_DATA.json
    └── ... (4 JSON files - 2 datasets × 2)
```

### Monitoring Batch Progress

Het batch script toont:
- ✅ Hoeveel datasets succesvol
- ❌ Welke datasets gefaald
- 📊 Progress per dataset

```
🎯 Batch Fetch: 47 datasets
📂 Output: output/cbs
🏘️  Gemeente filter: 1900
🌐 Endpoint: opendata.cbs.nl

[1/47] Ophalen: 82964NED
============================================================
📊 CBS Dataset: 82964NED
============================================================
1️⃣  Metadata ophalen...
  ✅ TableInfos opgehaald
  ✅ 35 DataProperties opgehaald
...
✅ Voltooid in 4.23 seconden
============================================================

[2/47] Ophalen: 83563NED
...
```

### Troubleshooting Batch

**Stop op fout?**
Batch stopt NIET bij fouten - gaat door met volgende dataset.
Aan het einde zie je overzicht van gefaalde datasets.

**Te langzaam?**
- Gebruik gemeente filter (-gm 1900) om data te beperken
- Run verschillende categorieën parallel in aparte terminals:
  ```bash
  # Terminal 1
  python batch_fetch.py datasets_cbs.txt -gm 1900 -o output/cbs
  
  # Terminal 2 (gelijktijdig)
  python batch_fetch.py datasets_rivm.txt -gm 1900 -e dataderden.cbs.nl -o output/rivm
  ```

**Disk space?**
Check ruimte vooraf:
```bash
df -h ./output  # Check beschikbare ruimte
```

Voor 50 datasets met gemeente filter: ~500MB-1GB nodig.

### Equivalent van Notebook Workflow

De originele notebook workflow:
```python
datasets_CBS = '82964NED 83563NED ...'
!python CBS_API_V4.py -ds "$datasets_CBS" -path "CBS_DATA" -gm "1900"
```

Is nu:
```bash
python batch_fetch.py datasets_cbs.txt -gm 1900 -o output/cbs
```

**Voordelen van nieuwe aanpak**:
- ✅ Overzichtelijke dataset lijsten (met comments)
- ✅ Per-dataset JSON output (metadata + data gescheiden)
- ✅ Progress tracking per dataset
- ✅ Georganiseerde output structuur
- ✅ Failure handling (gaat door bij errors)

---

## Output Structuur


### Metadata JSON (`*_METADATA.json`)

```json
{
  "dataset": {
    "id": "83739NED",
    "title": "Kerncijfers wijken en buurten 2023",
    "short_title": "Kerncijfers wijken en buurten 2023",
    "description": "...",
    "source": "CBS",
    "endpoint": "opendata.cbs.nl",
    "retrieved_at": "2026-01-19T16:00:00Z"
  },
  "metadata": {
    "properties": [
      {
        "key": "Aantal_Inwoners",
        "title": "Aantal inwoners",
        "description": "Totaal aantal inwoners op 1 januari",
        "datatype": "Integer",
        "unit": "personen",
        "decimals": 0
      }
    ]
  },
  "additional_info": {
    "modified": "2024-12-15",
    "catalog_frequency": "Jaarlijks",
    "default_presentation": "Table"
  }
}
```

### Data JSON (`*_DATA.json`)

```json
{
  "dataset": {
    "id": "83739NED",
    "table": "TypedDataSet",
    "source": "CBS",
    "endpoint": "opendata.cbs.nl",
    "retrieved_at": "2026-01-19T16:00:00Z",
    "filters_applied": {
      "gemeente_code": "1900"
    }
  },
  "data": {
    "records": [
      {
        "WijkenEnBuurten": "WK190000",
        "Perioden": "2023",
        "Aantal_Inwoners": 12450
      }
    ],
    "record_count": 640
  },
  "quality": {
    "completeness": 98.5
  }
}
```

## Voorbeeldscenario's

### Scenario 1: Kerncijfers voor gemeente
```bash
# Haal kerncijfers wijken en buurten op voor Súdwest-Fryslân
python cbs_data_fetcher.py -ds 83739NED -gm 1900 -o ./swf_data
```

**Output**:
- `./swf_data/Kerncijfers_wijken_en_buurten_2023_METADATA.json` - Beschrijvingen van alle indicatoren
- `./swf_data/Kerncijfers_wijken_en_buurten_2023_DATA.json` - Cijfers alleen voor SWF

### Scenario 2: Meerdere jaren
```bash
# Verschillende jaren apart ophalen
python cbs_data_fetcher.py -ds 83739NED -gm 1900 -o ./data_2023
python cbs_data_fetcher.py -ds 84417NED -gm 1900 -o ./data_2022
python cbs_data_fetcher.py -ds 84692NED -gm 1900 -o ./data_2021
```

### Scenario 3: Politie misdrijfcijfers
```bash
# Politie data heeft ander endpoint
python cbs_data_fetcher.py -ds 47026NED -e dataderden.cbs.nl -o ./politie_data
```

## Beste Practices

### 1. Start Klein
Test eerst met een klein dataset voordat je grote datasets ophaalt:
```bash
# Klein test dataset eerst
python cbs_data_fetcher.py -ds 83739NED -gm 1900
```

### 2. Gebruik Gemeente Filtering
Voor lokale analyses, gebruik altijd gemeente filter om data te beperken:
```bash
python cbs_data_fetcher.py -ds 83739NED -gm 1900
```

### 3. Organiseer Output
Maak aparte directories per thema of jaar:
```bash
mkdir -p output/{kerncijfers,bevolking,woningen}
python cbs_data_fetcher.py -ds 83739NED -o ./output/kerncijfers
python cbs_data_fetcher.py -ds 85217NED -o ./output/woningen
```

### 4. Check de Output
Valideer altijd de JSON output:
```bash
# Check file grootte
ls -lh output/

# Bekijk metadata
cat output/*_METADATA.json | jq '.metadata.properties[0]'

# Tel records
cat output/*_DATA.json | jq '.data.record_count'
```

## Verschillen met Oude Scripts

| Aspect | CBS_API_V4.py | Nieuwe Script |
|--------|---------------|---------------|
| **Output formaat** | CSV | JSON (2 files: data + metadata) |
| **Metadata** | Niet opgehaald | Automatisch mee opgehaald |
| **Progress** | Basic print | tqdm progress bars |
| **Structuur** | Plat CSV | Gestructureerd JSON |
| **Self-describing** | Nee | Ja (metadata inbegrepen) |
| **Timestamp** | Nee | Ja (retrieved_at) |
| **Quality metrics** | Nee | Ja (completeness) |

## Troubleshooting

### Probleem: "ModuleNotFoundError"
```bash
# Zorg dat venv geactiveerd is
source .venv/bin/activate

# Herinsta lleer dependencies
pip install -r requirements.txt
```

### Probleem: Connection timeout
```bash
# Verhoog timeout
python cbs_data_fetcher.py -ds 83739NED -t 60
```

### Probleem: Geen data in output
- Check of dataset code correct is (moet eindigen op NED)
- Bij gemeente filter: check of gemeente code bestaat in de data
- Bekijk console output voor waarschuwingen

### Probleem: JSON te groot
- Gebruik gemeente filtering om data te verkleinen
- Of: splits in meerdere kleinere datasets

## Volgende Stappen

1. **Test het script** met je favoriete dataset
2. **Bekijk de JSON output** - is de structuur geschikt?
3. **Feedback** - wat werkt goed, wat kan beter?
4. **Uitbreidingen** - zie TODO.md voor volgende features

## Vragen?

- Check `BUGFIX.md` voor bekend issues
- Zie `TODO.md` voor geplande features
- Bekijk `docs/7-projectmanagement/logs/CBS Scripts vergelijking.md` voor technische details
