#!/usr/bin/env python3
"""
CLI tool to compare element maps for regression testing
Usage: python compare_maps.py --domain <domain> --page <page> [--baseline <version>]
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.element_registry import get_registry


def print_comparison_report(comparison: dict):
    """Pretty print comparison results"""
    
    print("\n" + "="*70)
    print(" REGRESSION TEST REPORT - Element Map Comparison")
    print("="*70)
    
    print(f"\n📊 VERSIONS:")
    print(f"   Baseline: v{comparison.get('baseline_version', 'unknown')}")
    print(f"   Current:  v{comparison.get('current_version', 'unknown')}")
    
    print(f"\n🎯 RISK LEVEL: {comparison.get('risk_level', 'UNKNOWN')}")
    print(f"   Breaking Changes: {comparison.get('breaking_changes', 0)}")
    
    # Changed elements
    changed = comparison.get('changed', [])
    if changed:
        print(f"\n❌ CHANGED ({len(changed)}):")
        for item in changed:
            print(f"   • {item['name']}")
            print(f"     Before: {item['old_selector']}")
            print(f"     After:  {item['new_selector']}")
            print(f"     ⚠️  Tests using this element will FAIL")
    
    # Removed elements
    removed = comparison.get('removed', [])
    if removed:
        print(f"\n🗑️  REMOVED ({len(removed)}):")
        for item in removed:
            print(f"   • {item['name']}")
            print(f"     Selector: {item['selector']}")
            print(f"     ⚠️  Tests using this element will FAIL")
    
    # Added elements
    added = comparison.get('added', [])
    if added:
        print(f"\n✅ ADDED ({len(added)}):")
        for item in added:
            print(f"   • {item['name']}")
            print(f"     Selector: {item['selector']}")
            print(f"     Source: {item['source']}")
    
    # Unchanged elements
    unchanged = comparison.get('unchanged', [])
    if unchanged:
        print(f"\n✓  UNCHANGED ({len(unchanged)}):")
        for name in unchanged[:5]:  # Show first 5
            print(f"   • {name}")
        if len(unchanged) > 5:
            print(f"   ... and {len(unchanged) - 5} more")
    
    # Recommendation
    print("\n" + "="*70)
    if comparison.get('breaking_changes', 0) > 0:
        print(" ⚠️  ACTION REQUIRED:")
        print(" UI changes detected that will break tests.")
        print(" Review changes and update baseline if approved:")
        print(" $ git commit element_maps/")
    else:
        print(" ✅ ALL GOOD:")
        print(" No breaking changes detected.")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Compare element maps for regression testing')
    parser.add_argument('--domain', required=True, help='Domain (e.g., caninecommons.cancer.gov)')
    parser.add_argument('--page', required=True, help='Page name (e.g., explore)')
    parser.add_argument('--baseline', help='Baseline version (e.g., 1.0). If omitted, uses current as baseline.')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    registry = get_registry()
    
    print(f"📊 Comparing element maps...")
    print(f"   Domain: {args.domain}")
    print(f"   Page: {args.page}")
    
    comparison = registry.compare_maps(args.domain, args.page, args.baseline)
    
    if 'error' in comparison:
        print(f"\n❌ Error: {comparison['error']}")
        sys.exit(1)
    
    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        print_comparison_report(comparison)
    
    # Exit with non-zero if breaking changes
    if comparison.get('breaking_changes', 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
