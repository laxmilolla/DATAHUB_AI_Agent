"""
Excel-Based Playwright Generator
Reads Excel file with Step, URL, XPath, Action, etc. and generates Playwright code
Registry-aware: Uses element registry instead of hard-coded XPaths
Auto-populates registries from Excel before test generation
"""
import pandas as pd
import re
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlparse
import sys

# Add utils to path for ElementRegistry import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.element_registry import ElementRegistry


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
    Detect registry files needed (URL-free approach: ALWAYS loads ALL registries)
    
    Args:
        urls: List of URLs from Excel file (ignored - kept for backward compatibility)
        element_maps_dir: Base directory for element maps (usually 'element_maps')
    
    Returns:
        List of relative registry file paths (ALL registries)
    """
    registry_paths = set()
    
    # URL-free approach: ALWAYS load ALL registry files regardless of URLs
    if element_maps_dir.exists():
        # Load unified registry first (if it exists)
        unified_registry = element_maps_dir / 'unified_registry.json'
        if unified_registry.exists():
            registry_paths.add('element_maps/unified_registry.json')
        
        # Also load all domain/page registries (for backward compatibility with existing registries)
        for domain_dir in element_maps_dir.iterdir():
            if domain_dir.is_dir():
                for json_file in domain_dir.glob('*_page.json'):
                    registry_paths.add(f'element_maps/{domain_dir.name}/{json_file.name}')
    
    return sorted(list(registry_paths))


def populate_registry_from_excel(df: pd.DataFrame, element_maps_dir: Path) -> None:
    """
    Auto-populate unified registry from Excel data (Excel → JSON)
    URL-free approach: ALL elements go to ONE unified registry regardless of URL
    
    Args:
        df: DataFrame with Excel data (columns: step, url, xpath, action, object_type)
        element_maps_dir: Directory containing element_maps
    """
    from datetime import datetime
    import json
    
    print("📝 Auto-populating unified registry from Excel data (URL-free approach)...")
    added_count = 0
    skipped_count = 0
    
    # Unified registry path: ONE registry for all elements
    unified_registry_path = element_maps_dir / 'unified_registry.json'
    
    # Load existing unified registry or create new one
    if unified_registry_path.exists():
        with open(unified_registry_path, 'r') as f:
            element_map = json.load(f)
    else:
        element_map = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat() + "Z",
            "elements": {},
            "id_index": {},
            "statistics": {
                "total_elements": 0,
                "parsed_elements": 0,
                "discovered_elements": 0
            }
        }
    
    # Import ElementRegistry for ID generation
    sys.path.insert(0, str(element_maps_dir.parent))
    from utils.element_registry import ElementRegistry
    registry = ElementRegistry(str(element_maps_dir))
    
    # Process ALL rows (URL-free: no separation by domain/page)
    for idx, row in df.iterrows():
        xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
        
        action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else ''
        object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
        step = str(row.get('step', idx + 1)).strip()
        
        # Skip if no XPath
        if not xpath or xpath == 'N/A':
            continue
        
        # Skip navigate and wait actions (no element to register)
        if action in ['navigate', 'wait']:
            continue
        
        # Generate element name from step/action/object_type
        if object_type:
            element_name = f"{object_type}_{step}"
        elif action:
            element_name = f"{action}_{step}"
        else:
            element_name = f"element_{step}"
        
        # Check if XPath already exists in unified registry (match by XPath only)
        existing_element_key = None
        existing_element = None
        
        # Strategy: Check by XPath only (URL-free matching)
        for key, elem_data in element_map.get('elements', {}).items():
            if elem_data.get('xpath') == xpath:
                existing_element_key = key
                existing_element = elem_data
                break
        
        if existing_element_key and existing_element:
            # Update existing element (no duplicate)
            existing_element['object_type'] = object_type or existing_element.get('object_type', '')
            existing_element['action'] = action or existing_element.get('action', '')
            existing_element['source'] = 'excel'
            existing_element['last_updated'] = datetime.now().isoformat() + "Z"
            # Preserve existing element_id
            skipped_count += 1
        else:
            # Add new element if not found
            # Generate element_id based on element_name + XPath (URL-free)
            element_id = registry._generate_element_id(element_name, xpath)
            
            element_entry = {
                'xpath': xpath,
                'selector': xpath,
                'element_id': element_id,
                'source': 'excel',
                'object_type': object_type,
                'action': action,
                'discovered_at': datetime.now().isoformat() + "Z"
            }
            
            element_map['elements'][element_name] = element_entry
            element_map['id_index'][element_id] = element_name
            element_map['statistics']['total_elements'] = len(element_map['elements'])
            added_count += 1
    
    # Save unified registry
    if added_count > 0 or skipped_count > 0:
        element_map['last_updated'] = datetime.now().isoformat() + "Z"
        element_map['statistics']['total_elements'] = len(element_map['elements'])
        
        unified_registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(unified_registry_path, 'w') as f:
            json.dump(element_map, f, indent=2)
        
        update_msg = []
        if added_count > 0:
            update_msg.append(f"{added_count} new")
        if skipped_count > 0:
            update_msg.append(f"{skipped_count} updated")
        print(f"  ✅ Updated unified registry: unified_registry.json ({', '.join(update_msg)} elements, {len(element_map['elements'])} total)")
    
    print(f"✅ Unified registry population complete: {added_count} added, {skipped_count} skipped")


def _process_rows_for_registry(url_rows, element_map, registry, domain, page, url):
    """Helper function to process rows and add to registry (URL-free approach)"""
    from datetime import datetime
    
    added_count = 0
    skipped_count = 0
    
    for idx, row in url_rows.iterrows():
        xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
        
        action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else ''
        object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
        step = str(row.get('step', idx + 1)).strip()
        
        # Skip if no XPath
        if not xpath or xpath == 'N/A':
            continue
        
        # Skip navigate and wait actions (no element to register)
        if action in ['navigate', 'wait']:
            continue
        
        # Generate element name from step/action/object_type
        if object_type:
            element_name = f"{object_type}_{step}"
        elif action:
            element_name = f"{action}_{step}"
        else:
            element_name = f"element_{step}"
        
        # URL-free approach: Check if XPath already exists in registry (match by XPath only)
        existing_element_key = None
        existing_element = None
        
        # Strategy: Check by XPath only (URL-free matching)
        for key, elem_data in element_map.get('elements', {}).items():
            if elem_data.get('xpath') == xpath:
                existing_element_key = key
                existing_element = elem_data
                break
        
        if existing_element_key and existing_element:
            # Update existing element (no duplicate)
            existing_element['object_type'] = object_type or existing_element.get('object_type', '')
            existing_element['action'] = action or existing_element.get('action', '')
            existing_element['source'] = 'excel'
            existing_element['last_updated'] = datetime.now().isoformat() + "Z"
            # Preserve existing element_id
            skipped_count += 1
        else:
            # Add new element if not found
            # Generate element_id based on element_name + XPath (URL-free)
            element_id = registry._generate_element_id(element_name, xpath)
            
            element_entry = {
                'xpath': xpath,
                'selector': xpath,
                'element_id': element_id,
                'source': 'excel',
                'object_type': object_type,
                'action': action,
                'discovered_at': datetime.now().isoformat() + "Z"
            }
            
            element_map['elements'][element_name] = element_entry
            element_map['id_index'][element_id] = element_name
            element_map['statistics']['total_elements'] = len(element_map['elements'])
            added_count += 1
    
    return added_count, skipped_count


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


def lookup_element_id_by_xpath(xpath: str, registry_files: List[str], element_maps_dir: Path) -> Optional[str]:
    """
    Look up element_id from registry by matching XPath (URL-free approach)
    
    Args:
        xpath: XPath to find
        registry_files: List of registry file paths
        element_maps_dir: Base directory for element maps
    
    Returns:
        element_id if found, None otherwise
    """
    if not xpath or xpath == 'N/A':
        return None
    
    # Search ALL registries by XPath (no URL matching needed)
    for reg_path_str in registry_files:
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
            
            # Search for matching XPath (URL-free: match by XPath only)
            for key, element_data in elements.items():
                element_xpath = element_data.get('xpath', '')
                
                # Match XPath only (no URL matching)
                if element_xpath == xpath:
                    element_id = element_data.get('element_id')
                    if element_id:
                        return element_id
            
            # Also check id_index for reverse lookup
            for element_id, registry_key in id_index.items():
                if registry_key in elements:
                    element_data = elements[registry_key]
                    element_xpath = element_data.get('xpath', '')
                    
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
        code += f"{ind}        xpath = get_xpath_by_id('{element_id_escaped}', page.url)\n"
        code += f"{ind}        selector = f'xpath={{xpath}}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'✅ Step {step}: Using registry element_id: {element_id_escaped}')\n"
        code += f"{ind}    except Exception as registry_error:\n"
        code += f"{ind}        # Registry lookup failed - test must fail\n"
        code += f"{ind}        print(f'❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: {{registry_error}}')\n"
        code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png')\n"
        code += f"{ind}        raise Exception(f'Registry lookup failed for element_id {element_id_escaped}: {{registry_error}}')\n"
    else:
        # No element_id - test must fail (element not in registry)
        code += f"{ind}    # Element not found in registry - test must fail\n"
        code += f"{ind}    raise Exception(f'Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.')\n"
    
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
        code += f"{ind}        # Robust click with fallbacks (JavaScript + force)\n"
        code += f"{ind}        try:\n"
        code += f"{ind}            element.click()\n"
        code += f"{ind}        except Exception as click_error:\n"
        code += f"{ind}            if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):\n"
        code += f"{ind}                print(f'⚠️  Step {step}: Click timeout, trying JavaScript click...')\n"
        code += f"{ind}                try:\n"
        code += f"{ind}                    element.evaluate('el => el.click()')\n"
        code += f"{ind}                    print(f'✅ Step {step}: JavaScript click succeeded')\n"
        code += f"{ind}                except Exception as js_error:\n"
        code += f"{ind}                    print(f'⚠️  Step {step}: JavaScript click failed, trying force click...')\n"
        code += f"{ind}                    element.click(force=True)\n"
        code += f"{ind}                    print(f'✅ Step {step}: Force click succeeded')\n"
        code += f"{ind}            else:\n"
        code += f"{ind}                print(f'⚠️  Step {step}: Click failed, trying force click...')\n"
        code += f"{ind}                element.click(force=True)\n"
        code += f"{ind}                print(f'✅ Step {step}: Force click succeeded')\n"
    else:
        # Robust click with fallbacks for all non-Create button clicks
        code += f"{ind}    # Scroll into view if needed\n"
        code += f"{ind}    try:\n"
        code += f"{ind}        element.scroll_into_view_if_needed()\n"
        code += f"{ind}    except:\n"
        code += f"{ind}        pass  # Continue if scroll fails\n"
        code += f"{ind}    page.wait_for_timeout(500)  # Wait after scroll\n"
        code += f"{ind}    # Robust click with fallbacks (JavaScript + force)\n"
        code += f"{ind}    try:\n"
        code += f"{ind}        element.click()\n"
        code += f"{ind}    except Exception as click_error:\n"
        code += f"{ind}        if 'timeout' in str(click_error).lower() or 'Timeout' in str(click_error):\n"
        code += f"{ind}            print(f'⚠️  Step {step}: Click timeout, trying JavaScript click...')\n"
        code += f"{ind}            try:\n"
        code += f"{ind}                element.evaluate('el => el.click()')\n"
        code += f"{ind}                print(f'✅ Step {step}: JavaScript click succeeded')\n"
        code += f"{ind}            except Exception as js_error:\n"
        code += f"{ind}                print(f'⚠️  Step {step}: JavaScript click failed, trying force click...')\n"
        code += f"{ind}                element.click(force=True)\n"
        code += f"{ind}                print(f'✅ Step {step}: Force click succeeded')\n"
        code += f"{ind}        else:\n"
        code += f"{ind}            print(f'⚠️  Step {step}: Click failed, trying force click...')\n"
        code += f"{ind}            element.click(force=True)\n"
        code += f"{ind}            print(f'✅ Step {step}: Force click succeeded')\n"
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
            code += f"{ind}        xpath = get_xpath_by_id('{element_id_escaped}', page.url)\n"
            code += f"{ind}        selector = f'xpath={{xpath}}'\n"
            code += f"{ind}        element = page.locator(selector).nth(0)\n"
            code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
            code += f"{ind}        print(f'✅ Step {step}: Using registry element_id: {element_id_escaped}')\n"
            code += f"{ind}    except Exception as registry_error:\n"
            code += f"{ind}        # Registry lookup failed - test must fail\n"
            code += f"{ind}        print(f'❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: {{registry_error}}')\n"
            code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png')\n"
            code += f"{ind}        raise Exception(f'Registry lookup failed for element_id {element_id_escaped}: {{registry_error}}')\n"
        else:
            # No element_id - test must fail (element not in registry)
            code += f"{ind}    # Element not found in registry - test must fail\n"
            code += f"{ind}    raise Exception(f'Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.')\n"
    
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
        code += f"{ind}        xpath = get_xpath_by_id('{element_id_escaped}', page.url)\n"
        code += f"{ind}        selector = f'xpath={{xpath}}'\n"
        code += f"{ind}        element = page.locator(selector).nth(0)\n"
        code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}        print(f'✅ Step {step}: Using registry element_id: {element_id_escaped}')\n"
        code += f"{ind}    except Exception as registry_error:\n"
        code += f"{ind}        # Registry lookup failed - test must fail\n"
        code += f"{ind}        print(f'❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: {{registry_error}}')\n"
        code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png')\n"
        code += f"{ind}        raise Exception(f'Registry lookup failed for element_id {element_id_escaped}: {{registry_error}}')\n"
    else:
        # No element_id - test must fail (element not in registry)
        code += f"{ind}    # Element not found in registry - test must fail\n"
        code += f"{ind}    raise Exception(f'Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.')\n"
    element_display = element_name or 'element'
    code += f"{ind}    print(f'✅ Step {step}: Verified {element_display} is visible')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_verified.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step}: Verification failed: {{e}}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step}_{safe_name}_failed.png')\n"
    code += f"{ind}    critical_failures.append(f'Step {step}: Verification failed')\n"
    code += f"{ind}\n"
    return code


# REMOVED: generate_playwright_from_excel() - Python generator no longer used
# Use generate_playwright_ts_from_excel() in excel_generator_ts.py instead
# Function removed on cleanup-code branch - Python tests replaced by TypeScript tests

