import requests
import pandas as pd
import os
from config_experiment import BASE_URL, PROVINCIE, BATCH_SIZE, FRIESE_GEMEENTEN, OUTPUT_DIR, OUTPUT_DATA, OUTPUT_META


def get_all_pages(url, params=None):
    """Haal alle pagina's op via paginering."""
    results = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        results.extend(data.get('value', []))
        url = data.get('odata.nextLink')
        params = None
    return results

def get_metadata():
    print("Metadata ophalen...")
    meta_data = get_all_pages(f"{BASE_URL}/DataProperties")
    df_meta = pd.DataFrame(meta_data)
    print(f"  {len(df_meta)} indicatoren gevonden")
    return df_meta


def get_provincie_gebieden():
    print(f"Wijken en buurten ophalen voor {PROVINCIE}...")
    geo_data = get_all_pages(f"{BASE_URL}/WijkenEnBuurten")
    df_geo = pd.DataFrame(geo_data)

    # 1. Selecteer Friese gemeenten (GM)
    friese_gemeenten = FRIESE_GEMEENTEN
    print(f"  Friese gemeenten: {friese_gemeenten}")

    # 2. Selecteer ALLE gebieden (GM, WK, BU) die tot Friesland behoren
    df_provincie = df_geo[
        (df_geo['Key'].isin(friese_gemeenten)) |            # GM-niveau
        (df_geo['Municipality'].isin(friese_gemeenten))     # WK & BU niveau
    ]

    print(f"  {len(df_provincie)} gebieden gevonden in {PROVINCIE}")
    return df_provincie


def get_data_provincie(provincie_codes):
    print(f"Data ophalen voor {PROVINCIE}...")
    all_data = []

    for i in range(0, len(provincie_codes), BATCH_SIZE):
        batch = provincie_codes[i:i + BATCH_SIZE]
        filter_str = " or ".join([f"WijkenEnBuurten eq '{code}'" for code in batch])

        params = {"$filter": filter_str, "$top": 10000}
        batch_data = get_all_pages(f"{BASE_URL}/TypedDataSet", params=params)

        all_data.extend(batch_data)
        print(f"  Batch {i // BATCH_SIZE + 1} geladen ({len(batch_data)} rijen)")

    df_data = pd.DataFrame(all_data)

    print(f"  Totaal {len(df_data)} rijen opgehaald")
    return df_data


def koppel_metadata(df_data, df_meta):
    print("Metadata koppelen...")
    meta_dict = df_meta.set_index('Key')['Title'].to_dict()
    
    # WijkenEnBuurten uitsluiten van hernoemen
    meta_dict.pop('WijkenEnBuurten', None)
    
    rename_map = {k: v for k, v in meta_dict.items() if k in df_data.columns}
    df_data_labeled = df_data.rename(columns=rename_map)
    print(f"  {len(rename_map)} kolommen hernoemd")
    return df_data_labeled


def koppel_geo_info(df_data, df_provincie):
    print("Geografische info koppelen...")
    df_geo_info = df_provincie[['Key', 'Title']].rename(
        columns={'Title': 'Naam_gebied', 'Key': 'WijkenEnBuurten'}
    )
    return df_data.merge(df_geo_info, on='WijkenEnBuurten', how='left')

def sla_op(df_data, df_meta):
    print("Bestanden opslaan...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Stel bestandsnamen in    
    data_path = os.path.join(OUTPUT_DIR, OUTPUT_DATA)    
    meta_path = os.path.join(OUTPUT_DIR, OUTPUT_META)    

    # Sla csv’s op    
    df_data.to_csv(data_path, index=False)    
    df_meta.to_csv(meta_path, index=False)    
    
    print(f"  Data opgeslagen op: {os.path.abspath(data_path)}")    
    print(f"  Meta opgeslagen op: {os.path.abspath(meta_path)}")


def lees_opgeslagen_data():
    data_path = os.path.join(OUTPUT_DIR, OUTPUT_DATA)
    meta_path = os.path.join(OUTPUT_DIR, OUTPUT_META)

    print("Data vanaf schijf inlezen...")
    df_data = pd.read_csv(data_path, low_memory=False)
    df_meta = pd.read_csv(meta_path, low_memory=False) if os.path.exists(meta_path) else None

    print(f"Klaar! Shape: {df_data.shape}")
    return df_data, df_meta


