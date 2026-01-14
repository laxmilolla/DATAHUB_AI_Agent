"""
Browser Click Tool - Handle browser_click tool
Extracted from bedrock_playwright_agent.py lines 1271-2635
CRITICAL: Preserves registry checks, tree climbing, discovery tracking, XPath preservation
"""
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class BrowserClickTool:
    """Handle browser_click tool"""
    
    def __init__(self, page: Page, element_locator, action_executor, discovery_tracker,
                 registry_manager, xpath_generator, llm_helper, totp_handler,
                 screenshot_manager, execution_context, parsed_steps: dict, story: str):
        """Initialize click tool"""
        self.page = page
        self.element_locator = element_locator
        self.action_executor = action_executor
        self.discovery_tracker = discovery_tracker
        self.registry_manager = registry_manager
        self.xpath_generator = xpath_generator
        self.llm_helper = llm_helper
        self.totp_handler = totp_handler
        self.screenshot_manager = screenshot_manager
        self.context = execution_context
        self.parsed_steps = parsed_steps
        self.story = story
    
    async def execute(self, selector: str, element_description: str = None) -> str:
        """Execute click operation"""
        original_selector = selector
        element_name = element_description or selector.replace("text=", "").replace("_", " ")
        logger.info(f"Click: {selector}")
        
        # Get step metadata
        # Try step_identifier first, then fall back to step_number as string
        step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
        step_metadata = self.parsed_steps.get(step_identifier, {})
        step_text = step_metadata.get('text', '')
        step_type = step_metadata.get('type', '')
        
        # DEBUG: Log step context at start of execution
        logger.info(f"  📍 browser_click.execute() - step_identifier={step_identifier}, step_text='{step_text[:50]}...', step_type={step_type}")
        
        # Initialize variables
        chosen_locator = None
        original_element_for_xpath = None
        using_registry_xpath = False
        registry_button_element = None
        
        # Check if this is a dropdown option click - if so, search within open menu portal
        is_dropdown_option = await self._is_dropdown_option_click(selector, element_description, step_text)
        logger.info(f"  🔍 Dropdown option check: is_dropdown_option={is_dropdown_option}, open_menu={self.context.open_dropdown_menu}")
        
        if is_dropdown_option and self.context.open_dropdown_menu:
            # Search within the open menu portal
            logger.info(f"  🔍 Searching for dropdown option '{element_description or selector}' within open menu portal")
            menu_selector = self.context.open_dropdown_menu
            
            # ✅ NEW: Try to use unique_attributes from registry to narrow search
            registry_element = None
            if element_description:
                try:
                    domain, page_name = await self.element_locator.playwright_manager.get_domain_and_page()
                    if domain and page_name:
                        registry_element = self.element_locator.element_registry.get_element(domain, page_name, element_description)
                        if registry_element:
                            unique_attrs = registry_element.get('unique_attributes', {})
                            parent_dropdown_id = unique_attrs.get('parent_dropdown_id')
                            if parent_dropdown_id:
                                # Use parent dropdown ID to narrow search
                                logger.info(f"  🎯 Using unique_attributes['parent_dropdown_id']: {parent_dropdown_id}")
                                # Enhance menu selector with parent dropdown ID
                                enhanced_menu_selector = f'{menu_selector}[aria-labelledby="{parent_dropdown_id}"]'
                                option_locator = await self._find_option_in_menu(enhanced_menu_selector, element_description or selector)
                                if option_locator:
                                    chosen_locator = option_locator
                                    original_element_for_xpath = option_locator
                                    using_registry_xpath = False
                                    self.context.open_dropdown_menu = None
                                    logger.info(f"  ✅ Found option using unique_attributes['parent_dropdown_id']")
                except Exception as e:
                    logger.debug(f"  ⚠️ Could not use unique_attributes for dropdown option: {e}")
            
            # Fallback to normal menu search if unique_attributes didn't help
            if not chosen_locator:
                option_locator = await self._find_option_in_menu(menu_selector, element_description or selector)
                if option_locator:
                    chosen_locator = option_locator
                    original_element_for_xpath = option_locator
                    using_registry_xpath = False
                    # Clear the open menu after selecting option
                    self.context.open_dropdown_menu = None
                else:
                    logger.warning(f"  ⚠️ Option not found in menu portal, falling back to normal search")
                    # Fall through to normal search
                    selector, using_registry_xpath, registry_button_element = await self._resolve_selector(
                        selector, element_description or selector
                    )
                    chosen_locator, original_element_for_xpath = await self._find_and_choose_element(
                        selector, original_selector, using_registry_xpath
                    )
        else:
            # Normal flow: Check registry and resolve selector
            selector, using_registry_xpath, registry_button_element = await self._resolve_selector(
                selector, element_description or selector
            )
            
            # Find and choose element
            chosen_locator, original_element_for_xpath = await self._find_and_choose_element(
                selector, original_selector, using_registry_xpath
            )
        
        if not chosen_locator:
            return f"❌ Click FAILED: {selector} - Element not found"
        
        # Validate element
        validation_result = await self._validate_element(chosen_locator, selector, element_name)
        if not validation_result["exists"]:
            return f"❌ Click FAILED: {selector} - Element not found"
        
        # FIX #2: Close any open menus before opening a new dropdown
        if self.context.open_dropdown_menu:
            logger.info(f"  🔄 Closing previously open menu before opening new dropdown...")
            await self._close_open_menu(self.context.open_dropdown_menu)
            self.context.open_dropdown_menu = None
        
        # IMPROVEMENT #1: Pre-click dropdown detection
        is_dropdown_button = await self._is_dropdown_button_pre_click(chosen_locator, element_name)
        
        # Check accordion state
        accordion_result = await self._check_accordion(chosen_locator, element_name)
        if accordion_result:
            return accordion_result
        
        # Handle TOTP submission if needed
        await self._handle_totp_submission(step_text, selector)
        
        # Execute click and track discovery
        result = await self._execute_click_with_discovery(
            chosen_locator, selector, original_selector, element_name,
            original_element_for_xpath, registry_button_element,
            using_registry_xpath, validation_result,
            is_dropdown_button_pre_detected=is_dropdown_button  # Pass pre-detection result
        )
        
        return result
    
    async def _resolve_selector(self, selector: str, element_description: str) -> Tuple[str, bool, Optional[Locator]]:
        """Check registry and resolve selector"""
        domain, page_name = self._get_domain_and_page()
        
        # Extract page hints from step text (e.g., "authenticator" page)
        step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
        step_metadata = self.parsed_steps.get(step_identifier, {})
        step_text = step_metadata.get('text', '').lower() if step_metadata else ''
        
        page_hints = []
        if 'authenticator' in step_text:
            page_hints.append('authenticator')
        
        # Try registry lookup with URL-based page_name first, then page hints
        page_names_to_try = [page_name] + page_hints if page_hints else [page_name]
        registry_selector = None
        
        # FIX #4: Check if we're looking for a dropdown button (not an option)
        step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
        step_metadata = self.parsed_steps.get(step_identifier, {})
        step_type = step_metadata.get('type', '')
        step_text = step_metadata.get('text', '').lower() if step_metadata else ''
        
        is_looking_for_dropdown_button = (
            step_type == 'select' and 
            ('dropdown' in step_text or 'open' in step_text or 'click' in step_text) and
            'pick' not in step_text and 'select' not in step_text and 'choose' not in step_text
        )
        
        for try_page_name in page_names_to_try:
            if not try_page_name:
                continue
            logger.info(f"  🔍 Trying registry lookup with page_name='{try_page_name}'")
            registry_selector = self.element_locator.check_registry(element_description, domain, try_page_name)
            if registry_selector:
                # FIX #4: If looking for dropdown button, filter out option selectors
                if is_looking_for_dropdown_button and '[role="option"]' in registry_selector:
                    logger.warning(f"  ⚠️ Registry returned option selector for dropdown button - skipping: {registry_selector}")
                    # Try to find button selector instead
                    # Look for element with same name but button role
                    button_selector = registry_selector.replace('[role="option"]', '[role="button"]')
                    button_selector = button_selector.replace('[role="listbox"] [role="option"]', '[role="button"]')
                    # Try the modified selector
                    try:
                        button_matches = await self.page.locator(button_selector).all()
                        if button_matches and await button_matches[0].is_visible():
                            registry_selector = button_selector
                            logger.info(f"  ✅ Found button selector instead: {registry_selector}")
                        else:
                            # Fallback: Try to find by ID or other attributes
                            logger.warning(f"  ⚠️ Could not find button selector, will use discovery")
                            registry_selector = None
                    except Exception as e:
                        logger.debug(f"  ⚠️ Could not check button selector: {e}")
                        registry_selector = None
                
                if registry_selector:
                    logger.info(f"  ✅ Found in registry with page_name='{try_page_name}'")
                    break
        
        using_registry_xpath = False
        registry_button_element = None
        
        if registry_selector:
            selector = registry_selector
            if selector.startswith("xpath="):
                using_registry_xpath = True
                logger.info(f"  📋 Using XPath from registry (MANUAL)")
            else:
                logger.info(f"  📋 Using selector from registry")
                try:
                    registry_matches = await self.page.locator(registry_selector).all()
                    if registry_matches:
                        registry_button_element = registry_matches[0]
                        logger.info(f"  🔍 Found registry button element: {registry_selector}")
                except Exception as e:
                    logger.debug(f"  ⚠️ Could not locate registry button element: {e}")
        
        return selector, using_registry_xpath, registry_button_element
    
    def _get_domain_and_page(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract domain and page name from current URL (using proper URL parsing)"""
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
            return domain, page_name
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to parse URL: {e}")
            return None, None
    
    async def _find_and_choose_element(self, selector: str, original_selector: str, 
                                       using_registry_xpath: bool) -> Tuple[Optional[Locator], Optional[Locator]]:
        """Find elements and choose the best one"""
        try:
            all_matches = await self.page.locator(selector).all()
            
            # Verify XPath if using registry XPath
            if selector.startswith("xpath=") and len(all_matches) == 0:
                logger.warning(f"  ⚠️ XPath returned 0 matches, falling back")
                selector = original_selector
                using_registry_xpath = False
                all_matches = await self.page.locator(selector).all()
        except Exception as e:
            logger.warning(f"  ⚠️ Selector failed: {e}, falling back")
            selector = original_selector
            using_registry_xpath = False
            all_matches = await self.page.locator(selector).all()
        
        # CRITICAL FIX: Filter text= selectors for exact text matches
        # Prevents "text=Login" from matching "Smart Card Login"
        if selector.startswith("text=") and not using_registry_xpath:
            query_text = selector[5:].strip()  # Extract text after "text="
            logger.info(f"  🔍 Filtering text= selector for exact match: '{query_text}'")
            
            exact_matches = []
            for match in all_matches:
                try:
                    # Get normalized text content (trim whitespace)
                    element_text = await match.evaluate("el => el.textContent?.trim() || ''")
                    
                    # Check for exact match (case-insensitive)
                    if element_text.lower() == query_text.lower():
                        exact_matches.append(match)
                        logger.info(f"  ✅ Exact text match: '{element_text}'")
                    else:
                        logger.debug(f"  ✗ Skipped (not exact): '{element_text}' vs '{query_text}'")
                except Exception as e:
                    logger.debug(f"  ⚠️ Could not check text for element: {e}")
                    # If we can't check text, include it (fallback)
                    exact_matches.append(match)
            
            # If we found exact matches, use them; otherwise use all matches
            if exact_matches:
                logger.info(f"  ✅ Found {len(exact_matches)} exact text matches (filtered from {len(all_matches)})")
                all_matches = exact_matches
            else:
                logger.warning(f"  ⚠️ No exact text matches found, using all {len(all_matches)} matches")
        
        # Filter to visible elements
        visible_matches = [m for m in all_matches if await m.is_visible()]
        
        if not visible_matches:
            return None, None
        
        # Use registry XPath directly if available
        if using_registry_xpath and len(visible_matches) == 1:
            logger.info(f"  🔒 Using registry XPath directly")
            return visible_matches[0], visible_matches[0]
        
        # Handle multiple matches with LLM disambiguation
        if len(visible_matches) > 1:
            return await self._handle_multiple_matches(visible_matches, selector, using_registry_xpath)
        
        # Single match - check interactivity
        return await self._handle_single_match(visible_matches[0], using_registry_xpath)
    
    async def _handle_multiple_matches(self, visible_matches: List[Locator], selector: str,
                                       using_registry_xpath: bool) -> Tuple[Locator, Optional[Locator]]:
        """Handle multiple visible matches with LLM disambiguation"""
        logger.info(f"  🔍 Found {len(visible_matches)} visible matches, asking LLM to choose...")
        
        candidates = []
        actual_button_element = None
        
        # CRITICAL: Search for button element BEFORE click (page might navigate after click)
        # This ensures we have the button element reference for XPath generation
        if 'login' in selector.lower() or 'login' in str(selector).lower():
            try:
                button_locator = self.page.locator('#header-navbar-login-button, button:has-text("Login"), [id*="login"][role="button"]').first
                button_count = await button_locator.count()
                if button_count > 0:
                    actual_button_element = await button_locator.element_handle()
                    logger.info(f"  ✅ Found Login button element BEFORE click for XPath generation")
            except Exception as e:
                logger.debug(f"  ⚠️ Could not find Login button before click: {e}")
        
        # CRITICAL FIX: Prioritize <a> links over other elements when multiple matches
        # This ensures "Login" link is preferred over "Smart Card Login" heading
        link_matches = []
        other_matches = []
        
        for match in visible_matches:
            element_props = await self._get_element_props(match)
            tag_name = element_props['tagName']
            
            if tag_name == 'a':
                link_matches.append(match)
            else:
                other_matches.append(match)
        
        # If we have link matches, prioritize them
        if link_matches:
            logger.info(f"  ✅ Found {len(link_matches)} link(s) - prioritizing over {len(other_matches)} other element(s)")
            # Reorder: links first, then others
            visible_matches = link_matches + other_matches
        
        for i, match in enumerate(visible_matches):
            description = await self.llm_helper.describe_element(match)
            element_props = await self._get_element_props(match)
            
            is_interactive = self._is_interactive(element_props)
            is_link = element_props['tagName'] == 'a'
            is_button = element_props['tagName'] == 'button' or (element_props.get('id') and 'login' in element_props['id'].lower())
            
            if is_button and not actual_button_element:
                actual_button_element = match
                logger.info(f"  🔍 Found button element in matches: tag={element_props['tagName']}, id={element_props['id']}")
            
            candidates.append({
                "index": len(candidates),
                "element": match,
                "description": description,
                "is_original": True,
                "is_link": is_link,  # Add is_link flag for prioritization
                "is_button": is_button
            })
            
            # Tree climbing for non-interactive elements (but NOT for links/buttons)
            # CRITICAL FIX: Don't climb for links - they're always interactive
            if not is_interactive and not using_registry_xpath and not is_link:
                logger.info(f"  🔍 Candidate {i}: Not interactive, climbing tree...")
                parent = await self._try_tree_climbing(match)
                if parent:
                    parent_desc = await self.llm_helper.describe_element(parent)
                    candidates.append({
                        "index": len(candidates),
                        "element": parent,
                        "description": parent_desc + "\n(PARENT found via tree climbing)",
                        "is_original": False,
                        "original_element": match
                    })
        
        # LLM chooses best element
        if len(candidates) > 1:
            best_index = await self.llm_helper.choose_element(candidates, selector)
            chosen_locator = candidates[best_index]["element"]
            
            # Determine element for XPath generation - prioritize original element, not parent
            # CRITICAL FIX: Always use original element for XPath, not parent (parent is only for clicking)
            if candidates[best_index].get("is_original", True):
                # LLM chose original element - use it
                original_element_for_xpath = chosen_locator
            else:
                # LLM chose parent - use original element for XPath (parent is only for clicking)
                original_element_for_xpath = candidates[best_index].get("original_element", visible_matches[0])
                logger.info(f"  🔍 LLM chose parent for clicking, but using original element for XPath generation")
        else:
            chosen_locator = candidates[0]["element"]
            original_element_for_xpath = actual_button_element if actual_button_element else candidates[0]["element"]
        
        return chosen_locator, original_element_for_xpath
    
    async def _handle_single_match(self, match: Locator, using_registry_xpath: bool) -> Tuple[Locator, Locator]:
        """Handle single visible match"""
        if using_registry_xpath:
            return match, match
        
        element_props = await self._get_element_props(match)
        is_interactive = self._is_interactive(element_props)
        tag_name = element_props['tagName']
        
        # CRITICAL FIX: Don't replace <a> links with button parents
        # Links are always interactive and should never trigger tree climbing
        if tag_name == 'a':
            logger.info(f"  ✅ Link element detected - keeping original (no tree climbing)")
            return match, match
        
        # For other elements, check if interactive
        if not is_interactive:
            logger.info(f"  🔍 Element not interactive, climbing tree...")
            parent = await self._try_tree_climbing(match)
            if parent:
                # CRITICAL FIX: Always use original element for XPath, not parent
                # Parent is only for clicking, XPath should reflect what was actually targeted
                return parent, match
            else:
                return match, match
        else:
            return match, match
    
    async def _get_element_props(self, element: Locator) -> Dict[str, Any]:
        """Get element properties"""
        return await element.evaluate("""el => ({
            tagName: el.tagName.toLowerCase(),
            id: el.id,
            role: el.getAttribute('role'),
            ariaExpanded: el.getAttribute('aria-expanded'),
            ariaSelected: el.getAttribute('aria-selected'),
            hasClickHandler: typeof el.onclick === 'function' || el.hasAttribute('onclick'),
            className: el.className
        })""")
    
    def _is_interactive(self, props: Dict[str, Any]) -> bool:
        """Check if element is interactive"""
        return (
            props['tagName'] in ['button', 'a', 'input', 'select'] or
            props['role'] in ['button', 'tab', 'link', 'checkbox', 'radio'] or
            props['ariaExpanded'] is not None or
            props['ariaSelected'] is not None or
            props['hasClickHandler']
        )
    
    async def _is_button_element(self, element: Locator) -> bool:
        """Check if element is a button"""
        props = await element.evaluate("""el => ({
            tagName: el.tagName.toLowerCase(),
            id: el.id
        })""")
        return props['tagName'] == 'button' or (props.get('id') and 'login' in props['id'].lower())
    
    async def _validate_element(self, locator: Locator, selector: str, element_name: str) -> Dict[str, Any]:
        """Validate element exists and is visible"""
        if locator:
            return {
                "exists": True,
                "visible": await locator.is_visible(),
                "enabled": await locator.is_enabled(),
                "text_content": await locator.text_content() or "",
                "locator": locator,
                "selector": selector
            }
        else:
            validation_result = await self.action_executor.validate_visibility(selector, element_name)
            if not validation_result.get("locator"):
                validation_result["locator"] = self.page.locator(selector).nth(0)
            return validation_result
    
    async def _check_accordion(self, locator: Locator, element_name: str) -> Optional[str]:
        """Check if element is an accordion and handle accordingly"""
        try:
            aria_expanded = await locator.get_attribute("aria-expanded")
            if aria_expanded is not None:
                if aria_expanded == 'true':
                    logger.info(f"  ✅ Accordion already expanded - skipping click")
                    return f"✅ Accordion already open: {element_name}"
        except:
            pass
        return None
    
    async def _handle_totp_submission(self, step_text: str, selector: str) -> None:
        """Handle TOTP submission if detected"""
        if not step_text:
            return
        
        totp_keywords = ["submit", "click submit", "press submit", "continue", "verify"]
        submit_has_totp = any(kw in step_text.lower() for kw in totp_keywords)
        selector_is_submit = "submit" in selector.lower()
        
        try:
            has_totp_field = await self.page.evaluate("""() => {
                const selectors = ['input[name="code"]', 'input[type="text"][name*="code"]'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetWidth > 0 && el.offsetHeight > 0 && el.type !== 'hidden') {
                        return true;
                    }
                }
                return false;
            }""")
            
            if (submit_has_totp or selector_is_submit) and has_totp_field:
                logger.info(f"  [TOTP_SUBMIT] Detected TOTP submission - regenerating fresh TOTP code")
                try:
                    totp_code = self.totp_handler.generate_code(story=self.story)
                    logger.info(f"  [TOTP_SUBMIT] Generated fresh TOTP code: {totp_code}")
                    
                    totp_selectors = ["input[name='code']", "input[type='text'][name*='code']", "input.one-time-code"]
                    for totp_selector in totp_selectors:
                        try:
                            totp_field = self.page.locator(totp_selector).first
                            if await totp_field.count() > 0 and await totp_field.is_visible():
                                await totp_field.fill('')
                                await totp_field.type(totp_code, delay=10)
                                await self.page.wait_for_timeout(200)
                                logger.info(f"  [TOTP_SUBMIT] ✅ Updated TOTP field")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.error(f"  [TOTP_SUBMIT] Failed to regenerate TOTP: {e}")
        except:
            pass
    
    async def _execute_click_with_discovery(self, chosen_locator: Locator, selector: str,
                                           original_selector: str, element_name: str,
                                           original_element_for_xpath: Optional[Locator],
                                           registry_button_element: Optional[Locator],
                                           using_registry_xpath: bool,
                                           validation_result: Dict[str, Any],
                                           is_dropdown_button_pre_detected: bool = False) -> str:
        """Execute click and track discovery"""
        initial_html = await self.page.content()
        initial_url = self.page.url
        
        # CRITICAL FIX: Extract element attributes BEFORE click/navigation
        # After navigation, element handles become invalid and we'll find wrong elements
        element_attrs_before_click = {}
        if not using_registry_xpath:
            try:
                # Use the element that should be used for XPath generation
                element_for_xpath = original_element_for_xpath if original_element_for_xpath else chosen_locator
                element_attrs_before_click = await self.xpath_generator.extract_element_attributes(element_for_xpath)
                logger.info(f"  📝 Extracted element attributes BEFORE click (tag: {element_attrs_before_click.get('tag', 'N/A')})")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not extract attributes before click: {e}")
        
        # CRITICAL: Ensure element is ready before clicking
        try:
            # Check if element exists and is visible
            count = await chosen_locator.count()
            if count == 0:
                raise Exception(f"Element not found: {selector}")
            
            is_visible = await chosen_locator.is_visible()
            if not is_visible:
                logger.warning(f"  ⚠️ Element not visible, attempting scroll into view...")
                try:
                    await chosen_locator.scroll_into_view_if_needed(timeout=5000)
                    await self.page.wait_for_timeout(500)  # Wait for scroll to complete
                    is_visible = await chosen_locator.is_visible()
                    if not is_visible:
                        logger.warning(f"  ⚠️ Element still not visible after scroll, will try force click")
                except Exception as scroll_error:
                    logger.warning(f"  ⚠️ Scroll failed: {scroll_error}, will try force click")
            
            # Check if element is enabled
            is_enabled = await chosen_locator.is_enabled()
            if not is_enabled:
                logger.warning(f"  ⚠️ Element is disabled, will try force click")
            
            # Check if element is in viewport
            try:
                box = await chosen_locator.bounding_box()
                if box:
                    viewport = self.page.viewport_size
                    in_viewport = (0 <= box['x'] < viewport['width'] and 
                                 0 <= box['y'] < viewport['height'])
                    if not in_viewport:
                        logger.warning(f"  ⚠️ Element not in viewport (x={box['x']:.0f}, y={box['y']:.0f}), will scroll")
                        await chosen_locator.scroll_into_view_if_needed(timeout=5000)
            except Exception as e:
                logger.debug(f"  ⚠️ Could not check viewport: {e}")
            
            # Wait for element to be stable (not animating) - shorter timeout
            try:
                await chosen_locator.wait_for(state='visible', timeout=3000)
            except Exception as e:
                logger.debug(f"  ⚠️ Element stability check timeout (continuing): {e}")
            
            logger.info(f"  ✅ Element ready: visible={is_visible}, enabled={is_enabled}, count={count}")
        except Exception as e:
            logger.warning(f"  ⚠️ Pre-click validation failed: {e}, will try force click")
            # Continue anyway - might work with force click
        
        strategies = [
            {"desc": "direct click", "method": lambda: self.action_executor.click(chosen_locator)},
            {"desc": "force click", "method": lambda: self.action_executor.click(chosen_locator, force=True)},
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"  Trying strategy {i+1}: {strategy['desc']}")
                discovery_url_before_click = self.page.url
                
                await strategy["method"]()
                
                # IMPROVEMENT #1 & #2: Check if this was a dropdown click - use pre-detection OR post-click detection
                # Initialize dropdown detection variable
                is_dropdown_button = False
                
                # Only check if we don't already have an open menu (to avoid overwriting)
                if not self.context.open_dropdown_menu:
                    # Use pre-detection result if available, otherwise fall back to post-click detection
                    if is_dropdown_button_pre_detected:
                        is_dropdown_button = True
                        logger.info(f"  ✅ Dropdown detected BEFORE click (pre-detection)")
                    else:
                        # Fallback: Post-click detection (original logic)
                        selector_lower = (selector or '').lower()
                        element_desc_lower = (element_name or '').lower()
                        
                        dropdown_button_names = ['datacommons', 'study', 'dropdown']
                        is_known_dropdown_button = any(name in selector_lower or name in element_desc_lower 
                                                       for name in dropdown_button_names)
                        
                        is_dropdown_by_attributes = False
                        try:
                            element_role = await chosen_locator.get_attribute('role')
                            element_aria_expanded = await chosen_locator.get_attribute('aria-expanded')
                            element_class = await chosen_locator.get_attribute('class') or ''
                            is_dropdown_by_attributes = (
                                (element_role == 'button' and element_aria_expanded is not None) or
                                'MuiSelect' in element_class or
                                'select' in element_class.lower()
                            )
                        except Exception as e:
                            logger.debug(f"  ⚠️ Could not check element attributes for dropdown: {e}")
                        
                        step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
                        step_metadata = self.parsed_steps.get(step_identifier, {})
                        step_type = step_metadata.get('type', '')
                        step_text = step_metadata.get('text', '').lower()
                        
                        is_dropdown_by_metadata = (
                            step_type == 'select' and 
                            ('dropdown' in step_text or 'open' in step_text or 'click' in step_text) and
                            'pick' not in step_text and 'select' not in step_text and 'choose' not in step_text
                        )
                        
                        is_dropdown_button = is_known_dropdown_button or is_dropdown_by_attributes or is_dropdown_by_metadata
                        logger.info(f"  🔍 Post-click dropdown detection: known={is_known_dropdown_button}, attributes={is_dropdown_by_attributes}, metadata={is_dropdown_by_metadata}, final={is_dropdown_button}")
                    
                    if is_dropdown_button:
                        # This was a dropdown button click - wait for menu portal immediately (no delay)
                        logger.info(f"  ⏳ Waiting for dropdown menu portal to appear...")
                        menu_portal = await self._wait_for_dropdown_menu_portal(timeout=3000)
                        if menu_portal:
                            self.context.open_dropdown_menu = menu_portal
                            # IMPROVEMENT #3: Keep menu open
                            await self._keep_menu_open(menu_portal)
                            logger.info(f"  ✅ Dropdown menu portal opened and kept open: {menu_portal}")
                        else:
                            logger.warning(f"  ⚠️ Dropdown button clicked but menu portal not detected")
                
                # Small delay only if NOT a dropdown (dropdowns need immediate detection)
                if not is_dropdown_button:
                    await self.page.wait_for_timeout(1000)
                
                # Verify click
                new_html = await self.page.content()
                new_url = self.page.url
                dom_changed = new_html != initial_html
                url_changed = new_url != initial_url
                
                if url_changed:
                    # CRITICAL: Wait for page to load after navigation
                    logger.info(f"  ⏳ URL changed from {initial_url} to {new_url} - waiting for page to load...")
                    try:
                        # Wait for DOM content to load (sufficient for most cases)
                        await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                        # Only wait for networkidle if needed (with shorter timeout to avoid hanging)
                        try:
                            await self.page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception:
                            # networkidle can fail on pages with continuous activity - that's OK
                            logger.debug(f"  ⏭️ networkidle not reached (continuing anyway)")
                        await self.page.wait_for_timeout(500)  # Brief wait for page to settle
                        logger.info(f"  ✅ Page loaded after navigation")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Page load wait failed (continuing anyway): {e}")
                    
                    # SPECIAL HANDLING: After TOTP submission, wait for redirect back to hub page
                    step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
                    step_metadata = self.parsed_steps.get(step_identifier, {})
                    step_text = step_metadata.get('text', '').lower()
                    
                    # Check if this was a TOTP submit step
                    is_totp_submit = ('totp' in step_text or 'authenticator' in step_text) and 'submit' in step_text
                    is_on_authenticator_page = 'secure.login.gov' in new_url or 'authenticator' in new_url
                    
                    if is_totp_submit and is_on_authenticator_page:
                        logger.info(f"  🔄 TOTP submit detected - waiting for redirect back to hub page...")
                        try:
                            # Wait for navigation to hub domain (up to 15 seconds)
                            await self.page.wait_for_function(
                                "() => window.location.href.includes('hub-stage.datacommons.cancer.gov') || window.location.href.includes('datacommons.cancer.gov')",
                                timeout=15000
                            )
                            final_url = self.page.url
                            logger.info(f"  ✅ Redirected back to hub page: {final_url}")
                            new_url = final_url  # Update URL for tracking
                        except Exception as e:
                            logger.warning(f"  ⚠️ Did not redirect to hub page within timeout: {e}")
                            logger.info(f"  ℹ️ Current URL: {self.page.url}")
                    
                    self.discovery_tracker.update_url(new_url)
                    self.context.current_url = new_url
                    # Clear open menu if URL changed (navigation closes menus)
                    if self.context.open_dropdown_menu:
                        self.context.open_dropdown_menu = None
                
                # FIX #1: Clear menu portal after option selection (on DOM change, not just URL change)
                # If this was a dropdown option click, clear the menu portal
                if is_dropdown_option and self.context.open_dropdown_menu:
                    logger.info(f"  🔄 Clearing menu portal after option selection (DOM changed)")
                    self.context.open_dropdown_menu = None
                
                if url_changed or dom_changed:
                    logger.info(f"  ✅ Click verified: {'URL changed' if url_changed else 'DOM changed'}")
                    
                    # FIX #1: Also clear menu portal on DOM change (for cases where option selection doesn't change URL)
                    if dom_changed and self.context.open_dropdown_menu and not is_dropdown_button:
                        # DOM changed but not a dropdown button click - likely an option was selected
                        logger.info(f"  🔄 Clearing menu portal after DOM change (likely option selected)")
                        self.context.open_dropdown_menu = None
                    
                    # Track discovery
                    if not using_registry_xpath:
                        await self._track_discovery(
                            chosen_locator, original_selector, element_name,
                            original_element_for_xpath, registry_button_element,
                            discovery_url_before_click, new_url, url_changed,
                            element_attrs_before_click  # Pass pre-extracted attributes
                        )
                    # FIX: Always track discovery (removed skip logic)
                    
                    # Capture screenshot
                    try:
                        screenshot_result = await self.screenshot_manager.capture_post_click(
                            self.page, chosen_locator, element_name, validation_result.get("text_content", "")
                        )
                        if screenshot_result.get("screenshot_taken") and screenshot_result.get("screenshot_file"):
                            self.context.add_screenshot(screenshot_result["screenshot_file"])
                    except Exception as e:
                        logger.warning(f"  ⚠️ Screenshot capture failed: {e}")
                    
                    return f"✅ Clicked {selector} - Verified"
                else:
                    if i == 0:
                        logger.warning(f"  ⚠️ Click executed but no result detected, trying next strategy...")
                        continue
            except Exception as e:
                logger.info(f"  Strategy {i+1} failed: {str(e)[:100]}")
                continue
        
        return f"❌ Click FAILED: {selector} - No strategies produced verifiable result"
    
    async def _track_discovery(self, chosen_locator: Locator, original_selector: str,
                              element_name: str, original_element_for_xpath: Optional[Locator],
                              registry_button_element: Optional[Locator],
                              discovery_url_before_click: str, new_url: str, url_changed: bool,
                              element_attrs_pre_extracted: Dict = None) -> None:
        """Track element discovery"""
        # Temporarily set URL to pre-click URL for discovery tracking
        self.discovery_tracker.update_url(discovery_url_before_click)
        
        try:
            # CRITICAL FIX: Use pre-extracted attributes if available (extracted before navigation)
            # After navigation, element handles are invalid and we'll find wrong elements
            if element_attrs_pre_extracted and element_attrs_pre_extracted.get('tag'):
                element_attrs = element_attrs_pre_extracted
                logger.info(f"  ✅ Using pre-extracted attributes (before navigation) - tag: {element_attrs.get('tag')}")
            else:
                # Fallback: Try to extract normally (only works if no navigation)
                if url_changed:
                    logger.warning(f"  ⚠️ URL changed but no pre-extracted attributes - will use fallback XPath generation")
                    element_attrs = {}
                else:
                    # No navigation - safe to extract normally
                    element_for_xpath = await self._determine_xpath_element(
                        registry_button_element, original_element_for_xpath, chosen_locator
                    )
                    element_attrs = await self.xpath_generator.extract_element_attributes(element_for_xpath)
            
            # FIX: Pass original_selector to preserve simple text selectors (e.g., text=Login)
            final_selector = await self.xpath_generator.generate_final_selector(chosen_locator, original_selector)
            if not final_selector:
                final_selector = original_selector
            
            # Determine element for XPath generation (for clicked_element parameter)
            element_for_xpath = original_element_for_xpath if original_element_for_xpath else chosen_locator
            
            discovery_method = "tree_climbing" if original_element_for_xpath != chosen_locator else "direct"
            
            # Extract element type from element_attrs (tag name)
            element_type = 'unknown'
            if element_attrs and element_attrs.get('tag'):
                tag = element_attrs.get('tag').lower()
                # Map tag names to readable types
                if tag == 'a':
                    element_type = 'link'
                elif tag == 'button':
                    element_type = 'button'
                elif tag == 'input':
                    element_type = 'input'
                elif tag == 'select':
                    element_type = 'select'
                else:
                    element_type = tag  # Use tag name as-is for other elements
            
            metadata = {
                "element_attrs": element_attrs,
                "relationship": "parent" if original_element_for_xpath != chosen_locator else "direct",
                "type": element_type  # CRITICAL: Set type so registry saves correct element type (link vs button)
            }
            
            await self.discovery_tracker.track(
                element_name=element_name,
                original_query=original_selector,
                final_selector=final_selector or original_selector,
                discovery_method=discovery_method,
                metadata=metadata,
                clicked_element=element_for_xpath,
                discovery_url=discovery_url_before_click  # FIX: Use pre-click URL, not post-navigation URL
            )
            
            # Restore URL to post-navigation URL
            if url_changed:
                self.discovery_tracker.update_url(new_url)
                self.context.current_url = new_url
            # If URL didn't change, discovery_tracker.current_url is already correct
            
            logger.info(f"  ✅ Discovery tracked: {element_name}")
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to track discovery: {e}")
    
    async def _determine_xpath_element(self, registry_button_element: Optional[Locator],
                                      original_element_for_xpath: Optional[Locator],
                                      chosen_locator: Locator) -> Locator:
        """Determine which element to use for XPath generation"""
        if registry_button_element:
            logger.info(f"  🔍 Using registry button element for XPath generation")
            return registry_button_element
        
        if original_element_for_xpath:
            try:
                props = await original_element_for_xpath.evaluate("""el => ({
                    tagName: el.tagName.toLowerCase(),
                    id: el.id
                })""")
                
                if props['tagName'] != 'button' and not (props.get('id') and 'login' in props['id'].lower()):
                    logger.info(f"  🔍 Original element is {props['tagName']}, searching for button element...")
                    button_locator = self.page.locator('#header-navbar-login-button, button:has-text("Login"), [id*="login"][role="button"]').first
                    button_count = await button_locator.count()
                    if button_count > 0:
                        element_for_xpath = await button_locator.element_handle()
                        logger.info(f"  ✅ Found actual button element for XPath generation")
                        return element_for_xpath
                    else:
                        logger.info(f"  ⚠️  Could not find button element, using original element")
                        return original_element_for_xpath
                else:
                    return original_element_for_xpath
            except Exception as e:
                logger.debug(f"  ⚠️  Error checking original element: {e}")
                return original_element_for_xpath
        
        return chosen_locator
    
    async def _try_tree_climbing(self, element: Locator, max_depth: int = 5) -> Optional[Locator]:
        """
        Try tree climbing to find interactive parent
        CRITICAL: Only climbs for truly non-interactive elements (text, spans, divs)
        Never replaces <a> links or other interactive elements
        """
        # Get original element tag to check if it's already interactive
        try:
            original_props = await element.evaluate("""el => ({
                tagName: el.tagName.toLowerCase(),
                role: el.getAttribute('role')
            })""")
            
            # CRITICAL FIX: Don't climb if original element is already a link or button
            # Links and buttons should never be replaced by parents
            if original_props['tagName'] in ['a', 'button']:
                logger.info(f"  ✅ Original element is {original_props['tagName']} - skipping tree climbing")
                return None
        except:
            pass
        
        current_elem = element
        for depth in range(1, max_depth + 1):
            try:
                parent_handle = await current_elem.evaluate_handle("el => el.parentElement")
                if not parent_handle:
                    break
                
                parent_elem = parent_handle.as_element()
                if not parent_elem or not await parent_elem.is_visible():
                    break
                
                parent_props = await parent_elem.evaluate("""el => ({
                    tagName: el.tagName.toLowerCase(),
                    role: el.getAttribute('role'),
                    ariaExpanded: el.getAttribute('aria-expanded'),
                    ariaSelected: el.getAttribute('aria-selected'),
                    hasClickHandler: typeof el.onclick === 'function' || el.hasAttribute('onclick')
                })""")
                
                ancestor_is_interactive = (
                    parent_props['tagName'] in ['button', 'a', 'input', 'select'] or
                    parent_props['role'] in ['button', 'tab', 'link', 'checkbox', 'radio'] or
                    parent_props['ariaExpanded'] is not None or
                    parent_props['ariaSelected'] is not None or
                    parent_props['hasClickHandler']
                )
                
                if ancestor_is_interactive:
                    logger.info(f"  ✅ Found interactive ancestor at depth {depth} (tag: {parent_props['tagName']})")
                    return parent_elem
                else:
                    current_elem = parent_elem
            except Exception as e:
                logger.debug(f"  Error climbing at depth {depth}: {e}")
                break
        
        return None
    
    async def _is_dropdown_option_click(self, selector: str, element_description: str, step_text: str) -> bool:
        """
        Check if this click is for a dropdown option (not the dropdown button itself)
        Returns True if we're clicking an option from an opened dropdown menu
        """
        # If there's an open dropdown menu, and this doesn't look like a dropdown button click
        if not self.context.open_dropdown_menu:
            return False
        
        # Check if step text suggests this is selecting an option (not opening dropdown)
        step_lower = step_text.lower()
        option_keywords = ['pick', 'select', 'choose', 'from the', 'from opened menu']
        is_option_step = any(kw in step_lower for kw in option_keywords)
        
        # Check if element description doesn't match known dropdown button names
        desc_lower = (element_description or selector).lower()
        dropdown_button_names = ['datacommons', 'study', 'dropdown']
        is_dropdown_button = any(name in desc_lower for name in dropdown_button_names)
        
        return is_option_step and not is_dropdown_button
    
    async def _find_option_in_menu(self, menu_selector: str, option_text: str) -> Optional[Locator]:
        """
        Find an option within an opened dropdown menu portal
        Args:
            menu_selector: Selector for the menu portal (e.g., '[role="listbox"]')
            option_text: Text of the option to find (e.g., "GC", "NewTestSpn_laxmi")
        Returns:
            Locator for the option, or None if not found
        """
        try:
            # Wait for menu portal to be visible
            menu_locator = self.page.locator(menu_selector).first
            await menu_locator.wait_for(state='visible', timeout=5000)
            
            # Try multiple strategies to find the option
            option_selectors = [
                f'{menu_selector} li[role="option"]:has-text("{option_text}")',
                f'{menu_selector} div[role="option"]:has-text("{option_text}")',
                f'{menu_selector} li:has-text("{option_text}")',
                f'{menu_selector} div:has-text("{option_text}")',
                f'{menu_selector} [role="option"]:has-text("{option_text}")',
            ]
            
            for opt_selector in option_selectors:
                try:
                    option_locator = self.page.locator(opt_selector).first
                    if await option_locator.count() > 0 and await option_locator.is_visible():
                        logger.info(f"  ✅ Found option '{option_text}' in menu using: {opt_selector}")
                        return option_locator
                except Exception as e:
                    logger.debug(f"  ⚠️ Selector failed: {opt_selector} - {e}")
                    continue
            
            # Fallback: Search all options and match by text
            try:
                all_options = await menu_locator.locator('[role="option"]').all()
                for option in all_options:
                    option_text_content = await option.text_content()
                    if option_text_content and option_text.strip().lower() in option_text_content.strip().lower():
                        if await option.is_visible():
                            logger.info(f"  ✅ Found option '{option_text}' by text matching")
                            return option
            except Exception as e:
                logger.debug(f"  ⚠️ Fallback search failed: {e}")
            
            logger.warning(f"  ⚠️ Option '{option_text}' not found in menu portal")
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️ Error finding option in menu: {e}")
            return None
    
    async def _is_dropdown_button_pre_click(self, locator: Locator, element_name: str) -> bool:
        """
        IMPROVEMENT #1: Check if element is a dropdown button BEFORE clicking
        Returns True if element appears to be a dropdown button
        FIX #3: Improved detection even when another menu is open
        """
        try:
            # Check attributes
            role = await locator.get_attribute('role')
            aria_expanded = await locator.get_attribute('aria-expanded')
            aria_has_popup = await locator.get_attribute('aria-haspopup')
            aria_labelledby = await locator.get_attribute('aria-labelledby')
            id_attr = await locator.get_attribute('id') or ''
            class_name = await locator.get_attribute('class') or ''
            
            # Material-UI Select indicators (more specific checks)
            is_mui_select = (
                'MuiSelect' in class_name or
                'MuiSelect-select' in class_name or
                'MuiSelect-root' in class_name or
                (role == 'button' and aria_has_popup == 'listbox') or
                (id_attr and 'select' in id_attr.lower() and 'mui-component-select' in id_attr)
            )
            
            # Standard dropdown indicators
            is_standard_dropdown = (
                (role == 'button' and aria_expanded is not None) or
                aria_has_popup == 'listbox' or
                aria_has_popup == 'menu' or
                (role == 'combobox')
            )
            
            # Check if element name/description suggests dropdown
            element_text = await locator.text_content() or ''
            element_desc_lower = (element_name or element_text).lower()
            known_dropdowns = ['study', 'datacommons', 'dropdown', 'select']
            is_known_dropdown = any(name in element_desc_lower for name in known_dropdowns)
            
            # FIX #3: Check if this is a Material-UI Select button (even if another menu is open)
            # Material-UI Select buttons have specific ID patterns: mui-component-select-*
            is_mui_select_by_id = (
                id_attr and 
                'mui-component-select' in id_attr and 
                role == 'button'
            )
            
            result = is_mui_select or is_standard_dropdown or is_known_dropdown or is_mui_select_by_id
            logger.info(f"  🔍 Pre-click dropdown detection: mui={is_mui_select}, standard={is_standard_dropdown}, known={is_known_dropdown}, mui_id={is_mui_select_by_id}, result={result}")
            return result
        except Exception as e:
            logger.debug(f"  ⚠️ Pre-click dropdown detection failed: {e}")
            return False
    
    async def _wait_for_dropdown_menu_portal(self, timeout: int = 3000) -> Optional[str]:
        """
        IMPROVEMENT #2: Enhanced menu portal detection - checks document body and better selectors
        Wait for Material-UI Select dropdown menu portal to appear after clicking dropdown button
        Returns:
            Selector for the menu portal, or None if not found
        """
        try:
            # Enhanced selectors - Material-UI Select specific + standard
            menu_selectors = [
                # Material-UI Select specific (check in body for portals)
                'body > .MuiPopover-root [role="listbox"]',
                'body > [class*="MuiSelect-menu"]',
                'body > [class*="MuiMenu-root"]',
                'body > [class*="MuiPaper-root"][role="listbox"]',
                '.MuiPopover-root [role="listbox"]',
                '[class*="MuiSelect-menu"]',
                '[class*="MuiMenu-root"]',
                '[class*="MuiPaper-root"][role="listbox"]',
                
                # Standard selectors (check in body for portals)
                'body > [role="listbox"]',
                'body > [role="menu"]',
                '[role="listbox"]',
                '[role="menu"]',
                
                # Fallback selectors
                '[data-testid*="menu"]',
                '[id*="menu"]',
            ]
            
            logger.info(f"  🔍 Enhanced menu portal detection (timeout: {timeout}ms)...")
            
            # Try all selectors with shorter timeout each
            per_selector_timeout = min(500, timeout // len(menu_selectors))
            if per_selector_timeout < 200:
                per_selector_timeout = 200  # Minimum 200ms per selector
            
            for selector in menu_selectors:
                try:
                    menu_locator = self.page.locator(selector).first
                    # Check if element exists first (faster)
                    count = await menu_locator.count()
                    if count > 0:
                        # Element exists, wait for visibility
                        await menu_locator.wait_for(state='visible', timeout=per_selector_timeout)
                        if await menu_locator.is_visible():
                            logger.info(f"  ✅ Dropdown menu portal found: {selector}")
                            return selector
                        else:
                            logger.debug(f"  ⚠️ Menu selector '{selector}' exists but not visible")
                    else:
                        logger.debug(f"  ⚠️ Menu selector '{selector}' not found in DOM")
                except Exception as e:
                    logger.debug(f"  ⚠️ Menu selector '{selector}' check failed: {e}")
                    continue
            
            logger.warning(f"  ⚠️ Dropdown menu portal not found after {timeout}ms (tried {len(menu_selectors)} selectors)")
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️ Error waiting for dropdown menu: {e}")
            return None
    
    async def _keep_menu_open(self, menu_selector: str):
        """
        IMPROVEMENT #3: Prevent menu from auto-closing before option is selected
        Disables backdrop clicks and escape key closing
        """
        try:
            await self.page.evaluate(f"""
                () => {{
                    const menu = document.querySelector('{menu_selector}');
                    if (menu) {{
                        // Prevent backdrop clicks from closing
                        const backdrop = menu.closest('.MuiBackdrop-root');
                        if (backdrop) {{
                            backdrop.style.pointerEvents = 'none';
                            backdrop.setAttribute('data-keep-open', 'true');
                        }}
                        // Prevent escape key from closing
                        menu.setAttribute('data-keep-open', 'true');
                        // Prevent click-outside from closing
                        const popover = menu.closest('.MuiPopover-root');
                        if (popover) {{
                            popover.setAttribute('data-keep-open', 'true');
                        }}
                    }}
                }}
            """)
            logger.info(f"  🔒 Menu kept open: {menu_selector}")
        except Exception as e:
            logger.debug(f"  ⚠️ Could not keep menu open: {e}")
    
    async def _close_open_menu(self, menu_selector: str):
        """
        FIX #2: Close an open menu before opening a new dropdown
        """
        try:
            await self.page.evaluate(f"""
                () => {{
                    const menu = document.querySelector('{menu_selector}');
                    if (menu) {{
                        // Find and click backdrop to close menu
                        const backdrop = menu.closest('.MuiPopover-root')?.querySelector('.MuiBackdrop-root');
                        if (backdrop) {{
                            backdrop.click();
                        }} else {{
                            // Fallback: Press Escape key
                            const event = new KeyboardEvent('keydown', {{
                                key: 'Escape',
                                code: 'Escape',
                                keyCode: 27,
                                bubbles: true
                            }});
                            document.dispatchEvent(event);
                        }}
                    }}
                }}
            """)
            # Wait a bit for menu to close
            await self.page.wait_for_timeout(300)
            logger.info(f"  🔒 Closed previously open menu: {menu_selector}")
        except Exception as e:
            logger.debug(f"  ⚠️ Could not close menu: {e}")
