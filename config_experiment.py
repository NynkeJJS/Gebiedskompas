# config_experiment.py
# ======================================
# Centrale configuratie voor het project
# ======================================

import os
from html2image import Html2Image


# -------------------------------
# CBS configuratie
# -------------------------------

BASE_URL = "https://opendata.cbs.nl/ODataApi/odata/86165NED"
PROVINCIE = "Friesland"
BATCH_SIZE = 50

FRIESE_GEMEENTEN = [
    'GM0059',  # Achtkarspelen
    'GM0060',  # Ameland
    'GM1891',  # Dantumadiel
    'GM1940',  # De Fryske Marren
    'GM0072',  # Harlingen
    'GM0074',  # Heerenveen
    'GM0080',  # Leeuwarden
    'GM1970',  # Noardeast-Fryslân
    'GM0085',  # Ooststellingwerf
    'GM0086',  # Opsterland
    'GM0088',  # Schiermonnikoog
    'GM0090',  # Smallingerland
    'GM1900',  # Súdwest-Fryslân
    'GM0093',  # Terschelling
    'GM0737',  # Tytsjerksteradiel
    'GM0096',  # Vlieland
    'GM1949',  # Waadhoeke
    'GM0098',  # Weststellingwerf
]


# -------------------------------
# Data directories
# -------------------------------

RAW_DIR = "data/raw"

# Klimaatatlas
KLIMAAT_DATA_CSV = "Klimaateffectatlas_data.csv"
KLIMAAT_META_CSV = "Klimaateffectatlas_metadata.csv"

# Tussentijdse (enriched) data
BEWERKT_DIR = "data/bewerkt"
KERNCIJFERS_DATA = "kerncijfers_data.csv"
KERNCIJFERS_META = "kerncijfers_meta.csv"

# Output structuur
OUTPUT_DIR    = "data/output"
FIGURE_DIR    = os.path.join(OUTPUT_DIR, "figuren")
RAPPORT_DIR   = os.path.join(OUTPUT_DIR, "rapport")
_RENDER_TMP   = os.path.join(OUTPUT_DIR, "_render_tmp")

# Mappen aanmaken
os.makedirs(FIGURE_DIR, exist_ok=True)
os.makedirs(RAPPORT_DIR, exist_ok=True)
os.makedirs(_RENDER_TMP, exist_ok=True)


# -------------------------------
# Chrome executable path
# -------------------------------

# Dit pad is correct voor macOS installatie van Chrome
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Ctrl: als Chrome niet bestaat → geef waarschuwing
if not os.path.exists(CHROME_PATH):
    print("⚠️  Waarschuwing: Chrome niet gevonden op verwachte locatie.")
    print("   → Controleer installatie of pas CHROME_PATH aan in config_experiment.py")


# -------------------------------
# HTML2IMAGE (Chrome headless)
# -------------------------------



hti = Html2Image(
    browser_executable=CHROME_PATH,
    output_path=_RENDER_TMP,
    custom_flags=[
        "--headless=new",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-features=UseSkiaRenderer",
    ]
)

