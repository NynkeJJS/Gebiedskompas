# main.py
from functies import inlezen_json, toon_structuur, pretty_print_json

def main():
    pad_naar_json = "data/raw/kompas_hierarchie.json"

    try:
        data = inlezen_json(pad_naar_json)
        print("JSON succesvol ingelezen!\n")

        print("=== STRUCTUUR (hiërarchie) ===")
        toon_structuur(data)

        print("\n=== VOLLEDIGE JSON (netjes) ===")
        pretty_print_json(data)

    except Exception as e:
        print(f"Er ging iets mis bij het inlezen: {e}")

if __name__ == "__main__":
    main()
