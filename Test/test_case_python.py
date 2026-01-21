"""
Excel-Generated Playwright Test
Generated from: test_case.xlsx
"""
from playwright.sync_api import sync_playwright
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f'✅ Loaded environment variables from {env_path}')
else:
    print(f'⚠️  .env file not found at {env_path}')

# ============================================================================
# MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
# ============================================================================
# Automatically detects and loads all registry files needed based on URLs in Excel
REGISTRY_PATHS = [
    'element_maps/auth.nih.gov/LoginMFA_page.json',
    'element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json',
    'element_maps/hub-stage.datacommons.cancer.gov/home_page.json',
    'element_maps/secure.login.gov/home_page.json',
]

# Load registries per domain/page (for dynamic loading based on current page)
# NO MERGE: Keep registries separate to avoid conflicts when same element name exists in multiple registries
REGISTRIES_BY_PATH = {}  # registry_path -> registry_data
loaded_count = 0

for registry_path_str in REGISTRY_PATHS:
    try:
        registry_path = Path(registry_path_str)
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
                # Store per-path for dynamic loading (NO MERGE - prevents conflicts)
                REGISTRIES_BY_PATH[registry_path_str] = registry_data
            loaded_count += 1
            print(f"✅ Loaded registry: {len(registry_data.get('elements', {}))} elements from {registry_path.name}")
        else:
            print(f"⚠️  Registry file not found: {registry_path}")
    except Exception as e:
        print(f"⚠️  Failed to load registry {registry_path_str}: {e}")

if loaded_count > 0:
    total_elements = sum(len(reg.get('elements', {})) for reg in REGISTRIES_BY_PATH.values())
    total_ids = sum(len(reg.get('id_index', {})) for reg in REGISTRIES_BY_PATH.values())
    print(f"✅ Loaded {loaded_count} registries: {total_elements} total elements, {total_ids} total IDs (separate, not merged)")

def get_registry_for_page(page_url):
    """Get registry for current page based on URL"""
    if not page_url:
        return None
    
    parsed = urlparse(page_url)
    domain = parsed.netloc.split(':')[0]  # Remove port if present
    
    # Extract page name from URL path
    path_parts = [p for p in parsed.path.split('/') if p]
    if not path_parts:
        page_name = 'home'
    elif path_parts[-1] == 'explore':
        page_name = 'explore'
    else:
        # Get last path segment, remove query params
        page_name = path_parts[-1].split('?')[0].split('#')[0]
        # Remove file extension if present
        if '.' in page_name:
            page_name = page_name.rsplit('.', 1)[0]
    
    # Try to find matching registry file
    best_match = None
    best_score = 0
    
    for registry_path_str, registry_data in REGISTRIES_BY_PATH.items():
        # Check if registry path matches domain
        if domain not in registry_path_str:
            continue
        
        score = 0
        # Score based on how well the registry path matches the page
        
        # Exact page name match gets highest score
        if page_name in registry_path_str:
            score += 10
        
        # Check for specific page patterns in registry path
        registry_filename = registry_path_str.split('/')[-1]
        
        # Match page name in filename (e.g., LoginMFA.aspx_page.json for LoginMFA.aspx)
        if page_name.lower() in registry_filename.lower():
            score += 8
        
        # Match common patterns
        if 'home' in registry_filename.lower() and (not path_parts or path_parts[-1] == ''):
            score += 5
        
        # Match domain exactly
        if domain in registry_path_str:
            score += 3
        
        if score > best_score:
            best_score = score
            best_match = registry_data
    
    # If we found a good match, return it
    if best_match and best_score >= 3:
        return best_match
    
    # Fallback: return first registry that matches domain
    for registry_path_str, registry_data in REGISTRIES_BY_PATH.items():
        if domain in registry_path_str:
            return registry_data
    
    return None

def get_xpath_by_id(element_id, page_url=None):
    """Get XPath from registry by unique ID - prefers registry for current page, searches all registries for same domain if not found"""
    if not element_id:
        raise Exception(f"❌ element_id is required")
    
    # STEP 1: Try to get registry for current page first
    if page_url:
        page_registry = get_registry_for_page(page_url)
        if page_registry:
            current_registry = page_registry.get('elements', {})
            current_id_index = page_registry.get('id_index', {})
            
            # Check if element_id exists in current page registry
            if element_id in current_id_index:
                registry_key = current_id_index[element_id]
                if registry_key in current_registry:
                    xpath = current_registry[registry_key].get('xpath')
                    if xpath:
                        return xpath
    
    # STEP 2: If not found in page-specific registry, search all registries for same domain
    if page_url:
        parsed = urlparse(page_url)
        domain = parsed.netloc.split(':')[0]  # Remove port if present
        
        # Search all registries for this domain
        for registry_path_str, registry_data in REGISTRIES_BY_PATH.items():
            if domain in registry_path_str:
                id_index = registry_data.get('id_index', {})
                elements = registry_data.get('elements', {})
                
                if element_id in id_index:
                    registry_key = id_index[element_id]
                    if registry_key in elements:
                        xpath = elements[registry_key].get('xpath')
                        if xpath:
                            return xpath
    
    # STEP 3: Last resort - search ALL registries (cross-domain fallback)
    for registry_data in REGISTRIES_BY_PATH.values():
        id_index = registry_data.get('id_index', {})
        elements = registry_data.get('elements', {})
        
        if element_id in id_index:
            registry_key = id_index[element_id]
            if registry_key in elements:
                xpath = elements[registry_key].get('xpath')
                if xpath:
                    return xpath
    
    # Not found in any registry
    raise Exception(f"❌ element_id '{element_id}' not found in any registry id_index")



def test_excel_generated():
    """Auto-generated test from Excel file"""
    critical_failures = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Generate timestamp if needed
        TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Step 1: Navigate to https://hub-stage.datacommons.cancer.gov/
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                page.goto('https://hub-stage.datacommons.cancer.gov/')
                page.wait_for_load_state('networkidle')
                print('📍 Step 1: Navigated to https://hub-stage.datacommons.cancer.gov/')
                page.screenshot(path='storage/screenshots/pw_step1_navigate.png')
            except Exception as e:
                print(f'❌ Step 1: Navigation failed: {e}')
                page.screenshot(path='storage/screenshots/pw_step1_navigate_failed.png')
            
            # Step 1a: Wait 3000ms
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                page.wait_for_timeout(3000)
                print('⏱️  Step 1a: Waited 3000ms')
                page.screenshot(path='storage/screenshots/pw_step1a_wait.png')
            except Exception as e:
                print(f'❌ Step 1a: Wait failed: {e}')
            
            # Step 2: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            # Optional step - continue if element not found
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_c1bf258c', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 2: Using registry element_id: ID_c1bf258c')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 2: Registry lookup failed for element_id ID_c1bf258c: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step2_button_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_c1bf258c: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 2: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 2: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 2: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 2: Force click succeeded')
                    else:
                        print(f'⚠️  Step 2: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 2: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 2: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step2_button.png')
            except Exception as e:
                print(f'ℹ️  Step 2: Element not found (optional) - continuing')
            
            # Step 3: Click link
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_f0a2425a', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 3: Using registry element_id: ID_f0a2425a')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 3: Registry lookup failed for element_id ID_f0a2425a: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step3_link_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_f0a2425a: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 3: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 3: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 3: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 3: Force click succeeded')
                    else:
                        print(f'⚠️  Step 3: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 3: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 3: Clicked link')
                page.screenshot(path='storage/screenshots/pw_step3_link.png')
            except Exception as e:
                print(f'❌ Step 3: Failed to click link: {e}')
                page.screenshot(path='storage/screenshots/pw_step3_link_failed.png')
                critical_failures.append(f'Step 3: Click failed')
            
            # Step 4: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_c20d27bc', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 4: Using registry element_id: ID_c20d27bc')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 4: Registry lookup failed for element_id ID_c20d27bc: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step4_button_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_c20d27bc: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 4: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 4: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 4: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 4: Force click succeeded')
                    else:
                        print(f'⚠️  Step 4: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 4: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 4: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step4_button.png')
            except Exception as e:
                print(f'❌ Step 4: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step4_button_failed.png')
                critical_failures.append(f'Step 4: Click failed')
            
            # Step 5: Fill input
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_b92fade3', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 5: Using registry element_id: ID_b92fade3')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 5: Registry lookup failed for element_id ID_b92fade3: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step5_input_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_b92fade3: {registry_error}')
                element.fill('Laxmi_AI_test@yahoo.com')
                print(f'✅ Step 5: Filled input with Laxmi_AI_test@yahoo.com')
                page.wait_for_timeout(500)  # Wait after fill
                page.screenshot(path='storage/screenshots/pw_step5_input.png')
            except Exception as e:
                print(f'❌ Step 5: Failed to fill input: {e}')
                page.screenshot(path='storage/screenshots/pw_step5_input_failed.png')
                critical_failures.append(f'Step 5: Fill failed')
            
            # Step 6: Fill input
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_096dd456', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 6: Using registry element_id: ID_096dd456')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 6: Registry lookup failed for element_id ID_096dd456: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step6_input_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_096dd456: {registry_error}')
                element.fill('Testnci123456789!')
                print(f'✅ Step 6: Filled input with Testnci123456789!')
                page.wait_for_timeout(500)  # Wait after fill
                page.screenshot(path='storage/screenshots/pw_step6_input.png')
            except Exception as e:
                print(f'❌ Step 6: Failed to fill input: {e}')
                page.screenshot(path='storage/screenshots/pw_step6_input_failed.png')
                critical_failures.append(f'Step 6: Fill failed')
            
            # Step 7: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_33b5218d', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 7: Using registry element_id: ID_33b5218d')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 7: Registry lookup failed for element_id ID_33b5218d: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step7_button_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_33b5218d: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 7: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 7: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 7: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 7: Force click succeeded')
                    else:
                        print(f'⚠️  Step 7: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 7: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 7: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step7_button.png')
            except Exception as e:
                print(f'❌ Step 7: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step7_button_failed.png')
                critical_failures.append(f'Step 7: Click failed')
            
            # Step 8: Fill input
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            # TOTP field - code will be generated automatically
            try:
                # TOTP field - try multiple selectors (fallback approach)
                totp_selectors = [
                    'input.one-time-code-input__input',
                    "input[autocomplete='one-time-code']",
                    "input[type='text'][name='code']",
                    "input[name='code']:not([type='hidden'])",
                    'lg-one-time-code-input input[type=\'text\']',
                    'lg-validated-field input[type=\'text\']',
                    'lg-one-time-code-input input',
                    'input.one-time-code',
                    'xpath=//input[@class=\'one-time-code-input__input\']',  # Fallback to provided XPath
                ]
                selector_found = False
                element = None
                for totp_sel in totp_selectors:
                    try:
                        test_elem = page.locator(totp_sel).first
                        if test_elem.is_visible(timeout=2000):
                            element = test_elem
                            selector_found = True
                            print(f'✅ Step 8: Found TOTP field with selector: {totp_sel}')
                            break
                    except:
                        continue
                if not selector_found:
                    # Fallback to original selector
                    selector = 'xpath=//input[@class=\'one-time-code-input__input\']'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'⚠️  Step 8: TOTP field not found with fallback selectors, using original selector')
                # Generate TOTP code
                try:
                    import pyotp
                except ImportError:
                    # Auto-install pyotp if missing
                    import subprocess
                    import sys
                    print('⚠️  pyotp not found. Attempting to install...')
                    try:
                        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyotp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        import pyotp  # Try importing again after installation
                        print('✅ pyotp installed successfully')
                    except Exception as install_error:
                        raise Exception('pyotp library not installed and auto-install failed. Please install manually with: pip3 install pyotp')
                try:
                    secret_key = os.getenv('TOTP_SECRET_KEY')
                    if not secret_key:
                        raise ValueError('TOTP_SECRET_KEY not found in environment variables')
                    totp = pyotp.TOTP(secret_key)
                    totp_code = totp.now()
                    print(f'🔐 Step 8: Generated TOTP code: {totp_code[:2]}****')
                    
                    # For TOTP: clear field first, then use type() with delay (more reliable than fill())
                    element.fill('')
                    element.type(totp_code, delay=10)
                    page.wait_for_timeout(200)
                    print(f'✅ Step 8: Filled TOTP code using type() method')
                except Exception as e:
                    print(f'❌ Step 8: Failed to generate/fill TOTP code: {e}')
                    # Try fallback fill() method
                    try:
                        element.fill(totp_code)
                        print(f'✅ Step 8: Filled TOTP code using fill() fallback')
                    except Exception as fill_error:
                        print(f'❌ Step 8: fill() fallback also failed: {fill_error}')
                        raise
                page.wait_for_timeout(500)  # Wait after fill
                page.screenshot(path='storage/screenshots/pw_step8_input.png')
            except Exception as e:
                print(f'❌ Step 8: Failed to fill input: {e}')
                page.screenshot(path='storage/screenshots/pw_step8_input_failed.png')
                critical_failures.append(f'Step 8: Fill failed')
            
            # Step 9: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_8fcff2a7', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 9: Using registry element_id: ID_8fcff2a7')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 9: Registry lookup failed for element_id ID_8fcff2a7: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step9_button_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_8fcff2a7: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 9: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 9: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 9: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 9: Force click succeeded')
                    else:
                        print(f'⚠️  Step 9: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 9: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 9: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step9_button.png')
            except Exception as e:
                print(f'❌ Step 9: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step9_button_failed.png')
                critical_failures.append(f'Step 9: Click failed')
            
            # Step 10: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_38253381', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 10: Using registry element_id: ID_38253381')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 10: Registry lookup failed for element_id ID_38253381: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step10_button_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_38253381: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 10: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 10: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 10: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 10: Force click succeeded')
                    else:
                        print(f'⚠️  Step 10: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 10: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 10: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step10_button.png')
            except Exception as e:
                print(f'❌ Step 10: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step10_button_failed.png')
                critical_failures.append(f'Step 10: Click failed')
            
            # Step 11: Click input
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_07a4c7a7', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 11: Using registry element_id: ID_07a4c7a7')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 11: Registry lookup failed for element_id ID_07a4c7a7: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step11_input_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_07a4c7a7: {registry_error}')
                # Scroll into view if needed
                try:
                    element.scroll_into_view_if_needed()
                except:
                    pass  # Continue if scroll fails
                page.wait_for_timeout(500)  # Wait after scroll
                # Robust click with fallbacks (JavaScript + force)
                try:
                    element.click()
                except Exception as click_error:
                    if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):
                        print(f'⚠️  Step 11: Click timeout, trying JavaScript click...')
                        try:
                            element.evaluate('el => el.click()')
                            print(f'✅ Step 11: JavaScript click succeeded')
                        except Exception as js_error:
                            print(f'⚠️  Step 11: JavaScript click failed, trying force click...')
                            element.click(force=True)
                            print(f'✅ Step 11: Force click succeeded')
                    else:
                        print(f'⚠️  Step 11: Click failed, trying force click...')
                        element.click(force=True)
                        print(f'✅ Step 11: Force click succeeded')
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 11: Clicked input')
                page.screenshot(path='storage/screenshots/pw_step11_input.png')
            except Exception as e:
                print(f'❌ Step 11: Failed to click input: {e}')
                page.screenshot(path='storage/screenshots/pw_step11_input_failed.png')
                critical_failures.append(f'Step 11: Click failed')
            
            # Step 12: Fill input
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                # Try registry lookup first
                try:
                    xpath = get_xpath_by_id('ID_ce7aacba', page.url)
                    selector = f'xpath={xpath}'
                    element = page.locator(selector).nth(0)
                    element.wait_for(state='visible', timeout=10000)
                    print(f'✅ Step 12: Using registry element_id: ID_ce7aacba')
                except Exception as registry_error:
                    # Registry lookup failed - test must fail
                    print(f'❌ Step 12: Registry lookup failed for element_id ID_ce7aacba: {registry_error}')
                    page.screenshot(path='storage/screenshots/pw_step12_input_registry_failed.png')
                    raise Exception(f'Registry lookup failed for element_id ID_ce7aacba: {registry_error}')
                element.fill('${Timestamp}')
                print(f'✅ Step 12: Filled input with ${Timestamp}')
                page.wait_for_timeout(500)  # Wait after fill
                page.screenshot(path='storage/screenshots/pw_step12_input.png')
            except Exception as e:
                print(f'❌ Step 12: Failed to fill input: {e}')
                page.screenshot(path='storage/screenshots/pw_step12_input_failed.png')
                critical_failures.append(f'Step 12: Fill failed')
            

            if critical_failures:
                print(f"\n❌ Test completed with {len(critical_failures)} failure(s)")
                for failure in critical_failures:
                    print(f"  - {failure}")
                raise Exception("Test failed")
            else:
                print("✅ Test completed successfully")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
        finally:
            browser.close()

if __name__ == '__main__':
    test_excel_generated()
