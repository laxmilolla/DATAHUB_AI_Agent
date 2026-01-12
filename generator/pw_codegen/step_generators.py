"""
Step Generators - Generate code for each step type
Extracted from playwright_generator.py
"""
import re
import logging
from typing import Dict, List, Optional

from generator.pw_utils.selector_utils import sanitize_filename, escape_string
from generator.pw_utils.registry_utils import backfill_element_id
from generator.pw_matchers.discovery_matcher import find_discovery_by_step, find_verification_discovery

logger = logging.getLogger(__name__)


def generate_navigate_step(step_num: int, step_text: str, action: Dict, indent: int) -> str:
    """Generate navigation code"""
    ind = ' ' * indent
    url = action.get('input', {}).get('url', '')
    
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    code += f"{ind}    page.goto('{url}')\n"
    code += f"{ind}    page.wait_for_load_state('networkidle')\n"
    code += f"{ind}    print('📍 Step {step_num}: Navigated to {url}')\n"
    code += f"{ind}    # Capture screenshot after navigation\n"
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_navigate.png')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: storage/screenshots/pw_step{step_num}_navigate.png')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: Navigation failed: {{e}}')\n"
    code += f"{ind}    # Capture screenshot even on failure\n"
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_navigate_failed.png')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: storage/screenshots/pw_step{step_num}_navigate_failed.png')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass\n"
    code += f"{ind}    # Continuing to next step despite failure (to capture screenshots)\n"
    code += f"{ind}\n"
    
    return code


def generate_wait_step(step_num: int, step_text: str, action: Dict, indent: int) -> str:
    """Generate wait code"""
    ind = ' ' * indent
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    
    # Extract wait duration from step text
    wait_match = re.search(r'wait (\d+) seconds?', step_text, re.IGNORECASE)
    if wait_match:
        duration_sec = int(wait_match.group(1))
        duration_ms = duration_sec * 1000
    else:
        # Default to 1 second if not specified
        duration_ms = 1000
    code += f"{ind}try:\n"
    code += f"{ind}    page.wait_for_timeout({duration_ms})\n"
    code += f"{ind}    print('⏱️  Step {step_num}: Waited {duration_ms}ms')\n"
    code += f"{ind}    # Capture screenshot after wait\n"
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_wait.png')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: storage/screenshots/pw_step{step_num}_wait.png')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: Wait failed: {{e}}')\n"
    code += f"{ind}    # Capture screenshot even on failure\n"
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_wait_failed.png')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: storage/screenshots/pw_step{step_num}_wait_failed.png')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass\n"
    code += f"{ind}    # Continuing to next step despite failure (to capture screenshots)\n"
    code += f"{ind}\n"
    
    return code


def generate_click_step(
    step_num: int,
    step_text: str,
    action: Dict,
    discovery: Optional[Dict],
    registry: Dict,
    indent: int,
    next_step_discovery: Optional[Dict] = None
) -> str:
    """
    Generate click code using PURE REGISTRY system - element_id only, no fallbacks
    All XPaths come from JSON registry ONLY
    """
    ind = ' ' * indent
    
    # Determine if this is an optional click (e.g., popup dismissal)
    is_optional = ('optional' in step_text.lower() or 
                   'if there is' in step_text.lower() or 
                   'if appears' in step_text.lower() or
                   '(if appears)' in step_text.lower())
    
    # Extract element name for display
    element_name = discovery.get('name', 'element') if discovery else 'element'
    
    # Get element_id from discovery (REQUIRED for pure registry system)
    element_id = discovery.get('element_id') if discovery else None
    
    # If element_id is missing, try to backfill from registry
    if not element_id and discovery:
        backfilled = backfill_element_id(discovery, registry)
        if backfilled:
            element_id = discovery.get('element_id')
    
    # Get selector from AI action (what AI actually used)
    action_selector = action.get('input', {}).get('selector', '') if action else ''
    
    if not element_id:
        # If no element_id, check if we can use AI's selector directly
        if is_optional and action_selector:
            return _generate_optional_click_code(
                step_num, step_text, element_name, discovery, action_selector, indent, next_step_discovery
            )
        elif is_optional:
            # Optional but no selector - skip
            code = f"{ind}# Step {step_num}: {step_text}\n"
            code += f"{ind}# ⚠️  No element_id and no selector found - skipping optional element\n"
            code += f"{ind}print('ℹ️  Step {step_num}: {element_name} not found in registry (optional)')\n\n"
            return code
        else:
            raise Exception(f"❌ Step {step_num}: Discovery missing element_id for '{element_name}' - cannot generate Playwright step. Registry must be complete.")
    
    # Sanitize for screenshot filename
    safe_name = sanitize_filename(element_name)
    screenshot_path = f"storage/screenshots/pw_step{step_num}_{safe_name}.png"
    
    # Detect element type from step text
    is_checkbox = 'checkbox' in step_text.lower()
    is_accordion = 'accordion' in step_text.lower() or 'expand' in step_text.lower()
    is_nested_accordion = discovery and discovery.get('metadata', {}).get('nested', False) if discovery else False
    
    # Escape element_id for Python string
    element_id_escaped = escape_string(element_id)
    
    # Generate pure registry code
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}# Using element_id: {element_id} (PURE REGISTRY - XPath from JSON ONLY)\n"
    code += f"{ind}element_id = '{element_id_escaped}'\n"
    code += f"{ind}\n"
    code += f"{ind}try:\n"
    code += f"{ind}    xpath = get_xpath_by_id(element_id, page.url)  # Lookup from JSON registry (prefers current page registry)\n"
    code += f"{ind}    selector = f'xpath={{xpath}}'\n"
    code += f"{ind}    element = page.locator(selector).nth(0)\n"
    
    if is_checkbox:
        code += f"{ind}    # Checkbox: Wait for attached, then scroll into view\n"
        code += f"{ind}    element.wait_for(state='attached', timeout=10000)\n"
        code += f"{ind}    element.scroll_into_view_if_needed()\n"
        code += f"{ind}    page.wait_for_timeout(500)\n"
        code += f"{ind}    # Check if checkbox is already checked\n"
        code += f"{ind}    is_checked = element.is_checked()\n"
        code += f"{ind}    if is_checked:\n"
        code += f"{ind}        print(f'ℹ️  Checkbox already checked, skipping')\n"
        code += f"{ind}    else:\n"
        code += f"{ind}        element.click(force=True)\n"
        code += f"{ind}        page.wait_for_timeout(1000)\n"
        code += f"{ind}        if element.is_checked():\n"
        code += f"{ind}            print(f'✅ Step {step_num}: Checkbox checked (element_id: {{element_id}})')\n"
        code += f"{ind}        else:\n"
        code += f"{ind}            raise Exception(f'Checkbox click did not change state')\n"
        code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
    elif is_accordion:
        code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
        if is_nested_accordion:
            code += f"{ind}    # Nested accordion: always click\n"
            code += f"{ind}    element.click()\n"
            code += f"{ind}    page.wait_for_timeout(1000)\n"
            code += f"{ind}    print(f'✅ Step {step_num}: Clicked nested accordion (element_id: {{element_id}})')\n"
        else:
            code += f"{ind}    # Top-level accordion: check state\n"
            code += f"{ind}    initial_aria_expanded = element.get_attribute('aria-expanded')\n"
            code += f"{ind}    if initial_aria_expanded == 'true':\n"
            code += f"{ind}        print(f'ℹ️  Accordion already expanded, skipping click')\n"
            code += f"{ind}        page.wait_for_timeout(1000)\n"
            code += f"{ind}    else:\n"
            code += f"{ind}        element.click()\n"
            code += f"{ind}        page.wait_for_timeout(500)\n"
            code += f"{ind}        current_aria_expanded = element.get_attribute('aria-expanded')\n"
            code += f"{ind}        if current_aria_expanded == 'true':\n"
            code += f"{ind}            print(f'✅ Step {step_num}: Accordion expanded: {{initial_aria_expanded}} → {{current_aria_expanded}}')\n"
            code += f"{ind}        page.wait_for_timeout(1000)\n"
        code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
    else:
        # Detect if this is a popup dismissal button (Continue, OK, Accept, etc.)
        is_popup_dismissal = any(keyword in step_text.lower() or keyword in element_name.lower() 
                                for keyword in ['continue', 'ok', 'accept', 'dismiss', 'close', 'got it'])
        
        code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}    element.click()\n"
        code += f"{ind}    page.wait_for_timeout(1000)  # Wait after click (matches AI behavior)\n"
        
        # If popup dismissal button, wait for dialog to disappear and next element to be clickable
        if is_popup_dismissal:
            code += _generate_dialog_dismissal_code(indent + 4, next_step_discovery)
        
        code += f"{ind}    print(f'✅ Step {step_num}: Clicked {element_name} (element_id: {{element_id}})')\n"
        code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
    
    code += f"{ind}except Exception as e:\n"
    # Always capture screenshot even on failure
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='{screenshot_path.replace('.png', '_failed.png')}')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: {screenshot_path.replace('.png', '_failed.png')}')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass  # Screenshot capture failed, continue anyway\n"
    if is_optional:
        # Optional steps: log and continue (don't fail test)
        code += f"{ind}    print(f'ℹ️  Step {step_num}: {element_name} not found (optional step): {{e}}')\n"
        code += f"{ind}    # Optional step - continuing without failing test\n"
    else:
        code += f"{ind}    print(f'❌ Step {step_num}: Failed to click {element_name} (element_id: {{element_id}}): {{e}}')\n"
        # Don't raise - continue to next step to capture more screenshots
        code += f"{ind}    # Continuing to next step despite failure (to capture screenshots)\n"
    code += f"{ind}\n"
    
    return code


def _generate_optional_click_code(
    step_num: int,
    step_text: str,
    element_name: str,
    discovery: Optional[Dict],
    action_selector: str,
    indent: int,
    next_step_discovery: Optional[Dict]
) -> str:
    """Generate code for optional click (popup dismissal, etc.)"""
    ind = ' ' * indent
    
    # Extract selector from discovery to determine constant name
    discovery_selector = discovery.get('original_query', '') if discovery else ''
    if not discovery_selector:
        discovery_selector = discovery.get('final_selector', '') if discovery else ''
    selector_to_use = discovery_selector if discovery_selector else action_selector
    
    # Escape for Python string
    selector_escaped = escape_string(selector_to_use)
    
    # Find matching optional selector constant (embedded in test)
    disc_name = discovery.get('name', '') if discovery else ''
    name_for_constant = disc_name if disc_name else element_name
    safe_name = sanitize_filename(name_for_constant)
    constant_name = f"OPTIONAL_{safe_name.upper().replace('-', '_')}_SELECTOR"
    
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}# ⚠️  No element_id found - using test-specific selector (embedded in test, not hardcoded)\n"
    code += f"{ind}# Use selector from test-specific constants (matches AI behavior)\n"
    code += f"{ind}try:\n"
    code += f"{ind}    selector = {constant_name}\n"
    code += f"{ind}except NameError:\n"
    code += f"{ind}    # Fallback if constant not defined\n"
    code += f"{ind}    selector = '{selector_escaped}'\n"
    code += f"{ind}\n"
    code += f"{ind}try:\n"
    code += f"{ind}    element = page.locator(selector).nth(0)\n"
    code += f"{ind}    if element.is_visible(timeout=10000):\n"
    code += f"{ind}        element.click()\n"
    code += f"{ind}        page.wait_for_timeout(1000)  # Wait after click (matches AI behavior)\n"
    code += _generate_dialog_dismissal_code(indent + 8, next_step_discovery)
    code += f"{ind}        print(f'✅ Step {step_num}: Clicked (using selector from discovery: {{selector}})')\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_{sanitize_filename(element_name)}.png')\n"
    code += f"{ind}    else:\n"
    code += f"{ind}        print(f'ℹ️  Step {step_num}: {element_name} not found (optional)')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'ℹ️  Step {step_num}: {element_name} not found (optional): {{e}}')\n\n"
    
    return code


def _generate_dialog_dismissal_code(indent: int, next_step_discovery: Optional[Dict]) -> str:
    """Generate code to wait for dialog dismissal and next element to be clickable"""
    ind = ' ' * indent
    code = ""
    
    code += f"{ind}# Wait for dialog to disappear (if popup was dismissed)\n"
    code += f"{ind}try:\n"
    code += f"{ind}    # Wait for dialog to be detached (completely removed from DOM) - most reliable\n"
    code += f"{ind}    page.locator('[data-testid=\"system-use-warning-dialog\"]').wait_for(state='detached', timeout=5000)\n"
    code += f"{ind}except:\n"
    code += f"{ind}    # Fallback: dialog might stay in DOM but hidden\n"
    code += f"{ind}    try:\n"
    code += f"{ind}        page.locator('[data-testid=\"system-use-warning-dialog\"]').wait_for(state='hidden', timeout=3000)\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass  # Dialog may not exist or already dismissed\n"
    code += f"{ind}\n"
    code += f"{ind}# CRITICAL: Wait for next step's element to be clickable (not just visible)\n"
    code += f"{ind}# This ensures the dialog is fully dismissed and not blocking interactions\n"
    if next_step_discovery and next_step_discovery.get('element_id'):
        next_element_id = next_step_discovery.get('element_id')
        code += f"{ind}try:\n"
        code += f"{ind}    next_element_id = '{next_element_id}'\n"
        code += f"{ind}    next_xpath = get_xpath_by_id(next_element_id, page.url)\n"
        code += f"{ind}    next_element = page.locator(f'xpath={{next_xpath}}').nth(0)\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Wait for element to be visible first\n"
        code += f"{ind}    next_element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}    \n"
        code += f"{ind}    # CRITICAL: Wait for element to be clickable (not blocked by dialog)\n"
        code += f"{ind}    # Check if dialog is blocking by trying to click the element\n"
        code += f"{ind}    for attempt in range(20):  # Increased attempts (4 seconds max)\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            # Check if dialog still exists and is visible\n"
        code += f"{ind}            dialog_count = page.locator('[data-testid=\"system-use-warning-dialog\"]').count()\n"
        code += f"{ind}            if dialog_count == 0:\n"
        code += f"{ind}                # Dialog is gone - element should be clickable\n"
        code += f"{ind}                break\n"
        code += f"{ind}            \n"
        code += f"{ind}            # Check if dialog is visible (might be in DOM but hidden)\n"
        code += f"{ind}            dialog_visible = page.locator('[data-testid=\"system-use-warning-dialog\"]').first.is_visible(timeout=100)\n"
        code += f"{ind}            if not dialog_visible:\n"
        code += f"{ind}                # Dialog is hidden - element should be clickable\n"
        code += f"{ind}                break\n"
        code += f"{ind}            \n"
        code += f"{ind}            # Dialog still visible - wait a bit more\n"
        code += f"{ind}            page.wait_for_timeout(200)\n"
        code += f"{ind}        except:\n"
        code += f"{ind}            # Dialog check failed - assume it's gone\n"
        code += f"{ind}            break\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Additional wait to ensure animations complete\n"
        code += f"{ind}    page.wait_for_timeout(500)\n"
        code += f"{ind}    \n"
        code += f"{ind}    print(f'✅ Dialog dismissed, next element ({{next_element_id}}) ready')\n"
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    print(f'⚠️  Could not verify next element clickable: {{e}}')\n"
        code += f"{ind}    # Continue anyway - next step will handle its own timeout\n"
        code += f"{ind}    pass\n"
    else:
        code += f"{ind}# No next step discovery - wait for dialog to disappear and animations\n"
        code += f"{ind}page.wait_for_timeout(1500)  # Increased wait time\n"
    
    return code


def generate_fill_step(
    step_num: int,
    step_text: str,
    action: Dict,
    discovery: Optional[Dict],
    registry: Dict,
    indent: int
) -> str:
    """
    Generate fill code for input fields (username, password, TOTP, etc.)
    """
    ind = ' ' * indent
    
    # Get input parameters from action
    input_params = action.get('input', {}) if action else {}
    selector = input_params.get('selector', '')
    text = input_params.get('text', '')
    
    # Extract field name from step text (e.g., "Enter Username" -> "Username")
    field_name = 'field'
    if 'username' in step_text.lower() or 'email' in step_text.lower():
        field_name = 'Username'
    elif 'password' in step_text.lower():
        field_name = 'Password'
    elif 'totp' in step_text.lower() or 'one-time' in step_text.lower() or 'authenticator' in step_text.lower():
        field_name = 'TOTP'
    else:
        # Try to extract from step text
        match = re.search(r'enter\s+(?:the\s+)?(.+?)\s+as', step_text, re.IGNORECASE)
        if match:
            field_name = match.group(1).strip()
    
    # Check if this is a TOTP step (check both step_text and action/discovery)
    is_totp_step = any(keyword in step_text.lower() for keyword in ['totp', 'one-time', 'one time', '2fa', 'two-factor', 'authenticator code', 'security code'])
    
    # Also check action text and discovery name for TOTP indicators
    if not is_totp_step and action:
        action_text = str(action.get('input', {})).lower() + str(action.get('result', '')).lower()
        is_totp_step = any(keyword in action_text for keyword in ['totp', 'one-time', 'one time', '2fa', 'two-factor', 'authenticator', 'otp'])
    
    # Also check discovery name/selector for TOTP indicators
    if not is_totp_step and discovery:
        disc_name = str(discovery.get('name', '')).lower()
        disc_selector = str(discovery.get('final_selector', '') or discovery.get('original_query', '')).lower()
        is_totp_step = any(keyword in (disc_name + disc_selector) for keyword in ['totp', 'one-time', 'one-time-code', 'authenticator'])
    
    # Get element_id from discovery (REQUIRED for pure registry system)
    element_id = discovery.get('element_id') if discovery else None
    
    # If element_id is missing, try to backfill from registry
    if not element_id and discovery:
        backfilled = backfill_element_id(discovery, registry)
        if backfilled:
            element_id = discovery.get('element_id')
    
    # Escape text for Python string
    text_escaped = escape_string(text)
    
    # Generate code
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    
    # TOTP fields may not have element_id (dynamic fields) - allow fallback to action selector
    use_registry_lookup = element_id is not None
    
    if use_registry_lookup:
        code += f"{ind}# Using element_id: {element_id} (PURE REGISTRY - XPath from JSON ONLY)\n"
        element_id_escaped = escape_string(element_id)
        code += f"{ind}element_id = '{element_id_escaped}'\n"
    elif is_totp_step:
        # TOTP fallback: use action selector (TOTP fields are often dynamic and may not be in registry)
        code += f"{ind}# TOTP field - using action selector (element_id not available, TOTP fields are dynamic)\n"
        selector_escaped = escape_string(selector)
        code += f"{ind}selector = '{selector_escaped}'\n"
    else:
        # Non-TOTP fields MUST have element_id
        raise Exception(f"❌ Step {step_num}: Discovery missing element_id for '{field_name}' - cannot generate Playwright step. Registry must be complete.")
    
    code += f"{ind}\n"
    
    if is_totp_step:
        code += f"{ind}# TOTP step - generate code dynamically\n"
        code += f"{ind}import sys\n"
        code += f"{ind}from pathlib import Path\n"
        code += f"{ind}# Add project root to path for utils import\n"
        code += f"{ind}project_root = Path(__file__).parent.parent.parent\n"
        code += f"{ind}if str(project_root) not in sys.path:\n"
        code += f"{ind}    sys.path.insert(0, str(project_root))\n"
        code += f"{ind}from utils.otp_helper import generate_otp\n"
        code += f"{ind}import os\n"
        code += f"{ind}try:\n"
        code += f"{ind}    totp_code = generate_otp()  # Uses TOTP_SECRET_KEY from environment\n"
        code += f"{ind}    print(f'🔐 Step {step_num}: Generated TOTP code: {{totp_code[:2]}}****')\n"
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    raise Exception(f'Failed to generate TOTP code: {{e}}')\n"
        code += f"{ind}fill_text = totp_code\n"
    else:
        code += f"{ind}fill_text = '{text_escaped}'\n"
    
    code += f"{ind}\n"
    code += f"{ind}try:\n"
    
    if use_registry_lookup:
        code += f"{ind}    xpath = get_xpath_by_id(element_id, page.url)  # Lookup from JSON registry (prefers current page registry)\n"
        code += f"{ind}    selector = f'xpath={{xpath}}'\n"
        code += f"{ind}    element = page.locator(selector).nth(0)\n"
    else:
        # TOTP fallback: use multiple selectors if needed
        code += f"{ind}    # TOTP field - try multiple selectors if needed\n"
        code += f"{ind}    totp_selectors = [\n"
        code += f"{ind}        \"input.one-time-code-input__input\",\n"
        code += f"{ind}        \"input[autocomplete='one-time-code']\",\n"
        code += f"{ind}        \"input[type='text'][name='code']\",\n"
        code += f"{ind}        \"input[name='code']:not([type='hidden'])\",\n"
        code += f"{ind}        \"lg-one-time-code-input input[type='text']\",\n"
        code += f"{ind}        selector,  # Fallback to action selector\n"
        code += f"{ind}    ]\n"
        code += f"{ind}    selector_found = False\n"
        code += f"{ind}    for totp_sel in totp_selectors:\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            test_elem = page.locator(totp_sel).first\n"
        code += f"{ind}            if test_elem.is_visible(timeout=1000):\n"
        code += f"{ind}                selector = totp_sel\n"
        code += f"{ind}                element = test_elem\n"
        code += f"{ind}                selector_found = True\n"
        code += f"{ind}                break\n"
        code += f"{ind}        except:\n"
        code += f"{ind}            continue\n"
        code += f"{ind}    if not selector_found:\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
    
    code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
    
    code += f"{ind}    \n"
    code += f"{ind}    # Check if field is readonly/disabled\n"
    code += f"{ind}    is_readonly = element.evaluate('el => el.readOnly || el.disabled')\n"
    code += f"{ind}    if is_readonly:\n"
    code += f"{ind}        raise Exception(f'Field {{selector}} is readonly or disabled')\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Fill the field\n"
    code += f"{ind}    element.fill(fill_text)\n"
    code += f"{ind}    page.wait_for_timeout(500)  # Wait after fill (matches AI behavior)\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Verify the value was filled correctly\n"
    code += f"{ind}    actual_value = element.input_value()\n"
    code += f"{ind}    if actual_value == fill_text:\n"
    code += f"{ind}        print(f'✅ Step {step_num}: Filled {field_name} (verified)')\n"
    code += f"{ind}    else:\n"
    code += f"{ind}        print(f'⚠️  Step {step_num}: Fill mismatch - expected {{fill_text[:20]}}..., got {{actual_value[:20]}}...')\n"
    
    # Sanitize field name for screenshot filename
    safe_name = sanitize_filename(field_name)
    screenshot_path = f"storage/screenshots/pw_step{step_num}_{safe_name}.png"
    code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
    code += f"{ind}except Exception as e:\n"
    # Always capture screenshot even on failure
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_{sanitize_filename(field_name)}_failed.png')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: storage/screenshots/pw_step{step_num}_{sanitize_filename(field_name)}_failed.png')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass  # Screenshot capture failed, continue anyway\n"
    if use_registry_lookup:
        code += f"{ind}    print(f'❌ Step {step_num}: Failed to fill {field_name} (element_id: {{element_id}}): {{e}}')\n"
    else:
        code += f"{ind}    print(f'❌ Step {step_num}: Failed to fill {field_name} (selector: {{selector}}): {{e}}')\n"
    # Don't raise - continue to next step to capture more screenshots
    code += f"{ind}    # Continuing to next step despite failure (to capture screenshots)\n"
    code += f"{ind}\n"
    
    return code


def generate_verify_step(
    step_num: int,
    step_text: str,
    action: Dict,
    discovery: Optional[Dict],
    indent: int
) -> str:
    """Generate verification code"""
    ind = ' ' * indent
    
    if not discovery or discovery.get('discovery_method') != 'table_verification':
        # Generic verification
        code = f"{ind}# Step {step_num}: {step_text}\n"
        code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
        code += f"{ind}print('⚠️  Step {step_num}: Verification performed by AI - add specific assertions if needed')\n\n"
        return code
    
    # Table column verification
    metadata = discovery.get('metadata', {})
    column_name = metadata.get('column_name', 'unknown')
    expected_value = metadata.get('expected_value', '')
    
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}# Verify: All rows in column contain expected value (values from test-specific constants - NO HARDCODING)\n"
    code += f"{ind}# Use verification values embedded in test (test-specific, not in registry)\n"
    code += f"{ind}column_name = VERIFY_COLUMN_NAME\n"
    code += f"{ind}expected_value = VERIFY_EXPECTED_VALUE\n"
    code += f"{ind}if not column_name or not expected_value:\n"
    code += f"{ind}    raise Exception('❌ Verification values missing: VERIFY_COLUMN_NAME or VERIFY_EXPECTED_VALUE not defined')\n"
    code += f"{ind}\n"
    code += f"{ind}try:\n"
    code += f"{ind}    print(f'🔍 Step {step_num}: Verifying table column \"{{column_name}}\" contains \"{{expected_value}}\"...')\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Find table\n"
    code += f"{ind}    table = page.locator('table').nth(0)\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Find column index by header text\n"
    code += f"{ind}    headers = table.locator('thead th, thead td').all_text_contents()\n"
    code += f"{ind}    column_index = -1\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Try exact match (case-insensitive)\n"
    code += f"{ind}    for i, header in enumerate(headers):\n"
    code += f"{ind}        if column_name.lower() == header.lower().strip():\n"
    code += f"{ind}            column_index = i\n"
    code += f"{ind}            break\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Fallback: partial match\n"
    code += f"{ind}    if column_index == -1:\n"
    code += f"{ind}        for i, header in enumerate(headers):\n"
    code += f"{ind}            if column_name.lower() in header.lower():\n"
    code += f"{ind}                column_index = i\n"
    code += f"{ind}                break\n"
    code += f"{ind}    \n"
    code += f"{ind}    if column_index == -1:\n"
    code += f"{ind}        raise Exception(f\"Column '{{column_name}}' not found. Available: {{headers}}\")\n"
    code += f"{ind}    \n"
    code += f"{ind}    print(f'📋 Step {step_num}: Found column \"{{column_name}}\" at index {{column_index}}')\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Verify all rows\n"
    code += f"{ind}    rows = table.locator('tbody tr').all()\n"
    code += f"{ind}    total_rows = len(rows)\n"
    code += f"{ind}    matching_rows = 0\n"
    code += f"{ind}    \n"
    code += f"{ind}    print(f'🔍 Step {step_num}: Checking {{total_rows}} rows...')\n"
    code += f"{ind}    \n"
    code += f"{ind}    for row_idx, row in enumerate(rows):\n"
    code += f"{ind}        cells = row.locator('td').all()\n"
    code += f"{ind}        if column_index < len(cells):\n"
    code += f"{ind}            cell_text = cells[column_index].inner_text().strip()\n"
    code += f"{ind}            if expected_value.lower() in cell_text.lower():\n"
    code += f"{ind}                matching_rows += 1\n"
    code += f"{ind}            else:\n"
    code += f"{ind}                print(f'⚠️  Row {{row_idx + 1}}: Expected \"{{expected_value}}\", got \"{{cell_text}}\"')\n"
    code += f"{ind}    \n"
    code += f"{ind}    # Assert all rows match\n"
    code += f"{ind}    assert matching_rows == total_rows, f\"Only {{matching_rows}}/{{total_rows}} rows match\"\n"
    code += f"{ind}    \n"
    code += f"{ind}    print(f'✅ Step {step_num}: VERIFICATION PASSED: All {{total_rows}} rows contain \"{{expected_value}}\"')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_verify.png')\n"
    code += f"{ind}    print('📸 Screenshot: storage/screenshots/pw_step{step_num}_verify.png')\n"
    code += f"{ind}    \n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: VERIFICATION FAILED: {{e}}')\n"
    code += f"{ind}    try:\n"
    code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_verify_failed.png')\n"
    code += f"{ind}        print(f'📸 Screenshot saved: storage/screenshots/pw_step{step_num}_verify_failed.png')\n"
    code += f"{ind}    except:\n"
    code += f"{ind}        pass  # Screenshot capture failed, continue anyway\n"
    # Don't raise - continue to next step to capture more screenshots
    code += f"{ind}    # Continuing to next step despite failure (to capture screenshots)\n\n"
    
    return code

