"""
Extract all elements from Data Submissions page after logging in via Excel steps
Uses experiment_extended_test.py's login flow, then extracts elements
"""
import asyncio
import csv
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from utils.xpath_builder import XPathBuilder
import pandas as pd
import os
from dotenv import load_dotenv
import threading
from queue import Queue

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f'✅ Loaded environment variables from {env_path}')


def run_excel_steps_sync(result_queue):
    """Run Excel steps in sync mode (in separate thread)"""
    from playwright.sync_api import sync_playwright
    from datetime import datetime
    
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        excel_file = Path(__file__).parent / 'test_case.xlsx'
        if not excel_file.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file}")
        
        df = pd.read_excel(excel_file)
        
        # Only run steps up to step 11 (stop before step 12, user will click manually)
        # Handle mixed types: convert Step to string, then filter
        df['Step_Str'] = df['Step'].astype(str)
        # Keep steps where Step is numeric < 12 (so we stop after step 11)
        def should_keep_step(step_str):
            try:
                # Try to extract numeric part (e.g., "1a" -> 1, "12" -> 12)
                import re
                match = re.match(r'^(\d+)', step_str)
                if match:
                    num = int(match.group(1))
                    return num < 12  # Stop before step 12
                return False
            except:
                return False
        
        df = df[df['Step_Str'].apply(should_keep_step)]
        
        for index, row in df.iterrows():
            step = row.get('Step', index + 1)
            action = str(row.get('Action', '')).strip().lower() if pd.notna(row.get('Action')) else ''
            object_type = str(row.get('Object Type', '')).strip() if pd.notna(row.get('Object Type')) else ''
            xpath = str(row.get('XPath', '')).strip() if pd.notna(row.get('XPath')) else ''
            url = str(row.get('URL', '')).strip() if pd.notna(row.get('URL')) else ''
            text_value = str(row.get('Text Value', '')).strip() if pd.notna(row.get('Text Value')) else ''
            wait_time = row.get('Wait Time') if pd.notna(row.get('Wait Time')) else None
            
            if action == 'navigate':
                if url and url != 'nan' and url.startswith('http'):
                    page.goto(url)
                    page.wait_for_load_state('networkidle')
                    print(f'📍 Step {step}: Navigated to {url}')
            
            elif action == 'wait':
                wait_ms = int(wait_time) if wait_time and pd.notna(wait_time) else 3000
                page.wait_for_timeout(wait_ms)
                print(f'⏱️  Step {step}: Waited {wait_ms}ms')
            
            elif action == 'click':
                if xpath and xpath != 'N/A' and xpath != 'nan':
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    # For step 12, make it optional - skip if element not found
                    is_step_12 = (str(step) == '12')
                    timeout_ms = 15000 if is_step_12 else 10000
                    try:
                        element.wait_for(state='visible', timeout=timeout_ms)
                    except Exception as e:
                        if is_step_12:
                            print(f'⚠️  Step {step}: Element not found (skipping step 12), continuing to wait...')
                            page.wait_for_timeout(2000)  # Brief wait before continuing
                            continue
                        raise
                    
                    try:
                        element.scroll_into_view_if_needed(timeout=3000)
                    except:
                        pass
                    
                    try:
                        element.click(timeout=10000)
                    except Exception as e:
                        if "timeout" in str(e).lower():
                            try:
                                element.evaluate('el => el.click()')
                            except:
                                try:
                                    element.click(force=True, timeout=10000)
                                except:
                                    if is_step_12:
                                        print(f'⚠️  Step {step}: Click failed (skipping step 12), continuing...')
                                        continue
                                    raise e
                        else:
                            try:
                                element.click(force=True, timeout=10000)
                            except:
                                if is_step_12:
                                    print(f'⚠️  Step {step}: Click failed (skipping step 12), continuing...')
                                    continue
                                raise e
                    
                    page.wait_for_timeout(1000)
                    print(f'✅ Step {step}: Clicked {object_type or "element"}')
            
            elif action == 'fill':
                if 'totp' in object_type.lower() or 'totp' in str(row.get('Functions', '')).lower():
                    # TOTP field - try multiple selectors (fallback approach)
                    totp_selectors = [
                        'input.one-time-code-input__input',
                        "input[autocomplete='one-time-code']",
                        "input[type='text'][name='code']",
                        "input[name='code']:not([type='hidden'])",
                        'lg-one-time-code-input input[type="text"]',
                        'lg-validated-field input[type="text"]',
                        'lg-one-time-code-input input',
                        'input.one-time-code',
                        f'xpath={xpath}' if xpath and xpath != 'N/A' and xpath != 'nan' else None,
                    ]
                    selector_found = False
                    element = None
                    for totp_sel in totp_selectors:
                        if not totp_sel:
                            continue
                        try:
                            test_elem = page.locator(totp_sel).first
                            if test_elem.is_visible(timeout=2000):
                                element = test_elem
                                selector_found = True
                                print(f'✅ Step {step}: Found TOTP field with selector: {totp_sel}')
                                break
                        except:
                            continue
                    if not selector_found:
                        print(f'⚠️  Step {step}: TOTP field not found with fallback selectors')
                        continue
                    
                    # Generate TOTP using pyotp directly
                    try:
                        import pyotp
                    except ImportError:
                        import subprocess
                        import sys
                        print('⚠️  pyotp not found. Attempting to install...')
                        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyotp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        import pyotp
                    
                    secret_key = os.getenv('TOTP_SECRET_KEY')
                    if not secret_key:
                        raise ValueError('TOTP_SECRET_KEY not found in environment variables')
                    totp = pyotp.TOTP(secret_key)
                    totp_code = totp.now()
                    print(f'🔐 Step {step}: Generated TOTP code: {totp_code[:2]}****')
                    element.fill('')
                    element.type(totp_code, delay=10)
                    page.wait_for_timeout(500)
                    print(f'✅ Step {step}: Filled TOTP code')
                elif xpath and xpath != 'N/A' and xpath != 'nan':
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    
                    if text_value and text_value != 'nan':
                        element.fill(text_value)
                    
                    page.wait_for_timeout(500)
                    print(f'✅ Step {step}: Filled {object_type or "element"}')
        
        print("\n✅ Phase 1 Complete: Steps 1-11 completed")
        print("⏸️  Waiting 10 seconds for you to click/navigate manually...")
        print("   (Step 12 will be done manually during this wait)")
        
        # Wait 10 seconds for user to click/navigate (reduced for testing)
        page.wait_for_timeout(10000)
        
        # Get URL and cookies after user's manual actions
        current_url = page.url
        cookies = page.context.cookies()
        print(f"✅ Stopped after step 12 at: {current_url}")
        print("💡 Ready to extract elements from current page")
        
        result_queue.put((browser, page, current_url, cookies))
        
    except Exception as e:
        print(f"\n❌ Error in Excel steps: {e}")
        import traceback
        traceback.print_exc()
        result_queue.put((None, None, None, None))


async def extract_all_elements(page, current_url, output_file=None):
    """
    Extract all interactive elements from the page with their XPaths
    
    Args:
        page: Playwright page object
        current_url: Current page URL (for generating filename)
        output_file: Output CSV file path (optional, auto-generated if not provided)
    """
    print("\n" + "="*80)
    print("EXTRACTING ALL ELEMENTS FROM CURRENT PAGE")
    print("="*80)
    print(f"Page URL: {page.url}")
    print("="*80)
    
    xpath_builder = XPathBuilder(page)
    elements_data = []
    
    await page.wait_for_load_state('networkidle')
    await page.wait_for_timeout(2000)
    
    print("\n🔍 Extracting elements...")
    
    # Extract buttons
    print("  📌 Extracting buttons...")
    buttons = await page.locator('button, [role="button"], input[type="button"], input[type="submit"]').all()
    button_count = 0
    for btn in buttons:
        try:
            if not await btn.is_visible():
                continue
            
            attrs = await btn.evaluate('''element => ({
                tag: element.tagName.toLowerCase(),
                role: element.getAttribute('role') || (element.tagName.toLowerCase() === 'button' ? 'button' : null),
                id: element.id,
                text: element.textContent.trim().substring(0, 100),
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className,
                type: element.type || null
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('text') or attrs.get('id') or 'button'
            if not name.strip():
                name = 'button'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'button',
                'XPath': xpath,
                'Tag': attrs.get('tag', ''),
                'ID': attrs.get('id', ''),
                'Text': attrs.get('text', '')[:50]
            })
            button_count += 1
        except:
            continue
    
    print(f"    ✅ Found {button_count} buttons")
    
    # Extract links
    print("  🔗 Extracting links...")
    links = await page.locator('a[href]').all()
    link_count = 0
    for link in links:
        try:
            if not await link.is_visible():
                continue
            
            attrs = await link.evaluate('''element => ({
                tag: 'a',
                id: element.id,
                text: element.textContent.trim().substring(0, 100),
                href: element.href,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('text') or attrs.get('id') or attrs.get('href', 'link')
            if not name.strip():
                name = 'link'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'link',
                'XPath': xpath,
                'Tag': 'a',
                'ID': attrs.get('id', ''),
                'Text': attrs.get('text', '')[:50]
            })
            link_count += 1
        except:
            continue
    
    print(f"    ✅ Found {link_count} links")
    
    # Extract inputs
    print("  📝 Extracting inputs...")
    inputs = await page.locator('input:not([type="checkbox"]):not([type="radio"])').all()
    input_count = 0
    for inp in inputs:
        try:
            if not await inp.is_visible():
                continue
            
            attrs = await inp.evaluate('''element => ({
                tag: 'input',
                type: element.type,
                id: element.id,
                name: element.name,
                placeholder: element.placeholder,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('placeholder') or attrs.get('ariaLabel') or attrs.get('name') or attrs.get('id') or 'input'
            if not name.strip():
                name = f"input ({attrs.get('type', 'text')})"
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': f"input ({attrs.get('type', 'text')})",
                'XPath': xpath,
                'Tag': 'input',
                'ID': attrs.get('id', ''),
                'Text': attrs.get('placeholder', '')[:50]
            })
            input_count += 1
        except:
            continue
    
    print(f"    ✅ Found {input_count} inputs")
    
    # Extract selects/dropdowns
    print("  📋 Extracting dropdowns...")
    selects = await page.locator('select, [role="combobox"], [role="listbox"]').all()
    select_count = 0
    for sel in selects:
        try:
            if not await sel.is_visible():
                continue
            
            attrs = await sel.evaluate('''element => ({
                tag: element.tagName.toLowerCase(),
                role: element.getAttribute('role'),
                id: element.id,
                name: element.name,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('name') or attrs.get('id') or 'dropdown'
            if not name.strip():
                name = 'dropdown'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'dropdown',
                'XPath': xpath,
                'Tag': attrs.get('tag', ''),
                'ID': attrs.get('id', ''),
                'Text': ''
            })
            select_count += 1
        except:
            continue
    
    print(f"    ✅ Found {select_count} dropdowns")
    
    # Extract checkboxes
    print("  ☑️  Extracting checkboxes...")
    checkboxes = await page.locator('input[type="checkbox"]').all()
    checkbox_count = 0
    for cb in checkboxes:
        try:
            if not await cb.is_visible():
                continue
            
            attrs = await cb.evaluate('''element => ({
                tag: 'input',
                type: 'checkbox',
                id: element.id,
                name: element.name,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('name') or attrs.get('id') or 'checkbox'
            if not name.strip():
                name = 'checkbox'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'checkbox',
                'XPath': xpath,
                'Tag': 'input',
                'ID': attrs.get('id', ''),
                'Text': ''
            })
            checkbox_count += 1
        except:
            continue
    
    print(f"    ✅ Found {checkbox_count} checkboxes")
    
    # Use test1.csv if output_file not provided, otherwise use provided filename
    if not output_file:
        output_file = 'test1.csv'
    
    print(f"\n💾 Writing {len(elements_data)} elements to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if elements_data:
            writer = csv.DictWriter(f, fieldnames=['Element Name', 'Type', 'XPath', 'Tag', 'ID', 'Text'])
            writer.writeheader()
            writer.writerows(elements_data)
    
    print(f"✅ Done! Extracted {len(elements_data)} elements")
    print(f"📄 Saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    type_counts = {}
    for elem in elements_data:
        elem_type = elem['Type']
        type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    
    for elem_type, count in sorted(type_counts.items()):
        print(f"  {elem_type}: {count}")
    print("="*80)
    
    return elements_data


async def main():
    """Main function"""
    print("\n" + "="*80)
    print("EXTRACT ELEMENTS FROM DATA SUBMISSIONS PAGE")
    print("="*80)
    
    # Phase 1: Run Excel steps in separate thread (sync)
    print("\n" + "="*80)
    print("PHASE 1: Running Excel Test Steps (Login)")
    print("="*80)
    
    result_queue = Queue()
    thread = threading.Thread(target=run_excel_steps_sync, args=(result_queue,))
    thread.start()
    thread.join()
    
    browser_sync, page_sync, current_url, cookies = result_queue.get()
    
    if not browser_sync or not page_sync:
        print("❌ Failed to log in. Exiting.")
        return
    
    # Extract elements after user's manual actions
    print("\n" + "="*80)
    print("PHASE 2: Extracting Elements from Current Page")
    print("="*80)
    print(f"✅ Steps 1-12 completed")
    print(f"📍 Current URL: {current_url}")
    print("💡 Extracting all elements from this page...")
    
    # Phase 3: Extract elements (async)
    print("\n" + "="*80)
    print("PHASE 3: Extracting Elements")
    print("="*80)
    
    async with async_playwright() as p:
        browser_async = await p.chromium.launch(headless=False)
        context_async = await browser_async.new_context(viewport={'width': 1920, 'height': 1080})
        
        if cookies:
            await context_async.add_cookies(cookies)
        
        page_async = await context_async.new_page()
        await page_async.goto(current_url)
        await page_async.wait_for_load_state('networkidle')
        await page_async.wait_for_timeout(2000)
        
        # Extract elements and save to test1.csv
        elements = await extract_all_elements(page_async, current_url, 'test1.csv')
        
        print("\n⏸️  Browser will remain open for 10 seconds for inspection...")
        await page_async.wait_for_timeout(10000)
        
        await browser_async.close()
    
    # Close sync browser
    try:
        browser_sync.close()
        print("✅ Browser closed")
    except:
        pass
    
    print("\n✅ Extraction complete! Saved to test1.csv")


if __name__ == '__main__':
    asyncio.run(main())
