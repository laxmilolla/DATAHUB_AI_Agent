#!/usr/bin/env python3
"""Analyze the DOM tree structure to find parent-child relationships"""
import json
import sys

file_path = "/tmp/explore_page_new.json"
if len(sys.argv) > 1:
    file_path = sys.argv[1]

with open(file_path, 'r') as f:
    data = json.load(f)

tree_structure = data.get("tree_structure", {})
elements = data.get("elements", {})

print("=" * 80)
print("ANALYZING DOM TREE STRUCTURE FOR PARENT-CHILD RELATIONSHIPS")
print("=" * 80)

def find_in_tree(node, target_text="Diagnosis", depth=0, path=[]):
    """Recursively search tree for elements containing target text"""
    results = []
    
    node_text = node.get('text', '').strip()
    node_tag = node.get('tag', '')
    node_role = node.get('role', '')
    node_id = node.get('id', '')
    
    # Check if this node matches
    if target_text.lower() in node_text.lower() or target_text.lower() in (node_id or "").lower():
        results.append({
            'path': path + [node_text[:50]],
            'depth': depth,
            'tag': node_tag,
            'role': node_role,
            'id': node_id,
            'text': node_text[:100],
            'children_count': len(node.get('children', []))
        })
    
    # Recursively search children
    for i, child in enumerate(node.get('children', [])):
        child_results = find_in_tree(child, target_text, depth + 1, path + [f"{node_text[:30]}..."])
        results.extend(child_results)
    
    return results

print("\n1. SEARCHING FOR 'Diagnosis' IN DOM TREE:")
print("-" * 80)
diagnosis_nodes = find_in_tree(tree_structure, "Diagnosis")
print(f"Found {len(diagnosis_nodes)} nodes with 'Diagnosis':\n")
for i, node in enumerate(diagnosis_nodes[:5]):
    print(f"  {i+1}. Depth: {node['depth']}, Tag: {node['tag']}, Role: {node['role']}")
    print(f"     Text: {node['text'][:70]}")
    print(f"     Children: {node['children_count']}")
    print(f"     Path: {' > '.join(node['path'][-3:])}")
    print()

print("\n2. CHECKING ELEMENTS REGISTRY:")
print("-" * 80)
diag_elements = [(n, e) for n, e in elements.items() if "Diagnosis" in n]
print(f"Found {len(diag_elements)} elements with 'Diagnosis' in name")
for name, elem in diag_elements[:3]:
    print(f"\n  {name}")
    print(f"    Depth: {elem.get('depth')}")
    print(f"    Parent ID: {elem.get('parent_id')}")
    print(f"    Parent Name: {elem.get('parent_name')}")

print("\n3. ANALYZING DOM TREE DEPTH STRUCTURE:")
print("-" * 80)
def count_by_depth(node, depth=0, counts={}):
    counts[depth] = counts.get(depth, 0) + 1
    for child in node.get('children', []):
        count_by_depth(child, depth + 1, counts)
    return counts

depth_counts = count_by_depth(tree_structure)
print("Elements by depth:")
for depth in sorted(depth_counts.keys())[:15]:
    print(f"  Depth {depth}: {depth_counts[depth]} elements")

print("\n4. CHECKING IF WE CAN INFER RELATIONSHIPS FROM DEPTH:")
print("-" * 80)
print("Diagnosis accordion depth: 14")
print("Looking for checkboxes/buttons at depth 15-18 that might be children...")

# Find elements at depth 15-18 that might be children of Diagnosis
potential_children = [(n, e) for n, e in elements.items() 
                     if e.get('depth', 0) >= 15 and e.get('depth', 0) <= 18 
                     and e.get('type') in ['checkbox', 'button']]
print(f"Found {len(potential_children)} potential children at depth 15-18")
for name, elem in potential_children[:5]:
    print(f"  {name[:60]} (depth: {elem.get('depth')})")



