"""
Capture GraphQL queries and responses from CCDI
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def capture_graphql():
    graphql_calls = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture GraphQL requests and responses
        async def handle_response(response):
            if 'graphql' in response.url.lower():
                try:
                    request = response.request
                    post_data = request.post_data
                    
                    if post_data:
                        query_data = json.loads(post_data)
                        
                        # Get response
                        response_data = None
                        try:
                            response_data = await response.json()
                        except:
                            pass
                        
                        graphql_calls.append({
                            'url': response.url,
                            'query': query_data,
                            'response_keys': list(response_data.keys()) if response_data else None,
                            'response_data_keys': list(response_data.get('data', {}).keys()) if response_data and 'data' in response_data else None
                        })
                        
                        print(f"\n{'='*80}")
                        print(f"📡 GraphQL Call #{len(graphql_calls)}")
                        print(f"{'='*80}")
                        print(f"Query: {json.dumps(query_data, indent=2)[:500]}...")
                        if response_data:
                            print(f"\nResponse keys: {list(response_data.keys())}")
                            if 'data' in response_data:
                                print(f"Data keys: {list(response_data.get('data', {}).keys())}")
                except Exception as e:
                    print(f"Error parsing GraphQL: {e}")
        
        page.on('response', handle_response)
        
        # Navigate and interact
        print("\n🌐 Navigating to CCDI explore page...")
        await page.goto('https://clinicalcommons.ccdi.cancer.gov/#/explore', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        
        # Try to expand Diagnosis
        print("\n📂 Trying to expand Diagnosis accordion...")
        try:
            # Wait for page to be ready
            await page.wait_for_selector('button[id="Diagnosis"]', timeout=10000)
            diagnosis_btn = page.locator('button[id="Diagnosis"]').first
            await diagnosis_btn.click()
            print("  ✅ Clicked Diagnosis")
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  ⚠️ Could not expand: {e}")
        
        await browser.close()
    
    # Summary
    print(f"\n\n{'='*80}")
    print(f"📊 CAPTURED {len(graphql_calls)} GraphQL CALLS")
    print(f"{'='*80}")
    
    for i, call in enumerate(graphql_calls, 1):
        print(f"\nCall #{i}:")
        print(f"  Query operation: {call['query'].get('operationName', 'N/A')}")
        print(f"  Response data keys: {call['response_data_keys']}")

if __name__ == '__main__':
    asyncio.run(capture_graphql())






