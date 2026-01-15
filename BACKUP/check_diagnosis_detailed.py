#!/usr/bin/env python3
import json
import sys

file_path = "/home/ubuntu/DATAHUB_AI_Agent/element_maps/ccdi.cancer.gov/explore_page.json"
if len(sys.argv) > 1:
    file_path = sys.argv[1]

with open(file_path, 'r') as f:
    data = json.load(f)

elements = data.get("elements", {})
relationships = data.get("parent_child_relationships", {})

print("=" * 80)
print("DETAILED DIAGNOSIS ANALYSIS")
print("=" * 80)

# Find the Diagnosis accordion element
diag_elem = None
for name, elem in elements.items():
    if name == "Diagnosis accordion" or (name.startswith("Diagnosis") and elem.get("type") == "accordion" and "Anatomic" not in name and "Category" not in name and "Age" not in name):
        diag_elem = (name, elem)
        break

if diag_elem:
    name, elem = diag_elem
    print(f"\nFound Diagnosis element: {name}")
    print(f"  ID: {elem.get('id')}")
    print(f"  Type: {elem.get('type')}")
    print(f"  Depth: {elem.get('depth')}")
    print(f"  Parent ID: {elem.get('parent_id')}")
    print(f"  Parent Name: {elem.get('parent_name')}")
    
    # Check relationships
    if name in relationships:
        children = relationships[name]
        print(f"\n  Children in relationships map: {len(children)}")
        for child in children:
            print(f"    - {child}")
    else:
        print(f"\n  NOT FOUND in relationships map")

# Check all elements that should be children
print("\n" + "=" * 80)
print("ELEMENTS THAT SHOULD BE CHILDREN OF DIAGNOSIS")
print("=" * 80)

# Find elements with Diagnosis in parent_name
diag_children = [(n, e) for n, e in elements.items() 
                 if e.get("parent_name") and "Diagnosis" in e.get("parent_name", "")
                 and "Diagnosis Anatomic Site" not in e.get("parent_name", "")
                 and "Diagnosis Category" not in e.get("parent_name", "")
                 and "Age at Diagnosis" not in e.get("parent_name", "")]
print(f"\nTotal: {len(diag_children)}")
for name, elem in diag_children:
    print(f"  {name}")
    print(f"    Parent: {elem.get('parent_name')}")
    print(f"    Type: {elem.get('type')}")
    print(f"    Depth: {elem.get('depth')}")

# Check for elements at similar depth that might be missing
print("\n" + "=" * 80)
print("CHECKING FOR POTENTIALLY MISSING CHILDREN")
print("=" * 80)
# Find checkboxes/buttons at depth 16-19 without parent_name
potential_missing = [(n, e) for n, e in elements.items() 
                     if e.get("depth", 0) >= 16 and e.get("depth", 0) <= 19
                     and e.get("type") in ["checkbox", "button"]
                     and not e.get("parent_name")]
print(f"Found {len(potential_missing)} elements at depth 16-19 without parent_name")
for name, elem in potential_missing[:15]:
    print(f"  {name[:70]}")
    print(f"    Type: {elem.get('type')}, Depth: {elem.get('depth')}, Text: {elem.get('text', '')[:50]}")

# Count all checkboxes
print("\n" + "=" * 80)
print("ALL CHECKBOXES IN REGISTRY")
print("=" * 80)
checkboxes = [(n, e) for n, e in elements.items() if e.get("type") == "checkbox"]
print(f"Total checkboxes: {len(checkboxes)}")
for name, elem in checkboxes[:30]:
    print(f"  {name[:70]}")
    print(f"    Parent: {elem.get('parent_name')}")
    print(f"    Depth: {elem.get('depth')}")

