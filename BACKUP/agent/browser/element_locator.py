"""
Element Locator - Find elements using multiple strategies
Extracted from bedrock_playwright_agent.py lines 197-400, 476-492, 401-451
"""
import re
import logging
from typing import Optional, Tuple
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class ElementLocator:
    """Find elements using multiple strategies"""
    
    def __init__(self, page: Page, element_registry, parsed_steps: dict, current_step_number: int, context=None):
        """
        Initialize element locator
        Args:
            page: Playwright page object
            element_registry: ElementRegistry instance
            parsed_steps: Parsed story steps metadata
            current_step_number: Current step number
            context: ExecutionContext instance (optional, for step_identifier access)
        """
        self.page = page
        self.element_registry = element_registry
        self.parsed_steps = parsed_steps
        self.current_step_number = current_step_number
        self.context = context  # FIX: Store context for step_identifier access
    
    def check_registry(self, element_description: str, domain: str, page_name: str) -> Optional[str]:
        """
        Check if element exists in registry using current step metadata
        Returns: selector if found, None otherwise
        CRITICAL: This is the first check - registry XPath = source of truth
        """
        try:
            logger.info(f"  🔍 Registry check: element='{element_description}', domain={domain}, page={page_name}")
            if not domain or not page_name:
                logger.warning(f"  ⚠️ Registry check skipped: domain or page not determined")
                return None
            
            # Get current step metadata
            # Try step_identifier first, then fall back to step_number as string
            if self.context:
                step_identifier = getattr(self.context, 'current_step_identifier', None) or str(self.current_step_number)
            else:
                step_identifier = str(self.current_step_number)
            step_metadata = self.parsed_steps.get(step_identifier, {})
            logger.info(f"  📖 Step {self.current_step_number} metadata: {step_metadata}")
            
            # Check if step suggests modal context
            step_location = step_metadata.get('location', '').lower()
            step_parent_hint = step_metadata.get('parent_hint', '').lower()
            step_text_lower = step_metadata.get('text', '').lower()
            
            should_prefer_modal = (
                step_location == 'table' or
                'submission' in step_parent_hint or 'form' in step_parent_hint or
                'pop up' in step_text_lower or 'popup' in step_text_lower or
                'dialog' in step_text_lower or 'modal' in step_text_lower
            )
            
            # If modal context is suggested, try modal-specific page name first
            element = None
            if should_prefer_modal:
                modal_page_name = f"{page_name}-modal"
                element = self.element_registry.get_element(domain, modal_page_name, element_description)
                if element:
                    element_context = element.get('context', 'main-page')
                    if element_context == 'modal':
                        logger.info(f"  ✅ Found element in modal context (page_name='{modal_page_name}')")
                        selector = element.get('selector')
                        logger.info(f"  ✅ Modal context match: {element_description} -> {selector}")
                        self.element_registry.update_usage(domain, modal_page_name, element_description)
                        return selector
            
            # Try exact match first, but validate with unique_attributes and step metadata
            if not element:
                element = self.element_registry.get_element(domain, page_name, element_description)
            
            if element:
                # Check element context and prefer modal if step suggests modal
                element_context = element.get('context', 'main-page')
                if should_prefer_modal and element_context == 'main-page':
                    # Step suggests modal but element is main-page - might be wrong match
                    logger.info(f"  ⚠️ Step suggests modal but element is main-page - continuing search...")
                    # Don't return early, continue to find better match
                elif not should_prefer_modal and element_context == 'modal':
                    # Step doesn't suggest modal but element is modal - might be wrong match
                    logger.info(f"  ⚠️ Step doesn't suggest modal but element is modal - continuing search...")
                    # Don't return early, continue to find better match
                # ✅ NEW: Validate exact match using unique_attributes and step metadata
                unique_attrs = element.get('unique_attributes', {})
                elem_role = unique_attrs.get('role', '').lower()
                elem_type_from_attrs = unique_attrs.get('type', '').lower()
                elem_type = element.get('type', '').lower()
                
                # Check if step type matches element type/role
                step_type = step_metadata.get('type', '').lower()
                
                # Special handling for dropdowns: if step type is "select", prefer buttons over options
                if step_type == 'select':
                    # If exact match is an option but step wants to open dropdown, look for button instead
                    if elem_role == 'option' or elem_type == 'option':
                        logger.info(f"  ⚠️ Exact match is option, but step type is 'select' - searching for dropdown button...")
                        # Don't return early, continue to find dropdown button
                    elif elem_role == 'button' or elem_type in ['select', 'div']:
                        # This is a dropdown button - perfect match!
                        selector = element.get('selector')
                        logger.info(f"  ✅ Exact match (dropdown button): {element_description} -> {selector}")
                        self.element_registry.update_usage(domain, page_name, element_description)
                        return selector
                
                # For other types, validate match
                if step_type:
                    # Check if element type matches step type using both type field and unique_attributes
                    type_matches = (
                        elem_type == step_type or 
                        elem_type_from_attrs == step_type or
                        step_type in elem_type
                    )
                    
                    # Check role match if step type suggests a role
                    role_matches = True
                    if step_type == 'button' and elem_role and elem_role != 'button':
                        role_matches = False
                    elif step_type == 'select' and elem_role == 'option' and 'dropdown' not in element_description.lower():
                        # If step says "select" and wants to open dropdown, option is wrong
                        role_matches = False
                    
                    if not type_matches or not role_matches:
                        logger.info(f"  ⚠️ Exact match found but type/role mismatch - step_type={step_type}, elem_type={elem_type}, elem_role={elem_role}")
                        # Don't return early, continue to find better match
                    else:
                        selector = element.get('selector')
                        logger.info(f"  ✅ Exact match (validated): {element_description} -> {selector}")
                        self.element_registry.update_usage(domain, page_name, element_description)
                        return selector
                else:
                    # No step type specified, use exact match
                    selector = element.get('selector')
                    logger.info(f"  ✅ Exact match: {element_description} -> {selector}")
                    self.element_registry.update_usage(domain, page_name, element_description)
                    return selector
            
            # Load element map for metadata-based matching
            element_map = self.element_registry.load_map(domain, page_name)
            logger.info(f"  📂 Element map: {len(element_map.get('elements', {})) if element_map else 0} elements")
            if not element_map:
                return None
            
            # Extract clean text from selector
            clean_text = element_description.lower()
            if clean_text.startswith('text='):
                clean_text = clean_text[5:]
            clean_text = clean_text.strip()
            
            # Find all matching elements by name with priority ordering
            matches = []
            for name, elem in element_map.get("elements", {}).items():
                name_lower = name.lower()
                name_clean = name_lower.replace('text=', '').replace('selector=', '').strip()
                
                # PRIORITY 1: Exact match (highest priority)
                if name_clean == clean_text or name_lower == clean_text:
                    matches.insert(0, (name, elem))  # Insert at beginning for highest priority
                    logger.info(f"  ✓ Exact match (PRIORITY 1): {name}")
                    continue
                
                # PRIORITY 2: Starts with query (e.g., "Login" matches "Login button" but not "Smart Card Login")
                if name_clean.startswith(clean_text) or name_lower.startswith(clean_text):
                    matches.append((name, elem))
                    logger.info(f"  ✓ Starts with match (PRIORITY 2): {name}")
                    continue
                
                # PRIORITY 3: Word boundary match, but only if query is a complete word at start
                # This prevents "Login" from matching "Smart Card Login"
                pattern_start = r'^' + re.escape(clean_text) + r'\b'
                if re.search(pattern_start, name_lower):
                    matches.append((name, elem))
                    logger.info(f"  ✓ Word boundary start match (PRIORITY 3): {name}")
                    continue
                
                # PRIORITY 4: Word boundary anywhere, but prefer shorter matches
                # Only match if query is a complete word (not substring)
                pattern = r'\b' + re.escape(clean_text) + r'\b'
                if re.search(pattern, name_lower):
                    # Skip if name is much longer than query (likely wrong match)
                    # e.g., "Login" should not match "Smart Card Login" (3 words vs 1 word)
                    query_words = len(clean_text.split())
                    name_words = len(name_clean.split())
                    # Only allow if name has same or fewer words, or query is at start
                    if query_words >= name_words or name_clean.startswith(clean_text.split()[0]):
                        matches.append((name, elem))
                        logger.info(f"  ✓ Word boundary match (PRIORITY 4): {name}")
                    else:
                        logger.info(f"  ✗ Skipped long match: {name} (query: {query_words} words, name: {name_words} words)")
            
            if not matches:
                logger.info(f"  ⚠️ No name matches for '{clean_text}'")
                return None
            
            logger.info(f"  Found {len(matches)} name matches, filtering by step metadata...")
            
            # Filter by step metadata
            filtered = matches
            
            # Filter by TYPE if specified in metadata (using both type field and unique_attributes)
            if "type" in step_metadata:
                required_type = step_metadata["type"].lower()
                temp_filtered = []
                for name, elem in filtered:
                    elem_type = elem.get("type", "").lower()
                    unique_attrs = elem.get('unique_attributes', {})
                    elem_role = unique_attrs.get('role', '').lower()
                    elem_type_from_attrs = unique_attrs.get('type', '').lower()
                    
                    # Check type match using both type field and unique_attributes
                    type_matches = (
                        elem_type == required_type or 
                        elem_type_from_attrs == required_type or
                        required_type in elem_type or
                        required_type in name.lower()
                    )
                    
                    # Special handling for "select" type: prefer buttons over options
                    if required_type == 'select':
                        # If step wants to open dropdown (type="select"), prefer button/select elements over options
                        if elem_role == 'button' or elem_type in ['select', 'div']:
                            temp_filtered.insert(0, (name, elem))  # Prioritize buttons
                            logger.info(f"  ✓ Type match (select - dropdown button): {name}")
                        elif elem_role == 'option' or elem_type == 'option':
                            # Options are lower priority for opening dropdowns
                            temp_filtered.append((name, elem))
                            logger.info(f"  ✓ Type match (select - option, lower priority): {name}")
                        elif type_matches:
                            temp_filtered.append((name, elem))
                            logger.info(f"  ✓ Type match ({required_type}): {name}")
                    elif type_matches:
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Type match ({required_type}): {name}")
                    
                    # Also check role match for button/select types
                    if required_type == 'button' and elem_role == 'button':
                        # Prioritize elements with button role
                        if (name, elem) not in temp_filtered:
                            temp_filtered.insert(0, (name, elem))
                            logger.info(f"  ✓ Role match (button role): {name}")
                
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} by type={required_type}")
            
            # Filter by LOCATION if specified in metadata
            if "location" in step_metadata:
                required_location = step_metadata["location"]
                temp_filtered = []
                for name, elem in filtered:
                    elem_location = elem.get("location", "").lower()
                    if elem_location == required_location:
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Location match ({required_location}): {name}")
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} by location={required_location}")
            
            # Filter by NESTED/PARENT if specified in metadata
            if "nested" in step_metadata and step_metadata["nested"]:
                temp_filtered = []
                for name, elem in filtered:
                    parent_name = elem.get("parent_name")
                    if parent_name and parent_name != "None":
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Nested match (has parent): {name}")
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} - nested elements only")
            else:
                # NOT nested - prefer elements WITHOUT parent
                temp_filtered = []
                for name, elem in filtered:
                    parent_name = elem.get("parent_name")
                    if not parent_name or parent_name == "None":
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Parent match (no parent): {name}")
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} - top-level elements only")
            
            # Filter by PARENT HINT if specified
            if "parent_hint" in step_metadata:
                parent_hint = step_metadata["parent_hint"]
                temp_filtered = []
                for name, elem in filtered:
                    parent_text = elem.get("parent_text", "").lower()
                    parent_id = elem.get("parent_id", "").lower()
                    if parent_hint in parent_text or parent_hint in parent_id:
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Parent hint match ('{parent_hint}'): {name}")
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} by parent_hint='{parent_hint}'")
            
            # Filter by DEPTH preference if specified
            if "prefer_depth" in step_metadata:
                prefer_depth = step_metadata["prefer_depth"]
                temp_filtered = []
                for name, elem in filtered:
                    elem_depth = elem.get("depth", 0)
                    if elem_depth == prefer_depth:
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Depth match (depth={prefer_depth}): {name}")
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} by depth={prefer_depth}")
                else:
                    # If no exact match, prefer closest depth
                    filtered.sort(key=lambda x: abs(x[1].get("depth", 0) - prefer_depth))
                    logger.info(f"  📊 Sorted by depth proximity to {prefer_depth}")
            
            # Filter by SEMANTIC TYPE if available
            if "semantic_type" in step_metadata:
                required_semantic = step_metadata["semantic_type"]
                temp_filtered = []
                for name, elem in filtered:
                    elem_semantic = elem.get("semantic_type", "").lower()
                    if required_semantic in elem_semantic:
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Semantic type match ({required_semantic}): {name}")
                if temp_filtered:
                    filtered = temp_filtered
                    logger.info(f"  Filtered to {len(filtered)} by semantic_type='{required_semantic}'")
            
            # If we have filtered results, pick the best match
            if filtered:
                # Sort by name similarity
                def extract_element_name(desc):
                    """Extract just the element name from full description"""
                    parts = desc.lower().split()
                    for word in ['accordion', 'tab', 'button', 'checkbox', 'nested', 'in', 'left', 'sidebar', 'filter', 'panel']:
                        if word in parts:
                            parts.remove(word)
                    return ' '.join(parts[:2])
                
                def match_score(item):
                    name, elem = item
                    elem_name = extract_element_name(name)
                    elem_depth = elem.get("depth", 0)
                    unique_attrs = elem.get('unique_attributes', {})
                    elem_role = unique_attrs.get('role', '').lower()
                    elem_type = elem.get("type", "").lower()
                    step_type = step_metadata.get('type', '').lower()
                    
                    # Base score from name similarity
                    if elem_name == clean_text:
                        name_score = 0
                    elif clean_text in elem_name or elem_name in clean_text:
                        name_score = 1
                    else:
                        name_score = 2
                    
                    # Bonus/penalty based on unique_attributes and step type
                    role_bonus = 0
                    if step_type == 'select':
                        # For select steps, prefer buttons over options
                        if elem_role == 'button' or elem_type in ['select', 'div']:
                            role_bonus = -1  # Lower score = higher priority
                        elif elem_role == 'option' or elem_type == 'option':
                            role_bonus = 1  # Higher score = lower priority
                    elif step_type == 'button':
                        # For button steps, prefer elements with button role
                        if elem_role == 'button':
                            role_bonus = -1
                    
                    return (name_score + role_bonus, elem_depth, len(name))
                
                filtered = sorted(filtered, key=match_score)
                name, elem = filtered[0]
                
                # CRITICAL: If step is nested AND element has parent → use XPath
                if step_metadata.get("nested") and elem.get("parent_id"):
                    xpath = elem.get('xpath')
                    if xpath:
                        selector = f"xpath={xpath}"
                        logger.info(f"  ✅ Matched (NESTED - using XPath): '{element_description}' -> '{name}'")
                        logger.info(f"      XPath: {xpath}")
                    else:
                        selector = elem.get('selector')
                        logger.warning(f"  ⚠️ Nested element but no XPath available, using selector: {selector}")
                else:
                    selector = elem.get('selector')
                    logger.info(f"  ✅ Matched: '{element_description}' -> '{name}' -> {selector}")
                
                self.element_registry.update_usage(domain, page_name, name)
                return selector
            
            return None
        except Exception as e:
            logger.warning(f"  📋 Registry lookup skipped ({str(e)[:50]}), LLM will discover")
            return None
    
    def normalize_selector(self, selector: str) -> Tuple[str, Optional[str], str]:
        """
        Normalize selector to handle dynamic content
        Returns: (normalized_selector, semantic_type, text_content)
        """
        # Extract semantic type
        semantic_type = None
        type_match = re.search(r'(\[role=["\']([^"\']+)["\']\]|^(button|input|a|div|span|tab))', selector)
        if type_match:
            if type_match.group(2):
                semantic_type = type_match.group(2)
            elif type_match.group(3):
                semantic_type = type_match.group(3)
        
        # Extract text content
        text_content = selector
        
        # From :has-text()
        has_text_match = re.search(r':has-text\(["\']([^"\']+)["\']\)', selector)
        if has_text_match:
            text_content = has_text_match.group(1)
        # From text=
        elif selector.startswith('text='):
            text_content = selector[5:]
        
        # Remove dynamic counts
        normalized_text = re.sub(r'\(\d+\)', '', text_content).strip()
        
        # Build normalized selector
        if re.search(r'\(\d+\)', text_content):
            if semantic_type:
                if semantic_type in ['tab', 'button', 'link']:
                    if '[role=' in selector:
                        normalized_selector = f'[role="{semantic_type}"]:has-text(/{normalized_text}\\(\\d+\\)/)'
                    else:
                        normalized_selector = f'{semantic_type}:has-text(/{normalized_text}\\(\\d+\\)/)'
                else:
                    normalized_selector = f'[role="{semantic_type}"]:has-text(/{normalized_text}\\(\\d+\\)/)'
            else:
                normalized_selector = f':has-text(/{normalized_text}\\(\\d+\\)/)'
        else:
            normalized_selector = selector
        
        return normalized_selector, semantic_type, normalized_text
    
    async def find_parent_or_sibling(self, selector: str) -> Optional[Locator]:
        """
        Helper to click parent or sibling of target element
        Returns: Parent locator if found, None otherwise
        """
        try:
            locator = self.page.locator(selector).nth(0)
            if await locator.count() == 0:
                return None
            
            # Try to get parent element
            parent_locator = locator.locator('..')
            if await parent_locator.count() > 0:
                return parent_locator
            else:
                # Fallback to element itself
                return locator
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to find parent/sibling: {e}")
            return None


