# D-OmniTwin ETL Framework - Gebruikshandleiding

Welkom bij het geünificeerde ETL (Extract, Transform, Load) framework van D-OmniTwin. Dit framework is ontworpen om robuust, flexibel en eenvoudig uitbreidbaar te zijn voor OData bronnen zoals het **CBS**, het **RIVM** en de **Politie**.

## 🏗️ Architectuur Overzicht

Het framework bestaat in de kern uit twee hoofd-scripts die je vanuit de root `ETL/` map kunt aanroepen:

1. **`search_api.py`** - De ontdekkingstool. Helpt je datasets zoeken en kolomnamen (DataProperties) inspecteren bij zowel de publieke CBS portal (`opendata.cbs.nl`) als de dataderden portal (`dataderden.cbs.nl` - voor RIVM/Politie).
2. **`run_etl.py`** - De uitvoerings-engine. Voert de extractie (downloaden als JSON) en de import (opslaan in PostgreSQL & koppelen aan UUID's) in één vloeiende beweging uit.

De daadwerkelijke data-extractors en importers leven in de modulaire `/CBS` (en `/RIVM`) mappen.

---

## 🔎 Stap 1: Nieuwe Data Ontdekken (`search_api.py`)

Voordat je data importeert, moet je weten _welke_ dataset je nodig hebt en _hoe_ de kolommen heten.

**Zoek een dataset op trefwoord:**
```bash
python search_api.py -q "Gezondheid"
```
Dit doorzoekt live alle landelijke tafels en geeft je de benodigde **Dataset ID** (bijv. `83739NED` of `50150NED`).

**Inspecteer de kolomnamen (DataProperties):**
Heb je een CBS dataset ID gevonden? Gebruik flag `-i` om te zien welke kolommen je in je mapping file moet zetten.
```bash
python search_api.py -i 83739NED
```

💡 **RIVM & Politie (Dataderden):**
RIVM en Politie datasets staan op een afgescheiden server. Heb je een RIVM ID zoals `50150NED` of een politiedataset? Voeg altijd de `-d` of `--derden` flag toe:
```bash
python search_api.py -i 50150NED -d
```

---

## 🗺️ Stap 2: Mapping Configuratie

Voordat de import (Fase 2) begrijpt wat hij moet doen met jouw gekozen dataset, moet je deze toevoegen aan de mapping file: `ETL/CBS/cbs_mapping_v3.json` (wordt later overgeheveld naar een centrale configuratiemap).

### Wat doet de mapping?
De mapping koppelt de ruwe kolom ("Personenauto's per huishouden") aan de D-OmniTwin indicatornaam ("Auto bezit").
Indien een indicator nog niet bestaat in de `indicatoren` tabel, maakt het ETL script deze automatisch voor je aan onder een standaard Dimensie. Via het **Admin Panel** kun je deze vervolgens netjes verslepen (Hiërarchie editor) en visueel stijlen (Kleurschema's).

---

## 🚀 Stap 3: Data Uitvoeren (`run_etl.py`)

Als je mapping klaar is, run je simpelweg de ETL runner.

**Basis Import (CBS Data):**
Haal dataset `83739NED` op voor de Friese gemeenten `1900` (Súdwest-Fryslân) en `0090` (Smallingerland).
```bash
python run_etl.py -ds 83739NED -gm "1900,0090"
```

**RIVM/Politie (Derden) Import:**
Ook hier voeg je simpelweg `--derden` toe. Pas op: sommige RIVM datasets vereisen extra API validaties.
```bash
python run_etl.py -ds 50150NED -gm 1900 --derden
```

### Veelgebruikte opties
- `-gm <code(s)>` : Beperk de download tot specifieke CBS-gemeentecodes. (Als je dit weglaat, haalt hij in theorie álles op).
- `--extract-only` : Haalt alleen de JSON bestanden op (handig als je eerst of the data lokaal wilt inspecteren).
- `--import-only`  : Slaat de download over en zoekt in je output-map naar eerder opgevraagde JSON bestanden. Handig voor troubleshooting.

---

## 🎨 Fase 4: Integratie in het Beheerscherm (Visie/Roadmap)

We werken eraan om dit `run_etl.py` script native in het React Admin-paneel aan te roepen, inclusief:
- Visuele statusbalken (Welke dataset is momenteel aan het laden?).
- Het configureren van nieuwe mappings (geen JSON bestanden meer editen, maar direct de kolommen uit `search_api.py` selecteren en opslaan).
- Status en gezondheid van de CBS API endpoints monitoren.

*Dit document is Gegenereerd op: 24 Februari 2026 - D-OmniTwin Versie: 1.6.3*
