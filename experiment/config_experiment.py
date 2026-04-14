# ======================================
# Centrale configuratie voor het project
# ======================================

import os
from html2image import Html2Image

# ==========================================
# CENTRALE CONFIGURATIE
# ==========================================
# Print alle stappen (voor debugging)
VERBOSE = True

# ------------------------------------------------------
# Debug helpers
# ------------------------------------------------------

def vprint(msg: str):
    if VERBOSE:
        print(msg)


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

RAW_DIR = "../data/raw"
BEWERKT_DIR = "../data/bewerkt"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(BEWERKT_DIR, exist_ok=True)

# Klimaatatlas
KLIMAAT_DATA_CSV = os.path.join(RAW_DIR, "klimaateffectatlas_data.csv")
KLIMAAT_META_CSV = os.path.join(RAW_DIR, "klimaateffectatlas_metadata.csv")

# Tussentijdse (enriched) data
KERNCIJFERS_DATA = os.path.join(BEWERKT_DIR, "kerncijfers_data.csv")
KERNCIJFERS_META = os.path.join(BEWERKT_DIR, "kerncijfers_meta.csv")

# Output structuur
OUTPUT_DIR    = "../data/output"
FIGURE_DIR    = os.path.join(OUTPUT_DIR, "figuren")
RAPPORT_DIR   = os.path.join(OUTPUT_DIR, "rapport")
_RENDER_TMP   = os.path.join(OUTPUT_DIR, "_render_tmp")

PDF_PATH = os.path.join(RAPPORT_DIR, "rapport.pdf")


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
    print("Waarschuwing: Chrome niet gevonden op verwachte locatie.")
    print("Controleer installatie of pas CHROME_PATH aan in config_experiment.py")


# -------------------------------
# HTML2IMAGE (Chrome headless)
# -------------------------------



hti = Html2Image(
    browser_executable=CHROME_PATH,
    output_path=_RENDER_TMP,
    custom_flags=[
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--window-size=1920,1080",
    ],
)



# ======================================================
# KOLUMNEN DIE UITGESLOTEN MOETEN WORDEN VOOR PCA en FA
# ======================================================

EXCLUDE = {
    "ID",
    "Key",
    "WijkenEnBuurten",
    "Municipality",
    "Gemeente",
    "Title",
    "Naam_gebied",
    "Gebied",
    "Buurtcode",
}

# ======================================================
# PARAMETER VOOR PCA
# ======================================================
VARIANCE_THRESHOLD = 0.90 # Drempel voor cumulatieve variantie bij PCA