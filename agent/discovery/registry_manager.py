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
                url_path = discovery_url.split('/')[-1].split('#')[0]
                if url_path == 'explore':
                    page = 'explore'
                elif not url_path or url_path == '':
                    page = 'home'
                else:
                    page = url_path
            
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
                        if discovery.get('xpath'):
                            element_name = discovery['name']
                            element_id = discovery.get('element_id')
                            
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
                            
                            # Assign element_id if not present
                            if element_id:
                                element_entry['element_id'] = element_id
                            elif discovery['xpath']:
                                # Generate ID if missing
                                element_entry['element_id'] = self.element_registry._generate_element_id(
                                    element_name, discovery['xpath']
                                )
                            
                            # Check registry by XPath value (not just name)
                            xpath_value = discovery['xpath']
                            existing_key = None
                            
                            # Strategy 1: Check by element_id if available
                            if element_entry.get('element_id'):
                                element_id_to_find = element_entry['element_id']
                                for key, elem_data in element_map.get('elements', {}).items():
                                    if elem_data.get('element_id') == element_id_to_find:
                                        existing_key = key
                                        logger.info(f"    🎯 Found existing entry by element_id: {key} (ID: {element_id_to_find})")
                                        break
                            
                            # Strategy 2: Check by XPath value
                            if not existing_key and xpath_value:
                                for key, elem_data in element_map.get('elements', {}).items():
                                    if elem_data.get('xpath') == xpath_value:
                                        existing_key = key
                                        logger.info(f"    🎯 Found existing entry by XPath: {key}")
                                        break
                            
                            # Strategy 3: Check by name (fallback)
                            if not existing_key and element_name in element_map.get('elements', {}):
                                existing_key = element_name
                                logger.info(f"    🎯 Found existing entry by name: {element_name}")
                            
                            if existing_key:
                                # Update existing entry
                                existing_element = element_map['elements'][existing_key]
                                
                                # BACKFILL: If discovery is missing element_id, get it from registry
                                if not element_id and existing_element.get('element_id'):
                                    element_id = existing_element.get('element_id')
                                    discovery['element_id'] = element_id
                                    logger.info(f"    🔄 Backfilled element_id into discovery: {element_id}")
                                
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
                    self.element_registry.save_map(domain, page, element_map)
                    logger.info(f"  ✅ Saved registry updates to {domain}/{page}")
        except Exception as e:
            logger.error(f"  ❌ Failed to save discoveries to registry: {e}", exc_info=True)


