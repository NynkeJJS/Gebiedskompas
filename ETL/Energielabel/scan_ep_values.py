#!/usr/bin/env python3
"""
Scan een groter deel van de XML om unieke waarden te vinden voor Status, SoortOpname, Berekeningstype.
Doel: Onderscheid vinden tussen Definitief en Voorlopig.
"""
import xml.etree.ElementTree as ET
import os
from collections import defaultdict

xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data/ep-online/extracted_v20260202_v4_xml/v20260202_v4_xml.xml')

print(f"Scanning: {xml_path}")

context = ET.iterparse(xml_path, events=('end',))
count = 0
uniques = defaultdict(set)
fields_to_check = ['Status', 'SoortOpname', 'Berekeningstype', 'Energieklasse', 'IsVoorlopig', 'LabelType']

for event, elem in context:
    if 'Pandcertificaat' in elem.tag:
        count += 1
        
        for child in elem:
            tag = child.tag.split('}')[-1]
            if tag in fields_to_check:
                uniques[tag].add(child.text)
            
            # Check of er een expliciet 'Voorlopig' veld is dat we gemist hebben
            if 'voorlopig' in tag.lower():
                uniques['MOGELIJK_VOORLOPIG_VELD'].add(tag)
        
        if count % 100000 == 0:
            print(f"Scanned {count} records...")
        
        if count >= 500000: # Scan 500k records
            break
        
        elem.clear()

print(f"\n=== RESULTATEN (na {count} records) ===")
for field, values in uniques.items():
    print(f"\nField: {field}")
    for v in sorted(list(values))[:50]: # Max 50 waarden tonen
        print(f"  - {v}")
