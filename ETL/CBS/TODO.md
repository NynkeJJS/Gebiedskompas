# TODO - Development Roadmap

**Project**: CBS Scripts Integration & JSON Output  
**Laatst bijgewerkt**: 19 januari 2026

## 🎯 Overzicht

Dit document bevat de development roadmap voor de CBS data retrieval toolkit met gestructureerde JSON output.

---

## ✅ Voltooid (Fase 0: Planning)

- [x] Analyse van CBS_API_Gegevens scripts
- [x] Analyse van CBS_API_Omschrijvingen scripts  
- [x] Vergelijkingsdocument gemaakt
- [x] Overeenkomsten en verschillen gedocumenteerd
- [x] JSON schema ontworpen
- [x] Implementatieplan geschreven
- [x] Architectuur diagram gemaakt
- [x] Project documentatie opgezet

---

## 🚧 In Progress

*Geen items momenteel in progress*

---

## 📅 Fase 1: Foundation (Week 1)

**Doel**: Basis infrastructuur opzetten

### Core Setup
- [ ] Project structuur aanmaken
  - [ ] `cbs_toolkit/` package folder
  - [ ] `cbs_toolkit/core/` voor core modules
  - [ ] `cbs_toolkit/utils/` voor utilities
  - [ ] `cbs_toolkit/schemas/` voor JSON schemas
  - [ ] `cbs_toolkit/integrations/` voor externe APIs
  - [ ] `tests/` voor unit tests
  - [ ] `tests/integration/` voor integration tests

### Configuration Management
- [ ] `config/config.yaml` aanmaken
  - [ ] Endpoints configuratie (CBS, Politie, RIVM)
  - [ ] Default filter settings
  - [ ] Output instellingen
  - [ ] API rate limiting parameters
- [ ] `.env.example` template maken
- [ ] `.gitignore` updaten (credentials, __pycache__, etc.)
- [ ] Environment loader implementeren (`python-dotenv`)

### CBS API Client (Base)
- [ ] `cbs_toolkit/core/cbs_api_client.py` aanmaken
  - [ ] Base class met abstract methods
  - [ ] Connection handling en validatie
  - [ ] Error handling framework
  - [ ] Logging setup
- [ ] Endpoint configuratie inladen
- [ ] Basic connectivity tests

### Dependencies & Environment
- [ ] `requirements.txt` aanmaken
  - [ ] Core dependencies (requests, pandas, cbsodata)
  - [ ] Development dependencies (pytest, black, flake8)
  - [ ] Optional dependencies (pyyaml, python-dotenv, jsonschema)
- [ ] Virtual environment instructies in BUILD.md
- [ ] Python versie vereisten specificeren (3.8+)

### Documentation
- [ ] Code documentation standaarden definiëren
- [ ] Docstring template voor functies
- [ ] Type hints toevoegen aan functies

**Milestone 1**: ✅ Project structuur compleet, dependencies geïnstalleerd, basic API client werkend

---

## 📅 Fase 2: Data Processing (Week 2)

**Doel**: Data ophalen en verwerken

### Data Fetcher
- [ ] `cbs_toolkit/core/data_fetcher.py` implementeren
  - [ ] `fetch_dataset_tables()` - lijst van tabellen ophalen
  - [ ] `fetch_dataset_data()` - data ophalen met filters
  - [ ] Paginering afhandelen (odata.nextLink)
  - [ ] Filter logica voor gemeente codes
  - [ ] Progress tracking (tqdm integratie)
- [ ] Tests voor data fetcher

### Metadata Fetcher  
- [ ] `cbs_toolkit/core/metadata_fetcher.py` implementeren
  - [ ] `fetch_metadata()` - DataProperties ophalen
  - [ ] `fetch_table_info()` - TableInfos ophalen
  - [ ] Multi-source support (CBS, Politie, RIVM config)
  - [ ] Metadata caching overwegen
- [ ] Tests voor metadata fetcher

### Data Processor
- [ ] `cbs_toolkit/core/data_processor.py` implementeren
  - [ ] Text normalisatie (van cbs_omschrijvingen_ophalen.py)
  - [ ] Data + metadata merge logica
  - [ ] Missing value handling
  - [ ] Data type conversie en validatie
  - [ ] Quality metrics berekenen
- [ ] Tests voor data processor

### Utilities
- [ ] `cbs_toolkit/utils/text_utils.py`
  - [ ] `normalize_text()` functie migreren
  - [ ] Bestandsnaam sanitization (van CBS_API_V4.py)
- [ ] `cbs_toolkit/utils/file_utils.py`
  - [ ] Directory management
  - [ ] CSV reader/writer helpers
  - [ ] JSON pretty printer

**Milestone 2**: ✅ Data en metadata kunnen opgehaald en verwerkt worden

---

## 📅 Fase 3: JSON Schema & Output (Week 2-3)

**Doel**: Gestructureerde JSON output genereren

### JSON Schema Definition
- [ ] `cbs_toolkit/schemas/json_schema.py` aanmaken
  - [ ] Dataset metadata schema
  - [ ] Data properties schema  
  - [ ] Dimensions schema
  - [ ] Quality metrics schema
  - [ ] Complete dataset schema (alles samen)
- [ ] JSON Schema validator implementeren
- [ ] Example JSON output documenten maken

### JSON Generator
- [ ] `cbs_toolkit/core/json_generator.py` implementeren
  - [ ] `structure_for_json()` - DataFrame naar JSON dict
  - [ ] Metadata enrichment toevoegen
  - [ ] Labels naast codes toevoegen
  - [ ] Provenance info (bron, tijdstip)
  - [ ] Quality metrics includeren
- [ ] Pretty printing met indentation
- [ ] Compacte optie voor grote datasets

### Output Writer
- [ ] `cbs_toolkit/core/output_writer.py` implementeren
  - [ ] JSON writer met encoding handling
  - [ ] CSV writer (backwards compatibility)
  - [ ] Multiple output formats support
  - [ ] Atomic file writes (temp + rename)
- [ ] Tests voor verschillende output scenarios

**Milestone 3**: ✅ Gestructureerde JSON output kan gegenereerd worden

---

## 📅 Fase 4: CLI & Orchestration (Week 3)

**Doel**: User-friendly command-line interface

### CLI Tool
- [ ] `cbs_toolkit/cbs_to_json.py` hoofdscript
  - [ ] Argparse setup voor parameters
  - [ ] Dataset ID(s) input
  - [ ] Gemeente filter ondersteuning
  - [ ] Output path/directory specificatie
  - [ ] Source selectie (cbs/politie/rivm)
  - [ ] Opties: metadata, descriptions, quality metrics
- [ ] Batch processing voor multiple datasets
- [ ] Dataset list file support (txt/yaml)

### Workflow Orchestration
- [ ] Complete workflow implementeren:
  1. Config laden
  2. API client initialiseren
  3. Data ophalen
  4. Metadata ophalen
  5. Verwerken en mergen
  6. JSON genereren
  7. Valideren
  8. Schrijven
  9. Rapporteren
- [ ] Error recovery strategieën
- [ ] Partial success handling

### Logging & Reporting
- [ ] `cbs_toolkit/utils/logger.py` implementeren
  - [ ] Console logging (colored output)
  - [ ] File logging (detailed)
  - [ ] Progress tracking
  - [ ] Summary rapport na voltooiing
- [ ] Log levels (DEBUG, INFO, WARNING, ERROR)

**Milestone 4**: ✅ CLI tool volledig functioneel

---

## 📅 Fase 5: Integration & Testing (Week 4)

**Doel**: Alles testen en integreren

### Integration Tests
- [ ] End-to-end tests voor complete workflow
- [ ] Test met verschillende datasets:
  - [ ] Klein dataset (snelle test)
  - [ ] Medium dataset (normale use case)
  - [ ] Groot dataset (performance test)
- [ ] Test alle bronnen:
  - [ ] CBS opendata.cbs.nl
  - [ ] Politie dataderden.cbs.nl
  - [ ] RIVM dataderden.cbs.nl
- [ ] Gemeente filter tests
- [ ] Output validatie tests

### Unit Tests
- [ ] Minimaal 80% code coverage target
- [ ] Tests voor alle core modules
- [ ] Mock API responses voor snelle tests
- [ ] Edge case tests:
  - [ ] Lege datasets
  - [ ] Missing metadata
  - [ ] API timeouts
  - [ ] Invalid filters

### Performance Testing
- [ ] Benchmarks voor verschillende dataset sizes
- [ ] Memory profiling voor grote datasets
- [ ] Optimalisatie waar nodig:
  - [ ] Chunked processing voor grote datasets
  - [ ] Parallel downloads overwegen
  - [ ] Caching strategieën

### Kompas Integration (Optional)
- [ ] `cbs_toolkit/integrations/kompas_integration.py`
  - [ ] Bearer token authenticatie
  - [ ] API client voor Kompas
  - [ ] Data comparison logica migreren
- [ ] Credentials via .env
- [ ] Tests voor Kompas integratie

**Milestone 5**: ✅ Alle tests passing, performance acceptabel

---

## 📅 Fase 6: Documentation & Polish (Week 4-5)

**Doel**: Documentatie en gebruiksvriendelijkheid

### Code Documentation
- [ ] Docstrings voor alle publieke functies/classes
- [ ] Type hints complete
- [ ] Inline comments voor complexe logica
- [ ] Generate API documentation (Sphinx?)

### User Documentation
- [ ] BUILD.md updaten met setup instructies
- [ ] Usage examples in README.md
- [ ] Tutorial voor basic use cases
- [ ] Advanced usage guide
- [ ] FAQ sectie

### Examples & Templates
- [ ] Example scripts voor common scenarios
- [ ] Dataset list templates
- [ ] Configuration examples
- [ ] Output JSON examples

### Code Quality
- [ ] Code formatter setup (black)
- [ ] Linter setup (flake8 / pylint)
- [ ] Pre-commit hooks overwegen
- [ ] Code review checklist

**Milestone 6**: ✅ Production-ready met complete documentatie

---

## 🔮 Toekomstige Features (Backlog)

### Performance & Scaling
- [ ] Async/await voor parallelle downloads
- [ ] Database backend optie (vs CSV/JSON)
- [ ] Incremental updates (alleen nieuwe data ophalen)
- [ ] Delta updates (alleen gewijzigde records)
- [ ] Compression voor grote output files

### Data Features
- [ ] Data transformaties (pivoting, aggregaties)
- [ ] Custom filter query language
- [ ] Data quality rapportage dashboard
- [ ] Missing data imputation opties
- [ ] Time series specific features

### Integration
- [ ] REST API wrapper (Flask/FastAPI)
- [ ] Web dashboard voor monitoring
- [ ] Database loaders (PostgreSQL, MySQL)
- [ ] Cloud storage support (S3, Azure Blob)
- [ ] Notification webhooks (bij completion/errors)

### Developer Experience
- [ ] Docker container voor easy deployment
- [ ] CI/CD pipeline setup (GitHub Actions)
- [ ] Package publiceren naar PyPI
- [ ] Automated releases
- [ ] Version management

### Alternative Output Formats
- [ ] Parquet output (efficient columnar format)
- [ ] Excel export optie
- [ ] SQLite database file
- [ ] XML output (voor legacy systems)
- [ ] GraphQL API layer

---

## ⏸️ On Hold / Deferred

*Items die mogelijk interessant zijn maar geen prioriteit hebben*

- [ ] GUI applicatie (desktop app)
- [ ] Mobile app voor data viewing
- [ ] Real-time data streaming
- [ ] Machine learning pipelines integratie

---

## 🎓 Learning & Research Tasks

- [ ] CBS OData V4 protocol onderzoeken (upgrade van V3?)
- [ ] Best practices voor API rate limiting
- [ ] JSON-LD voor linked data overwegen
- [ ] Alternative CBS libraries evalueren
- [ ] Benchmarking tegen andere tools

---

## 📊 Success Metrics

**Definition of Done voor v1.0**:
- ✅ Alle Fase 1-6 milestones behaald
- ✅ Minimaal 80% test coverage
- ✅ Documentation 100% compleet
- ✅ Succesvol getest met 10+ verschillende datasets
- ✅ User acceptance testing door eindgebruikers
- ✅ Performance binnen acceptabele grenzen (<5 min voor gemiddeld dataset)

---

**Notities**:
- Prioriteiten kunnen verschuiven op basis van user feedback
- Elke fase eindigt met een review en demo
- Issues en bugs worden getrackt in BUGFIX.md
- Ideeën en experimenten gaan naar BRAINDUMP.md
