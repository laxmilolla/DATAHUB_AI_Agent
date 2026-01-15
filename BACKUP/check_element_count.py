#!/usr/bin/env python3
import json
import sys
from collections import Counter

file_path = "/home/ubuntu/DATAHUB_AI_Agent/element_maps/ccdi.cancer.gov/explore_page.json"
if len(sys.argv) > 1:
    file_path = sys.argv[1]

with open(file_path, 'r') as f:
    data = json.load(f)

elements = data.get("elements", {})
print("=" * 80)
print("ELEMENT COUNT ANALYSIS")
print("=" * 80)
print(f"\nTotal elements in registry: {len(elements)}")
print(f"Parser type: {data.get('parser_type', 'unknown')}")
print(f"Parsed at: {data.get('parsed_at', 'unknown')[:19] if data.get('parsed_at') else 'unknown'}")

# Count by type
types = Counter([e.get("type", "unknown") for e in elements.values()])
print(f"\nElements by type:")
for t, count in sorted(types.items()):
    print(f"  {t}: {count}")

# Check if elements are being filtered
print(f"\nTotal relationships: {len(data.get('parent_child_relationships', {}))}")






