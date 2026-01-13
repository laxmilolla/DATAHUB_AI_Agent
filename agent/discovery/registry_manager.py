"""
Registry Manager - Manage element registry operations
Extracted from bedrock_playwright_agent.py lines 3412-3580
CRITICAL: XPath preservation logic must be exact copy
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

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
                                
                                # 🔒 CRITICAL: NEVER overwrite existing XPath/selector if it exists (manual = absolute source of truth)
                                existing_xpath = existing_element.get('xpath', '')
                                existing_selector = existing_element.get('selector', '')
                                discovery_xpath = element_entry.get('xpath', '')
                                discovery_selector = element_entry.get('selector', '')
                                
                                # If registry already has an XPath, preserve both XPath AND selector (manual = source of truth)
                                if preserve_manual and existing_xpath:
                                    # Keep existing XPath AND selector, update other fields only
                                    preserved_xpath = existing_xpath
                                    preserved_selector = existing_selector
                                    existing_element.update(element_entry)
                                    existing_element['xpath'] = preserved_xpath  # Restore preserved XPath
                                    existing_element['selector'] = preserved_selector  # Restore preserved selector
                                    logger.info(f"    🔒 Preserved existing XPath (manual XPath = source of truth): {preserved_xpath[:80]}...")
                                    logger.info(f"    🔒 Preserved existing selector (manual selector = source of truth): {preserved_selector[:80] if preserved_selector else 'N/A'}...")
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
    
    def save_step_mapping(self, story: str, actions_taken: List[Dict], discoveries: List[Dict], parsed_steps: Dict[int, Dict]) -> None:
        """
        Save execution-specific step_number mapping (HYBRID APPROACH)
        Creates step_number → element_name mapping per execution
        
        Args:
            story: Story text
            actions_taken: List of actions taken during execution
            discoveries: List of discoveries
            parsed_steps: Parsed story steps with metadata
        """
        try:
            logger.info(f"  💾 Saving step_number mapping for execution {self.execution_id}...")
            
            # Create execution-specific directory for step mappings
            # Use the same maps_dir as the element registry
            element_maps_dir = Path(self.element_registry.maps_dir)
            step_mappings_dir = element_maps_dir / self.execution_id
            step_mappings_dir.mkdir(parents=True, exist_ok=True)
            
            # Parse story into steps
            story_lines = story.split('\n')
            story_steps = {}
            for line in story_lines:
                line = line.strip()
                if not line or not line.startswith('Step'):
                    continue
                
                # Extract step number: "Step 4:" or "4."
                step_match = re.match(r'Step\s+(\d+)[\.:)]?\s*(.+)', line, re.IGNORECASE)
                if not step_match:
                    continue
                
                step_num = int(step_match.group(1))
                step_text = step_match.group(2).strip()
                story_steps[step_num] = step_text
            
            # Build step_number → element_name mapping
            step_mapping = {}
            reverse_mapping = {}  # element_name → step_number (for lookup)
            
            # Group discoveries by step_number
            discoveries_by_step = {}
            for disc in discoveries:
                step_num = disc.get('step_number')
                if step_num:
                    if step_num not in discoveries_by_step:
                        discoveries_by_step[step_num] = []
                    discoveries_by_step[step_num].append(disc)
            
            # Map story steps to discoveries via actions
            # Key insight: Story Step N should map to the element that was actually used in that step
            # We match by finding the discovery whose action's step_number matches the story step
            for story_step_num, step_text in story_steps.items():
                step_lower = step_text.lower()
                
                # Check if this is an optional step
                is_optional = ('optional' in step_lower or 
                              'if there is' in step_lower or 
                              'if appears' in step_lower or
                              '(if appears)' in step_lower)
                
                # Find discovery for this story step
                discovery_for_step = None
                action_for_step = None  # CRITICAL FIX: Initialize action_for_step
                
                # Strategy 1: Find discovery by matching action's step_number to story step
                # Look for actions with step_number matching story step
                for action in actions_taken:
                    action_step_num = action.get('step_number')
                    if action_step_num == story_step_num:
                        action_for_step = action  # CRITICAL FIX: Capture the action
                        action_tool = action.get('tool', '')
                        action_selector = action.get('input', {}).get('selector', '').lower()
                        
                        # Find discovery that matches this action
                        for disc in discoveries:
                            disc_step_num = disc.get('step_number')
                            disc_selector = (disc.get('final_selector') or disc.get('original_query', '')).lower()
                            
                            # Match by step_number (most reliable)
                            if disc_step_num == action_step_num:
                                discovery_for_step = disc
                                break
                            
                            # Match by selector (fallback)
                            if action_selector and disc_selector and action_selector in disc_selector:
                                discovery_for_step = disc
                                break
                        
                        if discovery_for_step:
                            break
                
                # Strategy 2: For optional steps, check if element appears in next steps
                if not discovery_for_step and is_optional:
                    # Extract element name from step text
                    element_keywords = []
                    if 'continue' in step_lower:
                        element_keywords = ['continue']
                    elif 'grant' in step_lower:
                        element_keywords = ['grant']
                    elif 'reminder' in step_lower or '2fa' in step_lower:
                        element_keywords = ['submit', 'reminder']
                    
                    # Look for discovery in next few steps
                    for disc in discoveries:
                        disc_name_lower = disc.get('name', '').lower()
                        disc_step_num = disc.get('step_number')
                        
                        # Check if discovery matches keywords and is in next steps
                        if any(kw in disc_name_lower for kw in element_keywords):
                            if disc_step_num and disc_step_num > story_step_num:
                                discovery_for_step = disc
                                break
                
                # Build mapping entry
                if discovery_for_step:
                    element_name = discovery_for_step.get('name')
                    action_step_num = action_for_step.get('step_number') if action_for_step else None
                    action_tool = action_for_step.get('tool', '') if action_for_step else None
                    
                    mapping_entry = {
                        "element": element_name,
                        "is_optional": is_optional,
                        "action_step_number": action_step_num,
                        "action_type": action_tool
                    }
                    
                    # For optional steps, check if actual click happened in next step
                    if is_optional and action_tool != 'browser_click':
                        # Look for actual click action in next steps
                        for next_action in actions_taken:
                            next_step_num = next_action.get('step_number')
                            if next_step_num and next_step_num > story_step_num:
                                next_selector = next_action.get('input', {}).get('selector', '').lower()
                                if element_name.lower() in next_selector or next_selector in element_name.lower():
                                    mapping_entry["actual_action_step"] = next_step_num
                                    break
                    
                    step_mapping[str(story_step_num)] = mapping_entry
                    reverse_mapping[element_name] = story_step_num
                elif is_optional:
                    # Optional step but no discovery found - element didn't appear
                    step_mapping[str(story_step_num)] = {
                        "element": None,
                        "is_optional": True,
                        "action_step_number": action_for_step.get('step_number') if action_for_step else None,
                        "action_type": action_for_step.get('tool', '') if action_for_step else None
                    }
            
            # Save step mapping to execution-specific file
            # Group by page (similar to registry structure)
            mappings_by_page = {}
            for disc in discoveries:
                discovery_url = disc.get('discovery_url', '')
                if not discovery_url:
                    continue
                
                # Extract domain and page (same logic as save_discoveries)
                domain = discovery_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
                url_without_query = discovery_url.split('?')[0].split('#')[0]
                path_part = url_without_query.replace('https://', '').replace('http://', '').split('/', 1)[1] if '/' in url_without_query.replace('https://', '').replace('http://', '') else ''
                
                if not path_part or path_part == '':
                    page = 'home'
                elif path_part == 'explore':
                    page = 'explore'
                else:
                    page = path_part.rstrip('/').split('/')[-1]
                    page = re.sub(r'[<>:"/\\|?*]', '_', page)
                    page = page.split('?')[0].split('#')[0]
                
                page_key = f"{domain}/{page}"
                if page_key not in mappings_by_page:
                    mappings_by_page[page_key] = {
                        "execution_id": self.execution_id,
                        "domain": domain,
                        "page": page,
                        "step_mapping": {},
                        "reverse_mapping": {}
                    }
            
            # If no discoveries, create at least one mapping file
            if not mappings_by_page:
                mappings_by_page["default"] = {
                    "execution_id": self.execution_id,
                    "domain": "default",
                    "page": "default",
                    "step_mapping": {},
                    "reverse_mapping": {}
                }
            
            # Distribute step mappings to pages (simplified: put all in first page)
            # In future, could distribute based on discovery_url
            first_page_key = list(mappings_by_page.keys())[0]
            mappings_by_page[first_page_key]["step_mapping"] = step_mapping
            mappings_by_page[first_page_key]["reverse_mapping"] = reverse_mapping
            
            # Save each page mapping
            for page_key, mapping_data in mappings_by_page.items():
                domain = mapping_data["domain"]
                page = mapping_data["page"]
                
                # Create domain subdirectory
                domain_dir = step_mappings_dir / domain
                domain_dir.mkdir(parents=True, exist_ok=True)
                
                # Save mapping file
                mapping_file = domain_dir / f"{page}_steps.json"
                with open(mapping_file, 'w') as f:
                    json.dump(mapping_data, f, indent=2)
                
                logger.info(f"  ✅ Saved step mapping to {mapping_file}")
            
            logger.info(f"  ✅ Saved step_number mapping for {len(step_mapping)} steps")
            
        except Exception as e:
            logger.error(f"  ❌ Failed to save step_number mapping: {e}", exc_info=True)


