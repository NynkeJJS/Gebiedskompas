BASE_URL = "https://opendata.cbs.nl/ODataApi/odata/85318NED"
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

# Input paden
INPUT_DIR = "data/raw"
DATA_CSV = "Klimaateffectatlas_data.csv"       
META_CSV = "Klimaateffectatlas_metadata.csv"

# Output paden
OUTPUT_DIR = "data/output"
OUTPUT_DATA = "friesland_data.csv"
OUTPUT_META = "friesland_meta.csv"
