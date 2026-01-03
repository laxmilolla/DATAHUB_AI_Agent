#!/usr/bin/env python3
"""
🧪 Element Matching Test Utility
================================

Test the enhanced element matching logic WITHOUT deploying to server.
Perfect for developers to validate stories and debug element selection issues.

Usage:
    python test_enhanced_matching.py                    # Run default test story
    python test_enhanced_matching.py --story "..."      # Test custom story
    python test_enhanced_matching.py --step 5 "diagnosis"  # Test specific step
    python test_enhanced_matching.py --registry path/to/registry.json  # Use specific registry

Author: AI Agent QA Team
Date: January 2, 2026
"""
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Default test story (the problematic Diagnosis case)
DEFAULT_TEST_STORY = """
Step 1: Navigate to https://clinicalcommons.ccdi.cancer.gov/explore
Step 2: Click Continue button to dismiss popup
Step 3: Verify page loaded
Step 4: In left sidebar, click Diagnosis to expand
Step 5: In the expanded Diagnosis section, click on the nested Diagnosis accordion to expand it
Step 6: Click the checkbox for Acute leukemia, NOS
Step 7: Verify filter applied
Step 8: In bottom table tabs, click Diagnosis tab
"""

def parse_story_metadata(story: str):
    """Parse story once and extract metadata for each step"""
    print("=" * 80)
    print("📖 PARSING STORY METADATA")
    print("=" * 80)
    
    parsed_steps = {}
    lines = story.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or not line.startswith('Step'):
            continue
        
        # Extract step number
        step_match = re.match(r'Step\s+(\d+)[\.:)]?\s*(.+)', line, re.IGNORECASE)
        if not step_match:
            continue
        
        step_num = int(step_match.group(1))
        step_text = step_match.group(2).lower()
        
        # Extract metadata from step text
        metadata = {"text": step_text}
        
        # Detect TYPE
        if "tab" in step_text:
            metadata["type"] = "tab"
        elif "accordion" in step_text or "expand" in step_text:
            metadata["type"] = "accordion"
        elif "checkbox" in step_text or "check box" in step_text:
            metadata["type"] = "checkbox"
        elif "button" in step_text:
            metadata["type"] = "button"
        
        # Detect LOCATION
        if "sidebar" in step_text or "filter panel" in step_text or "left" in step_text:
            metadata["location"] = "sidebar"
        elif "table" in step_text or "bottom" in step_text or "main" in step_text or "content" in step_text:
            metadata["location"] = "table"
        
        # Detect PARENT/NESTED
        if "nested" in step_text or "inner" in step_text or "within" in step_text or "inside" in step_text:
            metadata["nested"] = True
            
        # Extract PARENT HINT from context
        parent_patterns = [
            r'in (?:the )?(?:expanded )?(\w+)(?: section| accordion| area)?',
            r'inside (?:the )?(\w+)',
            r'within (?:the )?(\w+)',
            r'under (?:the )?(\w+)'
        ]
        for pattern in parent_patterns:
            match = re.search(pattern, step_text)
            if match:
                parent_hint = match.group(1).lower()
                if parent_hint not in ['the', 'a', 'an', 'this', 'that', 'expanded', 'collapsed']:
                    metadata["parent_hint"] = parent_hint
                    break
        
        # Detect DEPTH preference
        if "top" in step_text or "main" in step_text or "primary" in step_text:
            metadata["prefer_depth"] = 0
        elif "first level" in step_text:
            metadata["prefer_depth"] = 1
        elif "second level" in step_text:
            metadata["prefer_depth"] = 2
        
        parsed_steps[step_num] = metadata
        print(f"\nStep {step_num}: {line}")
        print(f"  Metadata: {metadata}")
    
    return parsed_steps


def match_elements(element_name: str, step_metadata: dict, registry: dict):
    """Simulate the enhanced matching logic"""
    print("\n" + "=" * 80)
    print(f"🔍 MATCHING: '{element_name}'")
    print("=" * 80)
    print(f"Step metadata: {step_metadata}")
    
    elements = registry.get('elements', {})
    
    # Extract clean text
    clean_text = element_name.lower()
    if clean_text.startswith('text='):
        clean_text = clean_text[5:]
    clean_text = clean_text.strip()
    
    print(f"\nSearching for: '{clean_text}'")
    
    # Find all matching elements by name using word boundaries
    matches = []
    pattern = r'\b' + re.escape(clean_text) + r'\b'
    
    for name, elem in elements.items():
        name_lower = name.lower()
        if re.search(pattern, name_lower):
            matches.append((name, elem))
    
    print(f"\n✅ Found {len(matches)} name matches:")
    for name, elem in matches:
        depth = elem.get('depth', 0)
        parent = elem.get('parent_name') or 'None'
        print(f"  - {name[:80]}")
        parent_display = parent[:50] if parent and parent != 'None' else 'None'
        print(f"    depth={depth}, parent={parent_display}")
    
    if not matches:
        print("❌ No matches found!")
        return None
    
    # Filter by TYPE
    if "type" in step_metadata:
        required_type = step_metadata["type"]
        temp_filtered = [
            (name, elem) for name, elem in matches
            if elem.get("type", "").lower() == required_type
        ]
        if temp_filtered:
            matches = temp_filtered
            print(f"\n📋 After type filter ({required_type}): {len(matches)} matches")
    
    # Filter by LOCATION
    if "location" in step_metadata:
        required_location = step_metadata["location"]
        temp_filtered = [
            (name, elem) for name, elem in matches
            if required_location in elem.get("location", "").lower()
        ]
        if temp_filtered:
            matches = temp_filtered
            print(f"\n📍 After location filter ({required_location}): {len(matches)} matches")
    
    # Filter by NESTED
    if "nested" in step_metadata and step_metadata["nested"]:
        temp_filtered = [
            (name, elem) for name, elem in matches
            if elem.get("parent_name") and elem.get("parent_name") != "None"
        ]
        if temp_filtered:
            matches = temp_filtered
            print(f"\n🔗 After nested filter: {len(matches)} matches (only nested)")
    else:
        # Prefer top-level
        temp_filtered = [
            (name, elem) for name, elem in matches
            if not elem.get("parent_name") or elem.get("parent_name") == "None"
        ]
        if temp_filtered:
            matches = temp_filtered
            print(f"\n🔗 After top-level filter: {len(matches)} matches (only top-level)")
    
    # Filter by PARENT HINT
    if "parent_hint" in step_metadata:
        parent_hint = step_metadata["parent_hint"]
        temp_filtered = [
            (name, elem) for name, elem in matches
            if parent_hint in (elem.get("parent_text") or "").lower() or
               parent_hint in (elem.get("parent_id") or "").lower()
        ]
        if temp_filtered:
            matches = temp_filtered
            print(f"\n👨‍👧 After parent hint filter ('{parent_hint}'): {len(matches)} matches")
    
    # Filter by DEPTH
    if "prefer_depth" in step_metadata:
        prefer_depth = step_metadata["prefer_depth"]
        temp_filtered = [
            (name, elem) for name, elem in matches
            if elem.get("depth", 0) == prefer_depth
        ]
        if temp_filtered:
            matches = temp_filtered
            print(f"\n📊 After depth filter (depth={prefer_depth}): {len(matches)} matches")
    
    # Pick best match
    def extract_element_name(desc):
        parts = desc.lower().split()
        for word in ['accordion', 'tab', 'button', 'checkbox', 'nested', 'in', 'left', 'sidebar', 'filter', 'panel']:
            if word in parts:
                parts.remove(word)
        return ' '.join(parts[:2])
    
    def match_score(item):
        name, elem = item
        elem_name = extract_element_name(name)
        elem_depth = elem.get("depth", 0)
        
        if elem_name == clean_text:
            return (0, elem_depth, len(name))
        if clean_text in elem_name or elem_name in clean_text:
            return (1, elem_depth, len(name))
        return (2, elem_depth, len(name))
    
    matches = sorted(matches, key=match_score)
    
    print(f"\n🏆 FINAL MATCHES (sorted by score):")
    for i, (name, elem) in enumerate(matches[:5], 1):
        depth = elem.get('depth', 0)
        parent = elem.get('parent_name') or 'None'
        selector = elem.get('selector', 'N/A')
        parent_display = parent[:50] if parent and parent != 'None' else 'None'
        print(f"\n  {i}. {name}")
        print(f"     depth={depth}, parent={parent_display}")
        print(f"     selector={selector}")
    
    if matches:
        winner_name, winner_elem = matches[0]
        print(f"\n✅ SELECTED: {winner_name}")
        print(f"   Selector: {winner_elem.get('selector')}")
        return winner_elem
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description='🧪 Test element matching logic locally (no server deployment needed)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default test story
  python test_enhanced_matching.py
  
  # Test with custom story
  python test_enhanced_matching.py --story "Step 1: Click diagnosis tab"
  
  # Test specific step and element
  python test_enhanced_matching.py --step 5 --element "diagnosis" --story "..."
  
  # Use local registry
  python test_enhanced_matching.py --registry element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json
  
  # Use server registry (default)
  python test_enhanced_matching.py --server
        """
    )
    
    parser.add_argument('--story', '-s', type=str, help='Custom test story (multi-line string)')
    parser.add_argument('--step', type=int, help='Test only specific step number')
    parser.add_argument('--element', '-e', type=str, help='Element name to test (use with --step)')
    parser.add_argument('--registry', '-r', type=str, help='Path to element registry JSON file')
    parser.add_argument('--server', action='store_true', help='Use server registry (downloads from server)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed matching process')
    
    args = parser.parse_args()
    
    # Determine registry path
    if args.server:
        print("📥 Downloading registry from server...")
        import subprocess
        result = subprocess.run([
            'scp', '-i', '~/Downloads/ai-crdc-hub-key.pem',
            'ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json',
            '/tmp/server_explore_page.json'
        ], capture_output=True)
        if result.returncode != 0:
            print("❌ Failed to download from server")
            return
        registry_path = Path("/tmp/server_explore_page.json")
    elif args.registry:
        registry_path = Path(args.registry)
    else:
        # Default: use server registry cached in /tmp
        registry_path = Path("/tmp/server_explore_page.json")
        if not registry_path.exists():
            print("⚠️  No cached server registry found. Use --server to download or --registry to specify local file.")
            print("   Trying local registry...")
            registry_path = Path("element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json")
    
    if not registry_path.exists():
        print(f"❌ Registry not found: {registry_path}")
        print("   Use --server to download from server or --registry to specify path")
        return
    
    print("\n" + "=" * 80)
    print("🚀 ELEMENT MATCHING TEST UTILITY")
    print("=" * 80)
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    print(f"\n✅ Loaded registry: {registry_path}")
    print(f"   {len(registry.get('elements', {}))} elements")
    
    # Use custom story or default
    test_story = args.story if args.story else DEFAULT_TEST_STORY
    
    # Parse story
    parsed_steps = parse_story_metadata(test_story)
    
    # Single step test or full story test
    if args.step and args.element:
        print("\n\n" + "=" * 80)
        print(f"🧪 SINGLE STEP TEST")
        print("=" * 80)
        
        step_metadata = parsed_steps.get(args.step, {})
        result = match_elements(args.element, step_metadata, registry)
        
        if result:
            print(f"\n✅ SUCCESS: Found element")
            print(f"   Selector: {result.get('selector')}")
        else:
            print(f"\n❌ FAILED: No element found")
    
    else:
        # Default test cases
        test_cases = [
            (4, "diagnosis", "Should match TOP-LEVEL Diagnosis accordion"),
            (5, "diagnosis", "Should match NESTED Diagnosis accordion (inside Diagnosis parent)"),
            (6, "acute leukemia, nos", "Should match checkbox"),
            (8, "diagnosis", "Should match Diagnosis TAB (not accordion)")
        ]
        
        print("\n\n" + "=" * 80)
        print("🧪 RUNNING FULL TEST SUITE")
        print("=" * 80)
        
        passed = 0
        failed = 0
        
        for step_num, element_name, description in test_cases:
            if step_num not in parsed_steps:
                continue
                
            print(f"\n\n{'=' * 80}")
            print(f"TEST CASE: Step {step_num} - {description}")
            print("=" * 80)
            
            step_metadata = parsed_steps.get(step_num, {})
            result = match_elements(element_name, step_metadata, registry)
            
            if result:
                print(f"\n✅ PASS")
                passed += 1
            else:
                print(f"\n❌ FAIL")
                failed += 1
        
        print("\n\n" + "=" * 80)
        print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
        print("=" * 80)
    
    print("\n💡 TIP: Test changes locally before deploying to server!")


if __name__ == "__main__":
    main()

