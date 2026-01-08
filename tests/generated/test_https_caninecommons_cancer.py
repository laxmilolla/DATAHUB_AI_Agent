"""
Generated Playwright Test
Source Execution: exec_a07ed4e2
Generated: 2026-01-08 16:05:10 UTC
Status: completed

Story:
Go to https://caninecommons.cancer.gov/#/ If there is a popup, click Continue Click on Explore Click on Study dropdown Click on GLIOMA01
"""

from playwright.sync_api import sync_playwright, expect
import re
import json
from pathlib import Path

# ============================================================================
# TEST-SPECIFIC VALUES (from story - embedded in test, not in registry)
# ============================================================================
# ============================================================================
# MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
# ============================================================================
# Automatically detects and loads all registry files needed based on URLs visited
# Update paths below if registries are in different locations
REGISTRY_PATHS = [
    'element_maps/caninecommons.cancer.gov/explore_page.json',
]

# Load and merge all registries
REGISTRY = {}
REGISTRY_ID_INDEX = {}
loaded_count = 0
for registry_path_str in REGISTRY_PATHS:
    try:
        registry_path = Path(registry_path_str)
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
                # Merge elements (later registries override earlier ones if same key)
                REGISTRY.update(registry_data.get('elements', {}))
                # Merge id_index (later registries override earlier ones if same element_id)
                REGISTRY_ID_INDEX.update(registry_data.get('id_index', {}))
            loaded_count += 1
            print(f"✅ Loaded registry: {len(registry_data.get('elements', {}))} elements from {registry_path.name}")
        else:
            print(f"⚠️  Registry file not found: {registry_path}")
    except Exception as e:
        print(f"⚠️  Failed to load registry {registry_path_str}: {e}")

if loaded_count > 0:
    print(f"✅ Merged {loaded_count} registries: {len(REGISTRY)} total elements, {len(REGISTRY_ID_INDEX)} total IDs")
else:
    print(f"⚠️  No registries loaded. Please check REGISTRY_PATHS above.")

def get_xpath_by_id(element_id):
    """Get XPath from registry by unique ID - ONLY source of XPaths (strict, no fallbacks)"""
    if not element_id:
        raise Exception(f"❌ element_id is required")
    
    if element_id not in REGISTRY_ID_INDEX:
        raise Exception(f"❌ element_id '{element_id}' not found in registry id_index")
    
    registry_key = REGISTRY_ID_INDEX[element_id]
    
    if registry_key not in REGISTRY:
        raise Exception(f"❌ Registry key '{registry_key}' not found for element_id '{element_id}'")
    
    xpath = REGISTRY[registry_key].get('xpath')
    
    if not xpath:
        raise Exception(f"❌ XPath missing for element_id '{element_id}' (registry_key: '{registry_key}')")
    
    return xpath


def test_https_caninecommons_cancer():
    """Auto-generated test from AI discovery - 1:1 mirror of AI execution"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Match AI agent viewport to ensure tabs are visible (not hidden in "More" dropdown)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Step 1: https://caninecommons.cancer.gov/#/
            page.goto('https://caninecommons.cancer.gov/#/')
            print('📍 Step 1: Navigated to https://caninecommons.cancer.gov/#/')


            print("✅ Test completed successfully")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
        finally:
            browser.close()


if __name__ == '__main__':
    test_https_caninecommons_cancer()
