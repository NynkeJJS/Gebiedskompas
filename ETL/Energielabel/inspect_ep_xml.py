#!/usr/bin/env python3
"""Snel de XML structuur bekijken: welke velden zitten in een Pandcertificaat?"""
import xml.etree.ElementTree as ET
import os

xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data/ep-online/extracted_v20260202_v4_xml/v20260202_v4_xml.xml')

print(f"Inspecting: {xml_path}")
print(f"File size: {os.path.getsize(xml_path) / (1024**3):.1f} GB")
print()

context = ET.iterparse(xml_path, events=('end',))
count = 0
all_tags = set()
sample_records = []

for event, elem in context:
    if 'Pandcertificaat' in elem.tag:
        record = {}
        for child in elem:
            tag = child.tag.split('}')[-1]
            all_tags.add(tag)
            record[tag] = child.text
        
        sample_records.append(record)
        count += 1
        
        if count >= 50:  # 50 records is genoeg
            break
        
        elem.clear()

print(f"=== ALLE VELDEN IN Pandcertificaat ({len(all_tags)}) ===")
for tag in sorted(all_tags):
    print(f"  - {tag}")

print(f"\n=== SAMPLE RECORDS (eerste 5) ===")
for i, rec in enumerate(sample_records[:5]):
    print(f"\n--- Record {i+1} ---")
    for k, v in sorted(rec.items()):
        print(f"  {k:30s} = {v}")

# Check unieke waarden per veld
print(f"\n=== UNIEKE WAARDEN PER VELD (eerste 50 records) ===")
for tag in sorted(all_tags):
    values = set(r.get(tag) for r in sample_records if r.get(tag))
    if len(values) <= 20:
        print(f"  {tag}: {sorted(values)}")
    else:
        print(f"  {tag}: {len(values)} unieke waarden (sample: {sorted(list(values))[:5]})")

print(f"\n✅ Klaar")
