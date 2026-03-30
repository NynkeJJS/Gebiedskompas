#!/usr/bin/env python3
"""
Kompas UUID Mapping Validatie Script
=====================================
Dit script valideert de relaties tussen indicatoren in:
1. Kompas hiërarchie (kompas_indicator_mapping)
2. Indicatoren tabel (indicatoren)
3. Gebiedsmonitor dropdown (indicator_gebiedstype_relaties)
4. Beschikbare data (gebied_data)

Gebruik:
    python scripts/validate_kompas_uuid_mapping.py

Output:
    - Console rapport met statistieken
    - Markdown rapport in ontwikkelaarsvragen/

Auteur: D-OmniTwin Team
Laatste update: 23-01-2026
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import configparser

# Database
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# DATABASE CONNECTIE
# ============================================================================

def get_db_connection():
    """Maak database connectie op basis van config.ini"""
    config_path = Path(__file__).parent.parent / 'config.ini'
    
    if not config_path.exists():
        print(f"❌ Config file niet gevonden: {config_path}")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    db_config = config['DATABASE']
    return psycopg2.connect(
        host=db_config.get('host', 'localhost'),
        port=db_config.get('port', '5432'),
        database=db_config.get('dbname', 'omnitwin_db'),
        user=db_config.get('user', 'omnitwin_user'),
        password=db_config.get('password', '')
    )


# ============================================================================
# UUID MAPPING ANALYSE
# ============================================================================

def get_kompas_indicators(conn, config_id: int = None) -> dict:
    """
    Haal alle indicatoren op uit kompas configuratie(s)
    
    Returns: {uuid: {naam, config_id, config_naam, ...}}
    """
    query = """
        SELECT 
            kim.indicator_uuid,
            i.naam as indicator_naam,
            i.omschrijving as beschrijving,
            i.eenheid,
            kc.id as config_id,
            kc.naam as config_naam,
            kim.is_actueel
        FROM kompas_indicator_mapping kim
        JOIN indicatoren i ON kim.indicator_uuid = i.uuid
        JOIN kompas_configuraties kc ON kim.config_id = kc.id
        WHERE kc.is_actief = TRUE
    """
    if config_id:
        query += f" AND kim.config_id = {config_id}"
    
    query += " ORDER BY kc.id, i.naam"
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    result = {}
    for row in rows:
        uuid = str(row['indicator_uuid'])
        if uuid not in result:
            result[uuid] = {
                'naam': row['indicator_naam'],
                'beschrijving': row['beschrijving'],
                'eenheid': row['eenheid'],
                'configs': []
            }
        result[uuid]['configs'].append({
            'id': row['config_id'],
            'naam': row['config_naam'],
            'is_actueel': row['is_actueel']
        })
    
    return result


def get_dropdown_indicators(conn, gebiedstype_id: int = None) -> dict:
    """
    Haal alle indicatoren die in de dropdown kunnen verschijnen
    (basis: indicatoren met status O of C)
    
    Returns: {uuid: {naam, status, gebiedstypes: [...]}}
    """
    query = """
        SELECT 
            i.uuid,
            i.naam,
            i.status,
            i.omschrijving as beschrijving,
            i.eenheid,
            COALESCE(array_agg(DISTINCT gt.naam) FILTER (WHERE gt.naam IS NOT NULL), ARRAY[]::text[]) as gebiedstypes
        FROM indicatoren i
        LEFT JOIN indicator_gebiedstype_relaties igr ON i.uuid = igr.indicator_uuid
        LEFT JOIN gebiedstypes gt ON igr.gebiedstype_id = gt.id
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.status, i.omschrijving, i.eenheid
        ORDER BY i.naam
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    result = {}
    for row in rows:
        uuid = str(row['uuid'])
        result[uuid] = {
            'naam': row['naam'],
            'status': row['status'],
            'beschrijving': row['beschrijving'],
            'eenheid': row['eenheid'],
            'gebiedstypes': row['gebiedstypes'] if row['gebiedstypes'] else []
        }
    
    return result


def get_data_indicators(conn) -> dict:
    """
    Haal alle indicatoren met daadwerkelijke data op
    
    Returns: {uuid: {naam, count_records, count_gebieden, jaren: [...]}}
    """
    query = """
        SELECT 
            i.uuid,
            i.naam,
            COUNT(*) as count_records,
            COUNT(DISTINCT gd.gebied_id) as count_gebieden,
            array_agg(DISTINCT gd.jaar ORDER BY gd.jaar DESC) as jaren
        FROM indicatoren i
        JOIN gebied_data gd ON i.uuid = gd.indicator_uuid
        GROUP BY i.uuid, i.naam
        ORDER BY count_records DESC
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    result = {}
    for row in rows:
        uuid = str(row['uuid'])
        result[uuid] = {
            'naam': row['naam'],
            'count_records': row['count_records'],
            'count_gebieden': row['count_gebieden'],
            'jaren': row['jaren'] if row['jaren'] else []
        }
    
    return result


def get_kompas_configs(conn) -> list:
    """Haal alle actieve kompas configuraties op"""
    query = """
        SELECT 
            id, naam, is_standaard,
            (SELECT COUNT(*) FROM kompas_indicator_mapping WHERE config_id = kc.id) as indicator_count
        FROM kompas_configuraties kc
        WHERE is_actief = TRUE
        ORDER BY is_standaard DESC, id
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


# ============================================================================
# ANALYSE & VERGELIJKING
# ============================================================================

def analyze_mapping(kompas_indicators, dropdown_indicators, data_indicators) -> dict:
    """
    Analyseer de overlap tussen de drie sets indicatoren
    
    Returns: Dict met analyse resultaten
    """
    kompas_set = set(kompas_indicators.keys())
    dropdown_set = set(dropdown_indicators.keys())
    data_set = set(data_indicators.keys())
    
    # Venn diagram componenten
    analysis = {
        # Totalen
        'total_kompas': len(kompas_set),
        'total_dropdown': len(dropdown_set),
        'total_with_data': len(data_set),
        
        # Overlaps
        'kompas_and_dropdown': kompas_set & dropdown_set,
        'kompas_and_data': kompas_set & data_set,
        'dropdown_and_data': dropdown_set & data_set,
        'all_three': kompas_set & dropdown_set & data_set,
        
        # Problematische sets
        'kompas_only': kompas_set - dropdown_set - data_set,
        'kompas_no_data': kompas_set - data_set,
        'dropdown_no_data': dropdown_set - data_set,
        'data_not_in_kompas': data_set - kompas_set,
        'data_not_in_dropdown': data_set - dropdown_set,
        
        # Specifieke issues
        'kompas_not_in_dropdown': kompas_set - dropdown_set,
        'dropdown_not_in_kompas': dropdown_set - kompas_set,
    }
    
    return analysis


# ============================================================================
# RAPPORT GENERATIE
# ============================================================================

def generate_report(
    configs: list,
    kompas_ind: dict, 
    dropdown_ind: dict, 
    data_ind: dict,
    analysis: dict
) -> str:
    """Genereer Markdown rapport"""
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"""# Kompas UUID Mapping Validatie Rapport

**Gegenereerd:** {now}  
**Script:** `scripts/validate_kompas_uuid_mapping.py`

---

## 📊 Samenvatting

| Bron | Aantal Indicatoren |
|------|-------------------|
| Kompas Configuratie(s) | {analysis['total_kompas']} |
| Dropdown (status O/C) | {analysis['total_dropdown']} |
| Met Data (gebied_data) | {analysis['total_with_data']} |

### Overlap Analyse

| Combinatie | Aantal |
|------------|--------|
| ✅ In kompas + dropdown + data | {len(analysis['all_three'])} |
| ⚠️ In kompas, zonder data | {len(analysis['kompas_no_data'])} |
| ⚠️ In kompas, niet in dropdown | {len(analysis['kompas_not_in_dropdown'])} |
| 📋 Data aanwezig, niet in kompas | {len(analysis['data_not_in_kompas'])} |

---

## 🎯 Kompas Configuraties

"""
    
    for config in configs:
        status = "✅ STANDAARD" if config['is_standaard'] else ""
        report += f"- **{config['naam']}** (ID: {config['id']}) - {config['indicator_count']} indicatoren {status}\n"
    
    report += """
---

## ⚠️ Potentiële Problemen

### Kompas indicatoren ZONDER data
"""
    
    if analysis['kompas_no_data']:
        report += "\n| Indicator | UUID | In Dropdown? |\n|-----------|------|-------------|\n"
        for uuid in sorted(analysis['kompas_no_data'], key=lambda u: kompas_ind[u]['naam']):
            ind = kompas_ind[uuid]
            in_dropdown = "✅ Ja" if uuid in dropdown_ind else "❌ Nee"
            report += f"| {ind['naam'][:40]} | `{uuid[:8]}...` | {in_dropdown} |\n"
    else:
        report += "\n✅ Geen problemen - alle kompas indicatoren hebben data.\n"
    
    report += """
### Kompas indicatoren NIET in dropdown

> Deze indicatoren zijn wel in het kompas, maar zouden niet in de gebiedsmonitor dropdown verschijnen.

"""
    
    if analysis['kompas_not_in_dropdown']:
        report += "\n| Indicator | UUID | Reden |\n|-----------|------|-------|\n"
        for uuid in sorted(analysis['kompas_not_in_dropdown'], key=lambda u: kompas_ind[u]['naam']):
            ind = kompas_ind[uuid]
            report += f"| {ind['naam'][:40]} | `{uuid[:8]}...` | Status niet O/C? |\n"
    else:
        report += "\n✅ Geen problemen - alle kompas indicatoren zijn ook in dropdown.\n"
    
    report += """
---

## ✅ Werkende Indicatoren

### Volledige integratie (kompas + dropdown + data)

"""
    
    if analysis['all_three']:
        report += "| Indicator | Gebieden | Jaren | Eenheid |\n|-----------|----------|-------|--------|\n"
        for uuid in sorted(analysis['all_three'], key=lambda u: kompas_ind[u]['naam'])[:20]:
            ind_kompas = kompas_ind[uuid]
            ind_data = data_ind[uuid]
            jaren_str = ", ".join(map(str, ind_data['jaren'][:3])) if ind_data['jaren'] else "-"
            eenheid = ind_kompas.get('eenheid', '-') or '-'
            report += f"| {ind_kompas['naam'][:35]} | {ind_data['count_gebieden']} | {jaren_str} | {eenheid[:15]} |\n"
        
        if len(analysis['all_three']) > 20:
            report += f"\n*... en {len(analysis['all_three']) - 20} meer*\n"
    else:
        report += "\n⚠️ Geen indicatoren met volledige integratie gevonden.\n"
    
    report += """
---

## 📋 Data zonder Kompas Mapping

> Deze indicatoren hebben data maar zijn niet in een kompas configuratie opgenomen.

"""
    
    if analysis['data_not_in_kompas']:
        report += "| Indicator | Gebieden | Records |\n|-----------|----------|--------|\n"
        for uuid in sorted(analysis['data_not_in_kompas'], key=lambda u: data_ind[u]['count_records'], reverse=True)[:10]:
            ind = data_ind[uuid]
            report += f"| {ind['naam'][:40]} | {ind['count_gebieden']} | {ind['count_records']} |\n"
        
        if len(analysis['data_not_in_kompas']) > 10:
            report += f"\n*... en {len(analysis['data_not_in_kompas']) - 10} meer*\n"
    else:
        report += "\n✅ Alle indicatoren met data zijn in kompas opgenomen.\n"
    
    report += f"""
---

## 🔧 Aanbevelingen

"""
    
    # Genereer aanbevelingen op basis van analyse
    recommendations = []
    
    if analysis['kompas_not_in_dropdown']:
        recommendations.append(f"- {len(analysis['kompas_not_in_dropdown'])} kompas indicatoren ontbreken in dropdown - check status in `indicatoren` tabel")
    
    if analysis['kompas_no_data']:
        recommendations.append(f"- {len(analysis['kompas_no_data'])} kompas indicatoren hebben geen data - importeer metingen of verwijder uit kompas")
    
    if len(analysis['data_not_in_kompas']) > 5:
        recommendations.append(f"- {len(analysis['data_not_in_kompas'])} indicatoren met data zijn niet in kompas - overweeg toevoegen")
    
    if not recommendations:
        recommendations.append("- ✅ Geen directe acties nodig - mapping is consistent!")
    
    for rec in recommendations:
        report += f"{rec}\n"
    
    report += f"""
---

*Rapport gegenereerd door `validate_kompas_uuid_mapping.py`*
"""
    
    return report


def print_console_summary(analysis: dict, kompas_ind: dict):
    """Print beknopte samenvatting naar console"""
    print("\n" + "="*60)
    print("🔍 KOMPAS UUID MAPPING VALIDATIE")
    print("="*60)
    
    print(f"\n📊 Totalen:")
    print(f"   • Kompas indicatoren:  {analysis['total_kompas']}")
    print(f"   • Dropdown indicatoren: {analysis['total_dropdown']}")
    print(f"   • Met data:            {analysis['total_with_data']}")
    
    print(f"\n✅ Volledig werkend (kompas + dropdown + data): {len(analysis['all_three'])}")
    
    if analysis['kompas_no_data']:
        print(f"\n⚠️ Kompas ZONDER data: {len(analysis['kompas_no_data'])}")
        for uuid in list(analysis['kompas_no_data'])[:5]:
            print(f"   - {kompas_ind[uuid]['naam']}")
        if len(analysis['kompas_no_data']) > 5:
            print(f"   ... en {len(analysis['kompas_no_data']) - 5} meer")
    
    if analysis['kompas_not_in_dropdown']:
        print(f"\n⚠️ Kompas NIET in dropdown: {len(analysis['kompas_not_in_dropdown'])}")
        for uuid in list(analysis['kompas_not_in_dropdown'])[:3]:
            print(f"   - {kompas_ind[uuid]['naam']}")
    
    print("\n" + "="*60)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Hoofdfunctie"""
    print("🚀 Kompas UUID Mapping Validatie")
    print("-" * 40)
    
    # Database connectie
    try:
        conn = get_db_connection()
        print("✅ Database verbinding OK")
    except Exception as e:
        print(f"❌ Database fout: {e}")
        sys.exit(1)
    
    try:
        # Haal data op
        print("\n📥 Data ophalen...")
        configs = get_kompas_configs(conn)
        print(f"   • {len(configs)} kompas configuraties")
        
        kompas_ind = get_kompas_indicators(conn)
        print(f"   • {len(kompas_ind)} unieke kompas indicatoren")
        
        dropdown_ind = get_dropdown_indicators(conn)
        print(f"   • {len(dropdown_ind)} dropdown indicatoren")
        
        data_ind = get_data_indicators(conn)
        print(f"   • {len(data_ind)} indicatoren met data")
        
        # Analyse
        print("\n🔬 Analyseren...")
        analysis = analyze_mapping(kompas_ind, dropdown_ind, data_ind)
        
        # Console output
        print_console_summary(analysis, kompas_ind)
        
        # Genereer rapport
        report = generate_report(configs, kompas_ind, dropdown_ind, data_ind, analysis)
        
        # Schrijf naar bestand
        output_dir = Path(__file__).parent.parent / 'ontwikkelaarsvragen'
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"uuid_mapping_rapport_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        output_file.write_text(report, encoding='utf-8')
        
        print(f"\n📄 Rapport opgeslagen: {output_file}")
        print("\n✅ Validatie voltooid!")
        
    except Exception as e:
        print(f"❌ Fout tijdens validatie: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
