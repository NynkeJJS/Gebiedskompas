# BUILD - Setup & Development Instructions

**Project**: CBS Scripts Integration  
**Laatst bijgewerkt**: 19 januari 2026

---

## 📋 Prerequisites

### Required Software
- **Python**: 3.8 of hoger (3.10+ recommended)
- **pip**: Python package manager (usually included with Python)
- **git**: Version control (voor clonen repository)

### Optional but Recommended
- **Virtual environment tool**: `venv` (built-in) of `conda`
- **Code editor**: VS Code, PyCharm, of vergelijkbaar
- **Terminal**: Windows Terminal, iTerm2, of native terminal

### System Requirements
- **OS**: Windows 10+, Linux, macOS
- **RAM**: Minimaal 4GB (8GB+ recommended voor grote datasets)
- **Disk Space**: Minimaal 2GB vrij (voor datasets en dependencies)
- **Internet**: Stabiele verbinding voor CBS API calls

---

## 🚀 Quick Start (Huidige Scripts)

### 1. Clone/Download Project

```bash
# Via Git
git clone <repository-url>
cd CBS_Scripts_compare

# Of: download ZIP en extract
```

### 2. Setup Python Virtual Environment

**Windows**:
```cmd
# Maak virtual environment
python -m venv venv

# Activeer environment
venv\Scripts\activate
```

**Linux/macOS**:
```bash
# Maak virtual environment
python3 -m venv venv

# Activeer environment
source venv/bin/activate
```

Je prompt zou moeten veranderen naar: `(venv) $`

### 3. Install Dependencies

**Voor CBS_API_Gegevens**:
```bash
pip install requests pandas tqdm
```

**Voor CBS_API_Omschrijvingen**:
```bash
pip install cbsodata pandas requests
```

**Optioneel (voor Kompas integratie)**:
```bash
pip install oracledb  # Als Oracle DB nodig is
```

### 4. Verify Installation

```bash
python --version        # Should be 3.8+
pip list               # Check installed packages
```

---

## 📦 Detailed Setup Instructions

### Virtual Environment Best Practices

**Waarom virtual environment?**
- Isolatie van project dependencies
- Voorkomt conflicten tussen projecten
- Makkelijk recreëren op andere machines
- Best practice in Python development

**Alternatief: Conda**
```bash
conda create -n cbs-toolkit python=3.10
conda activate cbs-toolkit
```

### Requirements File Setup

**Maak `requirements.txt`** (nog te doen):
```txt
# CBS_API_Gegevens dependencies
requests>=2.28.0
pandas>=1.5.0
tqdm>=4.64.0

# CBS_API_Omschrijvingen dependencies  
cbsodata>=1.3.0

# Future toolkit dependencies
pyyaml>=6.0
python-dotenv>=1.0.0
jsonschema>=4.0.0

# Development dependencies
pytest>=7.2.0
black>=22.0.0
flake8>=5.0.0
```

**Install from requirements**:
```bash
pip install -r requirements.txt
```

### Development Dependencies

**Code Quality Tools**:
```bash
# Code formatter
pip install black

# Linter
pip install flake8 pylint

# Type checker
pip install mypy
```

**Testing Framework**:
```bash
pip install pytest pytest-cov
```

---

## 🔧 Running Current Scripts

### CBS_API_V4.py (Data Download)

**Basic Usage**:
```bash
cd CBS_API_Gegevens

# Single dataset
python CBS_API_V4.py -ds 83739NED -path ./output

# Met gemeente filter (Súdwest-Fryslân)
python CBS_API_V4.py -ds 83739NED -path ./output -gm 1900

# Politie data (andere endpoint)
python CBS_API_V4.py -ds 47026NED -path ./output -endpoint dataderden.cbs.nl
```

**Multiple Datasets**:
```bash
# Maak lijst van dataset IDs
datasets_CBS="83739NED 84417NED 85217NED"

# Run batch
python CBS_API_V4.py -ds "$datasets_CBS" -path ./output -gm 1900
```

**Parameters**:
- `-ds, --datasetcode`: CBS dataset code (bijv. `83739NED`)
- `-path, --folder_path`: Output directory voor CSV files
- `-gm, --gemeentecode`: [Optioneel] Gemeente code voor filtering (bijv. `1900`)
- `-endpoint, --api_endpoint`: [Optioneel] Alternatief endpoint (bijv. `dataderden.cbs.nl`)

### cbs_omschrijvingen_ophalen.py (Metadata)

**⚠️ Requires Edit First**:
Pas regel 221-223 aan met jouw paths:
```python
# EDIT DEZE PATHS:
cbs_title_matching_csv_path = r'./data/cbs_title_matching.csv'
cbs_details_csv_path = r'./data/cbs_dataset_details.csv'
csv_file_path = r'./data/indicator_testlijst.csv'
```

**Run**:
```bash
cd CBS_API_Omschrijvingen
python cbs_omschrijvingen_ophalen.py
```

**Output**:
- `indicator_descriptions.csv` - Gevonden beschrijvingen
- `indicators_without_description.csv` - Niet gevonden

### Jupyter Notebooks

**Install Jupyter**:
```bash
pip install jupyter
```

**Run Notebooks**:
```bash
cd CBS_API_Gegevens
jupyter notebook

# Opens browser → navigate to 1_Downloading_CBS.ipynb
```

---

## 🏗️ Development Setup (Future Toolkit)

*Deze sectie is voor de nieuwe geïntegreerde toolkit (nog te implementeren)*

### Project Structure Setup

```bash
# Maak project structuur
mkdir -p cbs_toolkit/{core,utils,schemas,integrations}
mkdir -p config
mkdir -p tests/{unit,integration}
mkdir -p docs

# Maak __init__.py files
touch cbs_toolkit/__init__.py
touch cbs_toolkit/core/__init__.py
touch cbs_toolkit/utils/__init__.py
```

### Configuration Files

**Create `.env` file**:
```bash
cp config/.env.example .env

# Edit .env met jouw credentials
nano .env  # of je favoriete editor
```

**Example `.env`**:
```bash
# Kompas API Credentials
KOMPAS_CLIENT_ID=monitor_device
KOMPAS_CLIENT_SECRET=your_secret_here
KOMPAS_BASE_URL=https://sudwestfryslan.gebiedsmonitor.nl

# Output Settings
OUTPUT_DIR=./output
LOG_LEVEL=INFO

# API Settings
CBS_TIMEOUT=30
CBS_MAX_RETRIES=3
```

**Create `config.yaml`**:
```yaml
# See implementation_plan.md for full example
endpoints:
  cbs:
    url: "opendata.cbs.nl"
    
filters:
  default_gemeente: "1900"
  
output:
  format: "json"
  pretty_print: true
```

### Git Setup

**Create `.gitignore`**:
```gitignore
# Virtual Environment
venv/
env/
.conda/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp

# Output
output/
*.csv
*.json
*.log

# OS
.DS_Store
Thumbs.db

# Data
CBS_DATA/
data/*.csv
```

**Initialize Git** (if not already):
```bash
git init
git add .
git commit -m "Initial project setup"
```

---

## 🧪 Testing Setup

### Run Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=cbs_toolkit --cov-report=html

# Specific test file
pytest tests/unit/test_api_client.py

# Verbose output
pytest -v
```

### Test Configuration

**Create `pytest.ini`**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

---

## 🔍 Code Quality Checks

### Format Code

```bash
# Format all Python files
black .

# Check formatting (without changing)
black --check .
```

### Lint Code

```bash
# Flake8
flake8 cbs_toolkit/

# Pylint
pylint cbs_toolkit/
```

### Type Checking

```bash
mypy cbs_toolkit/
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'requests'`
```bash
# Solution: Install dependencies
pip install requests pandas
```

**Issue**: Virtual environment not activating
```bash
# Windows: use PowerShell instead of CMD
# Or: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Linux/Mac: Check file permissions
chmod +x venv/bin/activate
```

**Issue**: `UnicodeDecodeError` bij CSV lezen
```python
# Solution: Specificeer encoding
pd.read_csv('file.csv', encoding='utf-8-sig')
```

**Issue**: API timeout errors
```python
# Solution: Verhoog timeout
requests.get(url, timeout=60)  # 60 seconds
```

**Issue**: Memory error bij grote datasets
```bash
# Solution: Gebruik chunks
for chunk in pd.read_csv('large.csv', chunksize=1000):
    process(chunk)
```

### Getting Help

1. Check bestaande documentatie in `docs/`
2. Review `BUGFIX.md` voor known issues
3. Search GitHub issues (wanneer repo public)
4. Contact project maintainer

---

## 🚢 Deployment

*Nog te bepalen - future planning*

### Package for Distribution

```bash
# Build wheel
python setup.py bdist_wheel

# Install locally
pip install dist/cbs_toolkit-0.1.0-py3-none-any.whl
```

### Docker (Future)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "cbs_to_json.py"]
```

---

## 📝 Development Workflow

**Recommended workflow**:

1. **Start**: Activate virtual environment
   ```bash
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Code**: Make changes in feature branch
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Test**: Run tests locally
   ```bash
   pytest
   black .
   flake8 .
   ```

4. **Commit**: Commit with clear message
   ```bash
   git add .
   git commit -m "feat: add nieuwe functionaliteit"
   ```

5. **Push**: Push en create pull request
   ```bash
   git push origin feature/my-feature
   ```

---

## 🔄 Updating Dependencies

```bash
# Update all packages
pip list --outdated
pip install --upgrade <package-name>

# Update requirements.txt
pip freeze > requirements.txt
```

---

## 📚 Additional Resources

- [Python Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)
- [pip Documentation](https://pip.pypa.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [CBS OData API Documentation](https://www.cbs.nl/nl-nl/onze-diensten/open-data/statline-als-open-data)

---

**Need help?** Check de andere documentatie:
- Setup problemen → dit document
- Feature requests → `TODO.md`
- Bugs → `BUGFIX.md`
- Ideeën → `BRAINDUMP.md`
