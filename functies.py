# functies.py
import json
from pathlib import Path
from typing import Any

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