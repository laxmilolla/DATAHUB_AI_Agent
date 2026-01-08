"""
Registry Utilities - Registry lookup and element_id backfilling
Extracted from playwright_generator.py
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def get_element_id_from_registry(element_name: str, registry: Dict) -> Optional[str]:
    """
    Find element_id in registry by element name
    Args:
        element_name: Name of the element to find
        registry: Registry dictionary with 'elements' and 'id_index'
    Returns:
        element_id if found, None otherwise
    """
    if not registry or not element_name:
        return None
    
    elements = registry.get('elements', {})
    element_lower = element_name.lower().strip()
    
    # Try exact match first
    if element_name in elements:
        return elements[element_name].get('element_id')
    
    # Try case-insensitive match
    for key, value in elements.items():
        if key.lower() == element_lower:
            return value.get('element_id')
    
    # Try partial match (element name in registry key or vice versa)
    for key, value in elements.items():
        key_lower = key.lower()
        key_clean = key_lower.replace('text=', '').replace('selector=', '').strip()
        
        if (element_lower in key_clean or key_clean in element_lower or
            element_lower.replace(' ', '') == key_clean.replace(' ', '')):
            return value.get('element_id')
    
    return None


def get_element_id_by_xpath(xpath: str, registry: Dict) -> Optional[str]:
    """
    Find element_id in registry by XPath
    Args:
        xpath: XPath to search for
        registry: Registry dictionary
    Returns:
        element_id if found, None otherwise
    """
    if not registry or not xpath:
        return None
    
    elements = registry.get('elements', {})
    
    # Search by XPath
    for key, elem_data in elements.items():
        if elem_data.get('xpath') == xpath:
            return elem_data.get('element_id')
    
    # Try reverse lookup via id_index
    id_index = registry.get('id_index', {})
    for elem_id, elem_key in id_index.items():
        elem_data = elements.get(elem_key)
        if elem_data and elem_data.get('xpath') == xpath:
            return elem_id
    
    return None


def get_xpath_by_id(element_id: str, registry: Dict) -> Optional[str]:
    """
    Get XPath from registry by element_id
    Args:
        element_id: Element ID to look up
        registry: Registry dictionary
    Returns:
        XPath if found, None otherwise
    """
    if not registry or not element_id:
        return None
    
    id_index = registry.get('id_index', {})
    if element_id not in id_index:
        return None
    
    registry_key = id_index[element_id]
    elements = registry.get('elements', {})
    
    if registry_key not in elements:
        return None
    
    return elements[registry_key].get('xpath')


def backfill_element_id(discovery: Dict, registry: Dict) -> bool:
    """
    Backfill element_id into discovery from registry
    Tries multiple lookup strategies:
    1. By discovery name
    2. By discovery XPath
    3. Reverse lookup via id_index
    
    Args:
        discovery: Discovery dictionary (modified in-place)
        registry: Registry dictionary
    Returns:
        True if element_id was found and backfilled, False otherwise
    """
    if not discovery or not registry:
        return False
    
    # Already has element_id
    if discovery.get('element_id'):
        return True
    
    discovery_xpath = discovery.get('xpath', '')
    discovery_name = discovery.get('name', '')
    element_id = None
    
    # Strategy 1: Try by name first
    if discovery_name:
        element_id = get_element_id_from_registry(discovery_name, registry)
        if element_id:
            logger.info(f"  🔍 Found element_id in registry by name: {discovery_name} -> {element_id}")
    
    # Strategy 2: Try by XPath
    if not element_id and discovery_xpath:
        element_id = get_element_id_by_xpath(discovery_xpath, registry)
        if element_id:
            logger.info(f"  🔍 Found element_id in registry by XPath: {discovery_name} -> {element_id}")
    
    # Strategy 3: Reverse lookup via id_index
    if not element_id and discovery_xpath:
        id_index = registry.get('id_index', {})
        elements = registry.get('elements', {})
        for elem_id, elem_key in id_index.items():
            elem_data = elements.get(elem_key)
            if elem_data and elem_data.get('xpath') == discovery_xpath:
                element_id = elem_id
                logger.info(f"  🔍 Found element_id via id_index reverse lookup: {elem_key} -> {element_id}")
                break
    
    # Backfill if found
    if element_id:
        discovery['element_id'] = element_id
        logger.info(f"  ✅ Backfilled element_id into discovery: {discovery_name} -> {element_id}")
        return True
    
    return False


def get_selector_from_registry(element_name: str, registry: Dict) -> Optional[str]:
    """
    Get optimized selector from registry by element name
    Returns selector (XPath preferred) or None
    """
    selector, _ = get_selector_and_key_from_registry(element_name, registry)
    return selector


def get_selector_and_key_from_registry(element_name: str, registry: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Get optimized selector AND registry key from registry
    Prefers XPath if available
    
    Returns:
        (selector, registry_key) tuple or (None, None) if not found
    """
    if not registry:
        return (None, None)
    
    element_lower = element_name.lower().strip()
    elements = registry.get('elements', {})
    
    # Try exact match first
    if element_name in elements:
        value = elements[element_name]
        selector = _extract_selector_from_registry_entry(value)
        if selector:
            return (selector, element_name)
    
    # Try case-insensitive match
    for key, value in elements.items():
        key_lower = key.lower()
        key_clean = key_lower.replace('text=', '').replace('selector=', '').strip()
        
        # Check if element matches registry key (bidirectional)
        if (element_lower in key_clean or key_clean in element_lower or
            element_lower.replace(' ', '') == key_clean.replace(' ', '')):
            selector = _extract_selector_from_registry_entry(value)
            if selector:
                return (selector, key)
    
    return (None, None)


def _extract_selector_from_registry_entry(entry: Dict) -> Optional[str]:
    """
    Extract selector from registry entry (prefer XPath)
    """
    if not isinstance(entry, dict):
        return None
    
    # Prefer XPath if available
    if 'xpath' in entry:
        return f"xpath={entry['xpath']}"
    elif 'selector' in entry:
        return entry['selector']
    elif 'query' in entry:
        return entry['query']
    
    return None


