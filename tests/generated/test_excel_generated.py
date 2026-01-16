"""
Excel-Generated Playwright Test
Generated from: test_case.xlsx
"""
from playwright.sync_api import sync_playwright
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f'✅ Loaded environment variables from {env_path}')
else:
    print(f'⚠️  .env file not found at {env_path}')

def test_excel_generated():
    """Auto-generated test from Excel file"""
    critical_failures = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
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
                selector = 'xpath=//div[@data-testid=\'system-use-warning-dialog\']//button[contains(., \'Continue\')]'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 2: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step2_button.png')
            except Exception as e:
                print(f'ℹ️  Step 2: Element not found (optional) - continuing')
            
            # Step 3: Click link
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                selector = 'xpath=(//a[@id=\'header-navbar-login-button\'])[1]'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
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
                selector = 'xpath=(//*[normalize-space(.)=\'Login.gov\'])[1]'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
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
                selector = 'xpath=//input[@type=\'email\']'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
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
                selector = 'xpath=//input[@type=\'password\']'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
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
                selector = 'xpath=(//*[normalize-space(.)=\'Submit\'])[1]'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
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
            
            # Step 9: Wait 5000ms
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                page.wait_for_timeout(5000)
                print('⏱️  Step 9: Waited 5000ms')
                page.screenshot(path='storage/screenshots/pw_step9_wait.png')
            except Exception as e:
                print(f'❌ Step 9: Wait failed: {e}')
            
            # Step 10: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                selector = 'xpath=(//*[normalize-space(.)=\'Submit\'])[1]'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 10: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step10_button.png')
            except Exception as e:
                print(f'❌ Step 10: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step10_button_failed.png')
                critical_failures.append(f'Step 10: Click failed')
            
            # Step 11: Wait 2000ms
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                page.wait_for_timeout(2000)
                print('⏱️  Step 11: Waited 2000ms')
                page.screenshot(path='storage/screenshots/pw_step11_wait.png')
            except Exception as e:
                print(f'❌ Step 11: Wait failed: {e}')
            
            # Step 12: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            # Optional step - continue if element not found
            try:
                selector = 'xpath=//input[@name=\'action\']'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 12: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step12_button.png')
            except Exception as e:
                print(f'ℹ️  Step 12: Element not found (optional) - continuing')
            
            # Step 14: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                selector = 'xpath=//div[@id=\'navbar-dropdown-data-submissions\' and @role=\'button\']'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 14: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step14_button.png')
            except Exception as e:
                print(f'❌ Step 14: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step14_button_failed.png')
                critical_failures.append(f'Step 14: Click failed')
            
            # Step 15: Click button
            page.wait_for_timeout(3000)  # Wait 3 seconds before step
            try:
                selector = 'xpath=//button[normalize-space(.)=\'Create a Data Submission\']'
                element = page.locator(selector).nth(0)
                element.wait_for(state='visible', timeout=10000)
                element.click()
                page.wait_for_timeout(1000)  # Wait after click
                print(f'✅ Step 15: Clicked button')
                page.screenshot(path='storage/screenshots/pw_step15_button.png')
            except Exception as e:
                print(f'❌ Step 15: Failed to click button: {e}')
                page.screenshot(path='storage/screenshots/pw_step15_button_failed.png')
                critical_failures.append(f'Step 15: Click failed')
            

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
