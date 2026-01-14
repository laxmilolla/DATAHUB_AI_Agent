"""
Browser Fill Tool - Handle browser_fill tool
Extracted from bedrock_playwright_agent.py lines 2636-2882
CRITICAL: Preserves registry checks, TOTP handling, discovery tracking
"""
import re
import logging
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page
from agent.utils.modal_utils import ModalUtils

logger = logging.getLogger(__name__)


class BrowserFillTool:
    """Handle browser_fill tool"""
    
    def __init__(self, page: Page, element_locator, action_executor, totp_handler,
                 discovery_tracker, execution_context, parsed_steps: dict, story: str):
        """
        Initialize fill tool
        Args:
            page: Playwright page object
            element_locator: ElementLocator instance
            action_executor: ActionExecutor instance
            totp_handler: TOTPHandler instance
            discovery_tracker: DiscoveryTracker instance
            execution_context: ExecutionContext instance
            parsed_steps: Parsed story steps metadata
            story: Story text
        """
        self.page = page
        self.element_locator = element_locator
        self.action_executor = action_executor
        self.totp_handler = totp_handler
        self.discovery_tracker = discovery_tracker
        self.context = execution_context
        self.parsed_steps = parsed_steps
        self.story = story
    
    def _validate_registry_selector(self, registry_element: Optional[dict], element_name: Optional[str], llm_selector: str = None) -> bool:
        """
        Generic validation: Check if registry element matches expected input type.
        Uses unique_attributes for direct type access (no string parsing needed).
        Returns False if registry element conflicts with element name expectations.
        """
        if not element_name or not registry_element:
            return True  # No validation needed if no element name or registry element
        
        element_lower = element_name.lower()
        
        # Define expected input types for common field names
        field_type_rules = {
            'username': {
                'allowed': ['email', 'text'],
                'forbidden': ['password']
            },
            'email': {
                'allowed': ['email', 'text'],
                'forbidden': ['password']
            },
            'password': {
                'allowed': ['password'],
                'forbidden': ['email', 'text']
            },
            'totp': {
                'allowed': ['text'],
                'forbidden': ['password', 'email']
            }
        }
        
        # Check if element name has validation rules
        if element_lower in field_type_rules:
            rules = field_type_rules[element_lower]
            
            # ✅ NEW: Use unique_attributes for direct type access (no parsing!)
            unique_attrs = registry_element.get('unique_attributes', {})
            registry_type = unique_attrs.get('type')
            
            # Fallback: Parse selector if unique_attributes not available (backward compatibility)
            if not registry_type:
                selector = registry_element.get('selector', '')
                selector_lower = selector.lower()
                # Extract type from selector (legacy support)
                import re
                type_match = re.search(r"type=['\"]([^'\"]+)['\"]", selector_lower)
                if type_match:
                    registry_type = type_match.group(1)
            
            # Check for forbidden types
            if registry_type:
                for forbidden_type in rules['forbidden']:
                    if registry_type == forbidden_type:
                        logger.warning(f"  ⚠️ Registry element invalid: {element_name} mapped to {forbidden_type} field - rejecting")
                        return False
                
                # If LLM selector is available, prefer it if registry doesn't match expected types
                if llm_selector and rules['allowed']:
                    llm_selector_lower = llm_selector.lower()
                    llm_has_allowed = any(f'type="{t}"' in llm_selector_lower or f"type='{t}'" in llm_selector_lower 
                                         for t in rules['allowed'])
                    registry_has_allowed = registry_type in rules['allowed']
                    
                    # If LLM has correct type but registry doesn't, prefer LLM
                    if llm_has_allowed and not registry_has_allowed:
                        logger.warning(f"  ⚠️ Registry element doesn't match expected type for {element_name} - preferring LLM selector")
                        return False
        
        return True  # Validation passed
    
    async def execute(self, selector: str, text: str) -> str:
        """
        Execute fill operation
        CRITICAL: Checks registry first, handles TOTP, tracks discovery
        """
        original_selector = selector
        logger.info(f"Fill: {selector} = {text}")
        
        # Get current step metadata
        # Try step_identifier first, then fall back to step_number as string
        step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
        step_metadata = self.parsed_steps.get(step_identifier, {})
        step_text = step_metadata.get('text', '')
        
        # 🔒 CRITICAL: Check element registry FIRST
        element_name_for_registry = None
        if step_text:
            step_lower = step_text.lower()
            
            # Extract element name from step text
            # Pattern 1: "Enter X in the Y text box" -> extract Y (field name)
            # This handles cases like "Enter Timestamp in the Submission name text box"
            pattern1 = r'(?:enter|fill|type|input)\s+[^"\']+\s+in\s+(?:the\s+)?([^"\']+?)\s+(?:text\s+box|field|input)'
            match1 = re.search(pattern1, step_lower)
            if match1:
                element_name_for_registry = match1.group(1).strip()
                element_name_for_registry = re.sub(r'\b(the|a|an|text|box|field|input)\b', '', element_name_for_registry).strip()
                # Capitalize first letter of each word for registry lookup
                element_name_for_registry = ' '.join(word.capitalize() for word in element_name_for_registry.split())
                logger.info(f"  🎯 Extracted element name using 'in the X' pattern: '{element_name_for_registry}'")
            elif 'password' in step_lower:
                element_name_for_registry = 'password'
            elif 'username' in step_lower or 'email' in step_lower:
                element_name_for_registry = 'username'
            elif 'totp' in step_lower or 'one-time' in step_lower or 'authenticator' in step_lower:
                element_name_for_registry = 'totp'
            elif 'code' in step_lower and ('one-time' in step_lower or 'totp' in step_lower):
                element_name_for_registry = 'totp'
            else:
                # Pattern 2: "Enter X as Y" or "Enter X" -> extract X or Y
                fill_pattern = r'(?:enter|fill|type|input)\s+(?:the\s+)?(?:field\s+)?(?:called\s+)?([^"\']+?)(?:\s+as|\s+with|\s+in|\s*=|\s*$)'
                match = re.search(fill_pattern, step_lower)
                if match:
                    element_name_for_registry = match.group(1).strip()
                    # Remove common words but preserve multi-word names
                    element_name_for_registry = re.sub(r'\b(as|with|field|input|the|a|an)\b', '', element_name_for_registry).strip()
                    # Capitalize first letter of each word for registry lookup
                    element_name_for_registry = ' '.join(word.capitalize() for word in element_name_for_registry.split())
            
            logger.info(f"  🔍 Extracted element name from step text: '{element_name_for_registry}'")
        
        # Get domain and page for registry check (using proper URL parsing)
        try:
            from urllib.parse import urlparse
            current_url = self.page.url
            parsed = urlparse(current_url)
            domain = parsed.netloc or parsed.path.split('/')[0] if parsed.path else None
            
            # Extract page name from path (properly handles query params, fragments)
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                page_name = path_parts[-1].replace('.html', '').replace('.php', '')
                if not page_name:
                    page_name = path_parts[0] if path_parts else 'home'
            else:
                page_name = 'home'
            
            logger.info(f"  🌐 URL parsing: domain={domain}, page_name={page_name} (from {current_url})")
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to parse URL: {e}")
            domain, page_name = None, None
        
        # Extract page hints from step text (e.g., "authenticator" page)
        page_hints = []
        if step_text:
            step_lower = step_text.lower()
            if 'authenticator' in step_lower:
                page_hints.append('authenticator')
            # Add more page hints as needed
        
        # Check if modal is open and step suggests modal context (use shared utility, cache result)
        if not hasattr(self.context, '_cached_modal_state') or self.context._cached_modal_state is None:
            is_modal_open, modal_selector = await ModalUtils.is_modal_open(self.page)
            self.context._cached_modal_state = (is_modal_open, modal_selector)
        else:
            is_modal_open, modal_selector = self.context._cached_modal_state
        step_location = step_metadata.get('location', '') if step_metadata else ''
        step_parent_hint = step_metadata.get('parent_hint', '') if step_metadata else ''
        
        # Determine if we should look in modal context (use shared utility)
        should_check_modal = ModalUtils.should_check_modal(
            is_modal_open, step_text, step_location, step_parent_hint
        )
        
        # Try registry lookup with URL-based page_name first, then page hints
        # If modal context is detected, also try modal-specific page name
        registry_selector = None
        registry_element = None
        page_names_to_try = [page_name] + page_hints if page_hints else [page_name]
        if should_check_modal:
            # Add modal-specific page name for registry lookup
            modal_page_name = f"{page_name}-modal"
            page_names_to_try.insert(0, modal_page_name)
            logger.info(f"  🔍 Modal context detected - will also check page_name='{modal_page_name}'")
        
        if element_name_for_registry:
            for try_page_name in page_names_to_try:
                if not try_page_name:
                    continue
                logger.info(f"  🔍 Trying registry lookup with page_name='{try_page_name}'")
                registry_selector = self.element_locator.check_registry(element_name_for_registry, domain, try_page_name)
                if registry_selector:
                    # Get the full element dict for validation
                    registry_element = self.element_locator.element_registry.get_element(domain, try_page_name, element_name_for_registry)
                    logger.info(f"  ✅ Found in registry with page_name='{try_page_name}'")
                    break
                registry_selector = self.element_locator.check_registry(element_name_for_registry.capitalize(), domain, try_page_name)
                if registry_selector:
                    registry_element = self.element_locator.element_registry.get_element(domain, try_page_name, element_name_for_registry.capitalize())
                    break
                registry_selector = self.element_locator.check_registry(f"{element_name_for_registry} input", domain, try_page_name)
                if registry_selector:
                    registry_element = self.element_locator.element_registry.get_element(domain, try_page_name, f"{element_name_for_registry} input")
                    break
                registry_selector = self.element_locator.check_registry(element_name_for_registry.upper(), domain, try_page_name)
                if registry_selector:
                    registry_element = self.element_locator.element_registry.get_element(domain, try_page_name, element_name_for_registry.upper())
                    break
        
        if not registry_selector:
            for try_page_name in page_names_to_try:
                if not try_page_name:
                    continue
                registry_selector = self.element_locator.check_registry(selector, domain, try_page_name)
                if registry_selector:
                    registry_element = self.element_locator.element_registry.get_element(domain, try_page_name, selector)
                    break
        
        using_registry_xpath = False
        if registry_selector:
            # ✅ NEW: Validate using unique_attributes (no string parsing!)
            selector_valid = self._validate_registry_selector(registry_element, element_name_for_registry, selector)
            
            if registry_selector and selector_valid:
                # FIX: Prefer XPath if available (especially for modal elements - XPath is already modal-scoped)
                registry_xpath = registry_element.get('xpath', '') if registry_element else ''
                
                if registry_xpath and should_check_modal:
                    # XPath in registry is already modal-scoped, use it directly
                    selector = f"xpath={registry_xpath}"
                    using_registry_xpath = True
                    logger.info(f"  📋 Using XPath from registry (already modal-scoped) for fill operation")
                elif registry_xpath and not should_check_modal:
                    # XPath exists but modal not needed - use XPath directly
                    selector = f"xpath={registry_xpath}"
                    using_registry_xpath = True
                    logger.info(f"  📋 Using XPath from registry for fill operation")
                else:
                    # No XPath, use CSS selector and scope if needed
                    selector = registry_selector
                    # If modal is open and selector doesn't already scope to modal, scope it
                    if should_check_modal and modal_selector and not selector.startswith(modal_selector):
                        # Scope selector to modal context (use shared utility)
                        selector = ModalUtils.scope_selector_to_modal(selector, modal_selector)
                    
                    logger.info(f"  📋 Using CSS selector from registry for fill operation")
            elif not selector_valid:
                logger.warning(f"  ⚠️ Registry selector validation failed - using LLM selector instead")
                registry_selector = None
        elif should_check_modal and modal_selector:
            # No registry match, but modal is open - scope the original selector to modal (use shared utility)
            if not selector.startswith(modal_selector):
                selector = ModalUtils.scope_selector_to_modal(selector, modal_selector)
        
        # TOTP Detection
        is_totp_step = self.totp_handler.is_totp_step(step_text, text)
        
        if is_totp_step:
            # COMMENTED OUT: Block static test value "123456" for TOTP
            # Prevent using static test value - must generate real TOTP code
            # if text == "123456":
            #     logger.warning(f"  [TOTP] Blocked use of static test value '123456' - TOTP must be generated")
            #     raise Exception("Static test value '123456' is disabled for TOTP. Real TOTP code must be generated.")
            
            logger.info(f"  [TOTP] TOTP detected - generating code")
            try:
                totp_code = self.totp_handler.generate_code(story=self.story, text=text)
                text = totp_code
                logger.info(f"  [TOTP] Generated TOTP code: {totp_code}")
            except Exception as e:
                logger.error(f"  [TOTP] Failed to generate TOTP code: {e}")
                # Don't raise - allow TOTP generation to fail gracefully
                # The original text will be used if generation fails
        
        # TOTP fallback selectors (only if NOT using registry XPath)
        if is_totp_step and not using_registry_xpath:
            selector_needs_fallback = (
                selector == "input[name='code']" or 
                selector == 'input[name="code"]' or
                selector == 'input[type="text"]' or
                selector == "input[type='text']"
            )
            
            if selector_needs_fallback:
                totp_selectors = [
                    "input.one-time-code-input__input",
                    "input[autocomplete='one-time-code']",
                    "input[type='text'][name='code']",
                    "input[name='code']:not([type='hidden'])",
                    "lg-one-time-code-input input[type='text']",
                    "lg-validated-field input[type='text']",
                    "lg-one-time-code-input input",
                    "input.one-time-code",
                ]
                
                selector_found = False
                for totp_selector in totp_selectors:
                    try:
                        locator = self.page.locator(totp_selector).first
                        if await locator.is_visible(timeout=2000):
                            selector = totp_selector
                            selector_found = True
                            logger.info(f"  [TOTP] Found visible input with selector: {selector}")
                            break
                    except:
                        continue
                
                if not selector_found:
                    logger.warning(f"  [TOTP] Could not find visible input with fallback selectors")
        
        # Execute fill
        try:
            timeout_ms = 60000 if is_totp_step else 10000
            await self.page.wait_for_selector(selector, state='visible', timeout=timeout_ms)
        except Exception as selector_error:
            if using_registry_xpath and selector != original_selector:
                logger.warning(f"  ⚠️ Registry selector failed: {selector_error}")
                logger.info(f"  ⚙️ Falling back to original selector: {original_selector}")
                selector = original_selector
                using_registry_xpath = False
                timeout_ms = 60000 if is_totp_step else 10000
                await self.page.wait_for_selector(selector, state='visible', timeout=timeout_ms)
            else:
                raise selector_error
        
        # Check if field is readonly
        try:
            locator = self.page.locator(selector).first
            is_readonly = await locator.evaluate("el => el.readOnly || el.disabled")
            if is_readonly:
                logger.warning(f"  ⚠️ Field {selector} is readonly or disabled")
                return f"⚠️ Fill FAILED: {selector} is readonly/disabled"
        except Exception as e:
            logger.warning(f"  ⚠️ Could not check readonly status: {e}")
        
        # Fill field
        if is_totp_step:
            try:
                await locator.fill('')
                await locator.type(text, delay=10)
                await self.page.wait_for_timeout(200)
                logger.info(f"  [TOTP] Used type() method for TOTP field")
            except Exception as e:
                logger.warning(f"  [TOTP] type() failed, using fill(): {e}")
                await locator.fill(text)
        else:
            await locator.fill(text)
        
        await self.page.wait_for_timeout(500)
        
        # Verify
        actual_value = await self.page.input_value(selector)
        
        if actual_value == text:
            logger.info(f"  ✅ Fill verified: value matches")
            
            # FIX: Always track discovery (even when using registry XPath) to ensure completeness
            try:
                # FIX: Ensure element_name is correctly extracted from step text
                element_name = element_name_for_registry
                if not element_name:
                    # Fallback: extract from selector or use selector itself
                    if selector.startswith('input['):
                        # Extract type from selector (e.g., input[type="email"] -> email)
                        type_match = re.search(r'type=["\'](\w+)["\']', selector)
                        if type_match:
                            element_name = type_match.group(1)
                    if not element_name:
                        element_name = selector
                
                # Extract element attributes to get tag/type
                element_attrs = {}
                element_type = 'input'  # Default for fill operations
                try:
                    fill_locator = self.page.locator(selector).first
                    tag_name = await fill_locator.evaluate("el => el.tagName?.toLowerCase() || ''")
                    if tag_name:
                        element_attrs['tag'] = tag_name
                        if tag_name == 'input':
                            element_type = 'input'
                        elif tag_name == 'textarea':
                            element_type = 'textarea'
                        else:
                            element_type = tag_name
                except Exception as e:
                    logger.debug(f"  ⚠️ Could not extract element attributes: {e}")
                
                await self.discovery_tracker.track(
                    element_name=element_name,
                    original_query=original_selector,
                    final_selector=selector,
                    discovery_method="direct" if not using_registry_xpath else "registry",
                    metadata={
                        "element_attrs": element_attrs,
                        "type": element_type  # Set type so registry saves correct element type
                    }
                )
                logger.info(f"  ✅ Discovery tracked: {element_name} (type: {element_type})")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to track discovery: {e}")
            
            return f"✅ Filled {selector} = '{text}' - Verified"
        else:
            logger.warning(f"  ⚠️ Fill mismatch: expected '{text}', got '{actual_value}'")
            return f"⚠️ Filled {selector} - Expected '{text}', got '{actual_value}'"

