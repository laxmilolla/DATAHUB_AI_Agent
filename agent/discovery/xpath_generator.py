"""
XPath Generator - Generate unique XPaths for elements
Extracted from bedrock_playwright_agent.py lines 941-1077
"""
import re
import logging
from typing import Dict, Optional
from playwright.async_api import Locator, ElementHandle

logger = logging.getLogger(__name__)


class XPathGenerator:
    """Generate unique XPaths for elements"""
    
    def __init__(self, page):
        """
        Initialize XPath generator
        Args:
            page: Playwright page object
        """
        self.page = page
        # XPathBuilder will be imported when needed to avoid circular dependencies
        # from utils.xpath_builder import XPathBuilder
    
    async def generate_final_selector(self, element, original_query: str = None) -> Optional[str]:
        """
        Generate a simple, stable selector from the element that was clicked
        Args:
            element: Playwright element
            original_query: Original search query (preserved for simple text selectors)
        Priority:
        1. role + aria attributes + text (semantic and stable)
        2. data-testid or stable id (purpose-built for testing)
        3. Preserve original_query if it's a simple text selector (maintains case/exact match)
        4. Simple text selector (stable, generic)
        """
        try:
            # Get element properties
            props = await element.evaluate("""el => ({
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role'),
                ariaExpanded: el.getAttribute('aria-expanded'),
                ariaSelected: el.getAttribute('aria-selected'),
                ariaLabel: el.getAttribute('aria-label'),
                type: el.getAttribute('type'),
                name: el.getAttribute('name'),
                id: el.id,
                dataTestId: el.getAttribute('data-testid'),
                text: el.textContent.trim().substring(0, 50)
            })""")
            
            # Strategy 1: Role + aria + text
            if props['role'] and props['text']:
                if props['ariaExpanded'] is not None:
                    return f"{props['tag']}[role='{props['role']}'][aria-expanded]:has-text('{props['text']}')"
                elif props['ariaSelected'] is not None:
                    return f"{props['tag']}[role='{props['role']}'][aria-selected]:has-text('{props['text']}')"
                else:
                    return f"{props['tag']}[role='{props['role']}']:has-text('{props['text']}')"
            
            # Strategy 2: data-testid
            if props['dataTestId']:
                return f"[data-testid='{props['dataTestId']}']"
            
            # Strategy 3: name attribute
            if props['name'] and props['tag'] in ['input', 'select', 'textarea', 'button']:
                return f"{props['tag']}[name='{props['name']}']"
            
            # Strategy 4: Stable id
            if props['id'] and not props['id'].startswith(('dropdown', 'checkbox', 'mui-', 'Mui')):
                if not re.search(r'-\d+$', props['id']):
                    return f"#{props['id']}"
            
            # Strategy 5: Preserve original_query if it's a simple text selector (FIX: maintain exact match)
            if original_query and original_query.startswith('text='):
                return original_query
            
            # Strategy 6: Simple text selector
            if props['text']:
                return f"text={props['text']}"
            
            # Last resort: tag + role
            if props['role']:
                return f"{props['tag']}[role='{props['role']}']"
            
            return None
        except Exception as e:
            logger.warning(f"  ⚠️ Could not generate final selector: {e}")
            return None
    
    async def extract_element_attributes(self, locator) -> Dict:
        """
        Extract all attributes from a Playwright locator or ElementHandle for XPath generation
        """
        try:
            from playwright.async_api import ElementHandle, Locator
            
            if isinstance(locator, ElementHandle):
                element = locator
            elif isinstance(locator, Locator):
                element = await locator.element_handle()
                if not element:
                    logger.warning("  ⚠️ Could not get element handle for attribute extraction")
                    return {}
            else:
                logger.warning(f"  ⚠️ Unexpected type for locator: {type(locator)}")
                return {}
            
            # Extract tag name
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            
            # Extract attributes
            attrs = {
                "tag": tag_name,
                "id": await element.get_attribute('id'),
                "role": await element.get_attribute('role'),
                "aria-label": await element.get_attribute('aria-label'),
                "aria-expanded": await element.get_attribute('aria-expanded'),
                "aria-selected": await element.get_attribute('aria-selected'),
                "title": await element.get_attribute('title'),
                "data-testid": await element.get_attribute('data-testid'),
                "class": await element.get_attribute('class'),
                "name": await element.get_attribute('name'),
                "text": await element.text_content()
            }
            
            # Clean up None values
            attrs = {k: v for k, v in attrs.items() if v is not None}
            
            logger.info(f"  📝 Extracted {len(attrs)} attributes: {list(attrs.keys())}")
            if attrs.get('tag'):
                logger.info(f"     🏷️  Tag: {attrs['tag']}")
            if attrs.get('id'):
                logger.info(f"     🆔 ID: {attrs['id']}")
            if attrs.get('text'):
                logger.info(f"     📄 Text: {attrs['text'][:50]}")
            
            return attrs
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to extract attributes: {e}")
            import traceback
            logger.warning(f"     {traceback.format_exc()}")
            return {}
    
    def extract_xpath_from_result(self, result_string: str) -> Optional[str]:
        """
        Extract XPath from AI result string
        Example: '✅ Clicked xpath=//div[...] - Verified'
        """
        if not result_string or 'Clicked' not in result_string:
            return None
        
        clicked_match = re.search(r'(?:✅\s*)?Clicked\s+(.+?)(?:\s+-\s+|$)', result_string)
        if clicked_match:
            selector_raw = clicked_match.group(1).strip().rstrip('.,;').strip()
            if selector_raw.startswith('xpath='):
                return selector_raw.replace('xpath=', '').strip()
            elif selector_raw.startswith('//') or ('[@' in selector_raw and ']' in selector_raw):
                return selector_raw
        return None
    
    async def generate_xpath(self, element_attrs: Dict, element_name: str) -> Dict:
        """
        Generate unique XPath using XPathBuilder
        Returns: {xpath, uniqueness_method}
        """
        from utils.xpath_builder import XPathBuilder
        
        try:
            xpath_builder = XPathBuilder(self.page)
            xpath_result = await xpath_builder.build_unique_xpath(element_attrs, element_name)
            return xpath_result
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to generate XPath: {e}")
            return {"xpath": None, "uniqueness_method": "failed"}


