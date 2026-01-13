"""
Test Template - Generate test file structure and header
Extracted from playwright_generator.py
"""
import re
from datetime import datetime
from typing import Dict, List


def build_test_template(
    execution_id: str,
    story: str,
    test_name: str,
    status: str,
    registry_files: List[str],
    test_constants: str,
    test_body: str
) -> str:
    """
    Build complete test file template with header, imports, registry loading, and body
    
    Args:
        execution_id: Execution ID
        story: Story text
        test_name: Test function name
        status: Execution status
        registry_files: List of registry file paths
        test_constants: Test-specific constants (verification values, optional selectors)
        test_body: Generated test body code
    Returns:
        Complete test file code as string
    """
    # Format registry paths list for Python code
    registry_paths_list_str = "[\n"
    for reg_path in registry_files:
        registry_paths_list_str += f"    '{reg_path}',\n"
    registry_paths_list_str += "]"
    
    code = f'''"""
Generated Playwright Test
Source Execution: {execution_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
Status: {status}

Story:
{story}
"""

from playwright.sync_api import sync_playwright, expect
import re
import json
import os
from pathlib import Path

# Load environment variables from .env file (for TOTP_SECRET_KEY, etc.)
# Check multiple locations: same dir, parent, home, or 3 levels up
try:
    from dotenv import load_dotenv
    test_file_dir = Path(__file__).parent
    possible_env_locations = [
        test_file_dir / '.env',  # Same directory as test file
        test_file_dir.parent / '.env',  # Parent directory
        Path.home() / '.env',  # Home directory
        test_file_dir.parent.parent.parent / '.env',  # 3 levels up (original behavior)
    ]
    env_file = None
    for loc in possible_env_locations:
        if loc.exists():
            env_file = loc
            load_dotenv(env_file)
            print(f"✅ Loaded environment variables from {{env_file}}")
            break
    if not env_file:
        print(f"⚠️  .env file not found. Checked locations:")
        for loc in possible_env_locations:
            print(f"   - {{loc}}")
        print(f"   Please create a .env file with TOTP_SECRET_KEY=your_secret_key")
except ImportError:
    print("⚠️  python-dotenv not installed - environment variables must be set manually")
except Exception as e:
    print(f"⚠️  Failed to load .env file: {{e}}")

# ============================================================================
# TEST-SPECIFIC VALUES (from story - embedded in test, not in registry)
# ============================================================================
{test_constants}# ============================================================================
# MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
# ============================================================================
# Automatically detects and loads all registry files needed based on URLs visited
# Update paths below if registries are in different locations
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
    from urllib.parse import urlparse
    import re
    
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
    
    from urllib.parse import urlparse
    
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


def {test_name}():
    """Auto-generated test from AI discovery - 1:1 mirror of AI execution"""
    # Track critical failures (non-optional steps that failed)
    critical_failures = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Match AI agent viewport to ensure tabs are visible (not hidden in "More" dropdown)
        page = browser.new_page(viewport={{'width': 1920, 'height': 1080}})
        
        try:
{test_body}
            # Check if there were any critical failures
            if critical_failures:
                print(f"\\n❌ Test completed with {{len(critical_failures)}} critical failure(s):")
                for failure in critical_failures:
                    print(f"  - {{failure}}")
                raise Exception(f"Test failed: {{len(critical_failures)}} critical step(s) failed")
            else:
                print("✅ Test completed successfully")
            
        except Exception as e:
            print(f"❌ Test failed: {{e}}")
            # Capture final screenshot even on failure
            try:
                page.screenshot(path='storage/screenshots/pw_test_final_failed.png')
                print(f'📸 Final screenshot saved: storage/screenshots/pw_test_final_failed.png')
            except:
                pass
            raise  # Re-raise to exit with non-zero code
        finally:
            browser.close()


if __name__ == '__main__':
    import sys
    try:
        {test_name}()
        sys.exit(0)  # Success
    except Exception as e:
        print(f"\\n❌ Test execution failed: {{e}}")
        sys.exit(1)  # Failure
'''
    
    return code


def extract_test_constants(discoveries: List[Dict]) -> str:
    """
    Extract test-specific constants from discoveries (verification values, optional selectors)
    These are embedded in the test, not loaded from registry
    
    Args:
        discoveries: List of discovery dictionaries
    Returns:
        Formatted constants section as string
    """
    test_constants = ""
    
    # Find verification discovery
    verify_discovery = None
    verify_column_name = ''
    verify_expected_value = ''
    for disc in discoveries:
        if disc.get('discovery_method') == 'table_verification':
            verify_discovery = disc
            metadata = disc.get('metadata', {})
            verify_column_name = metadata.get('column_name', '')
            verify_expected_value = metadata.get('expected_value', '')
            break
    
    # Find optional element selectors (elements without element_id)
    optional_selectors = {}  # element_name -> selector
    for disc in discoveries:
        if not disc.get('element_id'):
            element_name = disc.get('name', '')
            # Use original_query (what AI was instructed to use) for true mirroring
            selector = disc.get('original_query') or disc.get('final_selector', '')
            if selector and element_name:
                optional_selectors[element_name] = selector
    
    # Escape for Python string literals
    verify_column_name_escaped = verify_column_name.replace("'", "\\'").replace('"', '\\"')
    verify_expected_value_escaped = verify_expected_value.replace("'", "\\'").replace('"', '\\"')
    
    # Build test-specific constants section
    if verify_column_name and verify_expected_value:
        test_constants += f"# Verification values (test-specific, from story)\n"
        test_constants += f"VERIFY_COLUMN_NAME = '{verify_column_name_escaped}'\n"
        test_constants += f"VERIFY_EXPECTED_VALUE = '{verify_expected_value_escaped}'\n\n"
    
    if optional_selectors:
        test_constants += f"# Optional element selectors (test-specific, elements not in registry)\n"
        for name, selector in optional_selectors.items():
            selector_escaped = selector.replace("'", "\\'").replace('"', '\\"')
            # Create safe constant name (match what we'll use in code generation)
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            constant_name = f"OPTIONAL_{safe_name.upper()}_SELECTOR"
            test_constants += f"{constant_name} = '{selector_escaped}'\n"
        test_constants += "\n"
    
    return test_constants


