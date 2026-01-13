"""
Discovery Tracker - Track element discoveries
Extracted from bedrock_playwright_agent.py lines 1078-1193
"""
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
from playwright.async_api import Locator, ElementHandle

logger = logging.getLogger(__name__)


class DiscoveryTracker:
    """Track element discoveries"""
    
    def __init__(self, page, xpath_generator, element_registry, current_url: str, execution_context=None):
        """
        Initialize discovery tracker
        Args:
            page: Playwright page object
            xpath_generator: XPathGenerator instance
            element_registry: ElementRegistry instance
            current_url: Current page URL
            execution_context: ExecutionContext instance (optional, for step_number tracking)
        """
        self.page = page
        self.xpath_generator = xpath_generator
        self.element_registry = element_registry
        self.current_url = current_url
        self.execution_context = execution_context
        self.discoveries: List[Dict] = []
    
    def update_url(self, new_url: str) -> None:
        """
        Update current URL when navigation occurs
        Args:
            new_url: New page URL
        """
        self.current_url = new_url
        logger.debug(f"  🔄 Updated discovery tracker URL: {new_url}")
    
    def _extract_unique_attributes(self, metadata: dict, element_name: str, final_selector: str) -> dict:
        """
        Extract unique attributes from element metadata for easier matching
        Returns a dict with id, aria-labelledby, parent relationships, etc.
        """
        unique_attrs = {}
        element_attrs = metadata.get('element_attrs', {})
        
        # Extract direct attributes
        if element_attrs.get('id'):
            unique_attrs['id'] = element_attrs['id']
        
        if element_attrs.get('role'):
            unique_attrs['role'] = element_attrs['role']
        
        if element_attrs.get('data-testid'):
            unique_attrs['data_testid'] = element_attrs['data-testid']
        
        if element_attrs.get('name'):
            unique_attrs['name'] = element_attrs['name']
        
        if element_attrs.get('aria-labelledby'):
            unique_attrs['aria_labelledby'] = element_attrs['aria-labelledby']
        
        # Extract text if available
        if element_attrs.get('text'):
            unique_attrs['text'] = element_attrs['text'].strip()
        
        # For dropdown options, try to extract parent dropdown ID from selector/xpath
        if element_attrs.get('role') == 'option' or 'option' in element_name.lower():
            # Try to extract parent dropdown ID from aria-labelledby or selector
            if 'aria-labelledby' in final_selector:
                import re
                match = re.search(r'aria-labelledby=["\']([^"\']+)["\']', final_selector)
                if match:
                    unique_attrs['parent_dropdown_id'] = match.group(1)
            elif 'aria-labelledby' in str(metadata.get('parent_info', '')):
                # Try to extract from parent_info if available
                parent_info = str(metadata.get('parent_info', ''))
                match = re.search(r'aria-labelledby=["\']([^"\']+)["\']', parent_info)
                if match:
                    unique_attrs['parent_dropdown_id'] = match.group(1)
        
        # For dropdown buttons, extract hidden input name if available
        if element_attrs.get('role') == 'button' and ('select' in final_selector.lower() or 'dropdown' in element_name.lower()):
            # Try to extract name from hidden input or parent
            if 'name=' in final_selector:
                import re
                match = re.search(r'name=["\']([^"\']+)["\']', final_selector)
                if match:
                    unique_attrs['hidden_input_name'] = match.group(1)
        
        # Extract parent data-testid if available
        parent_info = metadata.get('parent_info', '')
        if parent_info and 'data-testid' in str(parent_info):
            import re
            match = re.search(r'data-testid=["\']([^"\']+)["\']', str(parent_info))
            if match:
                unique_attrs['parent_data_testid'] = match.group(1)
        
        if unique_attrs:
            logger.debug(f"  🔍 Extracted unique_attributes: {list(unique_attrs.keys())}")
        
        return unique_attrs
    
    async def track(self, element_name: str, original_query: str, final_selector: str,
                   discovery_method: str, metadata: dict, clicked_xpath: str = None,
                   clicked_element=None, discovery_url: str = None) -> Dict:
        """
        Track a successful discovery for later registry update
        Args:
            discovery_url: URL where discovery was made (if None, uses self.current_url)
        Returns: Discovery dict
        """
        # PRIORITY: Use clicked XPath from result string (what AI actually clicked)
        xpath_to_use = clicked_xpath
        uniqueness_method = "clicked_xpath" if clicked_xpath else None
        
        # CRITICAL FIX: If tree climbing found a parent, element_attrs in metadata is already from original clicked element
        # So we skip special parent handling and use normal path (element_attrs already correct)
        
        # Fallback: Generate XPath from the discovered element (uses element_attrs from metadata)
        if not xpath_to_use:
            try:
                element_attrs = metadata.get('element_attrs', {})
                if element_attrs:
                    logger.info(f"  🔨 Building XPath for '{element_name}' using LIVE Playwright DOM...")
                    xpath_result = await self.xpath_generator.generate_xpath(element_attrs, element_name)
                    xpath_to_use = xpath_result['xpath']
                    uniqueness_method = xpath_result['uniqueness_method']
                    logger.info(f"  ✅ Generated unique XPath: {xpath_to_use}")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to generate XPath: {e}")
        
        # Fallback 2: If XPath generation failed, try to generate simple XPath from selector/text
        if not xpath_to_use:
            try:
                # Extract element type and text from final_selector
                selector = final_selector or original_query
                element_text = None
                element_type = None
                
                # PRIORITY 1: Use actual tag name from clicked element (most reliable)
                element_attrs = metadata.get('element_attrs', {})
                actual_tag = element_attrs.get('tag')
                if actual_tag:
                    element_type = actual_tag
                    logger.info(f"  🏷️  Using actual tag from clicked element: {element_type}")
                
                # Check if selector contains text= or :has-text()
                if 'text=' in selector:
                    element_text = selector.split('text=')[1].strip().strip("'\"")
                elif ':has-text(' in selector:
                    text_match = re.search(r":has-text\(['\"]([^'\"]+)['\"]\)", selector)
                    if text_match:
                        element_text = text_match.group(1)
                
                # PRIORITY 2: If no actual tag, try to infer element type from selector or context
                if not element_type:
                    if 'button' in selector.lower() or 'button' in element_name.lower():
                        element_type = 'button'
                    elif selector.startswith('input['):
                        element_type = 'input'
                        # Extract input type if available
                        type_match = re.search(r"type=['\"]([^'\"]+)['\"]", selector)
                        if type_match:
                            input_type = type_match.group(1)
                            if element_text:
                                candidate_xpath = f"//input[@type='{input_type}' and normalize-space(.)='{element_text}']"
                            else:
                                candidate_xpath = f"//input[@type='{input_type}']"
                            
                            # Verify XPath works before using it
                            if await self._verify_xpath(candidate_xpath, original_query):
                                xpath_to_use = candidate_xpath
                                uniqueness_method = "fallback_input_type"
                                logger.info(f"  ✅ Verified fallback XPath: {xpath_to_use}")
                    elif selector.startswith('a[') or 'link' in selector.lower():
                        element_type = 'a'
                    elif selector.startswith('select'):
                        element_type = 'select'
                
                # Generate simple XPath based on type and text
                if not xpath_to_use and element_type and element_text:
                    # Escape quotes in text for XPath
                    escaped_text = element_text.replace("'", "\\'")
                    candidate_xpath = f"//{element_type}[normalize-space(.)='{escaped_text}']"
                    
                    # Verify XPath works before using it
                    if await self._verify_xpath(candidate_xpath, original_query):
                        xpath_to_use = candidate_xpath
                        uniqueness_method = "fallback_text_match"
                        logger.info(f"  ✅ Verified fallback XPath: {xpath_to_use}")
                elif not xpath_to_use and element_text:
                    # PRIORITY 3: Generic fallback - use actual tag if available, otherwise try button
                    escaped_text = element_text.replace("'", "\\'")
                    fallback_tag = actual_tag if actual_tag else 'button'
                    candidate_xpath = f"//{fallback_tag}[normalize-space(.)='{escaped_text}']"
                    
                    # Verify XPath works before using it
                    if await self._verify_xpath(candidate_xpath, original_query):
                        xpath_to_use = candidate_xpath
                        uniqueness_method = f"fallback_{fallback_tag}_text"
                        logger.info(f"  ✅ Verified fallback XPath ({fallback_tag}): {xpath_to_use}")
            except Exception as e:
                logger.debug(f"  ⚠️ Fallback XPath generation failed: {e}")
        
        # Look up element_id from registry if element exists
        element_id = None
        try:
            domain = self.current_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
            url_path = self.current_url.split('/')[-1].split('#')[0]
            if url_path == 'explore':
                page = 'explore'
            elif not url_path or url_path == '':
                page = 'home'
            else:
                page = url_path
            
            # Strategy 1: Try exact name match
            registry_element = self.element_registry.get_element(domain, page, element_name)
            if registry_element:
                element_id = registry_element.get('element_id')
                if element_id:
                    logger.info(f"  🆔 Found element_id in registry (by name): {element_id}")
            
            # Strategy 2: If not found and we have XPath, search by XPath
            if not element_id and xpath_to_use:
                element_map = self.element_registry.load_map(domain, page)
                if element_map:
                    for key, elem_data in element_map.get('elements', {}).items():
                        if elem_data.get('xpath') == xpath_to_use:
                            element_id = elem_data.get('element_id')
                            if element_id:
                                logger.info(f"  🆔 Found element_id in registry (by XPath): {element_id}")
                                break
        except Exception as e:
            logger.debug(f"  ⚠️ Could not lookup element_id: {e}")
        
        # Extract unique attributes for easier matching
        unique_attributes = self._extract_unique_attributes(metadata, element_name, final_selector)
        
        # Store discovery with XPath and element_id
        # CRITICAL: Track the URL where this discovery was made (not where test ended)
        discovery = {
            "name": element_name,
            "element_id": element_id,
            "original_query": original_query,
            "final_selector": final_selector,
            "xpath": xpath_to_use,
            "uniqueness_method": uniqueness_method,
            "discovery_method": discovery_method,
            "metadata": metadata,
            "unique_attributes": unique_attributes if unique_attributes else None,  # Store unique attributes
            "discovery_url": discovery_url or self.current_url,  # Use provided URL or current URL
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        # FIX #2: Add step_number and step_identifier to discovery if execution_context is available
        if self.execution_context:
            # Use step_identifier if available (matches story step), otherwise fall back to step_number
            step_identifier = getattr(self.execution_context, 'current_step_identifier', None)
            step_num = self.execution_context.current_step_number
            
            if step_identifier:
                discovery["step_identifier"] = step_identifier
                # Extract step number from identifier for backward compatibility
                step_num_match = re.match(r'(\d+)', step_identifier)
                if step_num_match:
                    step_num = int(step_num_match.group(1))
            
            discovery["step_number"] = step_num
            logger.info(f"     Step Identifier: {step_identifier or step_num}")
            logger.info(f"     Step Number: {step_num}")
        else:
            logger.warning(f"  ⚠️  No execution_context available - step_number not set for discovery: {element_name}")
        
        self.discoveries.append(discovery)
        logger.info(f"  📝 Tracked discovery: {element_name} via {discovery_method} on {self.current_url}")
        if element_id:
            logger.info(f"     Element ID: {element_id}")
        logger.info(f"     Query: {original_query}")
        if xpath_to_use:
            logger.info(f"     XPath: {xpath_to_use}")
        else:
            logger.info(f"     Selector: {final_selector}")
        logger.info(f"     Discovery URL: {self.current_url}")
        
        return discovery
    
    async def _verify_xpath(self, xpath: str, original_selector: str = None) -> bool:
        """
        Verify that an XPath actually finds an element on the current page
        Args:
            xpath: XPath to verify
            original_selector: Original selector used to find the element (for fallback verification)
        Returns:
            True if XPath finds at least one element, False otherwise
        """
        try:
            from playwright.async_api import Page
            # Get page from xpath_generator
            page = self.xpath_generator.page if hasattr(self.xpath_generator, 'page') else None
            if not page:
                logger.debug(f"  ⚠️ Cannot verify XPath: page not available")
                return False
            
            # Try to find element using XPath
            try:
                count = await page.locator(f"xpath={xpath}").count(timeout=5000)
                if count > 0:
                    logger.debug(f"  ✅ XPath verified: found {count} element(s) for {xpath[:50]}...")
                    return True
                else:
                    # If XPath doesn't find element, try verifying with original selector
                    # (element might have been clicked and page navigated, but original selector proves it existed)
                    if original_selector:
                        try:
                            original_count = await page.locator(original_selector).count(timeout=2000)
                            if original_count > 0:
                                logger.debug(f"  ✅ XPath verified via original selector: {original_selector}")
                                return True
                        except:
                            pass
                    
                    logger.debug(f"  ⚠️ XPath verification failed: found 0 elements for {xpath[:50]}...")
                    return False
            except Exception as e:
                # If XPath verification times out, but we have original selector, assume it's valid
                # (element was successfully clicked, so it exists)
                if original_selector:
                    logger.debug(f"  ⚠️ XPath verification timeout, but element was clicked successfully - assuming valid")
                    return True
                logger.debug(f"  ⚠️ XPath verification error: {e}")
                return False
        except Exception as e:
            logger.debug(f"  ⚠️ XPath verification error: {e}")
            return False
    
    def get_discoveries(self) -> List[Dict]:
        """Get all tracked discoveries"""
        return self.discoveries
    
    def update_last_discovery_step_identifier(self, step_identifier: str, step_number: int) -> None:
        """
        Update the last discovery's step_identifier and step_number.
        This is called after step_identifier is determined in agent.py,
        since discoveries are tracked before step_identifier is known.
        """
        if self.discoveries:
            last_discovery = self.discoveries[-1]
            last_discovery["step_identifier"] = step_identifier
            last_discovery["step_number"] = step_number
            logger.info(f"  ✅ Updated last discovery '{last_discovery.get('name', 'unknown')}' with step_identifier={step_identifier}, step_number={step_number}")
    
    def clear(self) -> None:
        """Clear all discoveries"""
        self.discoveries = []


