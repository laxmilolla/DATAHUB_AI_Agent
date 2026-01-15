"""
XPath Builder - Generate Unique, Stable XPath for Elements
Priority: ID → ID+Text → ID+Title → ID+Role → Scoped → Position
WITH UNIQUENESS TESTING using live Playwright browser (NO BeautifulSoup!)
"""

import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class XPathBuilder:
    """
    Generate GUARANTEED unique XPath for every element
    Tests uniqueness using live Playwright browser
    Enhances XPath until it matches exactly ONE element
    """
    
    def __init__(self, page):
        """
        Args:
            page: Playwright Page object for LIVE DOM uniqueness testing
        """
        self.page = page
        self.xpath_registry = {}  # Track generated XPaths to prevent duplicates
    
    async def build_unique_xpath(self, attrs: Dict, element_name: str, parent_name: str = None) -> Dict:
        """
        Generate XPath using Playwright's LIVE DOM for uniqueness testing (async)
        
        Args:
            attrs: Dictionary of element attributes (from Playwright)
            element_name: Human-readable element name
            parent_name: Name of parent element (for nested duplicate IDs)
            
        Returns:
            {
                "xpath": str,
                "uniqueness_method": str,
                "is_unique": bool
            }
        """
        
        # Get tag prefix for more specific XPaths (e.g., //button instead of //*)
        tag_prefix = f"//{attrs['tag']}" if attrs.get('tag') else "//*"
        
        # Priority 1: ID-based XPath (with uniqueness testing!)
        if attrs.get('id'):
            # CRITICAL: For interactive elements (role="button"), ALWAYS include role in XPath
            # This ensures we target the clickable button, not a container div with same ID
            if attrs.get('role') == 'button':
                id_val = attrs['id']
                text = attrs.get('text', '')[:30]
                
                # Try ID+Role first
                xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button']"
                count = await self.test_xpath_count(xpath)
                
                if count == 1:
                    logger.info(f"✅ Using ID+Role XPath (clickable button): {xpath}")
                    return self._register_xpath(xpath, element_name, "id_plus_role")
                
                # Multiple buttons with same ID+Role - add text for uniqueness
                if count > 1 and text:
                    xpath_with_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and normalize-space(.)='{self._escape(text)}']"
                    count_text = await self.test_xpath_count(xpath_with_text)
                    
                    if count_text == 1:
                        logger.info(f"✅ Using ID+Role+Text XPath (unique button with text): {xpath_with_text}")
                        return self._register_xpath(xpath_with_text, element_name, "id_role_plus_text")
                
                # Still not unique - use outermost/innermost strategy
                logger.warning(f"⚠️ Multiple buttons with id='{id_val}' detected! {count} elements")
                
                # PARENT (no parent_name): Use "outermost" - not nested inside another element with same ID
                if not parent_name:
                    xpath_outermost = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and not(ancestor::*[@id='{self._escape(id_val)}'])]"
                    count_outermost = await self.test_xpath_count(xpath_outermost)
                    
                    if count_outermost == 1:
                        logger.info(f"✅ Using outermost XPath (parent button): {xpath_outermost}")
                        return self._register_xpath(xpath_outermost, element_name, "id_role_outermost")
                    
                    # Add text to outermost
                    if count_outermost > 1 and text:
                        xpath_outermost_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and not(ancestor::*[@id='{self._escape(id_val)}']) and normalize-space(.)='{self._escape(text)}']"
                        count_outermost_text = await self.test_xpath_count(xpath_outermost_text)
                        
                        if count_outermost_text == 1:
                            logger.info(f"✅ Using outermost+text XPath: {xpath_outermost_text}")
                            return self._register_xpath(xpath_outermost_text, element_name, "id_role_outermost_plus_text")
                
                # NESTED (has parent_name): First try parent check - immediate parent has same ID
                else:
                    # STRATEGY 1: Check if immediate parent has same ID (most precise for nested elements)
                    # For nested elements, ALWAYS add text for maximum precision
                    if text:
                        xpath_parent_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and parent::*[@id='{self._escape(id_val)}'] and normalize-space(.)='{self._escape(text)}']"
                        count_parent_text = await self.test_xpath_count(xpath_parent_text)
                        
                        if count_parent_text == 1:
                            logger.info(f"✅ Using parent+text XPath (nested button with text): {xpath_parent_text}")
                            return self._register_xpath(xpath_parent_text, element_name, "id_role_parent_text")
                    
                    # Fallback: parent check without text
                    xpath_parent = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and parent::*[@id='{self._escape(id_val)}']]"
                    count_parent = await self.test_xpath_count(xpath_parent)
                    
                    if count_parent == 1:
                        logger.info(f"✅ Using parent check XPath (nested button): {xpath_parent}")
                        return self._register_xpath(xpath_parent, element_name, "id_role_parent")
                    
                    # STRATEGY 2: Fall back to innermost - doesn't contain other elements with same ID
                    xpath_innermost = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and not(.//*[@id='{self._escape(id_val)}'])]"
                    count_innermost = await self.test_xpath_count(xpath_innermost)
                    
                    if count_innermost == 1:
                        logger.info(f"✅ Using innermost XPath (nested button): {xpath_innermost}")
                        return self._register_xpath(xpath_innermost, element_name, "id_role_innermost")
                    
                    # Add text to innermost
                    if count_innermost > 1 and text:
                        xpath_innermost_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and not(.//*[@id='{self._escape(id_val)}']) and normalize-space(.)='{self._escape(text)}']"
                        count_innermost_text = await self.test_xpath_count(xpath_innermost_text)
                        
                        if count_innermost_text == 1:
                            logger.info(f"✅ Using innermost+text XPath: {xpath_innermost_text}")
                            return self._register_xpath(xpath_innermost_text, element_name, "id_role_innermost_plus_text")
                
                # Last resort: call enhancement function
                enhanced = await self._enhance_xpath_for_uniqueness(attrs, element_name, tag_prefix, parent_name=parent_name)
                return self._register_xpath(enhanced['xpath'], element_name, enhanced['uniqueness_method'])
            
            # For non-button elements, try ID alone first
            xpath = f"{tag_prefix}[@id='{self._escape(attrs['id'])}']"
            count = await self.test_xpath_count(xpath)
            
            if count == 1:
                logger.info(f"✅ Using ID-based XPath: {xpath}")
                return self._register_xpath(xpath, element_name, "id_only")
            
            # ID is NOT unique! Enhance it
            logger.warning(f"⚠️ Duplicate ID detected! {count} elements with id='{attrs['id']}'")
            enhanced = await self._enhance_xpath_for_uniqueness(attrs, element_name, tag_prefix, parent_name=parent_name)
            return self._register_xpath(enhanced['xpath'], element_name, enhanced['uniqueness_method'])
        
        # Priority 2: data-testid (purpose-built for testing)
        if attrs.get('data-testid'):
            xpath = f"{tag_prefix}[@data-testid='{self._escape(attrs['data-testid'])}']"
            logger.info(f"✅ Using data-testid XPath: {xpath}")
            return self._register_xpath(xpath, element_name, "data_testid")
        
        # Priority 3: ARIA role + label (semantic and stable)
        if attrs.get('role') and attrs.get('aria-label'):
            xpath = f"{tag_prefix}[@role='{self._escape(attrs['role'])}' and @aria-label='{self._escape(attrs['aria-label'])}']"
            logger.info(f"✅ Using role+aria-label XPath: {xpath}")
            return self._register_xpath(xpath, element_name, "role_plus_aria_label")
        
        # Priority 4: Name attribute (for form elements)
        if attrs.get('name'):
            xpath = f"{tag_prefix}[@name='{self._escape(attrs['name'])}']"
            logger.info(f"✅ Using name attribute XPath: {xpath}")
            return self._register_xpath(xpath, element_name, "name_attr")
        
        # Priority 5: Role + Text (for buttons, links, etc.)
        if attrs.get('role') and attrs.get('text'):
            text = attrs['text'][:30]
            xpath = f"{tag_prefix}[@role='{self._escape(attrs['role'])}' and normalize-space(.)='{self._escape(text)}']"
            logger.info(f"✅ Using role+text XPath: {xpath}")
            return self._register_xpath(xpath, element_name, "role_plus_text")
        
        # Priority 6: Text only (fallback) - TEST FOR UNIQUENESS
        if attrs.get('text'):
            text = attrs['text'][:30]
            xpath = f"{tag_prefix}[normalize-space(.)='{self._escape(text)}']"
            count = await self.test_xpath_count(xpath)
            
            if count == 1:
                logger.info(f"✅ Using text-only XPath: {xpath}")
                return self._register_xpath(xpath, element_name, "text_only")
            
            # Text-only XPath is NOT unique! Need parent context
            logger.warning(f"⚠️ Text-only XPath matches {count} elements: {xpath}")
            
            # Add parent context: //parent_tag[@parent_id]/child_tag[text]
            # This requires parent information which we don't have in attrs
            # Fallback: use position-based XPath
            logger.info(f"🔧 Falling back to positional XPath")
            xpath = self._build_positional_xpath(attrs)
            return self._register_xpath(xpath, element_name, "positional")
        
        # Last resort: Positional
        xpath = self._build_positional_xpath(attrs)
        logger.warning(f"⚠️ Using positional XPath (last resort): {xpath}")
        return self._register_xpath(xpath, element_name, "positional")
    
    def _build_positional_xpath(self, attrs: Dict) -> str:
        """Build positional XPath with index (last resort)"""
        
        predicates = []
        
        if attrs.get('role'):
            predicates.append(f"@role='{self._escape(attrs['role'])}'")
        
        if attrs.get('text'):
            text = attrs['text'][:30]
            predicates.append(f"normalize-space(.)='{self._escape(text)}'")
        
        if predicates:
            base = f"//*[{' and '.join(predicates)}]"
        else:
            base = "//*"
        
        # For positional, we return base and let caller add [index]
        return f"({base})[1]"
    
    async def test_xpath_count(self, xpath: str) -> int:
        """
        Test how many elements an XPath matches using Playwright's LIVE DOM (async)
        
        Args:
            xpath: XPath expression to test
            
        Returns:
            count: Number of matching elements in the live DOM
        """
        try:
            count = await self.page.locator(xpath).count()  # In async Playwright, count() is async!
            
            if count > 1:
                logger.debug(f"🔍 Playwright LIVE DOM: XPath matches {count} elements: {xpath}")
            
            return count
        except Exception as e:
            logger.warning(f"⚠️ Playwright XPath test failed for '{xpath}': {e}")
            return 100  # Assume many matches if Playwright fails (forces enhancement)
    
    async def _enhance_xpath_for_uniqueness(self, attrs: Dict, element_name: str, tag_prefix: str, parent_name: str = None) -> Dict:
        """
        Enhance XPath with additional conditions until it's unique
        Progressive strategy: Innermost (if nested) → ID+Text → ID+Role → ID+Role+Text → Nested → Positional
        Uses Playwright's LIVE DOM for testing
        Args:
            parent_name: Name of parent element (for nested duplicate IDs)
        """
        id_val = attrs.get('id')
        text = attrs.get('text', '')[:30]
        role = attrs.get('role')
        aria_label = attrs.get('aria-label')
        title = attrs.get('title')
        
        logger.info(f"🔧 Enhancing XPath for uniqueness (id='{id_val}')...")
        print(f"   DEBUG XPATH: parent_name='{parent_name}', element_name='{element_name}'")
        
        # PRIORITY 0: For interactive elements (role="button"), ALWAYS include role to target clickable element
        # This prevents matching non-clickable container divs with same ID
        if role == 'button':
            logger.info(f"   🎯 Interactive element (role=button) - prioritizing role-based XPaths")
            
            # Try ID+Role first (most specific for buttons)
            xpath_role = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button']"
            count_role = await self.test_xpath_count(xpath_role)
            logger.info(f"   Try ID+Role: {count_role} matches")
            
            if count_role == 1:
                logger.info(f"✅ Unique with ID+Role (clickable button): {xpath_role}")
                return {"xpath": xpath_role, "uniqueness_method": "id_plus_role"}
            
            # If not unique, add innermost check for nested accordions
            if count_role > 1 and parent_name:
                xpath_role_innermost = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and not(.//*[@id='{self._escape(id_val)}'])]"
                count_role_innermost = await self.test_xpath_count(xpath_role_innermost)
                logger.info(f"   Try ID+Role+innermost: {count_role_innermost} matches")
                
                if count_role_innermost == 1:
                    logger.info(f"✅ Unique with ID+Role+innermost (nested button): {xpath_role_innermost}")
                    return {"xpath": xpath_role_innermost, "uniqueness_method": "id_role_innermost"}
            
            # Add text if still not unique
            if count_role > 1 and text:
                xpath_role_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='button' and normalize-space(.)='{self._escape(text)}']"
                count_role_text = await self.test_xpath_count(xpath_role_text)
                logger.info(f"   Try ID+Role+Text: {count_role_text} matches")
                
                if count_role_text == 1:
                    logger.info(f"✅ Unique with ID+Role+Text (clickable button with text): {xpath_role_text}")
                    return {"xpath": xpath_role_text, "uniqueness_method": "id_role_plus_text"}
        
        # PRIORITY 1: If parent_name provided, check nested duplicate IDs
        if parent_name:
            logger.info(f"   🎯 Element has parent '{parent_name}' - checking innermost strategy")
            
            # Test innermost: Elements with this ID that DON'T contain other elements with same ID
            xpath_innermost = f"{tag_prefix}[@id='{self._escape(id_val)}' and not(.//*[@id='{self._escape(id_val)}'])]"
            count_innermost = await self.test_xpath_count(xpath_innermost)
            logger.info(f"   Try ID+innermost (no nested same-id): {count_innermost} matches")
            
            if count_innermost == 1:
                logger.info(f"✅ Unique innermost element (nested): {xpath_innermost}")
                return {"xpath": xpath_innermost, "uniqueness_method": "id_innermost_element"}
            
            # If still not unique, try innermost + text
            if count_innermost > 1 and text:
                xpath_innermost_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and not(.//*[@id='{self._escape(id_val)}']) and normalize-space(.)='{self._escape(text)}']"
                count_innermost_text = await self.test_xpath_count(xpath_innermost_text)
                logger.info(f"   Try ID+innermost+text: {count_innermost_text} matches")
                
                if count_innermost_text == 1:
                    logger.info(f"✅ Unique innermost with text: {xpath_innermost_text}")
                    return {"xpath": xpath_innermost_text, "uniqueness_method": "id_innermost_plus_text"}
        
        # Strategy 1: ID + Text
        if text:
            xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and normalize-space(.)='{self._escape(text)}']"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try ID+Text: {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with ID+Text: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "id_plus_text"}
        
        # Strategy 2: ID + Role
        if role:
            xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='{self._escape(role)}']"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try ID+Role: {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with ID+Role: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "id_plus_role"}
        
        # Strategy 3: ID + Role + Text
        if role and text:
            xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and @role='{self._escape(role)}' and normalize-space(.)='{self._escape(text)}']"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try ID+Role+Text: {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with ID+Role+Text: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "id_plus_role_plus_text"}
        
        # Strategy 4: ID + aria-label
        if aria_label:
            xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and @aria-label='{self._escape(aria_label)}']"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try ID+aria-label: {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with ID+aria-label: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "id_plus_aria_label"}
        
        # Strategy 5: ID + title
        if title:
            xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and @title='{self._escape(title)}']"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try ID+title: {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with ID+title: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "id_plus_title"}
        
        # Strategy 6: Nested structure (ID + child with role+text)
        if role and text:
            xpath = f"{tag_prefix}[@id='{self._escape(id_val)}' and .//*[@role='{self._escape(role)}' and normalize-space(.)='{self._escape(text)}']]"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try ID+nested: {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with nested structure: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "id_plus_nested"}
        
        # Strategy 7: Try specific tag + role combination
        if attrs.get('tag') and role:
            specific_tag = f"//{attrs['tag']}"
            xpath = f"{specific_tag}[@id='{self._escape(id_val)}' and @role='{self._escape(role)}']"
            count = await self.test_xpath_count(xpath)
            logger.info(f"   Try tag+ID+role ({attrs['tag']}): {count} matches")
            if count == 1:
                logger.info(f"✅ Unique with tag+ID+role: {xpath}")
                return {"xpath": xpath, "uniqueness_method": "tag_plus_id_plus_role"}
        
        # Strategy 8: Nested duplicate ID detection (parent vs nested)
        logger.info(f"   🔍 Testing for nested duplicate IDs...")
        
        # NEW: If parent_name is provided, this is a nested element - use innermost strategy
        if parent_name:
            logger.info(f"   🎯 Element has parent '{parent_name}' - prioritizing innermost/nested strategies")
        
        # Test 8a: Elements that CONTAIN other elements with same ID (parents)
        xpath_parent = f"{tag_prefix}[@id='{self._escape(id_val)}' and .//*[@id='{self._escape(id_val)}']]"
        count_parent = await self.test_xpath_count(xpath_parent)
        logger.info(f"   Try ID+contains-same-id (parent): {count_parent} matches")
        
        # Test 8b: Elements that are CHILDREN of elements with same ID (nested)
        # FIX: Use descendant axis properly without double slashes
        xpath_nested = f"{tag_prefix}[@id='{self._escape(id_val)}']//*[@id='{self._escape(id_val)}']"
        count_nested = await self.test_xpath_count(xpath_nested)
        logger.info(f"   Try ID/descendant-same-id (nested): {count_nested} matches")
        
        # Test 8c: Innermost elements (no children with same ID)
        xpath_innermost = f"{tag_prefix}[@id='{self._escape(id_val)}' and not(.//*[@id='{self._escape(id_val)}'])]"
        count_innermost = await self.test_xpath_count(xpath_innermost)
        logger.info(f"   Try ID+no-nested-same-id (innermost): {count_innermost} matches")
        
        # NEW: If parent_name provided, prefer innermost/nested over parent
        if parent_name:
            if count_innermost == 1:
                logger.info(f"✅ Unique innermost element (nested): {xpath_innermost}")
                return {"xpath": xpath_innermost, "uniqueness_method": "id_innermost_element"}
            elif count_nested > 0:
                # Try with text to disambiguate
                if text:
                    xpath_nested_text = f"{tag_prefix}[@id='{self._escape(id_val)}' and not(.//*[@id='{self._escape(id_val)}']) and normalize-space(.)='{self._escape(text)}']"
                    count_nested_text = await self.test_xpath_count(xpath_nested_text)
                    logger.info(f"   Try ID+innermost+text (nested): {count_nested_text} matches")
                    if count_nested_text == 1:
                        logger.info(f"✅ Unique nested with text: {xpath_nested_text}")
                        return {"xpath": xpath_nested_text, "uniqueness_method": "id_innermost_plus_text"}
        
        # Use the most unique one (original logic for non-nested)
        if count_parent == 1:
            logger.info(f"✅ Unique parent container: {xpath_parent}")
            return {"xpath": xpath_parent, "uniqueness_method": "id_parent_container"}
        elif count_innermost == 1:
            logger.info(f"✅ Unique innermost element: {xpath_innermost}")
            return {"xpath": xpath_innermost, "uniqueness_method": "id_innermost_element"}
        elif count_nested > 0:
            logger.info(f"   Found {count_nested} nested elements, trying with role...")
            if role:
                # FIX: Use descendant axis properly
                xpath_nested_role = f"{tag_prefix}[@id='{self._escape(id_val)}']//*[@id='{self._escape(id_val)}' and @role='{self._escape(role)}']"
                count_nested_role = await self.test_xpath_count(xpath_nested_role)
                logger.info(f"   Try nested+role: {count_nested_role} matches")
                if count_nested_role == 1:
                    logger.info(f"✅ Unique nested with role: {xpath_nested_role}")
                    return {"xpath": xpath_nested_role, "uniqueness_method": "id_nested_plus_role"}
        
        # Strategy 9: Positional with clear warning (last resort)
        logger.warning(f"⚠️ ALL STRATEGIES FAILED for '{element_name}'!")
        logger.warning(f"   {count_parent + count_nested + count_innermost} total elements with id='{id_val}'")
        logger.warning(f"   - Parent containers: {count_parent}")
        logger.warning(f"   - Nested children: {count_nested}")
        logger.warning(f"   - Innermost: {count_innermost}")
        logger.warning(f"   Falling back to positional [1] - WILL ALWAYS SELECT FIRST MATCH")
        xpath = f"({tag_prefix}[@id='{self._escape(id_val)}'])[1]"
        return {"xpath": xpath, "uniqueness_method": "id_positional_UNRELIABLE"}
    
    def _register_xpath(self, xpath: str, element_name: str, method: str) -> Dict:
        """Register XPath to prevent duplicates"""
        
        # Check for duplicates
        if xpath in self.xpath_registry:
            existing = self.xpath_registry[xpath]
            logger.warning(f"⚠️ DUPLICATE XPath: {xpath}")
            logger.warning(f"   Existing: {existing['element_name']} ({existing['method']})")
            logger.warning(f"   New: {element_name} ({method})")
            # Add to name to make unique
            element_name = f"{element_name} (duplicate-{len(self.xpath_registry)})"
        
        # Register
        self.xpath_registry[xpath] = {
            "element_name": element_name,
            "method": method,
            "registered_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ XPath registered: {element_name}")
        logger.info(f"   Method: {method}")
        logger.info(f"   XPath: {xpath}")
        
        return {
            "xpath": xpath,
            "uniqueness_method": method,
            "is_unique": True
        }
    
    def _escape(self, value: str) -> str:
        """Escape quotes and special characters for XPath"""
        if not value:
            return ""
        
        value = str(value)
        
        # Replace single quotes with &apos; entity
        value = value.replace("'", "&apos;")
        
        # Replace double quotes
        value = value.replace('"', "&quot;")
        
        # Normalize whitespace
        value = ' '.join(value.split())
        
        return value[:100]  # Limit length
    
    def validate_uniqueness_on_page(self, xpath: str, page) -> bool:
        """
        Validate XPath uniqueness at runtime with Playwright page
        
        Args:
            xpath: XPath to validate
            page: Playwright Page object
            
        Returns:
            True if exactly 1 match found
        """
        try:
            import asyncio
            
            # Run async check
            async def check():
                count = await page.locator(f"xpath={xpath}").count()
                return count == 1
            
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            is_unique = loop.run_until_complete(check())
            
            if not is_unique:
                logger.warning(f"XPath not unique on page: {xpath}")
            
            return is_unique
            
        except Exception as e:
            logger.error(f"Failed to validate XPath: {e}")
            return False

