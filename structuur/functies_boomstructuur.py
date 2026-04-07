# functies.py
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

def inlezen_json(pad: str | Path) -> Any:
    """
    Inlezen van een JSON-bestand en teruggeven als Python-object.
    """
    p = Path(pad)
    if not p.exists():
        raise FileNotFoundError(f"Bestand bestaat niet: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def toon_structuur(data, indent: int = 0) -> None:
    """
    Deze functie print in één oogopslag de structuur van een JSON‑achtige datastructuur 
    door per niveau te tonen welk type waarde er staat.    
    """
    sp = "  " * indent  # twee spaties per niveau
    """
    data = dictionary: Deze code doorloopt alle key‑value‑paren in een dictionary, print per key het type van de bijbehorende waarde en roept daarna recursief dezelfde functie aan om de onderliggende structuur verder te tonen.
    data = list: Deze code doorloopt alle elementen in een lijst, print per element het type en roept daarna recursief dezelfde functie aan om de onderliggende structuur verder te tonen.

    """    
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{sp}- {key}: {type(value).__name__}")
            toon_structuur(value, indent + 1)


    elif isinstance(data, list):
            print(f"{sp}- list ({len(data)} items)")
            if len(data) > 0:
                # Toon structuur van het eerste element als voorbeeld
                toon_structuur(data[0], indent + 1)

    else:
        print(f"{sp}- {type(data).__name__}")

def print_json(data) -> None:
    """
    Print de volledige JSON netjes met inspringing en Unicode.
    """
    try:        
        print(json.dumps(data, indent=2, ensure_ascii=False))    
    except TypeError as e:        
        print(f"Kan data niet serialiseren naar JSON: {e}")
        
def flatten_hierarchy(data: Any,
                      name_key: str = "name",
                      type_key: str = "type",
                      children_key: str = "children",
                      color_key: str = "color",
                      extra_keys: List[str] = None) -> pd.DataFrame:
    """
    Zet een hiërarchische JSON/dict/list om naar een platte tabel met:
    path, name, type, color, depth, parent + optionele extra velden (bv. uuid, value).
    """
    if extra_keys is None:
        extra_keys = []  # default: geen extra velden

    rows: List[Dict[str, Any]] = []

    def walk(node: Any, path: List[str], parent: Optional[str], depth: int):
        """
        walk is een recursieve functie die een boom van dict‑nodes doorloopt, 
        per node het pad en metadata (naam, type, kleur, diepte, ouder en extra velden) samenstelt, 
        deze als rij aan rows toevoegt en vervolgens alle kinderen bezoekt met een geüpdatet pad en verhoogde diepte.
        """
        if isinstance(node, dict):
            name  = node.get(name_key, "(zonder naam)")
            ntype = node.get(type_key)
            color = node.get(color_key)

            cur_path = path + [str(name)]
            row = {
                "path": "/".join(cur_path),
                "name": name,
                "type": ntype,
                "color": color,
                "depth": depth,
                "parent": parent
            }

            # Voeg extra velden toe (bv. "uuid", "value")
            for k in extra_keys:
                row[k] = node.get(k)

            rows.append(row)

            # Kinderen doorlopen
            children = node.get(children_key) or []
            if isinstance(children, list):
                for ch in children:
                    walk(ch, cur_path, name, depth + 1)

        elif isinstance(node, list):
            list_name = "(lijst)"
            cur_path = path + [list_name]
            rows.append({
                "path": "/".join(cur_path),
                "name": list_name,
                "type": None,
                "color": None,
                "depth": depth,
                "parent": parent,
                **{k: None for k in extra_keys}
            })
            for ch in node:
                walk(ch, cur_path, list_name, depth + 1)

    walk(data, [], parent=None, depth=0)
    return pd.DataFrame(rows)

def depth_type_kolommen(df_nodes):
    """
    Maak een tabel met per depth:
      - het type dat op die depth voorkomt
      - de kolommen die ergens NIET-NaN zijn binnen die depth
    """
    # Bepaal per depth welke kolommen ergens niet-NaN zijn
    kol_per_depth = (
        df_nodes
        .groupby("depth")
        .apply(lambda g: g.columns[g.notna().any()].tolist())
        .rename("kolommen")
        .reset_index()
    )

    # Bepaal per depth het type dat daar voorkomt
    type_per_depth = (
        df_nodes
        .groupby("depth")["type"]
        .apply(lambda s: sorted(s.dropna().unique().tolist()))
        .reset_index()
    )

    # merge depth → kolommen + type
    df = kol_per_depth.merge(type_per_depth, on="depth", how="left")

    # Omdat per depth precies 1 type hoort, nemen we de eerste (string ipv lijst)
    df["type"] = df["type"].apply(lambda lst: lst[0] if lst else None)

    return df[["depth", "type", "kolommen"]]
