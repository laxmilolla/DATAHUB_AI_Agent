#!/usr/bin/env python3
"""
CLI tool to parse HTML and create element maps
Usage: python create_element_map.py --html <file_or_string> --url <page_url>
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.html_parser import parse_html_to_element_map
from utils.element_registry import get_registry


def main():
    parser = argparse.ArgumentParser(description='Parse HTML and create element map')
    parser.add_argument('--html', required=True, help='HTML file path or HTML string')
    parser.add_argument('--url', required=True, help='Page URL (e.g., https://caninecommons.cancer.gov/#/explore)')
    parser.add_argument('--page', help='Page name (auto-detected if not provided)')
    parser.add_argument('--output', help='Output JSON file (optional, saves to element_maps/ by default)')
    parser.add_argument('--print', action='store_true', help='Print parsed elements to console')
    
    args = parser.parse_args()
    
    # Read HTML
    html_content = args.html
    if Path(html_content).exists():
        print(f"📄 Reading HTML from file: {html_content}")
        with open(html_content, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        print(f"📄 Using HTML string provided")
    
    # Parse HTML
    print(f"🔍 Parsing HTML for URL: {args.url}")
    element_map = parse_html_to_element_map(html_content, args.url)
    
    # Override page name if provided
    if args.page:
        element_map["page"] = args.page
    
    # Print summary
    print(f"\n✅ Parsed {len(element_map['elements'])} elements:")
    print(f"   - Buttons: {sum(1 for e in element_map['elements'].values() if e['type'] == 'button')}")
    print(f"   - Links: {sum(1 for e in element_map['elements'].values() if e['type'] == 'link')}")
    print(f"   - Accordions: {sum(1 for e in element_map['elements'].values() if e['type'] == 'accordion')}")
    print(f"   - Checkboxes: {sum(1 for e in element_map['elements'].values() if e['type'] == 'checkbox')}")
    print(f"   - Inputs: {sum(1 for e in element_map['elements'].values() if e['type'] == 'input')}")
    print(f"   - Dropdowns: {sum(1 for e in element_map['elements'].values() if e['type'] == 'select')}")
    print(f"   - Tables: {sum(1 for e in element_map['elements'].values() if e['type'] == 'table')}")
    
    # Print elements if requested
    if args.print:
        print(f"\n📋 Element Details:")
        for name, elem in element_map['elements'].items():
            print(f"\n  • {name}")
            print(f"    Type: {elem['type']}")
            print(f"    Selector: {elem['selector']}")
            if elem.get('alternatives'):
                print(f"    Alternatives: {', '.join(elem['alternatives'][:2])}")
    
    # Save to file
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(element_map, f, indent=2)
        print(f"\n💾 Saved to: {output_path}")
    else:
        # Save using registry
        registry = get_registry()
        domain = args.url.replace('https://', '').replace('http://', '').split('/')[0]
        page = element_map["page"]
        registry.save_map(domain, page, element_map)
        map_path = registry.get_map_path(domain, page)
        print(f"\n💾 Saved to: {map_path}")
    
    # Create baseline
    if not args.output:
        print(f"\n📸 Creating baseline version...")
        registry.create_baseline(domain, page)
    
    print(f"\n🎉 Done! Element map ready for use.")
    print(f"\n💡 Tip: Commit this to Git for version tracking!")


if __name__ == "__main__":
    main()
