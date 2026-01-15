#!/usr/bin/env python3
"""
Simple script to run PlaywrightTreeParser directly
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from utils.playwright_tree_parser import PlaywrightTreeParser
from utils.element_registry import get_registry

async def main():
    url = 'https://clinicalcommons.ccdi.cancer.gov/explore'
    
    print(f"🌐 Opening browser and navigating to: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Navigate
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Dismiss popup
        try:
            continue_btn = page.locator("text='Continue'").first
            if await continue_btn.is_visible(timeout=2000):
                print(f"  ✅ Dismissing Continue popup")
                await continue_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Parse WITHOUT accordion expansion first
        print("\n🔍 Parsing page (NO accordion expansion)...")
        parser = PlaywrightTreeParser(page)
        
        # Skip accordion expansion - just parse what's visible
        parser._expand_all_accordions = lambda: None  # Disable accordion expansion
        
        element_map = await parser.parse()
        
        await browser.close()
    
    # Save
    registry = get_registry(str(Path(__file__).parent / "element_maps"))
    domain = 'clinicalcommons.ccdi.cancer.gov'
    page_name = 'explore'
    
    registry.save_map(domain, page_name, element_map)
    print(f"\n✅ Saved {len(element_map['elements'])} elements to registry")
    print(f"   - Accordions: {sum(1 for e in element_map['elements'].values() if e['type'] == 'accordion')}")
    print(f"   - Checkboxes: {sum(1 for e in element_map['elements'].values() if e['type'] == 'checkbox')}")
    print(f"   - Tabs: {sum(1 for e in element_map['elements'].values() if e['type'] == 'tab')}")

if __name__ == "__main__":
    asyncio.run(main())






