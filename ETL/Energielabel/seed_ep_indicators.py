#!/usr/bin/env python3
"""
Seed EP-Online indicators manually to avoid import script issues.
"""
import psycopg2
import os, sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def seed_indicators():
    conn = psycopg2.connect(
        host=os.getenv('DATABASE_HOST'), port=os.getenv('DATABASE_PORT'),
        dbname=os.getenv('DATABASE_NAME'), user=os.getenv('DATABASE_USER'),
        password=os.getenv('DATABASE_PASSWORD'), sslmode=os.getenv('DATABASE_SSLMODE','prefer'))
    cur = conn.cursor()
    
    indicators = [
        ('Aantal energielabels (definitief)', 'aantal_energielabels_definitief', 'aantal', 'Aantal definitieve energielabels (Status: Bestaand of Oplevering)'),
        ('Aantal energielabels (voorlopig)', 'aantal_energielabels_voorlopig', 'aantal', 'Aantal voorlopige energielabels (Status: Vergunningsaanvraag)'),
        ('Aantal energielabels (totaal)', 'aantal_energielabels_totaal', 'aantal', 'Totaal aantal geregistreerde energielabels (Definitief + Voorlopig)'),
        ('Gemiddeld energielabel', 'gemiddeld_energielabel', 'labelklasse', 'Gemiddeld energielabel van definitieve labels')
    ]
    
    print("Seeding indicators...")
    
    for name, code, eenheid, omschrijving in indicators:
        # Check existing
        cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (name,))
        res = cur.fetchone()
        if res:
            print(f"ℹ️  Exists: {name} ({res[0]})")
            continue
            
        # Insert
        try:
            cur.execute("""
                INSERT INTO indicatoren (naam, code, eenheid, omschrijving, bron, interpretatie_logica)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING uuid
            """, (name, code, eenheid, omschrijving, 'RVO EP-Online', 'N/A'))
            uuid = cur.fetchone()[0]
            print(f"✅ Created: {name} ({uuid})")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print(f"⚠️  Unique violation for {name} (code={code})")
            
    conn.commit()
    conn.close()
    print("Done")

if __name__ == "__main__":
    seed_indicators()
