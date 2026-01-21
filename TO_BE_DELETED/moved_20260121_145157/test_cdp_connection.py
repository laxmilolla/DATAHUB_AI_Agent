#!/usr/bin/env python3
"""
Test CDP Connection
Tests if we can connect to Playwright browser via CDP
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright


def test_cdp_connection():
    """Test CDP connection between sync and async Playwright"""
    print("="*80)
    print("Testing CDP Connection")
    print("="*80)
    
    # Step 1: Launch sync browser with CDP
    print("\n1. Launching sync browser with CDP on port 9222...")
    playwright_sync = sync_playwright().start()
    browser_sync = playwright_sync.chromium.launch(
        headless=False,
        args=['--remote-debugging-port=9222']
    )
    page_sync = browser_sync.new_page(viewport={'width': 1920, 'height': 1080})
    page_sync.goto('https://example.com')
    current_url = page_sync.url
    cookies = page_sync.context.cookies()
    
    print(f"✅ Sync browser launched")
    print(f"   URL: {current_url}")
    print(f"   Cookies: {len(cookies)}")
    
    # Step 2: Connect async Playwright via CDP
    print("\n2. Connecting async Playwright via CDP...")
    
    async def connect_async():
        playwright_async = await async_playwright().start()
        
        try:
            # Connect via CDP
            cdp_endpoint = 'http://localhost:9222'
            print(f"   Connecting to: {cdp_endpoint}")
            
            browser_async = await playwright_async.chromium.connect_over_cdp(cdp_endpoint)
            
            # Wait for connection to stabilize
            await asyncio.sleep(0.5)
            
            # Get contexts
            contexts = browser_async.contexts
            print(f"   ✅ Connected! Found {len(contexts)} contexts")
            
            if contexts:
                context_async = contexts[0]
                pages = context_async.pages
                print(f"   Found {len(pages)} pages in context")
                
                if pages:
                    # Try to use existing page
                    page_async = None
                    for page in pages:
                        try:
                            url = page.url
                            page_async = page
                            print(f"   ✅ Using existing page: {url}")
                            break
                        except Exception as e:
                            print(f"   ⚠️  Page closed, trying next: {e}")
                            continue
                    
                    if not page_async:
                        print("   Creating new page in same browser...")
                        page_async = await context_async.new_page()
                        await page_async.goto(current_url)
                        await page_async.wait_for_load_state('networkidle')
                    
                    print(f"   ✅ Successfully using page: {page_async.url}")
                    print(f"   ✅ CDP connection works! Same browser window.")
                    
                    return True
                else:
                    print("   ⚠️  No pages found, creating new page...")
                    page_async = await context_async.new_page()
                    await page_async.goto(current_url)
                    await page_async.wait_for_load_state('networkidle')
                    print(f"   ✅ Created new page: {page_async.url}")
                    return True
            else:
                print("   ⚠️  No contexts found")
                return False
                
        except Exception as e:
            print(f"   ❌ CDP connection failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Don't close browser_async - it's connected to sync browser
            if 'playwright_async' in locals():
                await playwright_async.stop()
    
    # Run async connection test
    # Check if event loop is already running
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to use a different approach
            import threading
            result_container = {'result': False}
            
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result_container['result'] = new_loop.run_until_complete(connect_async())
                new_loop.close()
            
            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()
            result = result_container['result']
        else:
            result = loop.run_until_complete(connect_async())
    except RuntimeError:
        # No event loop, create new one
        result = asyncio.run(connect_async())
    
    # Keep sync browser open briefly for inspection
    print("\n3. Keeping sync browser open for 3 seconds...")
    import time
    time.sleep(3)
    
    # Cleanup
    browser_sync.close()
    playwright_sync.stop()
    
    print("\n" + "="*80)
    if result:
        print("✅ CDP Connection Test: PASSED")
    else:
        print("❌ CDP Connection Test: FAILED")
    print("="*80)
    
    return result


if __name__ == '__main__':
    test_cdp_connection()

