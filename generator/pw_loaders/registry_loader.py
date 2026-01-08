"""
Registry Loader - Load and merge registry files
Extracted from playwright_generator.py
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def load_registry(url: str, element_maps_dir: Path) -> Dict:
    """
    Load element registry for the domain
    Args:
        url: URL to determine which registry to load
        element_maps_dir: Directory containing element map JSON files
    Returns:
        Registry dictionary with 'elements' dict
    """
    if not url:
        return {}
    
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Look for registry file (try home_page.json or explore_page.json)
    domain_dir = element_maps_dir / domain
    if not domain_dir.exists():
        logger.warning(f"⚠️  Registry directory not found: {domain_dir}")
        return {}
    
    # Try common page names
    for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
        registry_file = domain_dir / page_name
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                data = json.load(f)
                logger.info(f"✅ Loaded registry from {registry_file.name}")
                return data.get('elements', {})
    
    logger.warning(f"⚠️  No registry file found in {domain_dir}")
    return {}


def get_registry_path(url: str, element_maps_dir: Path) -> str:
    """
    Get relative path to registry file for use in generated test
    Args:
        url: URL to determine registry path
        element_maps_dir: Base directory for element maps
    Returns:
        Relative path string (e.g., 'element_maps/domain.com/home_page.json')
    """
    if not url:
        # Default to main registry
        return 'element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json'
    
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Extract page name from URL path (same logic as agent)
    url_path = url.split('/')[-1].split('#')[0]
    if url_path == 'explore':
        page = 'explore'
    elif not url_path or url_path == '':
        page = 'home'
    else:
        page = url_path
    
    # Always return the expected path based on URL structure
    # (even if file doesn't exist yet - user can create it)
    expected_path = f'element_maps/{domain}/{page}_page.json'
    
    # Check if file exists - if so, use it; otherwise check for common alternatives
    domain_dir = element_maps_dir / domain
    if domain_dir.exists():
        # Try specific page first
        registry_file = domain_dir / f'{page}_page.json'
        if registry_file.exists():
            return expected_path
        
        # Fallback to common page names if specific page doesn't exist
        for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
            registry_file = domain_dir / page_name
            if registry_file.exists():
                return f'element_maps/{domain}/{page_name}'
    
    # Return expected path (even if it doesn't exist yet)
    # This allows the test to work once the registry is created
    return expected_path


def detect_registry_files(execution: Dict, element_maps_dir: Path) -> List[str]:
    """
    Detect all registry files needed based on URLs visited during test execution.
    Scans actions_taken for browser_navigate actions and extracts registry paths.
    
    Args:
        execution: Execution dictionary
        element_maps_dir: Base directory for element maps
    Returns:
        List of registry file paths (relative paths)
    """
    registry_files = set()
    
    # Get initial URL from story
    story_url = execution.get('story_url', '')
    if not story_url:
        # Try to extract URL from story
        if match := re.search(r'https?://[^\s]+', execution.get('story', '')):
            story_url = match.group(0)
    
    if story_url:
        registry_path = get_registry_path(story_url, element_maps_dir)
        if registry_path:
            registry_files.add(registry_path)
    
    # Scan actions_taken for navigations
    for action in execution.get('actions_taken', []):
        tool = action.get('tool', '')
        if tool == 'browser_navigate':
            url = action.get('input', {}).get('url', '')
            if url:
                registry_path = get_registry_path(url, element_maps_dir)
                if registry_path:
                    registry_files.add(registry_path)
    
    # Also check discoveries for URL metadata (if available)
    # This catches elements discovered on pages that weren't explicitly navigated to
    # (e.g., if page changed due to form submission)
    discoveries = execution.get('discoveries', [])
    for disc in discoveries:
        metadata = disc.get('metadata', {})
        url = metadata.get('url', '')
        if url:
            registry_path = get_registry_path(url, element_maps_dir)
            if registry_path:
                registry_files.add(registry_path)
    
    # Extract URLs from story text (catches URLs mentioned in steps like "goes to https://...")
    story = execution.get('story', '')
    if story:
        story_urls = re.findall(r'https?://[^\s\)]+', story)
        for url in story_urls:
            registry_path = get_registry_path(url, element_maps_dir)
            if registry_path:
                registry_files.add(registry_path)
    
    registry_list = sorted(list(registry_files))
    logger.info(f"✅ Detected {len(registry_list)} registry files: {registry_list}")
    return registry_list


def merge_registries(registry_files: List[str], element_maps_dir: Path) -> Dict:
    """
    Load and merge multiple registry files
    Args:
        registry_files: List of relative registry file paths
        element_maps_dir: Base directory for element maps
    Returns:
        Merged registry dictionary with 'elements' and 'id_index'
    """
    merged_registry = {'elements': {}, 'id_index': {}}
    
    for registry_path_str in registry_files:
        registry_file_path = element_maps_dir.parent / registry_path_str
        if registry_file_path.exists():
            try:
                with open(registry_file_path, 'r') as f:
                    registry_data = json.load(f)
                    # Merge elements (later registries override earlier ones if same key)
                    merged_registry['elements'].update(registry_data.get('elements', {}))
                    # Merge id_index (later registries override earlier ones if same element_id)
                    merged_registry['id_index'].update(registry_data.get('id_index', {}))
                    logger.info(f"✅ Merged registry: {len(registry_data.get('elements', {}))} elements from {registry_file_path.name}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load registry {registry_path_str}: {e}")
        else:
            logger.warning(f"⚠️  Registry file not found: {registry_file_path}")
    
    total_elements = len(merged_registry['elements'])
    total_ids = len(merged_registry['id_index'])
    logger.info(f"✅ Merged {len(registry_files)} registries: {total_elements} total elements, {total_ids} total IDs")
    
    return merged_registry


