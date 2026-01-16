"""
Quick script to extract all input fields and their XPaths from the current page
"""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from utils.xpath_builder import XPathBuilder

sys.path.insert(0, str(Path(__file__).parent))


async def extract_input_fields(url: str = None):
    """
    Extract all input fields from a page with their XPaths
    
    Args:
        url: URL to navigate to (if None, will try to connect to existing browser)
    """
    async with async_playwright() as p:
        # Try to connect to existing browser via CDP first
        browser = None
        page = None
        
        try:
            print("🔗 Attempting to connect to existing browser via CDP...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            contexts = browser.contexts
            if contexts:
                pages = contexts[0].pages
                if pages:
                    # Filter out DevTools pages
                    for pg in pages:
                        if not pg.url.startswith("devtools://"):
                            page = pg
                            print(f"✅ Connected to existing page: {page.url}")
                            break
        except Exception as e:
            print(f"⚠️  Could not connect via CDP: {e}")
            print("🆕 Launching new browser...")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            if url:
                await page.goto(url)
                await page.wait_for_load_state('networkidle')
            else:
                print("⚠️  No URL provided and no existing browser found")
                return
        
        print(f"\n📄 Current page: {page.url}")
        print(f"📄 Page title: {await page.title()}\n")
        
        # Wait for page to be fully loaded
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        xpath_builder = XPathBuilder(page)
        
        # Get all input fields
        print("🔍 Extracting all input fields...\n")
        inputs = await page.locator('input').all()
        
        print(f"Found {len(inputs)} input elements\n")
        print("="*100)
        print(f"{'Index':<6} {'Type':<12} {'Name':<20} {'Placeholder':<25} {'ID':<20} {'XPath':<50}")
        print("="*100)
        
        visible_count = 0
        for idx, inp in enumerate(inputs, 1):
            try:
                # Check if visible
                is_visible = await inp.is_visible()
                if not is_visible:
                    continue
                
                visible_count += 1
                
                # Get attributes
                attrs = await inp.evaluate('''element => ({
                    tag: 'input',
                    type: element.type || 'text',
                    id: element.id || '',
                    name: element.name || '',
                    placeholder: element.placeholder || '',
                    value: element.value || '',
                    class: element.className || '',
                    ariaLabel: element.getAttribute('aria-label') || ''
                })''')
                
                # Build XPath
                element_name = attrs.get('placeholder') or attrs.get('name') or attrs.get('id') or attrs.get('ariaLabel') or f'input_{idx}'
                xpath_result = await xpath_builder.build_unique_xpath(attrs, element_name)
                xpath = xpath_result.get('xpath', 'N/A')
                
                # Display
                print(f"{visible_count:<6} {attrs.get('type', 'text'):<12} {attrs.get('name', ''):<20} {attrs.get('placeholder', ''):<25} {attrs.get('id', ''):<20} {xpath[:48]:<50}")
                
            except Exception as e:
                continue
        
        print("="*100)
        print(f"\n✅ Found {visible_count} visible input fields")
        print(f"\n💡 To use these XPaths:")
        print(f"   - Copy the XPath from the table above")
        print(f"   - Use it in your selectors: xpath=<XPath>")
        print(f"   - Or use the name/placeholder/ID attributes directly")
        
        # Close browser
        print("\n👋 Closing browser...")
        await browser.close()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://hub-stage.datacommons.cancer.gov/data-submissions"
    asyncio.run(extract_input_fields(url))

