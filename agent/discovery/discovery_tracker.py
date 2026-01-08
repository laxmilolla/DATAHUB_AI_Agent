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


