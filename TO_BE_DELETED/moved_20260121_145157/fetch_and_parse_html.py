#!/usr/bin/env python3
"""
Fetch HTML from a URL and parse it with the enhanced HTML parser
This is used to populate the registry with rich structural knowledge
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from utils.playwright_tree_parser import parse_with_tree
from utils.element_registry import get_registry


def fetch_html_from_url(url: str) -> str:
    """Fetch HTML from URL using Playwright"""
    print(f"🌐 Fetching HTML from: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to URL
        page.goto(url, wait_until='networkidle')
        
        # Wait for page to fully load
        print(f"⏳ Waiting for page to load...")
        page.wait_for_timeout(3000)
        
        # Dismiss any popups
        try:
            continue_btn = page.locator("text='Continue'").first
            if continue_btn.is_visible(timeout=2000):
                print(f"  ✅ Dismissing Continue popup")
                continue_btn.click()
                page.wait_for_timeout(1000)
        except:
            pass
        
        # Get HTML content
        html = page.content()
        
        browser.close()
    
    print(f"✅ Fetched {len(html):,} characters of HTML")
    return html


async def main_async():
    """Main async function using Playwright-first parser"""
    if len(sys.argv) < 2:
        print("Usage: python fetch_and_parse_html.py <url> [page_name]")
        print("\nExample:")
        print("  python fetch_and_parse_html.py https://clinicalcommons.ccdi.cancer.gov/explore home")
        sys.exit(1)
    
    url = sys.argv[1]
    page_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 80)
    print("🎭 PLAYWRIGHT-FIRST PARSER - Live DOM Analysis")
    print("=" * 80)
    
    print(f"🌐 Opening browser and navigating to: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Set larger viewport to ensure all tabs and elements are visible
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print(f"  📐 Viewport set to 1920x1080 to capture all elements")
        
        # Navigate to URL (with timeout)
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(5000)  # Extra wait for dynamic content
        
        # Dismiss any popups
        try:
            continue_btn = page.locator("text='Continue'").first
            if await continue_btn.is_visible(timeout=2000):
                print(f"  ✅ Dismissing Continue popup")
                await continue_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Parse using tree-based parser (after accordions are already expanded)
        element_map = await parse_with_tree(page)
        
        await browser.close()
    
    # Override page name if provided
    if page_name:
        element_map["page"] = page_name
    
    # Step 3: Print detailed summary
    print(f"\n" + "=" * 80)
    print(f"📊 PARSING RESULTS")
    print("=" * 80)
    
    print(f"\n📈 Total Elements: {len(element_map['elements'])}")
    
    # Count by type
    by_type = {}
    for elem in element_map['elements'].values():
        elem_type = elem.get('type', 'unknown')
        by_type[elem_type] = by_type.get(elem_type, 0) + 1
    
    if by_type:
        print(f"\n🏷️  Elements by Type:")
        for elem_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"   - {elem_type.upper()}: {count}")
    
    relationships = element_map.get('parent_child_relationships', {})
    if relationships:
        print(f"\n🔗 Parent-Child Relationships: {len(relationships)}")
        for parent, children in list(relationships.items())[:5]:
            print(f"   • {parent}")
            for child in children[:3]:
                print(f"     └─ {child}")
    
    # Show some example elements
    print(f"\n💡 Sample Elements (first 10):")
    for idx, (name, elem) in enumerate(list(element_map['elements'].items())[:10]):
        location = elem.get('location', 'unknown')
        elem_type = elem.get('type', 'unknown')
        parent = elem.get('parent_name', None)
        parent_str = f" [child of: {parent.split(' accordion')[0]}]" if parent else ""
        print(f"   {idx+1}. {name}{parent_str}")
        print(f"      Type: {elem_type}, Location: {location}")
    
    # Step 4: Save to registry
    print(f"\n" + "=" * 80)
    print(f"💾 SAVING TO REGISTRY")
    print("=" * 80)
    
    registry = get_registry()
    domain = url.replace('https://', '').replace('http://', '').split('/')[0]
    page = element_map["page"]
    
    registry.save_map(domain, page, element_map)
    map_path = registry.get_map_path(domain, page)
    
    print(f"\n✅ Saved to: {map_path}")
    print(f"📂 Domain: {domain}")
    print(f"📄 Page: {page}")
    
    # Step 5: Create baseline
    print(f"\n📸 Creating baseline version...")
    baseline_path = registry.create_baseline(domain, page)
    
    print(f"\n" + "=" * 80)
    print(f"🎉 SUCCESS! Registry populated with rich metadata!")
    print("=" * 80)
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Commit the element map to Git for version tracking")
    print(f"   2. Run your test stories - they will now use this rich metadata!")
    print(f"   3. The AI Agent will have full structural knowledge upfront")
    
    print(f"\n📋 Registry Stats:")
    print(f"   - Version: {element_map.get('version')}")
    print(f"   - Elements: {len(element_map['elements'])}")
    print(f"   - Relationships: {len(relationships)}")
    print(f"   - Tabs: {by_type.get('tab', 0)}")
    print(f"   - Accordions: {by_type.get('accordion', 0)}")
    print(f"   - Checkboxes: {by_type.get('checkbox', 0)}")
    print(f"   - Buttons: {by_type.get('button', 0)}")
    print(f"   - Tables: {by_type.get('table', 0)}")
    print(f"   - Table Columns: {by_type.get('table_column', 0)}")


def main():
    """Synchronous main wrapper"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

