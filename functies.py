# functies.py
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

def inlezen_json(pad: str | Path) -> Any:
    p = Path(pad)
    if not p.exists():
        raise FileNotFoundError(f"Bestand bestaat niet: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def toon_structuur(data, indent: int = 0) -> None:
    """
    Print de hiërarchie van een JSON-structuur (dict of list) met types per niveau.
    """
    sp = "  " * indent  # twee spaties per niveau

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
        print(f"{sp}- value ({type(data).__name__})")

def pretty_print_json(data) -> None:
    """
    Print de volledige JSON netjes met inspringing en Unicode.
    """
    print(json.dumps(data, indent=2, ensure_ascii=False))

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


import pandas as pd

from typing import Any, Dict, List

def flatten_indicators(root: Any) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    def flatten_dict(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Maak nested dicts plat met key.pad (bv. metadata.bron)."""
        out = {}
        for k, v in d.items():
            if k == "children":            # children niet in dezelfde rij stoppen
                continue
            kk = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            if isinstance(v, dict):
                out.update(flatten_dict(v, kk))
            else:
                out[kk] = v
        return out

    def walk(node: Any, path: List[str]):
        if isinstance(node, dict):
            name = node.get("name", "(zonder naam)")
            if node.get("type") == "indicator":
                row = {"path": "/".join(path + [name])}
                row.update(flatten_dict(node))  # alle velden van de indicator
                rows.append(row)
            # verder dalen
            for ch in (node.get("children") or []):
                walk(ch, path + [name])
        elif isinstance(node, list):
            for it in node:
                walk(it, path)

    walk(root, [])
    return pd.DataFrame(rows)

