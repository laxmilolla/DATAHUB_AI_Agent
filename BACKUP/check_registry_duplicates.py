#!/usr/bin/env python3
"""
Check for duplicates in JSON registry files
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

def check_registry_file(file_path: Path) -> Dict:
    """Check a single registry file for duplicates"""
    issues = {
        'duplicate_selectors': [],
        'duplicate_xpaths': [],
        'duplicate_element_ids': [],
        'duplicate_names': [],
        'conflicting_contexts': []
    }
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        elements = data.get('elements', {})
        id_index = data.get('id_index', {})
        
        # Track selectors, xpaths, element_ids, names
        selector_map = defaultdict(list)
        xpath_map = defaultdict(list)
        element_id_map = defaultdict(list)
        name_map = defaultdict(list)
        
        for name, element in elements.items():
            selector = element.get('selector', '')
            xpath = element.get('xpath', '')
            element_id = element.get('element_id', '')
            context = element.get('context', 'main-page')
            
            # Track by selector
            if selector:
                selector_map[selector].append((name, context))
            
            # Track by xpath
            if xpath:
                xpath_map[xpath].append((name, context))
            
            # Track by element_id
            if element_id:
                element_id_map[element_id].append((name, context))
            
            # Track by name (case-insensitive)
            name_lower = name.lower()
            name_map[name_lower].append((name, context))
        
        # Check for duplicates
        for selector, entries in selector_map.items():
            if len(entries) > 1:
                issues['duplicate_selectors'].append({
                    'selector': selector,
                    'entries': entries
                })
        
        for xpath, entries in xpath_map.items():
            if len(entries) > 1:
                issues['duplicate_xpaths'].append({
                    'xpath': xpath,
                    'entries': entries
                })
        
        for element_id, entries in element_id_map.items():
            if len(entries) > 1:
                issues['duplicate_element_ids'].append({
                    'element_id': element_id,
                    'entries': entries
                })
        
        # Check for duplicate names (case-insensitive)
        for name_lower, entries in name_map.items():
            if len(entries) > 1:
                # Check if they're actually different (case-sensitive)
                unique_names = set(e[0] for e in entries)
                if len(unique_names) > 1:
                    issues['duplicate_names'].append({
                        'name': name_lower,
                        'entries': entries
                    })
        
        # Check for conflicting contexts (same name, different contexts)
        for name_lower, entries in name_map.items():
            contexts = set(e[1] for e in entries)
            if len(contexts) > 1:
                issues['conflicting_contexts'].append({
                    'name': name_lower,
                    'entries': entries,
                    'contexts': list(contexts)
                })
        
        # Check id_index for duplicates
        id_index_values = list(id_index.values())
        duplicate_ids_in_index = [v for v in id_index_values if id_index_values.count(v) > 1]
        if duplicate_ids_in_index:
            issues['duplicate_element_ids'].append({
                'element_id': 'in id_index',
                'entries': duplicate_ids_in_index
            })
        
    except Exception as e:
        issues['error'] = str(e)
    
    return issues

def check_cross_file_duplicates(element_maps_dir: Path) -> Dict:
    """Check for duplicates across different registry files (e.g., main page vs modal)"""
    issues = {
        'cross_file_duplicate_selectors': [],
        'cross_file_duplicate_xpaths': [],
        'cross_file_duplicate_names': []
    }
    
    # Load all registries
    all_registries = {}
    for json_file in element_maps_dir.rglob('*.json'):
        if 'backup' in json_file.name or 'deleted' in json_file.name or 'versions' in json_file.parts:
            continue
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            relative_path = str(json_file.relative_to(element_maps_dir))
            all_registries[relative_path] = data.get('elements', {})
        except Exception as e:
            continue
    
    # Check for duplicates across files
    selector_to_files = defaultdict(list)
    xpath_to_files = defaultdict(list)
    name_to_files = defaultdict(list)
    
    for file_path, elements in all_registries.items():
        for name, element in elements.items():
            selector = element.get('selector', '')
            xpath = element.get('xpath', '')
            
            if selector:
                selector_to_files[selector].append((file_path, name))
            if xpath:
                xpath_to_files[xpath].append((file_path, name))
            
            name_lower = name.lower()
            name_to_files[name_lower].append((file_path, name))
    
    # Find cross-file duplicates
    for selector, entries in selector_to_files.items():
        files = set(e[0] for e in entries)
        if len(files) > 1:
            issues['cross_file_duplicate_selectors'].append({
                'selector': selector,
                'files': list(files),
                'entries': entries
            })
    
    for xpath, entries in xpath_to_files.items():
        files = set(e[0] for e in entries)
        if len(files) > 1:
            issues['cross_file_duplicate_xpaths'].append({
                'xpath': xpath,
                'files': list(files),
                'entries': entries
            })
    
    for name_lower, entries in name_to_files.items():
        files = set(e[0] for e in entries)
        if len(files) > 1:
            issues['cross_file_duplicate_names'].append({
                'name': name_lower,
                'files': list(files),
                'entries': entries
            })
    
    return issues

def main():
    """Check all registry files"""
    element_maps_dir = Path('element_maps')
    
    if not element_maps_dir.exists():
        print("❌ element_maps directory not found")
        return
    
    all_issues = {}
    total_files = 0
    files_with_issues = 0
    
    for json_file in element_maps_dir.rglob('*.json'):
        # Skip backup and deleted files
        if 'backup' in json_file.name or 'deleted' in json_file.name:
            continue
        # Skip versions directory
        if 'versions' in json_file.parts:
            continue
        
        total_files += 1
        relative_path = json_file.relative_to(element_maps_dir)
        
        issues = check_registry_file(json_file)
        
        # Check if there are any issues
        has_issues = any(
            issues.get('duplicate_selectors') or
            issues.get('duplicate_xpaths') or
            issues.get('duplicate_element_ids') or
            issues.get('duplicate_names') or
            issues.get('conflicting_contexts')
        )
        
        if has_issues or 'error' in issues:
            files_with_issues += 1
            all_issues[str(relative_path)] = issues
    
    # Print summary
    print("=" * 80)
    print("REGISTRY DUPLICATES CHECK")
    print("=" * 80)
    print(f"\nTotal registry files checked: {total_files}")
    print(f"Files with issues: {files_with_issues}")
    
    # Check for cross-file duplicates
    print("\n" + "=" * 80)
    print("CHECKING CROSS-FILE DUPLICATES:")
    print("=" * 80)
    cross_file_issues = check_cross_file_duplicates(element_maps_dir)
    
    has_cross_file_issues = any(
        cross_file_issues.get('cross_file_duplicate_selectors') or
        cross_file_issues.get('cross_file_duplicate_xpaths') or
        cross_file_issues.get('cross_file_duplicate_names')
    )
    
    if not all_issues and not has_cross_file_issues:
        print("\n✅ No duplicates found!")
        return
    
    if has_cross_file_issues:
        print("\n⚠️  CROSS-FILE DUPLICATES FOUND:")
        
        if cross_file_issues.get('cross_file_duplicate_selectors'):
            print(f"\n  🔴 Duplicate Selectors Across Files ({len(cross_file_issues['cross_file_duplicate_selectors'])}):")
            for dup in cross_file_issues['cross_file_duplicate_selectors'][:10]:
                print(f"     Selector: {dup['selector']}")
                print(f"       Files: {', '.join(dup['files'])}")
                for file_path, name in dup['entries']:
                    print(f"         - {file_path}: '{name}'")
        
        if cross_file_issues.get('cross_file_duplicate_xpaths'):
            print(f"\n  🔴 Duplicate XPaths Across Files ({len(cross_file_issues['cross_file_duplicate_xpaths'])}):")
            for dup in cross_file_issues['cross_file_duplicate_xpaths'][:10]:
                print(f"     XPath: {dup['xpath'][:80]}...")
                print(f"       Files: {', '.join(dup['files'])}")
                for file_path, name in dup['entries']:
                    print(f"         - {file_path}: '{name}'")
        
        if cross_file_issues.get('cross_file_duplicate_names'):
            print(f"\n  🔴 Duplicate Names Across Files ({len(cross_file_issues['cross_file_duplicate_names'])}):")
            for dup in cross_file_issues['cross_file_duplicate_names'][:10]:
                print(f"     Name: {dup['name']}")
                print(f"       Files: {', '.join(dup['files'])}")
                for file_path, name in dup['entries']:
                    print(f"         - {file_path}: '{name}'")
    
    print("\n" + "=" * 80)
    print("ISSUES FOUND:")
    print("=" * 80)
    
    for file_path, issues in all_issues.items():
        print(f"\n📄 File: {file_path}")
        
        if 'error' in issues:
            print(f"  ❌ Error: {issues['error']}")
            continue
        
        if issues.get('duplicate_selectors'):
            print(f"  ⚠️  Duplicate Selectors ({len(issues['duplicate_selectors'])}):")
            for dup in issues['duplicate_selectors'][:5]:  # Show first 5
                print(f"     Selector: {dup['selector']}")
                for name, context in dup['entries']:
                    print(f"       - '{name}' (context: {context})")
        
        if issues.get('duplicate_xpaths'):
            print(f"  ⚠️  Duplicate XPaths ({len(issues['duplicate_xpaths'])}):")
            for dup in issues['duplicate_xpaths'][:5]:  # Show first 5
                print(f"     XPath: {dup['xpath'][:80]}...")
                for name, context in dup['entries']:
                    print(f"       - '{name}' (context: {context})")
        
        if issues.get('duplicate_element_ids'):
            print(f"  ⚠️  Duplicate Element IDs ({len(issues['duplicate_element_ids'])}):")
            for dup in issues['duplicate_element_ids'][:5]:  # Show first 5
                print(f"     Element ID: {dup['element_id']}")
                for name, context in dup['entries']:
                    print(f"       - '{name}' (context: {context})")
        
        if issues.get('duplicate_names'):
            print(f"  ⚠️  Duplicate Names (case-insensitive) ({len(issues['duplicate_names'])}):")
            for dup in issues['duplicate_names'][:5]:  # Show first 5
                print(f"     Name: {dup['name']}")
                for name, context in dup['entries']:
                    print(f"       - '{name}' (context: {context})")
        
        if issues.get('conflicting_contexts'):
            print(f"  ⚠️  Conflicting Contexts ({len(issues['conflicting_contexts'])}):")
            for dup in issues['conflicting_contexts'][:5]:  # Show first 5
                print(f"     Name: {dup['name']}")
                print(f"       Contexts: {', '.join(dup['contexts'])}")
                for name, context in dup['entries']:
                    print(f"       - '{name}' (context: {context})")

if __name__ == "__main__":
    main()

