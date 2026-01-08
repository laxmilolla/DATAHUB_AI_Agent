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
from pathlib import Path

# ============================================================================
# TEST-SPECIFIC VALUES (from story - embedded in test, not in registry)
# ============================================================================
{test_constants}# ============================================================================
# MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
# ============================================================================
# Automatically detects and loads all registry files needed based on URLs visited
# Update paths below if registries are in different locations
REGISTRY_PATHS = {registry_paths_list_str}

# Load and merge all registries
REGISTRY = {{}}
REGISTRY_ID_INDEX = {{}}
loaded_count = 0
for registry_path_str in REGISTRY_PATHS:
    try:
        registry_path = Path(registry_path_str)
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
                # Merge elements (later registries override earlier ones if same key)
                REGISTRY.update(registry_data.get('elements', {{}}))
                # Merge id_index (later registries override earlier ones if same element_id)
                REGISTRY_ID_INDEX.update(registry_data.get('id_index', {{}}))
            loaded_count += 1
            print(f"✅ Loaded registry: {{len(registry_data.get('elements', {{}}))}} elements from {{registry_path.name}}")
        else:
            print(f"⚠️  Registry file not found: {{registry_path}}")
    except Exception as e:
        print(f"⚠️  Failed to load registry {{registry_path_str}}: {{e}}")

if loaded_count > 0:
    print(f"✅ Merged {{loaded_count}} registries: {{len(REGISTRY)}} total elements, {{len(REGISTRY_ID_INDEX)}} total IDs")
else:
    print(f"⚠️  No registries loaded. Please check REGISTRY_PATHS above.")

def get_xpath_by_id(element_id):
    """Get XPath from registry by unique ID - ONLY source of XPaths (strict, no fallbacks)"""
    if not element_id:
        raise Exception(f"❌ element_id is required")
    
    if element_id not in REGISTRY_ID_INDEX:
        raise Exception(f"❌ element_id '{{element_id}}' not found in registry id_index")
    
    registry_key = REGISTRY_ID_INDEX[element_id]
    
    if registry_key not in REGISTRY:
        raise Exception(f"❌ Registry key '{{registry_key}}' not found for element_id '{{element_id}}'")
    
    xpath = REGISTRY[registry_key].get('xpath')
    
    if not xpath:
        raise Exception(f"❌ XPath missing for element_id '{{element_id}}' (registry_key: '{{registry_key}}')")
    
    return xpath


def {test_name}():
    """Auto-generated test from AI discovery - 1:1 mirror of AI execution"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Match AI agent viewport to ensure tabs are visible (not hidden in "More" dropdown)
        page = browser.new_page(viewport={{'width': 1920, 'height': 1080}})
        
        try:
{test_body}
            print("✅ Test completed successfully")
            
        except Exception as e:
            print(f"❌ Test failed: {{e}}")
            raise
        finally:
            browser.close()


if __name__ == '__main__':
    {test_name}()
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


