"""
Capture all GraphQL queries including filter data
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def capture_all_graphql():
    graphql_calls = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture ALL requests and responses
        async def handle_response(response):
            if 'graphql' in response.url.lower():
                try:
                    request = response.request
                    post_data = request.post_data
                    
                    if post_data:
                        query_data = json.loads(post_data)
                        response_data = None
                        try:
                            response_data = await response.json()
                        except:
                            pass
                        
                        graphql_calls.append({
                            'query': query_data,
                            'response': response_data
                        })
                        
                        print(f"\n📡 GraphQL Call #{len(graphql_calls)}")
                        print(f"  Query: {query_data.get('operationName', 'No operation name')}")
                        if response_data and 'data' in response_data:
                            data_keys = list(response_data['data'].keys())
                            print(f"  Data keys: {data_keys}")
                            # If it looks like filter data, show sample
                            for key in data_keys:
                                data_val = response_data['data'][key]
                                if isinstance(data_val, list) and len(data_val) > 0:
                                    print(f"    {key}: {len(data_val)} items (sample: {data_val[:3]})")
                except Exception as e:
                    print(f"Error: {e}")
        
        page.on('response', handle_response)
        
        print("🌐 Navigating...")
        await page.goto('https://clinicalcommons.ccdi.cancer.gov/#/explore', wait_until='networkidle')
        
        # Wait for page to fully load (longer wait)
        print("⏳ Waiting 10 seconds for all data to load...")
        await page.wait_for_timeout(10000)
        
        # Try to interact with filters
        print("\n🖱️ Trying to interact with page...")
        try:
            # Click on different tabs/sections to trigger more queries
            await page.mouse.move(100, 300)
            await page.wait_for_timeout(1000)
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  Interaction error: {e}")
        
        await browser.close()
    
    print(f"\n{'='*80}")
    print(f"📊 TOTAL: {len(graphql_calls)} GraphQL calls captured")
    print(f"{'='*80}")
    
    # Save to file for analysis
    with open('/tmp/graphql_calls.json', 'w') as f:
        json.dump(graphql_calls, f, indent=2)
    print("\n💾 Saved to /tmp/graphql_calls.json")

if __name__ == '__main__':
    asyncio.run(capture_all_graphql())



