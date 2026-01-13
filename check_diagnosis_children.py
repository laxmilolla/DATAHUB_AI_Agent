#!/usr/bin/env python3
import json
import sys

# Read the registry file
file_path = "/home/ubuntu/DATAHUB_AI_Agent/element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json"
if len(sys.argv) > 1:
    file_path = sys.argv[1]

with open(file_path, 'r') as f:
    data = json.load(f)

elements = data.get("elements", {})
relationships = data.get("parent_child_relationships", {})

print("=" * 80)
print("DIAGNOSIS ELEMENTS AND CHILDREN")
print("=" * 80)

# Find all elements with "Diagnosis" in name
diag_elements = [(n, e) for n, e in elements.items() if "Diagnosis" in n]
print(f"\nFound {len(diag_elements)} elements with 'Diagnosis' in name:\n")
for name, elem in diag_elements:
    print(f"  {name}")
    print(f"    Type: {elem.get('type')}")
    print(f"    Parent Name: {elem.get('parent_name', 'N/A')}")
    print(f"    Depth: {elem.get('depth', 'N/A')}")

# Find all children of Diagnosis
print("\n" + "=" * 80)
print("CHILDREN OF DIAGNOSIS (by parent_name)")
print("=" * 80)

diag_children = [(n, e) for n, e in elements.items() 
                 if e.get("parent_name") and "Diagnosis" in e.get("parent_name", "")]
print(f"\nFound {len(diag_children)} children of Diagnosis:\n")
for name, elem in diag_children:
    print(f"  {name}")
    print(f"    Type: {elem.get('type')}")
    print(f"    Parent: {elem.get('parent_name')}")

# Check relationships map
print("\n" + "=" * 80)
print("PARENT-CHILD RELATIONSHIPS MAP")
print("=" * 80)

diag_parents_in_rels = [p for p in relationships.keys() if "Diagnosis" in p]
print(f"\nFound {len(diag_parents_in_rels)} Diagnosis parents in relationships map:\n")
for parent in diag_parents_in_rels:
    children = relationships.get(parent, [])
    print(f"  {parent}")
    print(f"    Children ({len(children)}):")
    for child in children[:20]:  # Show first 20
        print(f"      - {child}")
    if len(children) > 20:
        print(f"      ... and {len(children) - 20} more")






