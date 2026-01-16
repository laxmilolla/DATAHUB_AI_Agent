"""
Label Matcher - Find form elements by their label text
Shared utility for all tools (browser_fill, browser_click, browser_verify)
"""
import logging
from typing import Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class LabelMatcher:
    """Find form elements (input, select, radio, checkbox) by their label text"""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def find_element_by_label(self, label_text: str, element_types: list = None) -> Optional[str]:
        """
        Find form element by its label text
        This handles the common pattern where labels are associated with form elements
        
        Args:
            label_text: Text to search for in labels (e.g., "Submission Name", "Program")
            element_types: List of element types to find ['input', 'select', 'textarea', 'button']
                          If None, finds all types
        Returns:
            Selector string if found, None otherwise
        """
        if element_types is None:
            element_types = ['input', 'select', 'textarea']
        
        try:
            # Normalize search text - remove spaces for flexible matching
            search_text = label_text.lower().strip()
            search_text_no_spaces = search_text.replace(' ', '').replace('-', '').replace('_', '')
            
            # Find all labels
            labels = await self.page.locator('label').all()
            
            for label in labels:
                try:
                    # Get label text
                    label_text_content = await label.text_content()
                    if not label_text_content:
                        continue
                    
                    label_text_lower = label_text_content.strip().lower()
                    label_text_no_spaces = label_text_lower.replace(' ', '').replace('-', '').replace('_', '')
                    
                    # Check if label contains search text (partial match)
                    # Try exact match first, then space-normalized match
                    if (search_text in label_text_lower or 
                        label_text_lower in search_text or
                        search_text_no_spaces in label_text_no_spaces or
                        label_text_no_spaces in search_text_no_spaces):
                        logger.info(f"  📋 Found matching label: '{label_text_content.strip()}'")
                        
                        # Strategy 1: Find element via 'for' attribute
                        label_for = await label.get_attribute('for')
                        if label_for:
                            # Find element with matching id
                            element_by_id = self.page.locator(f"#{label_for}").first
                            if await element_by_id.count() > 0:
                                if await element_by_id.is_visible(timeout=1000):
                                    # Get actual attributes
                                    tag_name = await element_by_id.evaluate("el => el.tagName.toLowerCase()")
                                    
                                    # Check if element type matches what we're looking for
                                    if tag_name not in element_types and 'button' not in element_types:
                                        continue
                                    
                                    name_attr = await element_by_id.get_attribute('name')
                                    id_attr = await element_by_id.get_attribute('id')
                                    
                                    # Build selector
                                    if name_attr:
                                        selector = f"{tag_name}[name='{name_attr}']"
                                    elif id_attr:
                                        selector = f"#{id_attr}"
                                    else:
                                        selector = f"#{label_for}"
                                    
                                    logger.info(f"  ✅ Found element via 'for' attribute: {selector}")
                                    return selector
                        
                        # Strategy 2: Find input/select within label (parent relationship)
                        element_types_str = ', '.join(element_types)
                        element_in_label = label.locator(element_types_str).first
                        if await element_in_label.count() > 0:
                            if await element_in_label.is_visible(timeout=1000):
                                # Get actual attributes
                                tag_name = await element_in_label.evaluate("el => el.tagName.toLowerCase()")
                                name_attr = await element_in_label.get_attribute('name')
                                id_attr = await element_in_label.get_attribute('id')
                                
                                # Build selector
                                if name_attr:
                                    selector = f"{tag_name}[name='{name_attr}']"
                                elif id_attr:
                                    selector = f"#{id_attr}"
                                else:
                                    # Use XPath to find this specific element within the label
                                    xpath = f"//label[contains(text(), '{label_text_content.strip()[:30]}')]//{tag_name}"
                                    selector = f"xpath={xpath}"
                                
                                logger.info(f"  ✅ Found element within label: {selector}")
                                return selector
                        
                        # Strategy 3: Find adjacent sibling using XPath
                        element_types_xpath = ' | '.join([f'{t}' for t in element_types])
                        xpath = f"//label[contains(normalize-space(text()), '{label_text_content.strip()[:30]}')]/following::{element_types_xpath}[1] | //label[contains(normalize-space(text()), '{label_text_content.strip()[:30]}')]//{element_types_xpath}[1] | //{element_types_xpath}[@id=//label[contains(normalize-space(text()), '{label_text_content.strip()[:30]}')]/@for]"
                        xpath_locator = self.page.locator(f"xpath={xpath}").first
                        if await xpath_locator.count() > 0:
                            if await xpath_locator.is_visible(timeout=1000):
                                # Get actual attributes for better selector
                                tag_name = await xpath_locator.evaluate("el => el.tagName.toLowerCase()")
                                name_attr = await xpath_locator.get_attribute('name')
                                id_attr = await xpath_locator.get_attribute('id')
                                
                                if name_attr:
                                    selector = f"{tag_name}[name='{name_attr}']"
                                    logger.info(f"  ✅ Found element via XPath label matching: {selector}")
                                    return selector
                                elif id_attr:
                                    selector = f"#{id_attr}"
                                    logger.info(f"  ✅ Found element via XPath label matching: {selector}")
                                    return selector
                                else:
                                    logger.info(f"  ✅ Found element via XPath label matching: xpath={xpath}")
                                    return f"xpath={xpath}"
                
                except Exception as e:
                    logger.debug(f"  ⚠️ Error processing label: {e}")
                    continue
            
            logger.info(f"  ⚠️ No matching label found for '{label_text}'")
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️ Label-to-element matching failed: {e}")
            return None

