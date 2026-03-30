# CBS Scripts Compare & Integration

**Project voor analyse en integratie van CBS data retrieval scripts**

## 📋 Overzicht

Dit project bevat een analyse van bestaande CBS (Centraal Bureau voor de Statistiek) data ophaal scripts en een implementatieplan voor een geïntegreerde, gestructureerde oplossing met JSON output.

### Projectdoelen

1. **Analyseren** van bestaande CBS data retrieval implementaties
2. **Vergelijken** van verschillende benaderingen en tools
3. **Ontwerpen** van een unified, schaalbare oplossing
4. **Implementeren** van gestructureerde JSON output voor CBS data

## 📁 Project Structuur

```
CBS_Scripts_compare/
├── CBS_API_Gegevens/          # Bestaande data download scripts
│   ├── CBS_API_V4.py          # Hoofdscript voor CBS data ophalen
│   ├── 1_Downloading_CBS.ipynb
│   └── CBS_DATA/              # Downloaded datasets
├── CBS_API_Omschrijvingen/    # Metadata en beschrijvingen scripts  
│   ├── cbs_omschrijvingen_ophalen.py
│   ├── extract_api_data.py    # Kompas API integratie
│   └── compare_with_kompas.py
├── docs/                      # Documentatie
│   └── CBS Scripts vergelijking.md
├── output/                    # Output directory voor JSON files
├── cbs_data_fetcher.py       # 🆕 Geïntegreerd script (data + metadata)
├── batch_fetch.py            # 🆕 Batch processing script
├── fetch_all.sh              # 🆕 Master script voor alle datasets
├── datasets_cbs.txt          # 🆕 CBS dataset lijst (47 datasets)
├── datasets_rivm.txt         # 🆕 RIVM dataset lijst
├── datasets_politie.txt      # 🆕 Politie dataset lijst
├── README.md                  # Dit bestand
├── USAGE.md                   # Gebruikshandleiding
├── TODO.md                    # Development roadmap
├── BUGFIX.md                  # Known issues
├── BRAINDUMP.md              # Ideeën en notities
└── BUILD.md                   # Build en setup instructies
```

## 🎯 Huidige Status

**Fase**: Eerste Implementatie ✅

- ✅ Scripts geanalyseerd en vergeleken
- ✅ Overeenkomsten en verschillen gedocumenteerd  
- ✅ Implementatieplan ontwikkeld voor JSON integratie
- ✅ **Werkende implementatie met dual JSON output**
- ✅ **Batch processing voor 50+ datasets**

## 🚀 Quick Start

### Enkel Dataset Ophalen

```bash
# Activeer virtual environment
source .venv/bin/activate

# Haal één dataset op (met gemeente filter)
python cbs_data_fetcher.py -ds 83739NED -gm 1900

# Output: 2 JSON files in ./output/
# - Kerncijfers_wijken_en_buurten_2023_METADATA.json
# - Kerncijfers_wijken_en_buurten_2023_DATA.json
```

### Batch: Alle Datasets Ophalen

```bash
# Run master script (haalt 50+ datasets op)
bash fetch_all.sh

# Output wordt georganiseerd:
# ./output/cbs/      - 47 CBS datasets (94 JSON files)
# ./output/rivm/     - 1 RIVM dataset (2 JSON files)
# ./output/politie/  - 2 Politie datasets (4 JSON files)
```

Zie [USAGE.md](USAGE.md) voor complete handleiding.

│   ├── CBS_API_V4.py          # Hoofdscript voor CBS data ophalen
│   ├── 1_Downloading_CBS.ipynb
│   └── CBS_DATA/              # Downloaded datasets (299 bestanden)
├── CBS_API_Omschrijvingen/    # Metadata en beschrijvingen scripts  
│   ├── cbs_omschrijvingen_ophalen.py
│   ├── extract_api_data.py    # Kompas API integratie
│   └── compare_with_kompas.py
├── docs/                      # Documentatie
│   └── CBS Scripts vergelijking.md
├── README.md                  # Dit bestand
├── TODO.md                    # Development roadmap
├── BUGFIX.md                  # Known issues en fixes
├── BRAINDUMP.md              # Ideeën en notities
└── BUILD.md                   # Build en setup instructies
```

## 🎯 Huidige Status

**Fase**: Planning & Analyse ✅

- ✅ Scripts geanalyseerd en vergeleken
- ✅ Overeenkomsten en verschillen gedocumenteerd  
- ✅ Implementatieplan ontwikkeld voor JSON integratie
- ⏳ Development toolkit nog niet geïmplementeerd

## 🔑 Belangrijkste Bevindingen

### CBS_API_Gegevens
**Focus**: CBS datasets downloaden (actuele data)
- Direct OData V3 API calls via `requests`
- Command-line interface met `argparse`
- Gemeente filtering (bijv. voor Súdwest-Fryslân)
- CSV output formaat

### CBS_API_Omschrijvingen  
**Focus**: Metadata en beschrijvingen (wat betekenen de cijfers)
- Gebruik van `cbsodata` Python library
- Text normalisatie voor fuzzy matching
- Integratie met Kompas Gebiedsmonitor API
- Validatie workflows

### Kern Inzichten

**Overeenkomsten**:
- Beide gebruiken CBS OData API
- Ondersteuning voor meerdere endpoints (CBS, Politie, RIVM)
- Pandas voor data processing
- CSV als output formaat

**Complementaire Functionaliteit**:
- CBS_API_Gegevens = **DATA** (de cijfers)
- CBS_API_Omschrijvingen = **METADATA** (wat cijfers betekenen)

## 🚀 Toekomstige Ontwikkeling

Zie [TODO.md](TODO.md) voor de volledige development roadmap.

### Voorgestelde Unified Toolkit

**Componenten**:
- 🔌 **CBS API Client**: Uniforme interface voor alle CBS endpoints
- 🔄 **Data Processor**: Transformatie en verrijking van data
- 📊 **JSON Schema**: Gestructureerde output met metadata
- ⚙️ **Config Management**: Centraal beheer van endpoints en credentials
- 🎯 **CLI Orchestrator**: User-friendly command-line tool

**Voordelen**:
- Gestructureerde JSON output (machine-readable)
- Data automatisch verrijkt met metadata
- Self-describing datasets
- Traceable provenance (bron, tijdstip)
- Quality metrics inbegrepen

## 📚 Documentatie

- **[CBS Scripts vergelijking](docs/CBS%20Scripts%20vergelijking.md)** - Uitgebreide technische vergelijking
- **[Implementation Plan](implementation_plan.md)** - Gedetailleerd implementatieplan (in artifacts)
- **[TODO](TODO.md)** - Development roadmap
- **[BUGFIX](BUGFIX.md)** - Known issues
- **[BRAINDUMP](BRAINDUMP.md)** - Ideeën en notities

## 🛠️ Tech Stack

**Huidige Scripts**:
- Python 3.x
- `requests` - HTTP client
- `pandas` - Data processing
- `cbsodata` - CBS API wrapper library
- `tqdm` - Progress bars

**Voorgestelde Additions**:
- `pyyaml` - Configuration management
- `python-dotenv` - Environment variables
- `jsonschema` - JSON validation
- `pytest` - Testing framework

## 👥 Data Bronnen

| Bron | Endpoint | Gebruik |
|------|----------|---------|
| **CBS Open Data** | opendata.cbs.nl | Algemene CBS statistieken |
| **Politie Data** | dataderden.cbs.nl | Misdrijf en overlast cijfers |
| **RIVM Data** | dataderden.cbs.nl | Gezondheidsdata |
| **Kompas API** | sudwestfryslan.gebiedsmonitor.nl | Lokale gebiedsmonitor |

## 🔐 Security & Credentials

⚠️ **BELANGRIJK**: API credentials staan momenteel in code (security risk!)

**TO DO**:
- Verplaats credentials naar `.env` bestand
- Voeg `.env` toe aan `.gitignore`
- Gebruik `python-dotenv` voor credential management

## 📞 Contact & Support

Voor vragen over dit project:
- Zie documentatie in `docs/` folder
- Check TODO.md voor geplande features
- Raadpleeg BUGFIX.md voor bekende problemen

## 📄 Licentie

*[Licentie informatie toe te voegen]*

---

**Laatst bijgewerkt**: 19 januari 2026  
**Status**: Planning & Analyse fase
