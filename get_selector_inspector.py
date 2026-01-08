#!/usr/bin/env python3
"""
Playwright Inspector Mode - Better selector generator
Uses Playwright's built-in Inspector
"""
import asyncio
import sys
import os
from playwright.async_api import async_playwright

async def main():
    if len(sys.argv) < 2:
        print("Usage: python get_selector_inspector.py <url>")
        print("\nExample:")
        print("  python get_selector_inspector.py https://hub-stage.datacommons.cancer.gov/")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("=" * 80)
    print("🎯 Playwright Inspector Mode")
    print("=" * 80)
    print(f"\n🌐 Opening browser with Inspector for: {url}")
    print("\n📋 INSTRUCTIONS:")
    print("  1. Playwright Inspector will open automatically")
    print("  2. Click 'Pick Locator' button (target icon)")
    print("  3. Click on any element on the page")
    print("  4. Inspector will show the suggested selector")
    print("  5. Copy the selector from Inspector")
    print("\n" + "=" * 80)
    
    # Set environment variable to enable Inspector
    os.environ['PWDEBUG'] = '1'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print(f"\n🚀 Navigating to: {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Dismiss popups
        try:
            continue_btn = page.locator("text='Continue'").first
            if await continue_btn.is_visible(timeout=2000):
                print("  ✅ Dismissing Continue popup")
                await continue_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
        
        print("\n✅ Browser ready! Playwright Inspector should be open.")
        print("💡 Click 'Pick Locator' in Inspector, then click elements on the page.")
        print("⏸️  Press Ctrl+C to close.")
        
        # Pause to open Inspector
        await page.pause()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())


