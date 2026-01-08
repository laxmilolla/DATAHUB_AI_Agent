"""
Browser Click Tool - Handle browser_click tool
Extracted from bedrock_playwright_agent.py lines 1271-2635
CRITICAL: Preserves registry checks, tree climbing, discovery tracking, XPath preservation
"""
import re
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class BrowserClickTool:
    """Handle browser_click tool"""
    
    def __init__(self, page: Page, element_locator, action_executor, discovery_tracker,
                 registry_manager, xpath_generator, llm_helper, totp_handler,
                 screenshot_manager, execution_context, parsed_steps: dict, story: str):
        """
        Initialize click tool
        Args:
            page: Playwright page object
            element_locator: ElementLocator instance
            action_executor: ActionExecutor instance
            discovery_tracker: DiscoveryTracker instance
            registry_manager: RegistryManager instance
            xpath_generator: XPathGenerator instance
            llm_helper: LLMHelper instance
            totp_handler: TOTPHandler instance
            screenshot_manager: ScreenshotManager instance
            execution_context: ExecutionContext instance
            parsed_steps: Parsed story steps metadata
            story: Story text
        """
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
        """
        Execute click operation
        CRITICAL: Checks registry first, preserves XPaths, tracks discovery
        """
        original_selector = selector
        element_name = element_description or selector.replace("text=", "").replace("_", " ")
        logger.info(f"Click: {selector}")
        
        # Get current step metadata
        step_num = self.context.current_step_number
        step_metadata = self.parsed_steps.get(step_num, {})
        step_text = step_metadata.get('text', '')
        
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
        
        # 🔒 CRITICAL: Check element registry FIRST
        registry_selector = self.element_locator.check_registry(element_description or selector, domain, page_name)
        using_registry_xpath = False
        optimized_selector_used = False
        
        if registry_selector:
            selector = registry_selector
            optimized_selector_used = True
            # If registry selector is an XPath, we're using manual XPath - skip tree climbing & discovery
            if selector.startswith("xpath="):
                using_registry_xpath = True
                logger.info(f"  📋 Using XPath from registry (MANUAL) - will skip tree climbing & discovery")
            else:
                logger.info(f"  📋 Using selector from registry")
        
        # Try to find element
        try:
            all_matches = await self.page.locator(selector).all()
            
            # Verify XPath uniqueness if using registry XPath
            if optimized_selector_used and selector.startswith("xpath="):
                xpath_count = len(all_matches)
                logger.info(f"  🔍 XPath verification: {xpath_count} match(es) found")
                
                if xpath_count == 0:
                    logger.warning(f"  ⚠️ XPath returned 0 matches, falling back to original selector")
                    selector = original_selector
                    optimized_selector_used = False
                    using_registry_xpath = False
                    all_matches = await self.page.locator(selector).all()
                elif xpath_count > 1:
                    logger.warning(f"  ⚠️ XPath returned {xpath_count} matches (not unique)")
                else:
                    logger.info(f"  ✅ XPath is unique (1 match)")
        except Exception as selector_error:
            if optimized_selector_used and selector != original_selector:
                logger.warning(f"  ⚠️ Optimized selector failed: {selector_error}")
                logger.info(f"  ⚙️ Falling back to original query: {original_selector}")
                selector = original_selector
                optimized_selector_used = False
                using_registry_xpath = False
                all_matches = await self.page.locator(selector).all()
            else:
                raise selector_error
        
        # Filter to visible elements
        visible_matches = []
        for match in all_matches:
            if await match.is_visible():
                visible_matches.append(match)
        
        chosen_locator = None
        original_element_for_xpath = None
        
        # 🔒 CRITICAL: If using registry XPath, SKIP tree climbing
        if using_registry_xpath and len(visible_matches) == 1:
            logger.info(f"  🔒 Using registry XPath directly - skipping tree climbing")
            chosen_locator = visible_matches[0]
            original_element_for_xpath = visible_matches[0]
        elif len(visible_matches) > 1:
            # Multiple matches - use LLM disambiguation
            logger.info(f"  🔍 Found {len(visible_matches)} visible matches, asking LLM to choose...")
            candidates = []
            original_element_map = {}  # Map parent element -> original element for XPath generation
            
            for i, match in enumerate(visible_matches):
                description = await self.llm_helper.describe_element(match)
                
                # Check if element is interactive
                element_props = await match.evaluate("""el => ({
                    tagName: el.tagName.toLowerCase(),
                    role: el.getAttribute('role'),
                    ariaExpanded: el.getAttribute('aria-expanded'),
                    ariaSelected: el.getAttribute('aria-selected'),
                    hasClickHandler: typeof el.onclick === 'function' || el.hasAttribute('onclick')
                })""")
                
                is_interactive = (
                    element_props['tagName'] in ['button', 'a', 'input', 'select'] or
                    element_props['role'] in ['button', 'tab', 'link', 'checkbox', 'radio'] or
                    element_props['ariaExpanded'] is not None or
                    element_props['ariaSelected'] is not None or
                    element_props['hasClickHandler']
                )
                
                candidates.append({
                    "index": len(candidates),
                    "element": match,
                    "description": description,
                    "is_original": True  # Mark original elements
                })
                
                # Tree climbing if not interactive and not using registry XPath
                if not is_interactive and not using_registry_xpath:
                    logger.info(f"  🔍 Candidate {i}: Element not interactive, climbing tree...")
                    parent = await self._try_tree_climbing(match)
                    if parent:
                        parent_desc = await self.llm_helper.describe_element(parent)
                        candidates.append({
                            "index": len(candidates),
                            "element": parent,
                            "description": parent_desc + "\n(PARENT found via tree climbing)",
                            "is_original": False,
                            "original_element": match  # Store reference to original element
                        })
                        # Map parent to original for XPath generation
                        original_element_map[id(parent)] = match
            
            # Ask LLM to choose
            if len(candidates) > 1:
                best_index = await self.llm_helper.choose_element(candidates, selector)
                chosen_locator = candidates[best_index]["element"]
                # CRITICAL FIX: Use original element for XPath, not the parent
                if candidates[best_index].get("is_original", True):
                    original_element_for_xpath = chosen_locator
                else:
                    # LLM chose a parent - use the original element that triggered tree climbing
                    original_element_for_xpath = candidates[best_index].get("original_element", visible_matches[0])
            else:
                chosen_locator = candidates[0]["element"]
                original_element_for_xpath = candidates[0]["element"]
        elif len(visible_matches) == 1:
            # Single match - check if interactive, try tree climbing if not
            match = visible_matches[0]
            if not using_registry_xpath:
                element_props = await match.evaluate("""el => ({
                    tagName: el.tagName.toLowerCase(),
                    role: el.getAttribute('role'),
                    ariaExpanded: el.getAttribute('aria-expanded'),
                    hasClickHandler: typeof el.onclick === 'function' || el.hasAttribute('onclick')
                })""")
                
                is_interactive = (
                    element_props['tagName'] in ['button', 'a', 'input', 'select'] or
                    element_props['role'] in ['button', 'tab', 'link'] or
                    element_props['ariaExpanded'] is not None or
                    element_props['hasClickHandler']
                )
                
                if not is_interactive:
                    logger.info(f"  🔍 Element not interactive, climbing tree...")
                    parent = await self._try_tree_climbing(match)
                    if parent:
                        chosen_locator = parent
                        original_element_for_xpath = match
                    else:
                        chosen_locator = match
                        original_element_for_xpath = match
                else:
                    chosen_locator = match
                    original_element_for_xpath = match
            else:
                chosen_locator = match
                original_element_for_xpath = match
        else:
            raise Exception(f"No visible elements found for selector: {selector}")
        
        # Pre-click validation
        if chosen_locator:
            validation_result = {
                "exists": True,
                "visible": await chosen_locator.is_visible(),
                "enabled": await chosen_locator.is_enabled(),
                "text_content": await chosen_locator.text_content() or "",
                "locator": chosen_locator,
                "selector": selector
            }
        else:
            validation_result = await self.action_executor.validate_visibility(selector, element_name)
            chosen_locator = validation_result.get("locator")
            if not chosen_locator:
                chosen_locator = self.page.locator(selector).nth(0)
        
        if not validation_result["exists"]:
            return f"❌ Click FAILED: {selector} - Element not found"
        
        # Check for accordion
        is_accordion = False
        initial_aria_expanded = None
        if chosen_locator:
            try:
                initial_aria_expanded = await chosen_locator.get_attribute("aria-expanded")
                if initial_aria_expanded is not None:
                    is_accordion = True
                    if initial_aria_expanded == 'true':
                        logger.info(f"  ✅ Accordion already expanded - skipping click")
                        return f"✅ Accordion already open: {element_name}"
            except:
                pass
        
        # TOTP submission detection
        is_totp_submission = False
        if step_text:
            totp_submit_keywords = ["submit", "click submit", "press submit", "continue", "verify"]
            submit_has_totp = any(keyword in step_text.lower() for keyword in totp_submit_keywords)
            selector_is_submit = "submit" in selector.lower()
            
            # Check if TOTP field exists on page
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
                is_totp_submission = (submit_has_totp or selector_is_submit) and has_totp_field
            except:
                pass
        
        # Handle TOTP submission
        if is_totp_submission:
            logger.info(f"  [TOTP_SUBMIT] Detected TOTP submission - regenerating fresh TOTP code")
            try:
                totp_code = self.totp_handler.generate_code(story=self.story)
                logger.info(f"  [TOTP_SUBMIT] Generated fresh TOTP code: {totp_code}")
                
                # Update TOTP field
                totp_selectors = [
                    "input[name='code']",
                    "input[type='text'][name*='code']",
                    "input.one-time-code"
                ]
                
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
        
        # Execute click
        initial_html = await self.page.content()
        initial_url = self.page.url
        
        try:
            # Try multiple strategies
            strategies = [
                {"desc": "direct click", "method": lambda: self.action_executor.click(chosen_locator)},
                {"desc": "force click", "method": lambda: self.action_executor.click(chosen_locator, force=True)},
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    logger.info(f"  Trying strategy {i+1}: {strategy['desc']}")
                    await strategy["method"]()
                    await self.page.wait_for_timeout(1000)
                    
                    # Verify click
                    new_html = await self.page.content()
                    new_url = self.page.url
                    dom_changed = new_html != initial_html
                    url_changed = new_url != initial_url
                    
                    if url_changed or dom_changed:
                        logger.info(f"  ✅ Click verified: {'URL changed' if url_changed else 'DOM changed'}")
                        
                        # Track discovery (skip if using registry XPath)
                        if not using_registry_xpath:
                            try:
                                final_selector = await self.xpath_generator.generate_final_selector(chosen_locator)
                                if not final_selector:
                                    final_selector = original_selector
                                
                                element_attrs = await self.xpath_generator.extract_element_attributes(
                                    original_element_for_xpath if original_element_for_xpath else chosen_locator
                                )
                                
                                discovery_method = "tree_climbing" if original_element_for_xpath != chosen_locator else "direct"
                                
                                metadata = {
                                    "element_attrs": element_attrs,
                                    "relationship": "parent" if original_element_for_xpath != chosen_locator else "direct"
                                }
                                
                                await self.discovery_tracker.track(
                                    element_name=element_name,
                                    original_query=original_selector,
                                    final_selector=final_selector or original_selector,
                                    discovery_method=discovery_method,
                                    metadata=metadata,
                                    # CRITICAL: Pass original clicked element (not parent) for XPath generation
                                    # The parent is only used for clicking, but XPath should target the actual element
                                    clicked_element=original_element_for_xpath if original_element_for_xpath else chosen_locator
                                )
                                logger.info(f"  ✅ Discovery tracked: {element_name}")
                            except Exception as e:
                                logger.warning(f"  ⚠️ Failed to track discovery: {e}")
                        else:
                            logger.info(f"  🔒 Skipped discovery tracking (using registry XPath)")
                        
                        # Post-click screenshot
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
        except Exception as e:
            logger.error(f"  ❌ Click error: {e}")
            return f"❌ Click FAILED: {selector} - {str(e)}"
    
    async def _try_tree_climbing(self, element: Locator, max_depth: int = 5) -> Optional[Locator]:
        """
        Try tree climbing to find interactive parent
        Returns: Parent locator if found, None otherwise
        """
        current_elem = element
        for depth in range(1, max_depth + 1):
            try:
                parent_handle = await current_elem.evaluate_handle("el => el.parentElement")
                if not parent_handle:
                    break
                
                parent_elem = parent_handle.as_element()
                if not parent_elem or not await parent_elem.is_visible():
                    break
                
                # Check if parent is interactive
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
                    logger.info(f"  ✅ Found interactive ancestor at depth {depth}")
                    return parent_elem
                else:
                    current_elem = parent_elem
            except Exception as e:
                logger.debug(f"  Error climbing at depth {depth}: {e}")
                break
        
        return None

