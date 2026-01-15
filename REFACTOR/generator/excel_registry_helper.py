"""
Excel Registry Helper - Extract elements from Excel and compare with registry
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import re


def extract_elements_from_excel(excel_file: Path) -> List[Dict[str, Any]]:
    """
    Extract unique (URL, XPath, element_name) pairs from Excel file.
    
    Args:
        excel_file: Path to Excel file
        
    Returns:
        List of dicts with 'url', 'xpath', 'element_name', 'action', 'object_type'
    """
    try:
        df = pd.read_excel(excel_file)
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        elements = []
        seen = set()  # Track (url, xpath) pairs to avoid duplicates
        
        for idx, row in df.iterrows():
            url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else None
            xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
            action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else ''
            object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
            step = str(row.get('step', idx + 1)).strip()
            
            # Skip if URL or XPath is missing or N/A
            if not url or url.upper() == 'N/A' or not xpath or xpath.upper() == 'N/A':
                continue
            
            # Skip navigate and wait actions (no element to register)
            if action in ['navigate', 'wait']:
                continue
            
            # Create unique key
            key = (url, xpath)
            if key in seen:
                continue
            seen.add(key)
            
            # Generate element name from object_type or step
            element_name = object_type if object_type else f"element_step_{step}"
            
            elements.append({
                'url': url,
                'xpath': xpath,
                'element_name': element_name,
                'action': action,
                'object_type': object_type,
                'step': step
            })
        
        return elements
    
    except Exception as e:
        raise Exception(f"Failed to extract elements from Excel: {e}")


def get_domain_from_url(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        return domain
    except:
        return ''


def get_page_from_url(url: str) -> str:
    """Extract page name from URL"""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path or path == '':
            return 'home'
        
        # Get last segment
        page = path.rstrip('/').split('/')[-1]
        # Sanitize
        page = re.sub(r'[<>:"/\\|?*]', '_', page)
        return page
    except:
        return 'home'


def compare_with_registry(elements: List[Dict[str, Any]], registry) -> Dict[str, Any]:
    """
    Compare Excel elements with registry to find new and updated elements.
    
    Args:
        elements: List of elements from Excel (from extract_elements_from_excel)
        registry: ElementRegistry instance
        
    Returns:
        Dict with 'new_elements', 'updated_elements', 'unchanged_elements'
    """
    new_elements = []
    updated_elements = []
    unchanged_elements = []
    
    # Group elements by domain and page
    elements_by_page = {}
    for elem in elements:
        domain = get_domain_from_url(elem['url'])
        page = get_page_from_url(elem['url'])
        key = (domain, page)
        if key not in elements_by_page:
            elements_by_page[key] = []
        elements_by_page[key].append(elem)
    
    # Compare with registry
    for (domain, page), page_elements in elements_by_page.items():
        # Load registry map for this page (try both main page and modal page)
        element_map = registry.load_map(domain, page)
        modal_page = f"{page}-modal"
        modal_map = registry.load_map(domain, modal_page)
        
        # Combine registry elements from both main and modal pages
        registry_elements = {}
        if element_map:
            registry_elements.update(element_map.get('elements', {}))
        if modal_map:
            registry_elements.update(modal_map.get('elements', {}))
        
        for elem in page_elements:
            xpath = elem['xpath']
            element_name = elem['element_name']
            url = elem['url']
            
            # Check if element exists in registry (by name or XPath)
            found = False
            existing_xpath = None
            found_page = page  # Track which page it was found on
            
            # First, try to find by element name
            if element_name in registry_elements:
                found = True
                existing_xpath = registry_elements[element_name].get('xpath') or registry_elements[element_name].get('selector', '')
                # Check which page it's on
                if element_map and element_name in element_map.get('elements', {}):
                    found_page = page
                elif modal_map and element_name in modal_map.get('elements', {}):
                    found_page = modal_page
            
            # If not found by name, check if XPath matches any existing element
            if not found:
                for reg_name, reg_elem in registry_elements.items():
                    reg_xpath = reg_elem.get('xpath') or reg_elem.get('selector', '')
                    if reg_xpath == xpath:
                        found = True
                        element_name = reg_name  # Use existing name
                        existing_xpath = reg_xpath
                        # Check which page it's on
                        if element_map and reg_name in element_map.get('elements', {}):
                            found_page = page
                        elif modal_map and reg_name in modal_map.get('elements', {}):
                            found_page = modal_page
                        break
            
            if not found:
                # New element - determine if it should go to modal or main page
                # Check if XPath contains modal indicators
                is_modal = 'modal' in xpath.lower() or 'dialog' in xpath.lower() or 'create-submission' in xpath.lower()
                target_page = f"{page}-modal" if is_modal else page
                
                new_elements.append({
                    'url': url,
                    'xpath': xpath,
                    'element_name': element_name,
                    'action': elem['action'],
                    'object_type': elem['object_type'],
                    'domain': domain,
                    'page': target_page
                })
            elif existing_xpath != xpath:
                # Updated element (XPath changed)
                updated_elements.append({
                    'url': url,
                    'old_xpath': existing_xpath,
                    'new_xpath': xpath,
                    'element_name': element_name,
                    'action': elem['action'],
                    'object_type': elem['object_type'],
                    'domain': domain,
                    'page': found_page  # Use the page where it was found
                })
            else:
                # Unchanged element
                unchanged_elements.append({
                    'url': url,
                    'xpath': xpath,
                    'element_name': element_name,
                    'action': elem['action'],
                    'object_type': elem['object_type'],
                    'domain': domain,
                    'page': found_page
                })
    
    return {
        'new_elements': new_elements,
        'updated_elements': updated_elements,
        'unchanged_elements': unchanged_elements,
        'total_new': len(new_elements),
        'total_updated': len(updated_elements),
        'total_unchanged': len(unchanged_elements)
    }

