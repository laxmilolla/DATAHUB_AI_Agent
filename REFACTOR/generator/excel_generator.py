"""
Excel-Based Playwright Generator
Reads Excel file with Step, URL, XPath, Action, etc. and generates Playwright code
Registry-aware: Uses element registry instead of hard-coded XPaths
"""
import pandas as pd
import re
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlparse


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


def detect_registry_files_from_urls(urls: List[str], element_maps_dir: Path) -> List[str]:
    """
    Detect registry files needed based on URLs in Excel file
    
    Args:
        urls: List of URLs from Excel file
        element_maps_dir: Base directory for element maps (usually 'element_maps')
    
    Returns:
        List of relative registry file paths
    """
    registry_paths = set()
    
    for url in urls:
        if not url or url == 'N/A':
            continue
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.split(':')[0]  # Remove port if present
            
            # Extract page name from URL path
            path_parts = [p for p in parsed.path.split('/') if p]
            if not path_parts:
                page = 'home'
            elif path_parts[-1] == 'explore':
                page = 'explore'
            else:
                page = path_parts[-1].split('?')[0].split('#')[0]
                if not page:
                    page = 'home'
            
            # Sanitize page name
            page_sanitized = re.sub(r'[^\w\-_\.]', '', page)
            if not page_sanitized:
                page_sanitized = 'home'
            
            # Check if registry file exists
            domain_dir = element_maps_dir / domain
            if domain_dir.exists():
                # Try exact match: page_page.json
                registry_file = domain_dir / f'{page_sanitized}_page.json'
                if registry_file.exists():
                    registry_paths.add(f'element_maps/{domain}/{page_sanitized}_page.json')
                    continue
                
                # Try without extension
                if '.' in page_sanitized:
                    page_no_ext = page_sanitized.rsplit('.', 1)[0]
                    registry_file = domain_dir / f'{page_no_ext}_page.json'
                    if registry_file.exists():
                        registry_paths.add(f'element_maps/{domain}/{page_no_ext}_page.json')
                        continue
                
                # Fallback to common page names
                for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
                    registry_file = domain_dir / page_name
                    if registry_file.exists():
                        registry_paths.add(f'element_maps/{domain}/{page_name}')
                        break
                
                # If no match found, try any JSON file in domain directory
                if not any(f'element_maps/{domain}' in p for p in registry_paths):
                    json_files = list(domain_dir.glob('*.json'))
                    if json_files:
                        registry_paths.add(f'element_maps/{domain}/{json_files[0].name}')
        except Exception as e:
            # Skip invalid URLs
            continue
    
    return sorted(list(registry_paths))


def build_registry_code(registry_files: List[str]) -> str:
    """
    Build registry loading code and helper functions
    
    Args:
        registry_files: List of relative registry file paths
    
    Returns:
        String containing registry loading code and helper functions
    """
    if not registry_files:
        # No registries - return empty string (tests will use hard-coded XPaths)
        return ""
    
    # Format registry paths list
    registry_paths_list_str = "[\n"
    for reg_path in registry_files:
        registry_paths_list_str += f"    '{reg_path}',\n"
    registry_paths_list_str += "]"
    
    code = f'''# ============================================================================
# MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
# ============================================================================
# Automatically detects and loads all registry files needed based on URLs in Excel
REGISTRY_PATHS = {registry_paths_list_str}

# Load registries per domain/page (for dynamic loading based on current page)
# NO MERGE: Keep registries separate to avoid conflicts when same element name exists in multiple registries
REGISTRIES_BY_PATH = {{}}  # registry_path -> registry_data
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
            print(f"✅ Loaded registry: {{len(registry_data.get('elements', {{}}))}} elements from {{registry_path.name}}")
        else:
            print(f"⚠️  Registry file not found: {{registry_path}}")
    except Exception as e:
        print(f"⚠️  Failed to load registry {{registry_path_str}}: {{e}}")

if loaded_count > 0:
    total_elements = sum(len(reg.get('elements', {{}})) for reg in REGISTRIES_BY_PATH.values())
    total_ids = sum(len(reg.get('id_index', {{}})) for reg in REGISTRIES_BY_PATH.values())
    print(f"✅ Loaded {{loaded_count}} registries: {{total_elements}} total elements, {{total_ids}} total IDs (separate, not merged)")

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
            current_registry = page_registry.get('elements', {{}})
            current_id_index = page_registry.get('id_index', {{}})
            
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
                id_index = registry_data.get('id_index', {{}})
                elements = registry_data.get('elements', {{}})
                
                if element_id in id_index:
                    registry_key = id_index[element_id]
                    if registry_key in elements:
                        xpath = elements[registry_key].get('xpath')
                        if xpath:
                            return xpath
    
    # STEP 3: Last resort - search ALL registries (cross-domain fallback)
    for registry_data in REGISTRIES_BY_PATH.values():
        id_index = registry_data.get('id_index', {{}})
        elements = registry_data.get('elements', {{}})
        
        if element_id in id_index:
            registry_key = id_index[element_id]
            if registry_key in elements:
                xpath = elements[registry_key].get('xpath')
                if xpath:
                    return xpath
    
    # Not found in any registry
    raise Exception(f"❌ element_id '{{element_id}}' not found in any registry id_index")

'''
    return code


def lookup_element_id_by_xpath(xpath: str, url: str, registry_files: List[str], element_maps_dir: Path) -> Optional[str]:
    """
    Look up element_id from registry by matching XPath
    
    Args:
        xpath: XPath to find
        url: URL for context (to determine which registry to check first)
        registry_files: List of registry file paths
        element_maps_dir: Base directory for element maps
    
    Returns:
        element_id if found, None otherwise
    """
    if not xpath or xpath == 'N/A':
        return None
    
    # Parse URL to determine domain/page
    parsed = urlparse(url) if url else None
    domain = parsed.netloc.split(':')[0] if parsed else None
    
    # Try registries in order: page-specific first, then domain, then all
    registries_to_check = []
    
    # Priority 1: Page-specific registry (if URL provided)
    if domain and url:
        for reg_path in registry_files:
            if domain in reg_path and url.split('/')[-1].split('?')[0] in reg_path:
                registries_to_check.insert(0, reg_path)
    
    # Priority 2: Domain-specific registries
    if domain:
        for reg_path in registry_files:
            if domain in reg_path and reg_path not in registries_to_check:
                registries_to_check.append(reg_path)
    
    # Priority 3: All other registries
    for reg_path in registry_files:
        if reg_path not in registries_to_check:
            registries_to_check.append(reg_path)
    
    # Search registries
    for reg_path_str in registries_to_check:
        try:
            # reg_path_str is relative (e.g., 'element_maps/domain/page.json')
            # element_maps_dir is absolute path to element_maps directory
            # So we need to construct the full path correctly
            if reg_path_str.startswith('element_maps/'):
                # Remove 'element_maps/' prefix and append to element_maps_dir
                relative_path = reg_path_str.replace('element_maps/', '')
                registry_file = element_maps_dir / relative_path
            else:
                # Assume it's already relative to element_maps
                registry_file = element_maps_dir / reg_path_str
            
            if not registry_file.exists():
                continue
            
            with open(registry_file, 'r') as f:
                registry_data = json.load(f)
            
            elements = registry_data.get('elements', {})
            id_index = registry_data.get('id_index', {})
            
            # Search for matching XPath
            for key, element_data in elements.items():
                element_xpath = element_data.get('xpath', '')
                if element_xpath == xpath:
                    # Found match - get element_id
                    element_id = element_data.get('element_id')
                    if element_id:
                        return element_id
            
            # Also check id_index for reverse lookup
            for element_id, registry_key in id_index.items():
                if registry_key in elements:
                    element_xpath = elements[registry_key].get('xpath', '')
                    if element_xpath == xpath:
                        return element_id
        except Exception:
            continue
    
    return None


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


def generate_click_code(step: str, xpath: str, url: str, element_name: str, is_optional: bool, indent: int = 12, is_modal_step: bool = False, element_id: Optional[str] = None) -> str:
    """Generate click code - registry-aware"""
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
    
    # Use registry lookup if element_id is available
    if element_id:
        element_id_escaped = escape_xpath(element_id)
        code += f"{ind}    # Try registry lookup first\n"
        code += f"{ind}    try:\n"
        code += f"{ind}        xpath = get_xpath_by_id('{element_id_escaped}', page.url())\n"
        code += f"{ind}        selector = f'xpath={{xpath}}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'✅ Step {step}: Using registry element_id: {element_id_escaped}')\n"
        code += f"{ind}    except Exception as registry_error:\n"
        code += f"{ind}        # Fallback to hard-coded XPath\n"
        code += f"{ind}        selector = 'xpath={xpath_escaped}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'⚠️  Step {step}: Registry lookup failed, using fallback XPath: {{registry_error}}')\n"
    else:
        # No element_id - use hard-coded XPath (with warning)
        code += f"{ind}    # Using hard-coded XPath (element not found in registry)\n"
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


def generate_fill_code(step: str, xpath: str, text_value: str, url: str, element_name: str, functions: str, is_optional: bool, indent: int = 12, is_modal_step: bool = False, element_id: Optional[str] = None) -> str:
    """Generate fill code - registry-aware"""
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
        # Use registry lookup if element_id is available
        if element_id:
            element_id_escaped = escape_xpath(element_id)
            code += f"{ind}    # Try registry lookup first\n"
            code += f"{ind}    try:\n"
            code += f"{ind}        xpath = get_xpath_by_id('{element_id_escaped}', page.url())\n"
            code += f"{ind}        selector = f'xpath={{xpath}}'\n"
            code += f"{ind}        element = page.locator(selector).nth(0)\n"
            code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
            code += f"{ind}        print(f'✅ Step {step}: Using registry element_id: {element_id_escaped}')\n"
            code += f"{ind}    except Exception as registry_error:\n"
            code += f"{ind}        # Fallback to hard-coded XPath\n"
            code += f"{ind}        selector = 'xpath={xpath_escaped}'\n"
            code += f"{ind}        element = page.locator(selector).nth(0)\n"
            code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
            code += f"{ind}        print(f'⚠️  Step {step}: Registry lookup failed, using fallback XPath: {{registry_error}}')\n"
        else:
            # No element_id - use hard-coded XPath (with warning)
            code += f"{ind}    # Using hard-coded XPath (element not found in registry)\n"
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


def generate_verify_code(step: str, xpath: str, url: str, element_name: str, indent: int = 12, element_id: Optional[str] = None) -> str:
    """Generate verify code - registry-aware"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    code = f"{ind}# Step {step}: Verify {element_name or 'element'}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    
    # Use registry lookup if element_id is available
    if element_id:
        element_id_escaped = escape_xpath(element_id)
        code += f"{ind}    # Try registry lookup first\n"
        code += f"{ind}    try:\n"
        code += f"{ind}        xpath = get_xpath_by_id('{element_id_escaped}', page.url())\n"
        code += f"{ind}        selector = f'xpath={{xpath}}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'✅ Step {step}: Using registry element_id: {element_id_escaped}')\n"
        code += f"{ind}    except Exception as registry_error:\n"
        code += f"{ind}        # Fallback to hard-coded XPath\n"
        code += f"{ind}        selector = 'xpath={xpath_escaped}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'⚠️  Step {step}: Registry lookup failed, using fallback XPath: {{registry_error}}')\n"
    else:
        # No element_id - use hard-coded XPath (with warning)
        code += f"{ind}    # Using hard-coded XPath (element not found in registry)\n"
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
        
        # Detect registry files from URLs in Excel
        project_root = output_file.parent.parent.parent  # Go up from storage/excel_tests to project root
        element_maps_dir = project_root / 'element_maps'
        
        # Get unique URLs from Excel
        urls = df['url'].dropna().unique().tolist() if 'url' in df.columns else []
        registry_files = detect_registry_files_from_urls(urls, element_maps_dir) if element_maps_dir.exists() else []
        
        # Generate registry code
        registry_code = build_registry_code(registry_files)
        
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
                    
                    # Lookup element_id from registry - use URL from this row (not current_url)
                    row_url = url if url and url != 'N/A' else current_url or ''
                    element_id = lookup_element_id_by_xpath(xpath, row_url, registry_files, element_maps_dir) if registry_files else None
                    test_body += generate_click_code(step, xpath, row_url, element_name, is_optional, is_modal_step=is_modal_step, element_id=element_id)
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
                    
                    # Lookup element_id from registry - use URL from this row (not current_url)
                    row_url = url if url and url != 'N/A' else current_url or ''
                    element_id = lookup_element_id_by_xpath(xpath, row_url, registry_files, element_maps_dir) if registry_files else None
                    test_body += generate_fill_code(step, xpath, text_value, row_url, element_name, functions, is_optional, is_modal_step=is_modal_step, element_id=element_id)
                else:
                    errors.append(f"Step {step}: Fill action requires XPath")
            
            elif action == 'verify':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    # Lookup element_id from registry - use URL from this row (not current_url)
                    row_url = url if url and url != 'N/A' else current_url or ''
                    element_id = lookup_element_id_by_xpath(xpath, row_url, registry_files, element_maps_dir) if registry_files else None
                    test_body += generate_verify_code(step, xpath, row_url, element_name, element_id=element_id)
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
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f'✅ Loaded environment variables from {{env_path}}')
else:
    print(f'⚠️  .env file not found at {{env_path}}')

{registry_code}

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

