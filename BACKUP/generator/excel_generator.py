"""
Excel-Based Playwright Generator
Reads Excel file with Step, URL, XPath, Action, etc. and generates Playwright code
"""
import pandas as pd
import re
from pathlib import Path
from typing import Dict, Optional


def escape_xpath(xpath: str) -> str:
    """Escape single quotes in XPath for Python string"""
    if not xpath or xpath == 'N/A':
        return ''
    return xpath.replace("'", "\\'")


def escape_text(text: str) -> str:
    """Escape single quotes in text for Python string"""
    if not text:
        return ''
    return str(text).replace("'", "\\'")


def generate_navigate_code(step: str, url: str, indent: int = 12) -> str:
    """Generate navigation code"""
    ind = ' ' * indent
    code = f"{ind}# Step {step}: Navigate to {url}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    code += f"{ind}    page.goto('{url}')\n"
    code += f"{ind}    page.wait_for_load_state('networkidle')\n"
    code += f"{ind}    print('📍 Step {step}: Navigated to {url}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_navigate.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step}: Navigation failed: {{e}}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_navigate_failed.png')\n"
    code += f"{ind}\n"
    return code


def generate_wait_code(step: str, wait_time: int, indent: int = 12) -> str:
    """Generate wait code"""
    ind = ' ' * indent
    wait_ms = int(wait_time) if wait_time else 1000
    code = f"{ind}# Step {step}: Wait {wait_ms}ms\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    code += f"{ind}    page.wait_for_timeout({wait_ms})\n"
    code += f"{ind}    print('⏱️  Step {step}: Waited {wait_ms}ms')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_wait.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step}: Wait failed: {{e}}')\n"
    code += f"{ind}\n"
    return code


def generate_click_code(step: str, xpath: str, url: str, element_name: str, is_optional: bool, indent: int = 12, is_modal_step: bool = False) -> str:
    """Generate click code"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    code = f"{ind}# Step {step}: Click {element_name or 'element'}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    
    # Scope XPath to modal if needed
    if is_modal_step:
        if not xpath_escaped.startswith('(//*[@data-testid="create-submission-dialog"])'):
            xpath_escaped = f'(//*[@data-testid="create-submission-dialog"])//{xpath_escaped.lstrip("/")}'
        
        code += f"{ind}# Modal step - wait for modal and scope selector\n"
        code += f"{ind}# Wait for modal to be visible\n"
        code += f"{ind}try:\n"
        code += f"{ind}    modal = page.locator('[role=\"dialog\"], [data-testid=\"create-submission-dialog\"]').first\n"
        code += f"{ind}    modal.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}    print(f'✅ Step {step}: Modal is visible')\n"
        code += f"{ind}except Exception as modal_error:\n"
        code += f"{ind}    print(f'⚠️  Step {step}: Modal not found, continuing anyway: {{modal_error}}')\n"
    
    if is_optional:
        code += f"{ind}# Optional step - continue if element not found\n"
        code += f"{ind}try:\n"
    else:
        code += f"{ind}try:\n"
    
    code += f"{ind}    selector = 'xpath={xpath_escaped}'\n"
    code += f"{ind}    element = page.locator(selector).nth(0)\n"
    code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
    
    # For Create button in modal (Step 19), wait for it to be enabled and scroll into view
    is_create_button = ('create-data-submission-dialog-create-button' in xpath_escaped or 
                       ('create' in str(step).lower() and is_modal_step))
    if is_create_button:
        code += f"{ind}    # Wait for Create button to be enabled (form validation may disable it)\n"
        code += f"{ind}    # Wait up to 10 seconds for button to become enabled\n"
        code += f"{ind}    button_enabled = False\n"
        code += f"{ind}    for attempt in range(50):  # Wait up to 10 seconds (50 * 200ms)\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            is_disabled = element.evaluate('el => el.disabled || el.hasAttribute(\"disabled\")')\n"
        code += f"{ind}            if not is_disabled:\n"
        code += f"{ind}                button_enabled = True\n"
        code += f"{ind}                print(f'✅ Step {step}: Create button is enabled (attempt {{attempt + 1}})')\n"
        code += f"{ind}                break\n"
        code += f"{ind}            else:\n"
        code += f"{ind}                if attempt % 10 == 0:  # Print every 2 seconds\n"
        code += f"{ind}                    print(f'⏳ Step {step}: Waiting for Create button to be enabled... (attempt {{attempt + 1}}/50)')\n"
        code += f"{ind}        except Exception as check_error:\n"
        code += f"{ind}            print(f'⚠️  Step {step}: Error checking button state: {{check_error}}')\n"
        code += f"{ind}        page.wait_for_timeout(200)\n"
        code += f"{ind}    \n"
        code += f"{ind}    if not button_enabled:\n"
        code += f"{ind}        print(f'⚠️  Step {step}: Create button still disabled after 10 seconds, trying force click')\n"
        code += f"{ind}        # Scroll into view if needed\n"
        code += f"{ind}        element.scroll_into_view_if_needed()\n"
        code += f"{ind}        page.wait_for_timeout(500)\n"
        code += f"{ind}        # Try force click as fallback\n"
        code += f"{ind}        element.click(force=True)\n"
        code += f"{ind}        print(f'✅ Step {step}: Clicked Create button with force=True')\n"
        code += f"{ind}    else:\n"
        code += f"{ind}        # Scroll into view if needed\n"
        code += f"{ind}        element.scroll_into_view_if_needed()\n"
        code += f"{ind}        page.wait_for_timeout(500)  # Wait after scroll\n"
        code += f"{ind}        element.click()\n"
    else:
        code += f"{ind}    element.click()\n"
    code += f"{ind}    page.wait_for_timeout(1000)  # Wait after click\n"
    element_display = element_name or 'element'
    code += f"{ind}    print(f'✅ Step {step}: Clicked {element_display}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}.png')\n"
    
    if is_optional:
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    print(f'ℹ️  Step {step}: Element not found (optional) - continuing')\n"
    else:
        code += f"{ind}except Exception as e:\n"
        element_display = element_name or 'element'
        code += f"{ind}    print(f'❌ Step {step}: Failed to click {element_display}: {{e}}')\n"
        code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_failed.png')\n"
        code += f"{ind}    critical_failures.append(f'Step {step}: Click failed')\n"
    
    code += f"{ind}\n"
    return code


def generate_fill_code(step: str, xpath: str, text_value: str, url: str, element_name: str, functions: str, is_optional: bool, indent: int = 12, is_modal_step: bool = False) -> str:
    """Generate fill code"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    text_escaped = escape_text(text_value)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'input'
    
    # Handle TOTP
    is_totp = 'TOTP' in str(functions).upper() if functions else False
    if is_totp:
        text_escaped = "${TOTP_CODE}"  # Will be replaced at runtime
    
    # Scope XPath to modal if needed
    if is_modal_step:
        if not xpath_escaped.startswith('(//*[@data-testid="create-submission-dialog"])'):
            xpath_escaped = f'(//*[@data-testid="create-submission-dialog"])//{xpath_escaped.lstrip("/")}'
    
    code = f"{ind}# Step {step}: Fill {element_name or 'input'}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    
    if is_modal_step:
        code += f"{ind}# Modal step - wait for modal\n"
        code += f"{ind}try:\n"
        code += f"{ind}    modal = page.locator('[role=\"dialog\"], [data-testid=\"create-submission-dialog\"]').first\n"
        code += f"{ind}    modal.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}    print(f'✅ Step {step}: Modal is visible')\n"
        code += f"{ind}except Exception as modal_error:\n"
        code += f"{ind}    print(f'⚠️  Step {step}: Modal not found, continuing anyway: {{modal_error}}')\n"
    
    if is_totp:
        code += f"{ind}# TOTP field - code will be generated automatically\n"
    
    if is_optional:
        code += f"{ind}# Optional step - continue if element not found\n"
        code += f"{ind}try:\n"
    else:
        code += f"{ind}try:\n"
    
    if is_totp:
        # For TOTP, try multiple selectors first (don't wait for original selector yet)
        code += f"{ind}    # TOTP field - try multiple selectors (fallback approach)\n"
        code += f"{ind}    totp_selectors = [\n"
        code += f"{ind}        'input.one-time-code-input__input',\n"
        code += f"{ind}        \"input[autocomplete='one-time-code']\",\n"
        code += f"{ind}        \"input[type='text'][name='code']\",\n"
        code += f"{ind}        \"input[name='code']:not([type='hidden'])\",\n"
        code += f"{ind}        'lg-one-time-code-input input[type=\\'text\\']',\n"
        code += f"{ind}        'lg-validated-field input[type=\\'text\\']',\n"
        code += f"{ind}        'lg-one-time-code-input input',\n"
        code += f"{ind}        'input.one-time-code',\n"
        code += f"{ind}        'xpath={xpath_escaped}',  # Fallback to provided XPath\n"
        code += f"{ind}    ]\n"
        code += f"{ind}    selector_found = False\n"
        code += f"{ind}    element = None\n"
        code += f"{ind}    for totp_sel in totp_selectors:\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            test_elem = page.locator(totp_sel).first\n"
        code += f"{ind}            if test_elem.is_visible(timeout=2000):\n"
        code += f"{ind}                element = test_elem\n"
        code += f"{ind}                selector_found = True\n"
        code += f"{ind}                print(f'✅ Step {step}: Found TOTP field with selector: {{totp_sel}}')\n"
        code += f"{ind}                break\n"
        code += f"{ind}        except:\n"
        code += f"{ind}            continue\n"
        code += f"{ind}    if not selector_found:\n"
        code += f"{ind}        # Fallback to original selector\n"
        code += f"{ind}        selector = 'xpath={xpath_escaped}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'⚠️  Step {step}: TOTP field not found with fallback selectors, using original selector')\n"
    else:
        code += f"{ind}    selector = 'xpath={xpath_escaped}'\n"
        code += f"{ind}    element = page.locator(selector).nth(0)\n"
        code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
    
    if is_totp:
        code += f"{ind}    # Generate TOTP code\n"
        code += f"{ind}    try:\n"
        code += f"{ind}        import pyotp\n"
        code += f"{ind}    except ImportError:\n"
        code += f"{ind}        # Auto-install pyotp if missing\n"
        code += f"{ind}        import subprocess\n"
        code += f"{ind}        import sys\n"
        code += f"{ind}        print('⚠️  pyotp not found. Attempting to install...')\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyotp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        code += f"{ind}            import pyotp  # Try importing again after installation\n"
        code += f"{ind}            print('✅ pyotp installed successfully')\n"
        code += f"{ind}        except Exception as install_error:\n"
        code += f"{ind}            raise Exception('pyotp library not installed and auto-install failed. Please install manually with: pip3 install pyotp')\n"
        code += f"{ind}    try:\n"
        code += f"{ind}        secret_key = os.getenv('TOTP_SECRET_KEY')\n"
        code += f"{ind}        if not secret_key:\n"
        code += f"{ind}            raise ValueError('TOTP_SECRET_KEY not found in environment variables')\n"
        code += f"{ind}        totp = pyotp.TOTP(secret_key)\n"
        code += f"{ind}        totp_code = totp.now()\n"
        code += f"{ind}        print(f'🔐 Step {step}: Generated TOTP code: {{totp_code[:2]}}****')\n"
        code += f"{ind}        \n"
        code += f"{ind}        # For TOTP: clear field first, then use type() with delay (more reliable than fill())\n"
        code += f"{ind}        element.fill('')\n"
        code += f"{ind}        element.type(totp_code, delay=10)\n"
        code += f"{ind}        page.wait_for_timeout(200)\n"
        code += f"{ind}        print(f'✅ Step {step}: Filled TOTP code using type() method')\n"
        code += f"{ind}    except Exception as e:\n"
        code += f"{ind}        print(f'❌ Step {step}: Failed to generate/fill TOTP code: {{e}}')\n"
        code += f"{ind}        # Try fallback fill() method\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            element.fill(totp_code)\n"
        code += f"{ind}            print(f'✅ Step {step}: Filled TOTP code using fill() fallback')\n"
        code += f"{ind}        except Exception as fill_error:\n"
        code += f"{ind}            print(f'❌ Step {step}: fill() fallback also failed: {{fill_error}}')\n"
        code += f"{ind}            raise\n"
    else:
        # Handle TIMESTAMP variable replacement
        if '${TIMESTAMP}' in text_escaped:
            code += f"{ind}    # Replace ${{TIMESTAMP}} with actual timestamp value\n"
            code += f"{ind}    fill_value = '{text_escaped}'.replace('${{TIMESTAMP}}', TIMESTAMP)\n"
            code += f"{ind}    element.fill(fill_value)\n"
            element_display = element_name or 'input'
            code += f"{ind}    print(f'✅ Step {step}: Filled {element_display} with {{fill_value}}')\n"
        else:
            code += f"{ind}    element.fill('{text_escaped}')\n"
            element_display = element_name or 'input'
            code += f"{ind}    print(f'✅ Step {step}: Filled {element_display} with {text_escaped}')\n"
    
    code += f"{ind}    page.wait_for_timeout(500)  # Wait after fill\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}.png')\n"
    
    if is_optional:
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    print(f'ℹ️  Step {step}: Element not found (optional) - continuing')\n"
    else:
        code += f"{ind}except Exception as e:\n"
        element_display = element_name or 'input'
        code += f"{ind}    print(f'❌ Step {step}: Failed to fill {element_display}: {{e}}')\n"
        code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_failed.png')\n"
        code += f"{ind}    critical_failures.append(f'Step {step}: Fill failed')\n"
    
    code += f"{ind}\n"
    return code


def generate_verify_code(step: str, xpath: str, url: str, element_name: str, indent: int = 12) -> str:
    """Generate verify code"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    code = f"{ind}# Step {step}: Verify {element_name or 'element'}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    code += f"{ind}    selector = 'xpath={xpath_escaped}'\n"
    code += f"{ind}    element = page.locator(selector).nth(0)\n"
    code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
    element_display = element_name or 'element'
    code += f"{ind}    print(f'✅ Step {step}: Verified {element_display} is visible')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_verified.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step}: Verification failed: {{e}}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_failed.png')\n"
    code += f"{ind}    critical_failures.append(f'Step {step}: Verification failed')\n"
    code += f"{ind}\n"
    return code


def generate_playwright_from_excel(excel_file: Path, output_file: Path) -> Dict:
    """
    Generate Playwright script from Excel file
    
    Expected Excel columns:
    - Step: Step number/identifier
    - URL: Page URL
    - XPath: Element XPath
    - Object Type: button/input/link/etc. (optional)
    - Action: click/fill/verify/wait/navigate
    - Functions: TOTP, etc. (optional)
    - Text Value: For fill actions (optional)
    - Wait Time: For wait actions in ms (optional)
    - Optional: true/false (optional)
    
    Returns:
        Dict with success status and info
    """
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        
        # Normalize column names (case-insensitive, handle spaces)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Generate code
        test_body = ""
        errors = []
        current_url = None
        
        for idx, row in df.iterrows():
            step = str(row.get('step', idx + 1)).strip()
            url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else None
            xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
            action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else 'click'
            object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
            functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else ''
            text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else ''
            wait_time = row.get('wait_time', None)
            is_optional = str(row.get('optional', '')).strip().lower() in ['true', 'yes', '1', 'y']
            
            # Update current URL
            if url and url != 'N/A':
                current_url = url
            
            # Generate code based on action
            if action == 'navigate':
                if url:
                    test_body += generate_navigate_code(step, url)
                else:
                    errors.append(f"Step {step}: Navigate action requires URL")
            
            elif action == 'wait':
                test_body += generate_wait_code(step, wait_time or 1000)
            
            elif action == 'click':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    # Check if this is a modal step (after "Create a Data Submission" button click)
                    # Steps 16-19 are modal steps (dropdowns and form fields in the modal)
                    is_modal_step = False
                    try:
                        step_num = int(str(step).replace('a', '').replace('b', ''))
                        if step_num >= 16:  # Steps 16+ are in the modal
                            is_modal_step = True
                    except:
                        # If step is not a number (e.g., '16b'), check if it contains '16' or '17' or '18' or '19'
                        if '16' in str(step) or '17' in str(step) or '18' in str(step) or '19' in str(step):
                            is_modal_step = True
                    test_body += generate_click_code(step, xpath, current_url or '', element_name, is_optional, is_modal_step=is_modal_step)
                else:
                    errors.append(f"Step {step}: Click action requires XPath")
            
            elif action == 'fill':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'input'
                    # Check if this is a modal step (after "Create a Data Submission" button click)
                    # Steps 16-19 are modal steps (dropdowns and form fields in the modal)
                    is_modal_step = False
                    try:
                        step_num = int(str(step).replace('a', '').replace('b', ''))
                        if step_num >= 16:  # Steps 16+ are in the modal
                            is_modal_step = True
                    except:
                        # If step is not a number (e.g., '16b'), check if it contains '16' or '17' or '18' or '19'
                        if '16' in str(step) or '17' in str(step) or '18' in str(step) or '19' in str(step):
                            is_modal_step = True
                    test_body += generate_fill_code(step, xpath, text_value, current_url or '', element_name, functions, is_optional, is_modal_step=is_modal_step)
                else:
                    errors.append(f"Step {step}: Fill action requires XPath")
            
            elif action == 'verify':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    test_body += generate_verify_code(step, xpath, current_url or '', element_name)
                else:
                    errors.append(f"Step {step}: Verify action requires XPath")
            
            else:
                errors.append(f"Step {step}: Unknown action '{action}'")
        
        # Build full test script
        test_name = "test_excel_generated"
        test_script = f'''"""
Excel-Generated Playwright Test
Generated from: {excel_file.name}
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
    print(f'✅ Loaded environment variables from {{env_path}}')
else:
    print(f'⚠️  .env file not found at {{env_path}}')

def {test_name}():
    """Auto-generated test from Excel file"""
    critical_failures = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={{'width': 1920, 'height': 1080}})
        
        # Generate timestamp if needed
        TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
{test_body}
            if critical_failures:
                print(f"\\n❌ Test completed with {{len(critical_failures)}} failure(s)")
                for failure in critical_failures:
                    print(f"  - {{failure}}")
                raise Exception("Test failed")
            else:
                print("✅ Test completed successfully")
        except Exception as e:
            print(f"❌ Test failed: {{e}}")
            raise
        finally:
            browser.close()

if __name__ == '__main__':
    {test_name}()
'''
        
        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(test_script)
        
        return {
            'success': len(errors) == 0,
            'output_file': str(output_file),
            'rows_processed': len(df),
            'errors': errors
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'rows_processed': 0,
            'errors': [str(e)]
        }

