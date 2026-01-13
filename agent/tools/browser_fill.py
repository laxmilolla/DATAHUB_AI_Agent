"""
Browser Fill Tool - Handle browser_fill tool
Extracted from bedrock_playwright_agent.py lines 2636-2882
CRITICAL: Preserves registry checks, TOTP handling, discovery tracking
"""
import re
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

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
            if 'password' in step_lower:
                element_name_for_registry = 'password'
            elif 'username' in step_lower or 'email' in step_lower:
                element_name_for_registry = 'username'
            elif 'totp' in step_lower or 'one-time' in step_lower or 'authenticator' in step_lower:
                element_name_for_registry = 'totp'
            elif 'code' in step_lower and ('one-time' in step_lower or 'totp' in step_lower):
                element_name_for_registry = 'totp'
            else:
                # Try pattern extraction
                fill_pattern = r'(?:enter|fill|type|input)\s+(?:the\s+)?(?:field\s+)?(?:called\s+)?(\w+)(?:\s+as|\s+with|\s*=|\s*$)'
                match = re.search(fill_pattern, step_lower)
                if match:
                    element_name_for_registry = match.group(1).strip()
                    element_name_for_registry = re.sub(r'\b(as|with|field|input|the|a|an)\b', '', element_name_for_registry).strip()
            
            logger.info(f"  🔍 Extracted element name from step text: '{element_name_for_registry}'")
        
        # Get domain and page for registry check  
        try:
            current_url = self.page.url
            domain = current_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
            url_path = current_url.split('/')[-1].split('#')[0]
            if url_path == 'explore':
                page_name = 'explore'
            elif not url_path or url_path == '':
                page_name = 'home'
            else:
                page_name = url_path
        except:
            domain, page_name = None, None
        
        # Try registry lookup
        registry_selector = None
        if element_name_for_registry:
            registry_selector = self.element_locator.check_registry(element_name_for_registry, domain, page_name)
            if not registry_selector:
                registry_selector = self.element_locator.check_registry(element_name_for_registry.capitalize(), domain, page_name)
            if not registry_selector:
                registry_selector = self.element_locator.check_registry(f"{element_name_for_registry} input", domain, page_name)
            if not registry_selector:
                registry_selector = self.element_locator.check_registry(element_name_for_registry.upper(), domain, page_name)
        
        if not registry_selector:
            registry_selector = self.element_locator.check_registry(selector, domain, page_name)
        
        using_registry_xpath = False
        if registry_selector:
            selector = registry_selector
            if selector.startswith("xpath="):
                using_registry_xpath = True
                logger.info(f"  📋 Using XPath from registry (MANUAL) for fill operation")
            else:
                logger.info(f"  📋 Using selector from registry")
        
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

