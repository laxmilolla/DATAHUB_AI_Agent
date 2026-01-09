"""
Registry Manager - Manage element registry operations
Extracted from bedrock_playwright_agent.py lines 3412-3580
CRITICAL: XPath preservation logic must be exact copy
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RegistryManager:
    """Manage element registry operations"""
    
    def __init__(self, element_registry, execution_id: str):
        """
        Initialize registry manager
        Args:
            element_registry: ElementRegistry instance
            execution_id: Current execution ID
        """
        self.element_registry = element_registry
        self.execution_id = execution_id
    
    async def save_discoveries(self, discoveries: List[Dict], current_url: str, 
                              preserve_manual: bool = True) -> None:
        """
        Save discoveries to registry
        CRITICAL: Preserves manual XPaths if preserve_manual=True
        CRITICAL: Groups discoveries by their discovery_url (where they were found), not current_url
        
        Args:
            discoveries: List of discovery dicts (each should have 'discovery_url' field)
            current_url: Current page URL (fallback if discovery_url not present)
            preserve_manual: If True, never overwrite existing XPaths
        """
        if not discoveries:
            return
        
        try:
            logger.info(f"  💾 Updating element registry with {len(discoveries)} discovered XPaths...")
            
            # Group discoveries by their discovery URL (where they were actually discovered)
            discoveries_by_url = {}
            for discovery in discoveries:
                # Use discovery_url if available, otherwise fallback to current_url
                discovery_url = discovery.get('discovery_url') or current_url
                if discovery_url not in discoveries_by_url:
                    discoveries_by_url[discovery_url] = []
                discoveries_by_url[discovery_url].append(discovery)
            
            logger.info(f"  📊 Grouped discoveries into {len(discoveries_by_url)} pages")
            
            # Save discoveries for each page
            for discovery_url, page_discoveries in discoveries_by_url.items():
                logger.info(f"  💾 Saving {len(page_discoveries)} discoveries for {discovery_url}")
                
                # Extract domain and page from discovery URL
                domain = discovery_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
                
                # Determine page name
                # Remove query parameters and fragments
                url_without_query = discovery_url.split('?')[0].split('#')[0]
                # Get the path part (everything after domain)
                path_part = url_without_query.replace('https://', '').replace('http://', '').split('/', 1)[1] if '/' in url_without_query.replace('https://', '').replace('http://', '') else ''
                
                if not path_part or path_part == '':
                    page = 'home'
                elif path_part == 'explore':
                    page = 'explore'
                else:
                    # Use the last segment of the path as page name
                    # For paths like /login/two_factor/authenticator, use 'authenticator'
                    # For paths like /data-submissions, use 'data-submissions'
                    page = path_part.rstrip('/').split('/')[-1]
                    # Sanitize page name (remove invalid filename characters)
                    # Replace invalid characters with underscores
                    import re
                    page = re.sub(r'[<>:"/\\|?*]', '_', page)
                    # Remove query parameters if any slipped through
                    page = page.split('?')[0].split('#')[0]
            
                # Load existing registry or create new one
                element_map = self.element_registry.load_map(domain, page)
                if not element_map:
                    # Auto-create registry file if it doesn't exist
                    logger.info(f"  📝 Creating new registry for {domain}/{page}")
                    element_map = {
                        "page": page,
                        "url": f"https://{domain}/{page}" if page != 'home' else f"https://{domain}/",
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
                    # Save empty registry file first
                    self.element_registry.save_map(domain, page, element_map)
                    logger.info(f"  ✅ Created new registry file for {domain}/{page}")
                
                if element_map:
                    added_count = 0
                    for discovery in page_discoveries:
                        element_name = discovery['name']
                        element_id = discovery.get('element_id')
                        
                        # Process discoveries with xpath (save to registry)
                        if discovery.get('xpath'):
                            
                            # CRITICAL FIX: Check registry FIRST before generating new element_id
                            # This ensures we use existing element_id from registry instead of generating new one
                            xpath_value = discovery['xpath']
                            existing_key = None
                            existing_element = None
                            
                            # Strategy 1: Check by XPath value (most reliable match)
                            if xpath_value:
                                for key, elem_data in element_map.get('elements', {}).items():
                                    if elem_data.get('xpath') == xpath_value:
                                        existing_key = key
                                        existing_element = elem_data
                                        logger.info(f"    🎯 Found existing entry by XPath: {key}")
                                        break
                            
                            # Strategy 2: Check by name (fallback)
                            if not existing_key and element_name in element_map.get('elements', {}):
                                existing_key = element_name
                                existing_element = element_map['elements'][existing_key]
                                logger.info(f"    🎯 Found existing entry by name: {element_name}")
                            
                            # Strategy 3: Check by element_id if discovery already has one
                            if not existing_key and element_id:
                                for key, elem_data in element_map.get('elements', {}).items():
                                    if elem_data.get('element_id') == element_id:
                                        existing_key = key
                                        existing_element = elem_data
                                        logger.info(f"    🎯 Found existing entry by element_id: {key} (ID: {element_id})")
                                        break
                            
                            # Create element entry
                            element_entry = {
                                "selector": discovery['final_selector'],
                                "xpath": discovery['xpath'],
                                "uniqueness_method": discovery.get('uniqueness_method', 'unknown'),
                                "type": discovery.get('metadata', {}).get('type', 'unknown'),
                                "description": f"Discovered by AI in test {self.execution_id}",
                                "source": "ai_discovery",
                                "discovery_method": discovery['discovery_method'],
                                "usage_count": 1,
                                "alternatives": [],
                                "discovery_url": discovery.get('discovery_url')  # Preserve discovery URL
                            }
                            
                            # Assign element_id: Use existing from registry if found, otherwise generate new
                            if existing_element and existing_element.get('element_id'):
                                # Use existing element_id from registry (maintains consistency)
                                element_entry['element_id'] = existing_element.get('element_id')
                                logger.info(f"    ✅ Using existing element_id from registry: {element_entry['element_id']}")
                            elif element_id:
                                # Discovery already has element_id
                                element_entry['element_id'] = element_id
                            elif discovery['xpath']:
                                # Generate new ID only if entry doesn't exist
                                element_entry['element_id'] = self.element_registry._generate_element_id(
                                    element_name, discovery['xpath']
                                )
                                logger.info(f"    🔄 Generated new element_id: {element_entry['element_id']}")
                            elif discovery.get('final_selector') or discovery.get('original_query'):
                                # Generate ID from selector if xpath is missing
                                selector_for_id = discovery.get('final_selector') or discovery.get('original_query', '')
                                element_entry['element_id'] = self.element_registry._generate_element_id(
                                    element_name, selector_for_id
                                )
                                logger.info(f"    🔄 Generated element_id from selector (no xpath): {element_entry['element_id']}")
                            
                            # CRITICAL: Backfill element_id into discovery object (always, regardless of existing/new)
                            if element_entry.get('element_id') and not discovery.get('element_id'):
                                discovery['element_id'] = element_entry['element_id']
                                logger.info(f"    🔄 Backfilled element_id into discovery: {discovery['element_id']}")
                            
                            if existing_key:
                                # Update existing entry
                                # Note: element_id already backfilled above (line 181-184) if needed
                                
                                # 🔒 CRITICAL: NEVER overwrite existing XPath if it exists (manual XPath = absolute source of truth)
                                existing_xpath = existing_element.get('xpath', '')
                                discovery_xpath = element_entry.get('xpath', '')
                                
                                # If registry already has an XPath, preserve it (manual XPath should never be overwritten)
                                if preserve_manual and existing_xpath:
                                    # Keep existing XPath, update other fields only
                                    preserved_xpath = existing_xpath
                                    existing_element.update(element_entry)
                                    existing_element['xpath'] = preserved_xpath  # Restore preserved XPath
                                    logger.info(f"    🔒 Preserved existing XPath (manual XPath = source of truth): {preserved_xpath[:80]}...")
                                else:
                                    # No existing XPath - update normally (including new XPath from discovery)
                                    existing_element.update(element_entry)
                                    logger.info(f"    ✅ Updated registry entry with new XPath: {discovery_xpath[:80] if discovery_xpath else 'N/A'}...")
                                
                                # Ensure element_id is preserved from registry if it exists
                                if existing_element.get('element_id'):
                                    element_entry['element_id'] = existing_element['element_id']
                                    element_map['elements'][existing_key]['element_id'] = existing_element['element_id']
                                logger.info(f"    📝 Updated registry entry: {existing_key}")
                            else:
                                # Add new entry
                                element_map['elements'][element_name] = element_entry
                                added_count += 1
                                logger.info(f"    ✅ Added to registry: {element_name} (ID: {element_entry.get('element_id', 'N/A')})")
                                
                                # Ensure element_id is backfilled into discovery
                                if element_entry.get('element_id') and not discovery.get('element_id'):
                                    discovery['element_id'] = element_entry['element_id']
                                    logger.info(f"    🔄 Backfilled element_id into discovery (new entry): {discovery['element_id']}")
                        else:
                            # FIX #1a: Handle discoveries WITHOUT xpath - still generate element_id and backfill
                            if not discovery.get('element_id'):
                                selector_for_id = discovery.get('final_selector') or discovery.get('original_query', '')
                                if selector_for_id:
                                    generated_id = self.element_registry._generate_element_id(element_name, selector_for_id)
                                    discovery['element_id'] = generated_id
                                    logger.info(f"    🔄 Generated element_id from selector (no xpath) for {element_name}: {generated_id}")
                
                    if added_count > 0:
                        logger.info(f"  ℹ️ Added {added_count} new entries to registry for {domain}/{page}")
                    else:
                        logger.info(f"  ℹ️ No new entries added to {domain}/{page} (all already in registry)")
                    
                    # Update id_index
                    id_index = {}
                    for name, elem_data in element_map.get('elements', {}).items():
                        element_id = elem_data.get('element_id')
                        if element_id:
                            id_index[element_id] = name
                    
                    element_map['id_index'] = id_index
                    
                    # Save updated registry
                    try:
                        self.element_registry.save_map(domain, page, element_map)
                        # Verify file was actually created
                        map_path = self.element_registry.get_map_path(domain, page)
                        if map_path.exists():
                            logger.info(f"  ✅ Saved registry updates to {domain}/{page} (file: {map_path})")
                        else:
                            logger.error(f"  ❌ Registry save reported success but file not found: {map_path}")
                    except Exception as save_error:
                        logger.error(f"  ❌ Failed to save registry file for {domain}/{page}: {save_error}", exc_info=True)
        except Exception as e:
            logger.error(f"  ❌ Failed to save discoveries to registry: {e}", exc_info=True)


