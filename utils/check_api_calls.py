"""
Quick script to check what API calls CCDI makes
"""
import asyncio
from playwright.async_api import async_playwright

async def check_ccdi_apis():
    api_calls = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture all network requests
        def handle_request(request):
            url = request.url
            # Filter for potential API calls
            if any(x in url.lower() for x in ['api', 'graphql', 'query', 'data', 'filter', 'search', '.json']):
                api_calls.append({
                    'url': url,
                    'method': request.method,
                    'resource_type': request.resource_type
                })
                print(f"📡 API Call: {request.method} {url}")
        
        page.on('request', handle_request)
        
        # Navigate to explore page
        print("\n🌐 Navigating to CCDI explore page...")
        await page.goto('https://clinicalcommons.ccdi.cancer.gov/#/explore', wait_until='networkidle')
        
        # Wait for page to fully load
        await page.wait_for_timeout(3000)
        
        # Try to expand Diagnosis accordion to trigger data loading
        print("\n📂 Expanding Diagnosis accordion...")
        try:
            diagnosis_btn = page.locator('button[id="Diagnosis"]').first
            await diagnosis_btn.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except:
            print("  ⚠️ Could not expand Diagnosis")
        
        # Try scrolling in a filter list to trigger lazy loading
        print("\n📜 Scrolling in filter lists...")
        try:
            scrollable = page.locator('div[id="Diagnosis"] + div').first
            await scrollable.evaluate('el => el.scrollTop = el.scrollHeight')
            await page.wait_for_timeout(2000)
        except:
            print("  ⚠️ Could not scroll")
        
        await browser.close()
    
    print(f"\n\n{'='*80}")
    print(f"📊 SUMMARY: Found {len(api_calls)} potential API calls")
    print(f"{'='*80}")
    
    for call in api_calls:
        print(f"\n{call['method']} {call['url']}")
        print(f"  Type: {call['resource_type']}")

if __name__ == '__main__':
    asyncio.run(check_ccdi_apis())



