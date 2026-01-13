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
        
        # Initialize variables
        chosen_locator = None
        original_element_for_xpath = None
        using_registry_xpath = False
        registry_button_element = None
        
        # Check if this is a dropdown option click - if so, search within open menu portal
        is_dropdown_option = await self._is_dropdown_option_click(selector, element_description, step_text)
        
        if is_dropdown_option and self.context.open_dropdown_menu:
            # Search within the open menu portal
            logger.info(f"  🔍 Searching for dropdown option '{element_description or selector}' within open menu portal")
            menu_selector = self.context.open_dropdown_menu
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
        
        # Check accordion state
        accordion_result = await self._check_accordion(chosen_locator, element_name)
        if accordion_result:
            return accordion_result
        
        # Handle TOTP submission if needed
        await self._handle_totp_submission(step_text, selector)
        
        # Execute click and track discovery
        return await self._execute_click_with_discovery(
            chosen_locator, selector, original_selector, element_name,
            original_element_for_xpath, registry_button_element,
            using_registry_xpath, validation_result
        )
    
    async def _resolve_selector(self, selector: str, element_description: str) -> Tuple[str, bool, Optional[Locator]]:
        """Check registry and resolve selector"""
        domain, page_name = self._get_domain_and_page()
        registry_selector = self.element_locator.check_registry(element_description, domain, page_name)
        
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
        """Extract domain and page name from current URL"""
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
            return domain, page_name
        except:
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
                                           validation_result: Dict[str, Any]) -> str:
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
        
        strategies = [
            {"desc": "direct click", "method": lambda: self.action_executor.click(chosen_locator)},
            {"desc": "force click", "method": lambda: self.action_executor.click(chosen_locator, force=True)},
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"  Trying strategy {i+1}: {strategy['desc']}")
                discovery_url_before_click = self.page.url
                
                await strategy["method"]()
                await self.page.wait_for_timeout(1000)
                
                # Check if this was a dropdown click - wait for menu portal to open
                # Only check if we don't already have an open menu (to avoid overwriting)
                if not self.context.open_dropdown_menu:
                    step_identifier = self.context.current_step_identifier or str(self.context.current_step_number)
                    step_metadata = self.parsed_steps.get(step_identifier, {})
                    step_type = step_metadata.get('type', '')
                    step_text = step_metadata.get('text', '').lower()
                    
                    # Check if this was a dropdown button click (not an option selection)
                    is_dropdown_button = (
                        step_type == 'select' and 
                        ('dropdown' in step_text or 'open' in step_text or 'click' in step_text) and
                        'pick' not in step_text and 'select' not in step_text and 'choose' not in step_text
                    )
                    
                    if is_dropdown_button:
                        # This was a dropdown button click - wait for menu portal
                        menu_portal = await self._wait_for_dropdown_menu_portal()
                        if menu_portal:
                            self.context.open_dropdown_menu = menu_portal
                            logger.info(f"  ✅ Dropdown menu portal opened: {menu_portal}")
                
                # Verify click
                new_html = await self.page.content()
                new_url = self.page.url
                dom_changed = new_html != initial_html
                url_changed = new_url != initial_url
                
                if url_changed:
                    self.discovery_tracker.update_url(new_url)
                    self.context.current_url = new_url
                    # Clear open menu if URL changed (navigation closes menus)
                    if self.context.open_dropdown_menu:
                        self.context.open_dropdown_menu = None
                
                if url_changed or dom_changed:
                    logger.info(f"  ✅ Click verified: {'URL changed' if url_changed else 'DOM changed'}")
                    
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
    
    async def _wait_for_dropdown_menu_portal(self, timeout: int = 5000) -> Optional[str]:
        """
        Wait for Material-UI Select dropdown menu portal to appear after clicking dropdown button
        Returns:
            Selector for the menu portal, or None if not found
        """
        try:
            # Material-UI Select menus appear in portals with role="listbox"
            menu_selectors = [
                '[role="listbox"]',
                '[role="menu"]',
                '.MuiMenu-root',
                '.MuiPopover-root [role="listbox"]',
                '[class*="MuiMenu"]',
            ]
            
            for selector in menu_selectors:
                try:
                    menu_locator = self.page.locator(selector).first
                    await menu_locator.wait_for(state='visible', timeout=timeout)
                    if await menu_locator.is_visible():
                        logger.info(f"  ✅ Dropdown menu portal appeared: {selector}")
                        return selector
                except Exception as e:
                    logger.debug(f"  ⚠️ Menu selector '{selector}' not found: {e}")
                    continue
            
            logger.warning(f"  ⚠️ Dropdown menu portal not found after {timeout}ms")
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️ Error waiting for dropdown menu: {e}")
            return None
