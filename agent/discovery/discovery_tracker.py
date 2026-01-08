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
    
    def __init__(self, page, xpath_generator, element_registry, current_url: str):
        """
        Initialize discovery tracker
        Args:
            page: Playwright page object
            xpath_generator: XPathGenerator instance
            element_registry: ElementRegistry instance
            current_url: Current page URL
        """
        self.page = page
        self.xpath_generator = xpath_generator
        self.element_registry = element_registry
        self.current_url = current_url
        self.discoveries: List[Dict] = []
    
    def update_url(self, new_url: str) -> None:
        """
        Update current URL when navigation occurs
        Args:
            new_url: New page URL
        """
        self.current_url = new_url
        logger.debug(f"  🔄 Updated discovery tracker URL: {new_url}")
    
    async def track(self, element_name: str, original_query: str, final_selector: str,
                   discovery_method: str, metadata: dict, clicked_xpath: str = None,
                   clicked_element=None) -> Dict:
        """
        Track a successful discovery for later registry update
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
                
                # Check if selector contains text= or :has-text()
                if 'text=' in selector:
                    element_text = selector.split('text=')[1].strip().strip("'\"")
                elif ':has-text(' in selector:
                    text_match = re.search(r":has-text\(['\"]([^'\"]+)['\"]\)", selector)
                    if text_match:
                        element_text = text_match.group(1)
                
                # Try to infer element type from selector or context
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
                        if await self._verify_xpath(candidate_xpath):
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
                    if await self._verify_xpath(candidate_xpath):
                        xpath_to_use = candidate_xpath
                        uniqueness_method = "fallback_text_match"
                        logger.info(f"  ✅ Verified fallback XPath: {xpath_to_use}")
                elif not xpath_to_use and element_text:
                    # Generic fallback: try button first (most common for text selectors)
                    escaped_text = element_text.replace("'", "\\'")
                    candidate_xpath = f"//button[normalize-space(.)='{escaped_text}']"
                    
                    # Verify XPath works before using it
                    if await self._verify_xpath(candidate_xpath):
                        xpath_to_use = candidate_xpath
                        uniqueness_method = "fallback_button_text"
                        logger.info(f"  ✅ Verified fallback XPath (button): {xpath_to_use}")
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
            "discovery_url": self.current_url,  # Track URL where discovery was made
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
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
    
    def get_discoveries(self) -> List[Dict]:
        """Get all tracked discoveries"""
        return self.discoveries
    
    def clear(self) -> None:
        """Clear all discoveries"""
        self.discoveries = []


