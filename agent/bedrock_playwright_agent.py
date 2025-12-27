"""
Pure Python Agent - Bedrock + Direct Playwright
No MCP, No Bridge, No Node.js - Clean Architecture 2
"""
import boto3
import json
import asyncio
from typing import Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page, Playwright
from pathlib import Path
import logging
import uuid
import time
import sys
import re
from datetime import datetime

# Add utils to path for element registry
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.element_registry import get_registry

logger = logging.getLogger(__name__)


class BedrockPlaywrightAgent:
    """
    Autonomous QA Agent
    - Bedrock for intelligence
    - Playwright for browser automation
    - Direct calls, no middleware
    """
    
    def __init__(self, region: str = 'us-east-1'):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        # Playwright
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.page: Page = None
        
        # State
        self.execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        # Use absolute path to project root to avoid issues when Flask runs from different directories
        project_root = Path(__file__).parent.parent
        self.screenshots_dir = project_root / 'storage' / 'screenshots'
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_counter = 0
        
        # Element Registry for cached selectors
        self.element_registry = get_registry()
        self.current_url = ""
        self.discovered_elements = []  # Track newly discovered elements
        self.pre_click_screenshots = []  # Track pre-click validation screenshots
        self.story = ""  # Initialize story for AI disambiguation
        self.discoveries = []  # Track discovery metadata (query + final selector + method)
        
    async def start_browser(self):
        """Launch Playwright browser"""
        logger.info("Launching Chromium browser...")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page(viewport={'width': 1280, 'height': 720})
        
        logger.info("Browser ready")
    
    async def close_browser(self):
        """Cleanup"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _get_domain_and_page(self) -> tuple:
        """Extract domain and page from current URL - always fetch live from browser"""
        if not self.page:
            return None, None
        
        try:
            # Always get current URL from the live page
            current_url = self.page.url
            if not current_url:
                return None, None
            
            # Extract domain
            domain = current_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
            
            # Extract page name
            import re
            match = re.search(r'/#/(\w+)', current_url)
            if match:
                page = match.group(1)
            else:
                page = "home"
            
            return domain, page
        except Exception as e:
            logger.warning(f"Error getting domain/page: {e}")
            return None, None

    def _check_element_registry(self, element_description: str) -> str:
        """Check if element exists in registry and return selector. Returns None if not found (LLM will discover)."""
        try:
            domain, page = self._get_domain_and_page()
            logger.info(f"  🔍 Registry check: element='{element_description}', domain={domain}, page={page}, url={self.page.url if self.page else "N/A"}")
            if not domain or not page:
                logger.warning(f"  ⚠️ Registry check skipped: domain or page not determined")
                return None
            
            # Try exact match first
            element = self.element_registry.get_element(domain, page, element_description)
            logger.info(f"  📍 Exact match result: {'Found' if element else 'Not found'}")
            if element:
                selector = element.get('selector')
                logger.info(f"  ✅ Found in element map: {element_description} -> {selector}")
                self.element_registry.update_usage(domain, page, element_description)
                return selector
            
            # Load element map for fuzzy matching
            element_map = self.element_registry.load_map(domain, page)
            logger.info(f"  📂 Element map loaded: {len(element_map.get('elements', {})) if element_map else 0} elements")
            if not element_map:
                return None
            
            logger.info(f"  📝 Starting keyword extraction for: {element_description}")
            
            # Normalize selector to handle dynamic counts and preserve semantic type
            normalized_selector, semantic_type, normalized_text = self._normalize_selector_for_dynamic_content(element_description)
            
            # Strip Playwright selector syntax before keyword extraction
            clean_desc = normalized_text  # Use normalized text without counts
            
            # Extract from attribute selectors: [data-testid="Study-Facet"] -> Study-Facet
            import re as re_import
            attr_match = re_import.search(r'\[(?:data-testid|id|class|aria-label)=["\']([^"\']*)["\']\]', clean_desc)
            if attr_match:
                clean_desc = attr_match.group(1)
                # Further clean: Study-Facet -> Study
                clean_desc = re.sub(r'[-_](Facet|facet|Dropdown|dropdown|Button|button)', '', clean_desc)
            
            # Remove text= prefix
            if clean_desc.startswith('text='):
                clean_desc = clean_desc[5:]
            
            # Remove :has-text() wrapper
            if ':has-text(' in clean_desc:
                match = re.search(r":has-text\((.+?)\)", clean_desc)
                if match:
                    clean_desc = match.group(1).strip('"\'').strip()
            
            # Don't remove element type prefixes - we need them!
            # But extract for matching
            element_type_prefix = None
            type_prefix_match = re.search(r'^(button|input|a|div|span|tab):', clean_desc)
            if type_prefix_match:
                element_type_prefix = type_prefix_match.group(1)
            
            logger.info(f"  🧹 Cleaned: '{element_description}' -> '{clean_desc}' (type={semantic_type or element_type_prefix})")
            # Extract keywords from cleaned description
            keywords = re.sub(r"[^a-zA-Z0-9]", " ", clean_desc).lower().split()
            keywords = [k for k in keywords if k and len(k) > 2]  # Filter short words
            # Filter out technical keywords (data, testid, aria, etc.)
            keywords = [k for k in keywords if k not in ["data", "testid", "aria", "label", "class", "button", "input", "span", "div"]]
            logger.info(f"  DEBUG_KEYWORDS: {keywords}")
            
            # Prioritized matching: better matches win
            best_match = None
            best_score = 0
            
            element_desc_lower = element_description.lower()
            element_desc_clean = " ".join(keywords)  # Cleaned version: "text study" -> "study"
            
            for name, elem in element_map.get("elements", {}).items():
                name_lower = name.lower()
                elem_type = elem.get("type", "").lower()
                score = 0
                
                # FILTER: If semantic type specified, only match same type
                if semantic_type:
                    # Check if element type matches requested semantic type
                    type_matches = False
                    
                    # Handle role="tab" matching
                    if semantic_type == "tab":
                        if elem_type in ["tab", "button"] and "tab" in name_lower:
                            type_matches = True
                    # Handle button: matching
                    elif semantic_type == "button":
                        if elem_type == "button":
                            type_matches = True
                    # Handle other role types
                    else:
                        if elem_type == semantic_type:
                            type_matches = True
                    
                    # Skip if type doesn't match
                    if not type_matches:
                        logger.debug(f"  ⏭️ Skipping '{name}' (type={elem_type}) - doesn't match requested type={semantic_type}")
                        continue
                
                # Priority 1: Element name exactly matches query (case-insensitive) - Score 100
                if name_lower == element_desc_lower or name_lower == element_desc_clean:
                    score = 100
                
                # Priority 2: Element name starts with query - Score 80
                elif name_lower.startswith(element_desc_clean) or any(name_lower.startswith(k) for k in keywords):
                    score = 80
                
                # Priority 3: Element name ends with query - Score 70
                elif name_lower.endswith(element_desc_clean) or any(name_lower.endswith(k) for k in keywords):
                    score = 70
                
                # Priority 4: Query is substring of element name - Score 60
                elif element_desc_clean in name_lower:
                    score = 60
                
                # Priority 5: Keyword appears in element name - Score 40
                elif any(k in name_lower for k in keywords):
                    score = 40
                
                # Priority 6: Keyword appears in description - Score 20
                elif any(k in elem.get("description", "").lower() for k in keywords):
                    score = 20
                
                # Bonus: Element type is accordion/dropdown - add 10 points if query suggests dropdown
                if elem.get("type") in ["accordion", "dropdown"] and "dropdown" in element_desc_lower:
                    score += 10
                
                # Bonus: Semantic type match adds confidence
                if semantic_type and elem_type == semantic_type:
                    score += 15
                
                # Penalty: ID-based selectors (likely nested/hidden elements)
                if elem.get("selector", "").startswith("#"):
                    score -= 30
                    logger.debug(f"  ⬇️ ID selector penalty for '{name}': {elem.get('selector')}")
                
                # Penalty: Specific selectors (button:, [role=) when query is generic text=
                # Prefer simpler text= matches for AI discovery
                if not semantic_type and element_description.startswith("text="):
                    if elem.get("selector", "").startswith(("button:", "[role=")):
                        score -= 15
                        logger.debug(f"  ⬇️ Specific selector penalty for '{name}' (query is generic)")
                
                # Track best match
                if score > best_score or (score == best_score and best_match and len(name) < len(best_match[0])):
                    best_score = score
                    best_match = (name, elem)
            
            # Return best match if found
            if best_match and best_score >= 80:  # Minimum score threshold (raised to prevent false matches)
                name, elem = best_match
                
                # OPTIMIZATION: Try final selector first (from successful discovery)
                # This is the actual working selector that was used successfully
                final_selector_from_discovery = elem.get("selector")  # New format stores final selector here
                query_selector = elem.get("query")  # Original query (if available)
                
                # If this element has discovery metadata, it means we have a proven working selector
                if elem.get("discovery"):
                    logger.info(f"  🚀 Using optimized selector from discovery (method: {elem.get('discovery', {}).get('method')})")
                    logger.info(f"     Original query: {query_selector}")
                    logger.info(f"     Final selector: {final_selector_from_discovery}")
                    # Update usage and return the optimized selector directly
                    self.element_registry.update_usage(domain, page, name)
                    return final_selector_from_discovery
                
                # Otherwise, proceed with normal logic for legacy elements
                base_selector = final_selector_from_discovery or elem.get("selector")
                
                # Check if matched element has dynamic count
                import re as re_module
                if re_module.search(r'\(\d+\)', name):
                    # Element has count - use regex selector to match any count
                    # Extract clean text from the selector, not the name field
                    if ':has-text(' in base_selector:
                        # Extract from selector like "button:has-text('Samples(1507)')"
                        text_match = re_module.search(r':has-text\(["\']?([^"\'()]+)', base_selector)
                        if text_match:
                            element_text = text_match.group(1).strip()
                        else:
                            # Fallback: clean the name field
                            element_text = re_module.sub(r'\s*(button|link|dropdown|tab|filter)$', '', name)
                            element_text = re_module.sub(r'\(\d+\)', '', element_text).strip()
                    else:
                        # For text= selectors or others - clean the name field
                        element_text = re_module.sub(r'\s*(button|link|dropdown|tab|filter)$', '', name)
                        element_text = re_module.sub(r'\(\d+\)', '', element_text).strip()
                    
                    # Determine element type from selector or elem info
                    if semantic_type:
                        if semantic_type == "tab":
                            final_selector = f'[role="tab"]:has-text(/{element_text}\\(\\d+\\)/)'
                        elif semantic_type == "button":
                            final_selector = f'button:has-text(/{element_text}\\(\\d+\\)/)'
                        else:
                            final_selector = f'[role="{semantic_type}"]:has-text(/{element_text}\\(\\d+\\)/)'
                    elif base_selector.startswith('button'):
                        final_selector = f'button:has-text(/{element_text}\\(\\d+\\)/)'
                    else:
                        # Generic text match with regex
                        final_selector = f':has-text(/{element_text}\\(\\d+\\)/)'
                    
                    logger.info(f"  ✅ Best match (score={best_score}): '{element_description}' matched '{name}'")
                    logger.info(f"  🔄 Dynamic count detected - using regex selector: {final_selector}")
                    self.element_registry.update_usage(domain, page, name)
                    return final_selector
                else:
                    # No dynamic count - use selector as-is, but apply semantic type if specified
                    if semantic_type and not ('[role=' in base_selector or base_selector.startswith(semantic_type)):
                        # Add semantic type qualifier if not already present
                        if ':has-text(' in base_selector:
                            text_part = re_module.search(r':has-text\(([^)]+)\)', base_selector)
                            if text_part:
                                if semantic_type in ['tab', 'button', 'link']:
                                    final_selector = f'{semantic_type}:has-text({text_part.group(1)})'
                                else:
                                    final_selector = f'[role="{semantic_type}"]:has-text({text_part.group(1)})'
                            else:
                                final_selector = base_selector
                        else:
                            final_selector = base_selector
                    else:
                        final_selector = base_selector
                    
                    logger.info(f"  ✅ Best match (score={best_score}): '{element_description}' matched '{name}' -> {final_selector}")
                    self.element_registry.update_usage(domain, page, name)
                    return final_selector

            return None
        except Exception as e:
            # Registry lookup failed - no problem, LLM will discover
            logger.warning(f"  📋 Registry lookup skipped ({str(e)[:50]}), LLM will discover")
            return None

    def _normalize_selector_for_dynamic_content(self, selector: str) -> tuple:
        """
        Normalize selector to handle dynamic counts and preserve semantic info.
        Returns: (normalized_selector, semantic_type, text_content)
        """
        import re
        
        # Extract semantic type (role, element tag)
        semantic_type = None
        type_match = re.search(r'(\[role=["\']([^"\']+)["\']\]|^(button|input|a|div|span|tab))', selector)
        if type_match:
            if type_match.group(2):  # role attribute
                semantic_type = type_match.group(2)  # e.g., "tab"
            elif type_match.group(3):  # element tag
                semantic_type = type_match.group(3)  # e.g., "button"
        
        # Extract text content
        text_content = selector
        
        # From :has-text()
        has_text_match = re.search(r':has-text\(["\']([^"\']+)["\']\)', selector)
        if has_text_match:
            text_content = has_text_match.group(1)
        # From text=
        elif selector.startswith('text='):
            text_content = selector[5:]
        
        # Remove dynamic counts from text: "Samples(1507)" -> "Samples"
        normalized_text = re.sub(r'\(\d+\)', '', text_content).strip()
        
        # Build normalized selector with regex for dynamic counts
        if re.search(r'\(\d+\)', text_content):  # Had a count
            # Use regex to match any count
            if semantic_type:
                if semantic_type in ['tab', 'button', 'link']:
                    # Use role or tag with regex text
                    if '[role=' in selector:
                        normalized_selector = f'[role="{semantic_type}"]:has-text(/{normalized_text}\\(\\d+\\)/)'
                    else:
                        normalized_selector = f'{semantic_type}:has-text(/{normalized_text}\\(\\d+\\)/)'
                else:
                    normalized_selector = f'[role="{semantic_type}"]:has-text(/{normalized_text}\\(\\d+\\)/)'
            else:
                # No type specified, just text with regex
                normalized_selector = f':has-text(/{normalized_text}\\(\\d+\\)/)'
        else:
            # No count, keep as-is but preserve semantic type
            normalized_selector = selector
        
        return normalized_selector, semantic_type, normalized_text
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove special characters from filename that could cause issues"""
        # Replace problematic characters
        name = name.replace('[', '').replace(']', '')
        name = name.replace('"', '').replace("'", '')
        name = name.replace('#', '').replace('/', '_')
        name = name.replace('=', '_').replace(':', '_')
        name = name.replace('.', '_')
        name = name.replace(' ', '_')
        name = name.replace('(', '_').replace(')', '_')
        # Remove multiple underscores
        while '__' in name:
            name = name.replace('__', '_')
        return name
    
    def _record_discovered_element(self, element_name: str, selector: str, element_type: str = "unknown"):
        """Record newly discovered element for later addition to registry"""
        self.discovered_elements.append({
            "name": element_name,
            "selector": selector,
            "type": element_type,
            "url": self.current_url
        })
    
    async def _click_parent_or_sibling(self, selector):
        """Helper to click parent or sibling of target element using Playwright API"""
        try:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                raise Exception(f"Element not found: {selector}")
            
            # Try to click parent element
            parent_locator = locator.locator('..')
            if await parent_locator.count() > 0:
                await parent_locator.click(timeout=5000)
            else:
                # Fallback to clicking the element itself
                await locator.click(timeout=5000)
        except Exception as e:
            raise e
    
    async def _validate_element_visibility(self, selector: str, element_description: str = "") -> Dict[str, Any]:
        """Pre-click validation: Verify element exists and is visible"""
        validation_result = {
            "exists": False,
            "visible": False,
            "enabled": False,
            "text_content": "",
            "location": {},
            "screenshot_taken": False,
            "screenshot_file": None,
            "screenshot_size": None,
            "locator": None  # Store locator for reuse
        }
        
        try:
            locator = self.page.locator(selector).first
            validation_result["locator"] = locator  # Preserve locator reference
            
            # Check if element exists
            count = await locator.count()
            validation_result["exists"] = count > 0
            
            if not validation_result["exists"]:
                logger.warning(f"  ⚠️ Pre-validation: Element not found: {selector}")
                return validation_result
            
            # Check if visible
            validation_result["visible"] = await locator.is_visible()
            
            # Check if enabled
            validation_result["enabled"] = await locator.is_enabled()
            
            # Get text content
            try:
                validation_result["text_content"] = await locator.text_content()
            except:
                pass
            
            # Get location
            try:
                box = await locator.bounding_box()
                if box:
                    validation_result["location"] = {"x": box["x"], "y": box["y"]}
            except:
                pass
            
            # Highlight element for visual confirmation
            if validation_result["visible"]:
                try:
                    # CRITICAL: Scroll element into view first!
                    logger.info(f"  📍 Scrolling element into view...")
                    await locator.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)  # Let scroll animation complete
                    
                    # Add thick red outline
                    await locator.evaluate("el => el.style.outline = '5px solid red'")
                    await locator.evaluate("el => el.style.outlineOffset = '2px'")
                    await self.page.wait_for_timeout(1000)  # Wait for browser to render highlight
                    
                    # Take screenshot showing highlighted element
                    self.screenshot_counter += 1
                    safe_name = self._sanitize_filename(element_description)
                    filename = f"{self.screenshot_counter:03d}_pre_click_{safe_name}.png"
                    filepath = self.screenshots_dir / filename
                    
                    # Take full page screenshot (element is now in view)
                    await self.page.screenshot(path=str(filepath), full_page=False)
                    
                    # Store screenshot info
                    if filepath.exists():
                        size = filepath.stat().st_size
                        validation_result["screenshot_taken"] = True
                        validation_result["screenshot_file"] = filename
                        validation_result["screenshot_size"] = size
                        logger.info(f"  ✅ Pre-validation: Element visible and highlighted in screenshot: {filename} ({size} bytes)")
                    
                    # Keep highlight visible briefly, then remove
                    await self.page.wait_for_timeout(200)
                    await locator.evaluate("el => el.style.outline = ''")
                    await locator.evaluate("el => el.style.outlineOffset = ''")
                    
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not highlight element: {e}")
            
            return validation_result
            
        except Exception as e:
            logger.warning(f"  ⚠️ Pre-validation error: {e}")
            return validation_result
    
    async def _capture_post_click_screenshot(self, locator, element_name: str, clicked_text: str = "") -> Dict[str, Any]:
        """Generic post-click green screenshot - handles elements that stay or disappear"""
        result = {
            "screenshot_taken": False,
            "screenshot_file": None,
            "screenshot_size": None
        }
        
        try:
            # Check if original element still exists in DOM
            count = await locator.count()
            
            if count > 0 and await locator.is_visible():
                # CASE 1: Element still visible - highlight it green
                await locator.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(300)
                
                # Apply GREEN highlight
                await locator.evaluate("el => el.style.outline = '5px solid lime'")
                await locator.evaluate("el => el.style.outlineOffset = '2px'")
                await self.page.wait_for_timeout(1000)
                
                # Screenshot
                self.screenshot_counter += 1
                sanitized_element = self._sanitize_filename(element_name)
                filename = f"{self.screenshot_counter:03d}_post_click_{sanitized_element}.png"
                filepath = self.screenshots_dir / filename
                await self.page.screenshot(path=str(filepath))
                
                # Remove highlight
                await self.page.wait_for_timeout(200)
                await locator.evaluate("el => el.style.outline = ''")
                await locator.evaluate("el => el.style.outlineOffset = ''")
                
                result["screenshot_taken"] = True
                result["screenshot_file"] = filename
                result["screenshot_size"] = filepath.stat().st_size
                logger.info(f"  📸 ✅ Post-click screenshot: {filename} ({result['screenshot_size']} bytes)")
                logger.info(f"  🟢 Post-click GREEN highlight captured")
                
            else:
                # CASE 2: Element disappeared - find the result/echo in the page
                logger.info(f"  📍 Original element not in DOM, searching for result...")
                
                # Generic: Look for the clicked text in NEW locations (likely result indicators)
                search_text = clicked_text or element_name
                new_elements = self.page.locator(f'text="{search_text}"')
                element_found = False
                
                for i in range(await new_elements.count()):
                    elem = new_elements.nth(i)
                    try:
                        box = await elem.bounding_box()
                        # Heuristic: Top of page (y < 200) likely = result area (filter chips, headers)
                        if box and box['y'] < 200:
                            await elem.scroll_into_view_if_needed()
                            await self.page.wait_for_timeout(300)
                            
                            # Highlight result in green
                            await elem.evaluate("el => el.style.outline = '5px solid lime'")
                            await elem.evaluate("el => el.style.outlineOffset = '2px'")
                            await self.page.wait_for_timeout(1000)
                            
                            # Screenshot
                            self.screenshot_counter += 1
                            sanitized_element = self._sanitize_filename(element_name)
                            filename = f"{self.screenshot_counter:03d}_post_click_result_{sanitized_element}.png"
                            filepath = self.screenshots_dir / filename
                            await self.page.screenshot(path=str(filepath))
                            
                            # Remove highlight
                            await elem.evaluate("el => el.style.outline = ''")
                            await elem.evaluate("el => el.style.outlineOffset = ''")
                            
                            result["screenshot_taken"] = True
                            result["screenshot_file"] = filename
                            result["screenshot_size"] = filepath.stat().st_size
                            logger.info(f"  📸 ✅ Post-click result screenshot: {filename} ({result['screenshot_size']} bytes)")
                            logger.info(f"  🟢 Post-click GREEN highlight on result")
                            element_found = True
                            break
                    except:
                        continue
                
                # Fallback: Just screenshot the page state if result not found
                if not element_found:
                    self.screenshot_counter += 1
                    sanitized_element = self._sanitize_filename(element_name)
                    filename = f"{self.screenshot_counter:03d}_post_click_page_{sanitized_element}.png"
                    filepath = self.screenshots_dir / filename
                    await self.page.screenshot(path=str(filepath))
                    
                    result["screenshot_taken"] = True
                    result["screenshot_file"] = filename
                    result["screenshot_size"] = filepath.stat().st_size
                    logger.info(f"  📸 ✅ Post-click page screenshot: {filename} ({result['screenshot_size']} bytes)")
            
            return result
            
        except Exception as e:
            logger.warning(f"  ⚠️ Could not capture post-click screenshot: {e}")
            return result
    
    async def _validate_filter_applied(self, filter_name: str, initial_state: Dict) -> Dict[str, Any]:
        """Post-click validation: Verify filter was actually applied (for dropdown/filter clicks)"""
        validation_result = {
            "url_changed": False,
            "visual_indicator": False,
            "data_filtered": False,
            "count_changed": False,
            "initial_count": None,
            "new_count": None,
            "verdict": "UNKNOWN"
        }
        
        try:
            # Wait for any network activity to complete
            await self.page.wait_for_timeout(1500)
            
            # Check 1: URL changed
            new_url = self.page.url
            if new_url != initial_state.get("url"):
                validation_result["url_changed"] = True
                logger.info(f"  ✓ URL changed: {initial_state.get('url')} -> {new_url}")
            
            # Check 2: Look for visual indicator that filter is selected
            # Common patterns: checked checkbox, highlighted item, active state
            try:
                # Check for aria-checked or selected attributes
                selected_elements = await self.page.locator('[aria-checked="true"], [aria-selected="true"], .selected, .active').count()
                if selected_elements > 0:
                    validation_result["visual_indicator"] = True
                    logger.info(f"  ✓ Found {selected_elements} selected/active elements")
            except:
                pass
            
            # Check 3: Generic count changed (any element with count pattern)
            try:
                # Look for any count in format "Text(XXX)" or "Text (XXX)"
                # Generic: matches Cases(50), Products(100), Files(20), etc.
                count_locator = self.page.locator('text=/\\w+\\s*\\(\\d+\\)/')
                if await count_locator.count() > 0:
                    count_text = await count_locator.first.text_content()
                    match = re.search(r'\\((\\d+)\\)', count_text)
                    if match:
                        new_count = int(match.group(1))
                        initial_count = initial_state.get("count")
                        
                        validation_result["initial_count"] = initial_count
                        validation_result["new_count"] = new_count
                        
                        if initial_count and new_count != initial_count:
                            validation_result["count_changed"] = True
                            logger.info(f"  ✓ Count changed: {initial_count} -> {new_count}")
                        else:
                            logger.info(f"  ⚠️ Count unchanged: {new_count}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not check count: {e}")
            
            # Check 4: Data table content changed
            try:
                new_html = await self.page.content()
                if filter_name.upper() in new_html or filter_name.lower() in new_html:
                    validation_result["data_filtered"] = True
                    logger.info(f"  ✓ Filter name '{filter_name}' appears in page content")
            except:
                pass
            
            # Determine overall verdict
            validations_passed = sum([
                validation_result["url_changed"],
                validation_result["visual_indicator"],
                validation_result["data_filtered"],
                validation_result["count_changed"]
            ])
            
            if validations_passed >= 2:
                validation_result["verdict"] = "VERIFIED"
                logger.info(f"  ✅ Filter validation: VERIFIED ({validations_passed}/4 checks passed)")
            elif validations_passed == 1:
                validation_result["verdict"] = "LIKELY"
                logger.info(f"  ⚠️ Filter validation: LIKELY ({validations_passed}/4 checks passed)")
            else:
                validation_result["verdict"] = "FAILED"
                logger.warning(f"  ❌ Filter validation: FAILED (0/4 checks passed)")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"  ❌ Filter validation error: {e}")
            validation_result["verdict"] = "ERROR"
            return validation_result
    
    async def _describe_element(self, element) -> str:
        """Describe an element for LLM to understand its context and purpose"""
        try:
            tag = await element.evaluate("el => el.tagName")
            role = await element.get_attribute("role") or "none"
            aria_expanded = await element.get_attribute("aria-expanded")
            aria_selected = await element.get_attribute("aria-selected")
            text = (await element.text_content() or "")[:80]  # Increased for more context
            
            # Get element's own classes and data attributes
            class_name = await element.get_attribute("class") or ""
            data_attrs = await element.evaluate("""el => {
                const attrs = {};
                for (let attr of el.attributes) {
                    if (attr.name.startsWith('data-')) {
                        attrs[attr.name] = attr.value;
                    }
                }
                return JSON.stringify(attrs);
            }""")
            
            # Get location context (sidebar vs main content)
            box = await element.bounding_box()
            if box:
                x_pos = int(box['x'])
                y_pos = int(box['y'])
                
                # Determine semantic location
                if x_pos < 300:
                    location = "LEFT SIDEBAR (filter panel)"
                elif x_pos > 1100:
                    location = "RIGHT SIDEBAR"
                else:
                    # Main content area - differentiate tab area vs data table
                    if y_pos < 400:
                        location = "CENTER TOP (tab bar / header area)"
                    else:
                        location = "CENTER MAIN (data table area)"
                
                location_detail = f"{location} at x={x_pos}, y={y_pos}"
            else:
                location_detail = "HIDDEN/OFF-SCREEN"
            
            # Detect element type/purpose
            element_type = "unknown"
            if aria_expanded is not None:
                element_type = "FILTER ACCORDION/DROPDOWN (collapsible section)"
            elif role == "tab":
                element_type = "DATA TABLE TAB (switches table view)"
            elif "filter" in class_name.lower() or "filter" in data_attrs.lower():
                element_type = "FILTER CONTROL"
            elif "column" in class_name.lower() or "header" in class_name.lower():
                element_type = "TABLE COLUMN HEADER"
            elif tag == "BUTTON":
                element_type = "BUTTON"
            elif tag == "A":
                element_type = "LINK"
            
            # Get parent context for additional hints
            parent_info = await element.evaluate("""el => {
                const parent = el.parentElement;
                if (!parent) return 'no parent';
                const classes = parent.className || '';
                if (classes.includes('sidebar') || classes.includes('filter')) return 'inside sidebar/filter';
                if (classes.includes('tab')) return 'inside tab bar';
                if (classes.includes('table') || classes.includes('grid')) return 'inside data table';
                return classes.slice(0, 50) || 'no class';
            }""")
            
            # Check if it's interactive
            is_button = tag == "BUTTON"
            is_link = tag == "A"
            has_click_handler = await element.evaluate("el => typeof el.onclick === 'function' || el.hasAttribute('onclick')")
            
            description = f"""
TYPE: {element_type}
TAG: <{tag.lower()}>
ROLE: {role}
TEXT: "{text}"
LOCATION: {location_detail}
EXPANDABLE: {"YES (aria-expanded=" + aria_expanded + ")" if aria_expanded else "no"}
SELECTED: {"YES (active tab)" if aria_selected == "true" else "no"}
CLASSES: {class_name[:60] or "none"}
PARENT: {parent_info}
INTERACTIVE: {"button" if is_button else "link" if is_link else "has onclick" if has_click_handler else "maybe not clickable"}
"""
            return description.strip()
        except Exception as e:
            return f"Error describing element: {e}"
    
    async def _call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        """Quick LLM call for simple decisions (no tools)"""
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }]
                })
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
        except Exception as e:
            logger.error(f"  ❌ LLM call failed: {e}")
            return "0"  # Default to first element
    
    async def _llm_choose_element(self, candidates: List[Dict], selector: str) -> int:
        """Let LLM decide which element to click based on story context"""
        
        # Get story context safely
        story = getattr(self, 'story', '') or 'No specific story context available'
        
        # Format candidates for LLM
        candidates_text = ""
        for i, candidate in enumerate(candidates):
            candidates_text += f"\n--- Element {i} ---\n{candidate['description']}\n"
        
        prompt = f"""I'm trying to click: {selector}

The test story says: "{story}"

I found {len(candidates)} matching elements on the page:
{candidates_text}

Based on the story context, which element should I click?

Consider these rules:
- If story mentions "sidebar" or "side filter" → prefer elements in left sidebar (x < 400)
- If story mentions "expand" → prefer elements with aria-expanded attribute
- If story mentions "filter" or "dropdown" → prefer elements with role="button" in filter panels
- If story mentions "tab" → prefer elements with role="tab"
- Always prefer interactive elements (buttons, links) over static text/displays
- Avoid elements that are just displays or counters

Respond with ONLY the element number (0, 1, 2, etc.) - nothing else.
"""
        
        response = await self._call_llm_simple(prompt, max_tokens=10)
        
        # Parse response
        try:
            # Extract just the number
            import re
            match = re.search(r'\b(\d+)\b', response)
            if match:
                chosen = int(match.group(1))
                if 0 <= chosen < len(candidates):
                    logger.info(f"  🤖 LLM chose element {chosen} based on story context")
                    return chosen
                else:
                    logger.warning(f"  ⚠️ LLM chose {chosen} but valid range is 0-{len(candidates)-1}, using 0")
                    return 0
            else:
                logger.warning(f"  ⚠️ LLM response unclear: '{response}', using element 0")
                return 0
        except Exception as e:
            logger.warning(f"  ⚠️ Could not parse LLM response: {e}, using element 0")
            return 0
    
    async def _generate_final_selector(self, element) -> str:
        """
        Generate a simple, stable selector from the element that was clicked.
        This captures what the AI actually interacted with, not necessarily a "perfect" selector.
        
        The discovery metadata (tree_depth, element_type, etc.) will be used to generate
        Playwright helper functions that mimic the AI's tree climbing logic.
        
        Priority:
        1. role + aria attributes + text (semantic and stable)
        2. data-testid or stable id (purpose-built for testing)
        3. Simple text selector (stable, generic)
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
            
            # Strategy 1: Role + aria + text (BEST for accordions, tabs, buttons)
            if props['role'] and props['text']:
                if props['ariaExpanded'] is not None:
                    return f"{props['tag']}[role='{props['role']}'][aria-expanded]:has-text('{props['text']}')"
                elif props['ariaSelected'] is not None:
                    return f"{props['tag']}[role='{props['role']}'][aria-selected]:has-text('{props['text']}')"
                else:
                    return f"{props['tag']}[role='{props['role']}']:has-text('{props['text']}')"
            
            # Strategy 2: data-testid (EXCELLENT - purpose-built for testing)
            if props['dataTestId']:
                return f"[data-testid='{props['dataTestId']}']"
            
            # Strategy 3: name attribute (GOOD for form elements)
            if props['name'] and props['tag'] in ['input', 'select', 'textarea', 'button']:
                return f"{props['tag']}[name='{props['name']}']"
            
            # Strategy 4: Stable id (not dynamic)
            if props['id'] and not props['id'].startswith(('dropdown', 'checkbox', 'mui-', 'Mui')):
                # Check if ID looks stable (no numbers at the end)
                import re
                if not re.search(r'-\d+$', props['id']):
                    return f"#{props['id']}"
            
            # Strategy 5: Simple text selector (STABLE - captures what the AI saw)
            if props['text']:
                return f"text={props['text']}"
            
            # Last resort: tag + role (if has role but no text)
            if props['role']:
                return f"{props['tag']}[role='{props['role']}']"
            
            # Could not generate a good selector
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️ Could not generate final selector: {e}")
            return None
    
    def _track_discovery(self, element_name: str, original_query: str, final_selector: str, 
                         discovery_method: str, metadata: dict):
        """Track a successful discovery for later registry update"""
        discovery = {
            "name": element_name,
            "original_query": original_query,
            "final_selector": final_selector,
            "discovery_method": discovery_method,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.discoveries.append(discovery)
        logger.info(f"  📝 Tracked discovery: {element_name} via {discovery_method}")
        logger.info(f"     Query: {original_query}")
        logger.info(f"     Final: {final_selector}")
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute tool - Direct Playwright calls!"""
        
        if tool_name == "browser_navigate":
            url = tool_input['url']
            logger.info(f"Navigate: {url}")
            
            # Track current URL and page for element registry
            self.current_url = url
            
            # Execute
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(1000)  # Allow page to settle
            
            # Verify
            actual_url = self.page.url
            page_state = await self.page.evaluate("document.readyState")
            has_errors = await self.page.query_selector('[role="alert"], .error, #error') is not None
            
            # Check verification
            url_match = url in actual_url  # Allow for redirects
            page_loaded = page_state == 'complete'
            
            if url_match and page_loaded and not has_errors:
                logger.info(f"  ✅ Navigate verified: URL correct, page loaded")
                return f"✅ Navigated to {url} - Verified"
            else:
                issues = []
                if not url_match: issues.append(f"URL mismatch: expected {url}, got {actual_url}")
                if not page_loaded: issues.append(f"Page state: {page_state}")
                if has_errors: issues.append("Error elements detected on page")
                logger.warning(f"  ⚠️ Navigate completed but issues: {issues}")
                return f"⚠️ Navigated to {url} - Issues: {', '.join(issues)}"
        
        elif tool_name == "browser_snapshot":
            logger.info("Getting snapshot")
            
            # Get page summary instead of full HTML to save tokens
            title = await self.page.title()
            url = self.page.url
            html = await self.page.content()
            
            # Count interactive elements
            buttons = await self.page.locator("button").count()
            links = await self.page.locator("a").count()
            inputs = await self.page.locator("input").count()
            
            # Get visible text (first 1000 chars for context)
            body_text = await self.page.locator("body").inner_text()
            visible_text = body_text[:1000].strip() if body_text else "(no text)"
            
            summary = f"""Page Snapshot Summary:
- Title: {title}
- URL: {url}
- HTML size: {len(html):,} characters
- Interactive elements: {buttons} buttons, {links} links, {inputs} inputs
- Visible text preview: {visible_text}...
"""
            logger.info(f"  Snapshot: {len(html)} chars, {buttons} buttons, {links} links")
            return summary
        elif tool_name == "browser_click":
            selector = tool_input['selector']
            original_selector = selector
            logger.info(f"Click: {selector}")
            
            # Check element registry first for known good selectors
            registry_selector = self._check_element_registry(selector)
            optimized_selector_used = False
            if registry_selector:
                selector = registry_selector
                optimized_selector_used = True
                logger.info(f"  📋 Using selector from registry")
            
            # SMART AI DISAMBIGUATION: Always check element context, even for single matches
            # Verify element type matches story intent (accordion vs tab vs button)
            # Check parent if direct match isn't interactive or appropriate
            chosen_locator = None  # Track if we have a specific locator from AI disambiguation
            
            # TRY optimized selector first, with fallback to original query if it fails
            try:
                all_matches = await self.page.locator(selector).all()
            except Exception as selector_error:
                # Optimized selector failed, fall back to original query
                if optimized_selector_used and selector != original_selector:
                    logger.warning(f"  ⚠️ Optimized selector failed: {selector_error}")
                    logger.info(f"  ⚙️ Falling back to original query: {original_selector}")
                    selector = original_selector
                    optimized_selector_used = False
                    all_matches = await self.page.locator(selector).all()
                else:
                    raise selector_error
            
            # Continue with normal logic
            try:
                
                # Filter to only VISIBLE elements to avoid hidden elements
                visible_matches = []
                for match in all_matches:
                    if await match.is_visible():
                        visible_matches.append(match)  # Store visible elements only
                
                candidates = []
                
                if len(visible_matches) > 1:
                    logger.info(f"  🔍 Found {len(visible_matches)} visible matches for '{selector}' (of {len(all_matches)} total), asking LLM to choose...")
                    
                    # Describe each VISIBLE candidate for the LLM
                    for i, match in enumerate(visible_matches):
                        description = await self._describe_element(match)
                        candidates.append({
                            "index": i,
                            "element": match,
                            "description": description
                        })
                
                elif len(visible_matches) == 1:
                    # SINGLE MATCH: Check if it's appropriate for story context
                    logger.info(f"  🔍 Found 1 visible match, checking if it's the right element type...")
                    
                    match = visible_matches[0]
                    description = await self._describe_element(match)
                    
                    # Check if THIS SPECIFIC ELEMENT is interactive (not just description text)
                    # We need to check the element's actual properties, not search the description
                    element_props = await match.evaluate("""el => ({
                        tagName: el.tagName.toLowerCase(),
                        role: el.getAttribute('role'),
                        ariaExpanded: el.getAttribute('aria-expanded'),
                        ariaSelected: el.getAttribute('aria-selected'),
                        type: el.getAttribute('type'),
                        hasClickHandler: typeof el.onclick === 'function' || el.hasAttribute('onclick')
                    })""")
                    
                    # Element is interactive if it's a button, link, or has interactive roles/attributes
                    is_interactive = (
                        element_props['tagName'] in ['button', 'a', 'input', 'select'] or
                        element_props['role'] in ['button', 'tab', 'link', 'checkbox', 'radio'] or
                        element_props['ariaExpanded'] is not None or
                        element_props['ariaSelected'] is not None or
                        element_props['hasClickHandler']
                    )
                    
                    logger.info(f"  📋 Element check: tag={element_props['tagName']}, role={element_props['role']}, interactive={is_interactive}")
                    
                    candidates.append({
                        "index": 0,
                        "element": match,
                        "description": description
                    })
                    
                    # If element is NOT directly interactive, climb DOM tree to find interactive ancestors
                    if not is_interactive:
                        logger.info(f"  🔍 Element is not directly interactive (tag={element_props['tagName']}), climbing DOM tree...")
                        
                        # Climb up to 5 levels to find an interactive ancestor
                        current_elem = match
                        max_depth = 5
                        
                        for depth in range(1, max_depth + 1):
                            try:
                                parent_handle = await current_elem.evaluate_handle("el => el.parentElement")
                                if not parent_handle:
                                    logger.info(f"  🔚 Reached top of DOM at depth {depth}")
                                    break
                                
                                parent_elem = parent_handle.as_element()
                                if not parent_elem or not await parent_elem.is_visible():
                                    logger.info(f"  ⚠️ Parent at depth {depth} not visible")
                                    break
                                
                                # Check this ancestor's properties
                                parent_props = await parent_elem.evaluate("""el => ({
                                    tagName: el.tagName.toLowerCase(),
                                    role: el.getAttribute('role'),
                                    ariaExpanded: el.getAttribute('aria-expanded'),
                                    ariaSelected: el.getAttribute('aria-selected'),
                                    hasClickHandler: typeof el.onclick === 'function' || el.hasAttribute('onclick')
                                })""")
                                
                                # Check if this ancestor is interactive
                                ancestor_is_interactive = (
                                    parent_props['tagName'] in ['button', 'a', 'input', 'select'] or
                                    parent_props['role'] in ['button', 'tab', 'link', 'checkbox', 'radio'] or
                                    parent_props['ariaExpanded'] is not None or
                                    parent_props['ariaSelected'] is not None or
                                    parent_props['hasClickHandler']
                                )
                                
                                if ancestor_is_interactive:
                                    # Found an interactive ancestor!
                                    logger.info(f"  ✅ Found interactive ancestor at depth {depth}: tag={parent_props['tagName']}, role={parent_props['role']}, aria-expanded={parent_props['ariaExpanded']}")
                                    
                                    parent_desc = await self._describe_element(parent_elem)
                                    candidates.append({
                                        "index": len(candidates),
                                        "element": parent_elem,
                                        "description": parent_desc + f"\n(ANCESTOR at depth {depth}: <{parent_props['tagName']}> with role={parent_props['role']}, aria-expanded={parent_props['ariaExpanded']})"
                                    })
                                    # Found interactive ancestor, stop climbing
                                    break
                                else:
                                    logger.info(f"  ⬆️ Depth {depth}: tag={parent_props['tagName']}, role={parent_props['role']} - not interactive, continuing...")
                                    # Move to next level
                                    current_elem = parent_elem
                                    
                            except Exception as pe:
                                logger.debug(f"  Could not check ancestor at depth {depth}: {pe}")
                                break
                        
                        # If we climbed the tree but found no interactive ancestor
                        if len(candidates) == 1:
                            logger.warning(f"  ⚠️ Climbed {depth} levels, no interactive ancestor found. Element may not be clickable!")
                
                # If we have multiple candidates (multiple matches OR single match + parent), ask LLM
                if len(candidates) > 1:
                    logger.info(f"  🤖 Asking LLM to choose from {len(candidates)} candidates based on story context...")
                    
                    # Ask LLM to choose based on story context
                    best_index = await self._llm_choose_element(candidates, selector)
                    
                    # Use the chosen element directly
                    logger.info(f"  🎯 LLM chose element {best_index} of {len(candidates)}")
                    chosen_locator = candidates[best_index]["element"]
                
                elif len(candidates) == 1:
                    # Single candidate that looks appropriate, use it
                    logger.info(f"  ✅ Single appropriate element found")
                    chosen_locator = candidates[0]["element"]
                    
            except Exception as e:
                # If we can't check for multiple matches, continue with original selector
                logger.warning(f"  ⚠️ Could not check element context: {e}")
            
            # If we have a chosen locator from AI disambiguation, use it directly
            if chosen_locator:
                # Use the specific locator element instead of selector string
                # Smart retry strategy using the chosen locator
                strategies = [
                    {"desc": "direct click", "method": lambda: chosen_locator.click()},
                    {"desc": "exact coordinates", "method": lambda: chosen_locator.click()},
                    {"desc": "force click", "method": lambda: chosen_locator.click(force=True)},
                ]
                
                # Use chosen locator for validation (already visible, we filtered for it)
                element_name = original_selector.replace("text=", "").replace("_", " ")
                
                # CHECK ACTUAL ELEMENT ROLE: Detect if this is a tab by checking the element's role
                try:
                    element_role = await chosen_locator.get_attribute('role')
                    if element_role == 'tab':
                        is_tab_click = True
                        logger.info(f"  🎯 Tab detected (by element role='tab')")
                        
                        # Capture initial tab state if not already done
                        if not initial_tab_state:
                            try:
                                selected_tab = await self.page.locator('[role="tab"][aria-selected="true"]').text_content()
                                initial_tab_state = {
                                    "selected_tab": selected_tab.strip() if selected_tab else None,
                                    "target_element": original_selector
                                }
                                logger.info(f"  🎯 Current tab: {initial_tab_state['selected_tab']}")
                            except:
                                pass
                except Exception as e:
                    logger.debug(f"  Could not check element role: {e}")
                
                # Directly validate the chosen locator with screenshot
                try:
                    # Scroll into view and highlight
                    await chosen_locator.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)
                    await chosen_locator.evaluate("el => el.style.outline = '5px solid red'")
                    await chosen_locator.evaluate("el => el.style.outlineOffset = '2px'")
                    await self.page.wait_for_timeout(1000)
                    
                    # Take screenshot
                    self.screenshot_counter += 1
                    safe_name = self._sanitize_filename(element_name)
                    filename = f"{self.screenshot_counter:03d}_pre_click_{safe_name}.png"
                    filepath = self.screenshots_dir / filename
                    await self.page.screenshot(path=str(filepath), full_page=False)
                    
                    screenshot_taken = filepath.exists()
                    screenshot_size = filepath.stat().st_size if screenshot_taken else 0
                    
                    # Remove highlight
                    await self.page.wait_for_timeout(200)
                    await chosen_locator.evaluate("el => el.style.outline = ''")
                    await chosen_locator.evaluate("el => el.style.outlineOffset = ''")
                    
                    logger.info(f"  ✅ Pre-validation: Element visible and highlighted in screenshot: {filename} ({screenshot_size} bytes)")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not capture pre-click screenshot: {e}")
                    screenshot_taken = False
                    filename = None
                    screenshot_size = None
                
                validation_result = {
                    "exists": True,
                    "visible": await chosen_locator.is_visible(),
                    "enabled": await chosen_locator.is_enabled(),
                    "text_content": await chosen_locator.text_content() or "",
                    "location": {},
                    "screenshot_taken": screenshot_taken,
                    "screenshot_file": filename,
                    "screenshot_size": screenshot_size,
                    "locator": chosen_locator
                }
                pre_validation = validation_result
            else:
                # Normal selector-based flow
                # Smart retry strategy for complex UI elements (dropdowns, accordions, etc.)
                strategies = [
                    {"desc": "direct click", "method": lambda: self.page.click(selector)},
                    {"desc": "clickable parent/sibling", "method": lambda: self._click_parent_or_sibling(selector)},
                    {"desc": "force click", "method": lambda: self.page.click(selector, force=True)},
                ]
                
                # Try to find the element - be forgiving with selectors
                try:
                    await self.page.wait_for_selector(selector, state='visible', timeout=10000)
                except Exception as e:
                    # FALLBACK: If optimized selector failed, try original query
                    if optimized_selector_used and selector != original_selector:
                        logger.warning(f"  ⚠️ Optimized selector not found (likely dynamic CSS classes)")
                        logger.info(f"  ⚙️ Falling back to original query + discovery method: {original_selector}")
                        selector = original_selector
                        optimized_selector_used = False
                        await self.page.wait_for_selector(selector, state='visible', timeout=10000)
                    # If registry gave us a bad ID selector that failed, try the original query
                    elif selector.startswith("#") and not original_selector.startswith("#"):
                        logger.info(f"  Registry ID selector failed, trying original: {original_selector}")
                        selector = original_selector
                        await self.page.wait_for_selector(selector, state='visible', timeout=10000)
                    else:
                        # No fallback - let it fail naturally for AI to handle
                        logger.info(f"  Selector not found: {selector}")
                        raise e
                
                # PRE-CLICK VALIDATION: Verify element is visible and capture state
                element_name = original_selector.replace("text=", "").replace("_", " ")
                pre_validation = await self._validate_element_visibility(selector, element_name)
            
            if not pre_validation["exists"]:
                logger.error(f"  ❌ Pre-validation failed: Element does not exist")
                return f"❌ Click FAILED: {selector} - Element not found"
            
            if not pre_validation["visible"]:
                logger.warning(f"  ⚠️ Pre-validation warning: Element exists but not visible")
            
            # Store pre-click screenshot info for results
            if pre_validation["screenshot_taken"]:
                screenshot_msg = f"✅ Pre-click screenshot: {pre_validation['screenshot_file']} ({pre_validation['screenshot_size']} bytes)"
                self.pre_click_screenshots.append(screenshot_msg)
                logger.info(f"  📸 {screenshot_msg}")
            
            logger.info(f"  ✅ Pre-validation passed: Element exists and is {'visible' if pre_validation['visible'] else 'hidden'}")
            
            # Get preserved locator and clicked text for reuse
            preserved_locator = pre_validation.get("locator")
            clicked_text = pre_validation.get("text_content", "")
            
            # Capture initial state (for verification)
            initial_html = await self.page.content()
            initial_url = self.page.url
            
            # Capture initial count for validation (generic - any element with count)
            initial_count = None
            try:
                # Generic: matches Cases(50), Products(100), Files(20), etc.
                count_locator = self.page.locator('text=/\\w+\\s*\\(\\d+\\)/')
                if await count_locator.count() > 0:
                    count_text = await count_locator.first.text_content()
                    match = re.search(r'\\((\\d+)\\)', count_text)
                    if match:
                        initial_count = int(match.group(1))
                        logger.info(f"  📊 Initial count: {initial_count}")
            except:
                pass
            
            # ACCORDION DETECTION: Check if element is an accordion/expandable
            is_accordion = False
            initial_aria_expanded = None
            accordion_locator = None
            try:
                # Check if the element or its clickable parent has aria-expanded
                if preserved_locator:
                    accordion_locator = preserved_locator
                else:
                    accordion_locator = self.page.locator(selector)
                
                initial_aria_expanded = await accordion_locator.get_attribute("aria-expanded")
                if initial_aria_expanded is not None:
                    is_accordion = True
                    logger.info(f"  🎯 Accordion detected: aria-expanded={initial_aria_expanded}")
            except Exception as e:
                # Not an accordion or can't determine
                pass
            
            # Capture initial state for generic validation
            initial_text_count = 0
            initial_selected_count = 0
            try:
                if clicked_text:
                    initial_text_count = await self.page.locator(f'text="{clicked_text}"').count()
                
                initial_selected_count = await self.page.evaluate("""
                    () => {
                        const selected = document.querySelectorAll('[aria-selected="true"], [aria-checked="true"], [aria-pressed="true"], .selected, .active');
                        return selected.length;
                    }
                """)
            except:
                pass
            
            # TAB-SPECIFIC: Capture currently selected tab if this is a tab click
            initial_tab_state = None
            is_tab_click = False
            try:
                # Check if selector indicates tab interaction
                if '[role="tab"]' in original_selector or ':nth-child' in original_selector:
                    is_tab_click = True
                    # Get currently selected tab's text
                    selected_tab = await self.page.locator('[role="tab"][aria-selected="true"]').text_content()
                    initial_tab_state = {
                        "selected_tab": selected_tab.strip() if selected_tab else None,
                        "target_element": original_selector
                    }
                    logger.info(f"  🔖 Tab click detected - current tab: {initial_tab_state['selected_tab']}")
            except:
                pass
            
            initial_state = {
                "url": initial_url,
                "count": initial_count,
                "text_count": initial_text_count,
                "selected_elements": initial_selected_count,
                "tab_state": initial_tab_state,
                "is_tab_click": is_tab_click
            }
            
            # Updated strategies using preserved locator for better reliability
            async def click_with_preserved_locator():
                """Strategy 1: Direct click using preserved locator"""
                if preserved_locator:
                    await preserved_locator.click()
                else:
                    await self.page.click(selector)
            
            async def click_at_exact_coordinates():
                """Strategy 2: Click at exact element center coordinates"""
                if preserved_locator:
                    box = await preserved_locator.bounding_box()
                    if box:
                        center_x = box['x'] + box['width'] / 2
                        center_y = box['y'] + box['height'] / 2
                        await self.page.mouse.click(center_x, center_y)
                    else:
                        await self._click_parent_or_sibling(selector)
                else:
                    await self._click_parent_or_sibling(selector)
            
            async def force_click_with_preserved():
                """Strategy 3: Force click using preserved locator"""
                if preserved_locator:
                    await preserved_locator.click(force=True)
                else:
                    await self.page.click(selector, force=True)
            
            strategies = [
                {"desc": "direct click", "method": click_with_preserved_locator},
                {"desc": "exact coordinates", "method": click_at_exact_coordinates},
                {"desc": "force click", "method": force_click_with_preserved},
            ]
            
            last_error = None
            for i, strategy in enumerate(strategies):
                try:
                    logger.info(f"  Trying strategy {i+1}: {strategy['desc']}")
                    await strategy["method"]()
                    
                    # TAB-SPECIFIC: Wait longer for tab content to load
                    if is_tab_click:
                        await self.page.wait_for_timeout(2000)  # 2 seconds for tab content
                        try:
                            # Wait for network to settle after tab switch
                            await self.page.wait_for_load_state('networkidle', timeout=5000)
                        except:
                            pass  # Continue if networkidle times out
                    else:
                        await self.page.wait_for_timeout(1000)
                    
                    # Verify click result with multiple checks
                    new_html = await self.page.content()
                    new_url = self.page.url
                    
                    # Check what changed
                    dom_changed = new_html != initial_html
                    url_changed = new_url != initial_url
                    dom_grew = len(new_html) > len(initial_html) * 1.05  # 5% growth
                    
                    # ACCORDION VALIDATION: Check if accordion expanded
                    aria_expanded = False
                    accordion_opened = False
                    try:
                        if is_accordion and accordion_locator:
                            # Get current aria-expanded state
                            current_aria_expanded = await accordion_locator.get_attribute('aria-expanded')
                            
                            if current_aria_expanded == 'true':
                                aria_expanded = True
                                
                                # Check if accordion actually opened (state changed from false to true)
                                if initial_aria_expanded == 'false' and current_aria_expanded == 'true':
                                    accordion_opened = True
                                    logger.info(f"  ✅ Accordion expanded: {initial_aria_expanded} → {current_aria_expanded}")
                                elif initial_aria_expanded == 'true' and current_aria_expanded == 'false':
                                    logger.info(f"  ℹ️ Accordion collapsed: {initial_aria_expanded} → {current_aria_expanded}")
                            else:
                                logger.warning(f"  ⚠️ Accordion did NOT expand: aria-expanded still {current_aria_expanded}")
                        else:
                            # Generic check for any aria-expanded elements
                            if preserved_locator and await preserved_locator.count() > 0:
                                attr = await preserved_locator.get_attribute('aria-expanded')
                                if attr == 'true':
                                    aria_expanded = True
                                else:
                                    # Check parent elements
                                    parent_locator = preserved_locator.locator('..')
                                    if await parent_locator.count() > 0:
                                        attr = await parent_locator.get_attribute('aria-expanded')
                                        aria_expanded = (attr == 'true')
                    except Exception as e:
                        logger.debug(f"  Could not check aria-expanded: {e}")
                    
                    # Generic check: Did any element get selected/activated?
                    state_changed = False
                    try:
                        # Count elements with selection/active state
                        selected_elements = await self.page.evaluate("""
                            () => {
                                const selected = document.querySelectorAll('[aria-selected="true"], [aria-checked="true"], [aria-pressed="true"], .selected, .active');
                                return selected.length;
                            }
                        """)
                        
                        # Check if clicked text now appears in new locations (result indicators)
                        if clicked_text:
                            new_text_count = await self.page.locator(f'text="{clicked_text}"').count()
                            initial_text_count = initial_state.get('text_count', 0)
                            if new_text_count > initial_text_count:
                                state_changed = True
                        
                        # Store for comparison
                        if 'selected_elements' not in initial_state:
                            initial_state['selected_elements'] = 0
                        
                        if selected_elements > initial_state.get('selected_elements', 0):
                            state_changed = True
                            
                    except:
                        pass
                    
                    # Determine if click was successful (stricter validation)
                    # For strategy 1: require strong evidence
                    # For strategy 2+: allow weaker evidence since element might be tricky
                    if i == 0:
                        # Strategy 1: Require URL change OR significant DOM growth OR state change OR accordion opened
                        click_succeeded = url_changed or dom_grew or state_changed or aria_expanded or accordion_opened
                    else:
                        # Strategy 2+: Allow DOM change as fallback
                        click_succeeded = url_changed or dom_grew or aria_expanded or accordion_opened or state_changed or dom_changed
                    
                    if click_succeeded:
                        reasons = []
                        if url_changed: reasons.append("page navigated")
                        if dom_grew: reasons.append(f"content expanded ({len(new_html) - len(initial_html)} bytes)")
                        if accordion_opened: reasons.append("accordion expanded (aria-expanded: false→true)")
                        elif aria_expanded: reasons.append("dropdown/section expanded")
                        if state_changed: reasons.append("element state changed")
                        if dom_changed and not reasons: reasons.append("DOM changed")
                        
                        logger.info(f"  ✅ Click verified: {', '.join(reasons)}")
                        
                        # POST-CLICK GREEN SCREENSHOT: Generic handler for elements that stay or disappear
                        if preserved_locator:
                            post_click_result = await self._capture_post_click_screenshot(
                                preserved_locator, 
                                element_name,
                                clicked_text
                            )
                            
                            # Store post-click screenshot info
                            if post_click_result["screenshot_taken"]:
                                screenshot_msg = f"✅ Post-click screenshot: {post_click_result['screenshot_file']} ({post_click_result['screenshot_size']} bytes)"
                                self.pre_click_screenshots.append(screenshot_msg)
                        
                        # TRACK DISCOVERY: If this was found via tree climbing or AI disambiguation
                        if chosen_locator:
                            try:
                                logger.info(f"  📝 Tracking discovery metadata...")
                                
                                # Generate final working selector from the element that was actually clicked
                                final_selector = await self._generate_final_selector(chosen_locator)
                                
                                if final_selector:
                                    # Determine discovery method based on what happened
                                    discovery_method = "unknown"
                                    metadata = {}
                                    
                                    # Check if tree climbing was used
                                    if len(candidates) > 1 or (len(candidates) == 1 and candidates[0].get("index") == 1):
                                        # Multiple candidates or parent was chosen
                                        if "PARENT" in candidates[-1].get("description", "").upper() or \
                                           "ANCESTOR" in candidates[-1].get("description", "").upper():
                                            discovery_method = "tree_climbing"
                                            # Try to extract tree depth from description
                                            desc = candidates[-1].get("description", "")
                                            import re
                                            depth_match = re.search(r'depth\s+(\d+)', desc, re.IGNORECASE)
                                            if depth_match:
                                                metadata["tree_depth"] = int(depth_match.group(1))
                                            metadata["relationship"] = "parent" if "PARENT" in desc.upper() else "ancestor"
                                        else:
                                            discovery_method = "ai_disambiguation"
                                            metadata["candidates_count"] = len(candidates)
                                            metadata["chosen_index"] = best_index if 'best_index' in locals() else 0
                                    
                                    # Track the discovery
                                    self._track_discovery(
                                        element_name=element_name,
                                        original_query=original_selector,
                                        final_selector=final_selector,
                                        discovery_method=discovery_method,
                                        metadata=metadata
                                    )
                                else:
                                    logger.warning(f"  ⚠️ Could not generate final selector for tracking")
                            
                            except Exception as e:
                                logger.warning(f"  ⚠️ Failed to track discovery: {e}")
                        
                        # POST-CLICK VALIDATION: Tab-specific validation first
                        if is_tab_click and initial_tab_state:
                            try:
                                logger.info(f"  🔍 Running tab-specific validation...")
                                # Check if the target element (or text) is now selected
                                tab_switch_verified = False
                                new_selected_tab = None
                                
                                # Get currently selected tab
                                try:
                                    new_selected_tab = await self.page.locator('[role="tab"][aria-selected="true"]').text_content()
                                    new_selected_tab = new_selected_tab.strip() if new_selected_tab else None
                                except:
                                    pass
                                
                                # Check if tab actually changed
                                if new_selected_tab and new_selected_tab != initial_tab_state.get("selected_tab"):
                                    tab_switch_verified = True
                                    logger.info(f"  ✅ Tab switched: '{initial_tab_state.get('selected_tab')}' → '{new_selected_tab}'")
                                    reasons.append(f"tab switched to '{new_selected_tab}'")
                                    
                                    # SCROLL TO CONTENT AREA: After tab switch, scroll down to show data table
                                    try:
                                        logger.info(f"  📊 Scrolling to tab content area...")
                                        # Wait for content to load (data tables can be slow)
                                        await self.page.wait_for_timeout(2000)
                                        
                                        # Scroll down to show the content area (data table is usually below tabs)
                                        await self.page.evaluate("window.scrollBy(0, 400)")
                                        await self.page.wait_for_timeout(500)  # Let scroll animation complete
                                        
                                        # Take additional screenshot showing the content
                                        self.screenshot_counter += 1
                                        safe_name = self._sanitize_filename(f"{new_selected_tab}_content")
                                        filename = f"{self.screenshot_counter:03d}_tab_content_{safe_name}.png"
                                        filepath = self.screenshots_dir / filename
                                        await self.page.screenshot(path=str(filepath), full_page=False)
                                        
                                        screenshot_size = filepath.stat().st_size if filepath.exists() else 0
                                        logger.info(f"  📊 Tab content screenshot: {filename} ({screenshot_size} bytes)")
                                        
                                        # Store for results
                                        screenshot_msg = f"✅ Tab content screenshot: {filename} ({screenshot_size} bytes)"
                                        self.pre_click_screenshots.append(screenshot_msg)
                                        
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ Could not capture tab content: {e}")
                                elif clicked_text and new_selected_tab and clicked_text in new_selected_tab:
                                    # Clicked text appears in selected tab (handles dynamic counts)
                                    tab_switch_verified = True
                                    logger.info(f"  ✅ Tab switched: target '{clicked_text}' is now selected")
                                    reasons.append(f"tab switched to '{new_selected_tab}'")
                                    
                                    # SCROLL TO CONTENT AREA: After tab switch, scroll down to show data table
                                    try:
                                        logger.info(f"  📊 Scrolling to tab content area...")
                                        # Wait for content to load (data tables can be slow)
                                        await self.page.wait_for_timeout(2000)
                                        
                                        # Scroll down to show the content area (data table is usually below tabs)
                                        await self.page.evaluate("window.scrollBy(0, 400)")
                                        await self.page.wait_for_timeout(500)  # Let scroll animation complete
                                        
                                        # Take additional screenshot showing the content
                                        self.screenshot_counter += 1
                                        safe_name = self._sanitize_filename(f"{clicked_text}_content")
                                        filename = f"{self.screenshot_counter:03d}_tab_content_{safe_name}.png"
                                        filepath = self.screenshots_dir / filename
                                        await self.page.screenshot(path=str(filepath), full_page=False)
                                        
                                        screenshot_size = filepath.stat().st_size if filepath.exists() else 0
                                        logger.info(f"  📊 Tab content screenshot: {filename} ({screenshot_size} bytes)")
                                        
                                        # Store for results
                                        screenshot_msg = f"✅ Tab content screenshot: {filename} ({screenshot_size} bytes)"
                                        self.pre_click_screenshots.append(screenshot_msg)
                                        
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ Could not capture tab content: {e}")
                                else:
                                    logger.warning(f"  ⚠️ Tab validation: current tab still '{new_selected_tab}', expected change from '{initial_tab_state.get('selected_tab')}'")
                                    # Override click_succeeded if tab didn't actually switch
                                    if not url_changed and not dom_grew:
                                        click_succeeded = False
                                        logger.error(f"  ❌ Tab switch FAILED - page content unchanged")
                                        continue  # Try next strategy
                            except Exception as e:
                                logger.warning(f"  ⚠️ Tab validation error: {e}")
                        
                        # POST-CLICK VALIDATION: Generic validation for any click that might filter/change data
                        filter_validation = None
                        # Always try validation - it will gracefully handle if not applicable
                        if not is_tab_click:  # Skip filter validation for tab clicks
                            logger.info(f"  🔍 Running post-click validation...")
                            filter_name = original_selector.replace("text=", "")
                            filter_validation = await self._validate_filter_applied(filter_name, initial_state)
                            
                            if filter_validation["verdict"] == "VERIFIED":
                                reasons.append(f"filter verified ({filter_validation['new_count']} items)")
                            elif filter_validation["verdict"] == "LIKELY":
                                reasons.append("filter likely applied")
                            elif filter_validation["verdict"] == "FAILED":
                                reasons.append("⚠️ filter validation failed")
                        
                        # Record if this was a newly discovered selector (not from registry)
                        if not registry_selector:
                            self._record_discovered_element(original_selector, selector, "button")
                            logger.info(f"  📝 Recorded new element for registry update")
                        
                        # Build result message with validation details
                        result_msg = f"✅ Clicked {selector} - Verified: {', '.join(reasons)}"
                        
                        if filter_validation and filter_validation["verdict"] in ["VERIFIED", "LIKELY"]:
                            result_msg += f" | Count: {filter_validation['initial_count']} → {filter_validation['new_count']}"
                        
                        return result_msg
                    
                    # First strategy always gets a chance, others need verification
                    if i == 0 and not click_succeeded:
                        logger.warning(f"  ⚠️ Click executed but no obvious result detected, trying next strategy...")
                        continue
                    
                except Exception as e:
                    last_error = e
                    logger.info(f"  Strategy {i+1} failed: {str(e)[:100]}")
                    continue
            
            # If all strategies tried and none verified
            logger.error(f"  ❌ All click strategies failed to produce expected result")
            return f"❌ Click FAILED: {selector} - No strategies produced verifiable result"
        
        elif tool_name == "browser_fill":
            selector = tool_input['selector']
            text = tool_input['text']
            logger.info(f"Fill: {selector} = {text}")
            
            # Execute
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            
            # Check if field is editable
            is_readonly = await self.page.evaluate(f"""
                const el = document.querySelector('{selector}');
                el ? (el.readOnly || el.disabled) : true
            """)
            
            if is_readonly:
                logger.warning(f"  ⚠️ Field {selector} is readonly or disabled")
                return f"⚠️ Fill FAILED: {selector} is readonly/disabled"
            
            await self.page.fill(selector, text)
            await self.page.wait_for_timeout(500)
            
            # Verify
            actual_value = await self.page.input_value(selector)
            
            if actual_value == text:
                logger.info(f"  ✅ Fill verified: value matches")
                return f"✅ Filled {selector} = '{text}' - Verified"
            else:
                logger.warning(f"  ⚠️ Fill mismatch: expected '{text}', got '{actual_value}'")
                return f"⚠️ Filled {selector} - Expected '{text}', got '{actual_value}'"
        
        elif tool_name == "browser_screenshot":
            self.screenshot_counter += 1
            name = tool_input.get('name', 'screenshot')
            filename = f"{self.screenshot_counter:03d}_{name}.png"
            filepath = self.screenshots_dir / filename
            logger.info(f"Screenshot: {filepath}")
            
            # Wait for page to be ready
            await self.page.wait_for_load_state('domcontentloaded')
            await self.page.wait_for_timeout(500)  # Allow rendering
            
            # Capture page metadata for context
            try:
                title = await self.page.title()
                url = self.page.url
                
                # Check for any count to include in filename/metadata
                # Generic: matches Cases(50), Products(100), Files(20), etc.
                count_locator = self.page.locator('text=/\\w+\\s*\\(\\d+\\)/')
                count_info = ""
                if await count_locator.count() > 0:
                    count_text = await count_locator.first.text_content()
                    match = re.search(r'\\((\\d+)\\)', count_text)
                    if match:
                        count_value = match.group(1)
                        count_info = f" | {count_value} items"
                
                logger.info(f"  📸 {title} | {url}{count_info}")
            except:
                pass
            
            # Execute
            await self.page.screenshot(path=str(filepath), full_page=False)
            
            # Verify
            if not filepath.exists():
                logger.error(f"  ❌ Screenshot file not created")
                return f"❌ Screenshot FAILED: file not created"
            
            size = filepath.stat().st_size
            min_size = 5000  # 5KB minimum for valid screenshot
            
            if size < min_size:
                logger.warning(f"  ⚠️ Screenshot very small ({size} bytes), may be blank")
                return f"⚠️ Screenshot saved: {filename} ({size} bytes) - WARNING: file too small, may be blank"
            else:
                logger.info(f"  ✅ Screenshot verified: {size} bytes")
                return f"✅ Screenshot saved: {filename} ({size} bytes)"
        
        elif tool_name == "browser_evaluate":
            code = tool_input['code']
            logger.info("Evaluating JS")
            
            # Auto-wrap code in function if needed
            if 'return' in code and not code.strip().startswith('(') and not code.strip().startswith('function'):
                wrapped_code = f"(() => {{ {code} }})()"
            else:
                wrapped_code = code
            
            # Execute with error handling
            try:
                result = await self.page.evaluate(wrapped_code)
                
                # Verify execution
                if result is None:
                    logger.info(f"  ✅ JS executed, returned null/undefined")
                    return f"✅ JS executed successfully - Result: null"
                else:
                    logger.info(f"  ✅ JS executed, returned {type(result).__name__}")
                    return f"✅ JS executed successfully - Result: {json.dumps(result, indent=2)}"
                    
            except Exception as js_error:
                logger.error(f"  ❌ JS execution failed: {str(js_error)}")
                return f"❌ JS execution FAILED: {str(js_error)}"
        
        return f"Unknown tool: {tool_name}"
    
    def get_tools(self) -> List[Dict]:
        """Tool definitions for Bedrock"""
        return [
            {
                "toolSpec": {
                    "name": "browser_navigate",
                    "description": "Navigate to a URL",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"url": {"type": "string"}},
                            "required": ["url"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_snapshot",
                    "description": "Get a summary of the current page including title, URL, element counts, and visible text preview",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "browser_click",
                    "description": "Click an element. PREFERRED: Use element descriptions from the page (e.g., 'Study dropdown', 'Continue button', 'Search button'). ALTERNATIVE: Use CSS selectors (e.g., '#id', '.class', 'button') or text selectors (e.g., 'text=Continue'). Do NOT use jQuery syntax like :contains().",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"selector": {"type": "string", "description": "CSS selector or text=Value for Playwright"}},
                            "required": ["selector"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_fill",
                    "description": "Fill input field",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "selector": {"type": "string"},
                                "text": {"type": "string"}
                            },
                            "required": ["selector", "text"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_screenshot",
                    "description": "Take screenshot",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_evaluate",
                    "description": "Execute JavaScript",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"code": {"type": "string"}},
                            "required": ["code"]
                        }
                    }
                }
            }
        ]
    
    async def execute_story(self, story: str, max_iterations: int = 50) -> Dict[str, Any]:
        """
        AGENTIC LOOP - LLM makes real-time decisions
        """
        # Store story for AI disambiguation
        self.story = story
        
        logger.info(f"Execution {self.execution_id} starting")
        logger.info(f"Story: {story}")
        
        await self.start_browser()
        
        messages = [{
            "role": "user",
            "content": [{"text": f"Execute this test scenario:\n\n{story}\n\nUse browser tools. Take screenshots at key steps."}]
        }]
        
        results = {
            "execution_id": self.execution_id,
            "story": story,
            "actions_taken": [],
            "screenshots": [],
            "status": "running",
            "started_at": time.time()
        }
        
        system_prompt = """You are a QA automation agent. Use browser tools to execute tests.

SMART ELEMENT SELECTION:
- Use simple text= selectors - the system intelligently validates each element
- Even for single matches, you'll see descriptions to verify it's the RIGHT element
- System checks: Is it clickable? Is it a tab/accordion/button? Is parent better?
- Descriptions show: LOCATION, TYPE, and ATTRIBUTES
- Match story keywords to element attributes:
  * "sidebar filter" → LOCATION: "LEFT SIDEBAR", TYPE: "FILTER ACCORDION"
  * "tab" → TYPE: "DATA TABLE TAB", ROLE: tab
  * "expand/dropdown" → EXPANDABLE: "YES" (has aria-expanded)
- If element isn't interactive, system checks parent automatically
- Be specific in stories: "click sidebar filter dropdown" vs "click tab"

After navigating, use browser_snapshot() to see the page.
Use browser_evaluate() to find selectors when needed.
Take screenshots at important steps.
Be adaptive and methodical."""
        
        # AGENTIC LOOP
        for iteration in range(1, max_iterations + 1):
            logger.info(f"Iteration {iteration}/{max_iterations}")
            
            try:
                response = self.bedrock.converse(
                    modelId=self.model_id,
                    messages=messages,
                    system=[{"text": system_prompt}],
                    toolConfig={"tools": self.get_tools()},
                    inferenceConfig={"maxTokens": 4096, "temperature": 0.0}
                )
                
                stop_reason = response['stopReason']
                
                if stop_reason == 'tool_use':
                    # LLM wants to use tools
                    tool_uses = [
                        block['toolUse']
                        for block in response['output']['message']['content']
                        if 'toolUse' in block
                    ]
                    
                    logger.info(f"LLM requested {len(tool_uses)} tools")
                    
                    tool_results = []
                    for tool_use in tool_uses:
                        tool_name = tool_use['name']
                        tool_input = tool_use['input']
                        
                        # Execute directly with Playwright!
                        result_text = await self.execute_tool(tool_name, tool_input)
                        
                        # Enhanced action logging with metadata
                        action_entry = {
                            "iteration": iteration,
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result_text
                        }
                        
                        # Add page context for click actions
                        if tool_name == "browser_click":
                            try:
                                action_entry["page_url"] = self.page.url
                                action_entry["page_title"] = await self.page.title()
                            except:
                                pass
                        
                        results["actions_taken"].append(action_entry)
                        
                        if tool_name == "browser_screenshot":
                            results["screenshots"].append(result_text)
                        
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use['toolUseId'],
                                "content": [{"text": result_text}]
                            }
                        })
                    
                    messages.append(response['output']['message'])
                    messages.append({"role": "user", "content": tool_results})
                
                elif stop_reason == 'end_turn':
                    final_text = response['output']['message']['content'][0]['text']
                    results["status"] = "completed"
                    results["summary"] = final_text
                    results["completed_at"] = time.time()
                    results["duration"] = results["completed_at"] - results["started_at"]
                    break
                
                elif stop_reason == 'max_tokens':
                    messages.append(response['output']['message'])
                    messages.append({"role": "user", "content": [{"text": "Continue."}]})
                
                else:
                    results["status"] = "error"
                    results["error"] = f"Unexpected stop: {stop_reason}"
                    break
            
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                results["status"] = "error"
                results["error"] = str(e)
                break
        
        else:
            results["status"] = "timeout"
            results["error"] = f"Max iterations reached"
        
        # Save discovered elements if test passed
        if results['status'] == 'completed' and self.discovered_elements:
            logger.info(f"💾 Saving {len(self.discovered_elements)} discovered elements to registry")
            domain, page = self._get_domain_and_page()
            if domain and page:
                for elem in self.discovered_elements:
                    try:
                        element_data = {
                            "selector": elem['selector'],
                            "type": elem['type'],
                            "description": f"Discovered during test {self.execution_id}"
                        }
                        self.element_registry.add_element(
                            domain, page, elem['name'], 
                            element_data, self.execution_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add element {elem['name']}: {e}")
        
        # Add pre-click validation screenshots to results
        if self.pre_click_screenshots:
            logger.info(f"📸 Adding {len(self.pre_click_screenshots)} pre-click screenshots to results")
            results["screenshots"] = self.pre_click_screenshots + results["screenshots"]
        
        # Add discovery metadata to results
        if self.discoveries:
            logger.info(f"📝 Saving {len(self.discoveries)} discoveries to results")
            results["discoveries"] = self.discoveries
            
            # Also save to a separate JSON file for reference
            try:
                project_root = Path(__file__).parent.parent
                discoveries_dir = project_root / 'storage' / 'discoveries'
                discoveries_dir.mkdir(parents=True, exist_ok=True)
                
                discovery_file = discoveries_dir / f"{self.execution_id}_discoveries.json"
                with open(discovery_file, 'w') as f:
                    json.dump({
                        "execution_id": self.execution_id,
                        "story": story,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "discoveries": self.discoveries
                    }, f, indent=2)
                
                logger.info(f"  💾 Discovery metadata saved to: {discovery_file}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not save discovery file: {e}")
        
        await self.close_browser()
        logger.info(f"Finished: {results['status']}")
        return results
