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
from utils.xpath_builder import XPathBuilder

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
        
        # Story step tracking
        self.current_step_number = 0
        self.parsed_steps = {}  # {step_number: {metadata}}
        
        # Element Registry for cached selectors - use absolute path from project root
        self.element_registry = get_registry(str(project_root / "element_maps"))
        self.current_url = ""
        self.discovered_elements = []  # Track newly discovered elements
        self.last_clicked_element = None  # ✨ Track last clicked for parent-child relationships
        self.pre_click_screenshots = []  # Track pre-click validation screenshots
        self.story = ""  # Initialize story for AI disambiguation
        self.discoveries = []  # Track discovery metadata (query + final selector + method)
    
    def parse_story_metadata(self, story: str):
        """Parse story once and extract metadata for each step"""
        import re
        
        logger.info("📖 Parsing story metadata...")
        self.story = story
        self.parsed_steps = {}
        
        # Split into steps
        lines = story.split('\n')
        for line in lines:
            line = line.strip()
            if not line or not line.startswith('Step'):
                continue
            
            # Extract step number: "Step 4:" or "4."
            step_match = re.match(r'Step\s+(\d+)[\.:)]?\s*(.+)', line, re.IGNORECASE)
            if not step_match:
                continue
            
            step_num = int(step_match.group(1))
            step_text = step_match.group(2).lower()
            
            # Extract metadata from step text
            metadata = {"text": step_text}
            
            # Detect TYPE
            if "tab" in step_text:
                metadata["type"] = "tab"
            elif "accordion" in step_text or "expand" in step_text:
                metadata["type"] = "accordion"
            elif "checkbox" in step_text or "check box" in step_text:
                metadata["type"] = "checkbox"
            
            # Detect LOCATION
            if "sidebar" in step_text or "filter panel" in step_text or "left" in step_text:
                metadata["location"] = "sidebar"
            elif "table" in step_text or "bottom" in step_text or "main" in step_text or "content" in step_text:
                metadata["location"] = "table"
            
            # Detect PARENT/NESTED
            if "nested" in step_text or "inner" in step_text or "within" in step_text or "inside" in step_text:
                metadata["nested"] = True
                
            # Extract PARENT HINT from context (e.g., "in the Diagnosis section")
            parent_patterns = [
                r'in (?:the )?(\w+)(?: section| accordion| area)?',
                r'inside (?:the )?(\w+)',
                r'within (?:the )?(\w+)',
                r'under (?:the )?(\w+)'
            ]
            for pattern in parent_patterns:
                match = re.search(pattern, step_text)
                if match:
                    parent_hint = match.group(1).lower()
                    # Exclude common words
                    if parent_hint not in ['the', 'a', 'an', 'this', 'that', 'expanded', 'collapsed']:
                        metadata["parent_hint"] = parent_hint
                        break
            
            # Detect DEPTH preference
            if "top" in step_text or "main" in step_text or "primary" in step_text:
                metadata["prefer_depth"] = 0  # Top-level
            elif "first level" in step_text:
                metadata["prefer_depth"] = 1
            elif "second level" in step_text:
                metadata["prefer_depth"] = 2
            
            self.parsed_steps[step_num] = metadata
            logger.info(f"  Step {step_num}: {metadata}")
        
        logger.info(f"✅ Parsed {len(self.parsed_steps)} steps with metadata")
        
    async def start_browser(self):
        """Launch Playwright browser"""
        logger.info("Launching Chromium browser...")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        # Set larger viewport to ensure all tabs and elements are visible
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        
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
            from urllib.parse import urlparse
            
            # Parse URL to get path
            parsed = urlparse(current_url)
            path = parsed.path.strip('/')
            
            # Try hash routing first (e.g., /#/explore)
            match = re.search(r'/#/(\w+)', current_url)
            if match:
                page = match.group(1)
            elif path:
                # Extract first segment of path (e.g., /explore/something -> explore)
                segments = path.split('/')
                page = segments[0] if segments[0] else "home"
            else:
                page = "home"
            
            logger.debug(f"  🔍 Page detection: URL={current_url}, path={path}, page={page}")
            return domain, page
        except Exception as e:
            logger.warning(f"Error getting domain/page: {e}")
            return None, None

    def _check_element_registry(self, element_description: str) -> str:
        """Check if element exists in registry using current step metadata. Returns None if not found (LLM will discover)."""
        try:
            domain, page = self._get_domain_and_page()
            logger.info(f"  🔍 Registry check: element='{element_description}', domain={domain}, page={page}")
            if not domain or not page:
                logger.warning(f"  ⚠️ Registry check skipped: domain or page not determined")
                return None
            
            # Get current step metadata
            step_metadata = self.parsed_steps.get(self.current_step_number, {})
            logger.info(f"  📖 Step {self.current_step_number} metadata: {step_metadata}")
            
            # Try exact match first
            element = self.element_registry.get_element(domain, page, element_description)
            if element:
                selector = element.get('selector')
                logger.info(f"  ✅ Exact match: {element_description} -> {selector}")
                self.element_registry.update_usage(domain, page, element_description)
                return selector
            
            # Load element map for metadata-based matching
            element_map = self.element_registry.load_map(domain, page)
            logger.info(f"  📂 Element map: {len(element_map.get('elements', {})) if element_map else 0} elements")
            if not element_map:
                return None
            
            # Extract clean text from selector
            import re
            clean_text = element_description.lower()
            if clean_text.startswith('text='):
                clean_text = clean_text[5:]
            clean_text = clean_text.strip()
            
            # Find all matching elements by name using word boundaries
            matches = []
            for name, elem in element_map.get("elements", {}).items():
                name_lower = name.lower()
                # Use word boundary matching to avoid partial matches
                # "diagnosis" should match "Diagnosis" but NOT "Age at Diagnosis"
                pattern = r'\b' + re.escape(clean_text) + r'\b'
                if re.search(pattern, name_lower):
                    matches.append((name, elem))
                    logger.info(f"  ✓ Name match: {name}")
            
            if not matches:
                logger.info(f"  ⚠️ No name matches for '{clean_text}'")
                return None
            
            logger.info(f"  Found {len(matches)} name matches, filtering by step metadata...")
            
            # Filter by step metadata
            filtered = matches
            
            # Filter by TYPE if specified in metadata
            if "type" in step_metadata:
                required_type = step_metadata["type"]
                temp_filtered = []
                for name, elem in filtered:
                    elem_type = elem.get("type", "").lower()
                    if elem_type == required_type or required_type in name.lower():
                        temp_filtered.append((name, elem))
                        logger.info(f"  ✓ Type match ({required_type}): {name}")
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
            
            # Filter by PARENT HINT if specified (e.g., "in the Diagnosis section")
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
                # Sort by name similarity - prefer shorter names and exact matches
                # Extract just the element name from description (remove location/type info)
                def extract_element_name(desc):
                    """Extract just the element name from full description"""
                    # Example: "Diagnosis accordion nested in Diagnosis" -> "diagnosis"
                    parts = desc.lower().split()
                    # Remove common suffixes
                    for word in ['accordion', 'tab', 'button', 'checkbox', 'nested', 'in', 'left', 'sidebar', 'filter', 'panel']:
                        if word in parts:
                            parts.remove(word)
                    return ' '.join(parts[:2])  # Take first 2 words max
                
                # Sort: exact matches first, then by depth (prefer shallower), then by name length
                def match_score(item):
                    name, elem = item
                    elem_name = extract_element_name(name)
                    elem_depth = elem.get("depth", 0)
                    
                    # Exact match gets score 0 (best)
                    if elem_name == clean_text:
                        return (0, elem_depth, len(name))
                    # Close match gets score 1
                    if clean_text in elem_name or elem_name in clean_text:
                        return (1, elem_depth, len(name))
                    # Otherwise sort by depth and length
                    return (2, elem_depth, len(name))
                
                filtered = sorted(filtered, key=match_score)
                name, elem = filtered[0]
                
                # CRITICAL: If step is nested AND element has parent → use XPath (includes parent check)
                # Simple selector like [id='Diagnosis'] matches BOTH outer and inner accordions
                # XPath like parent::*[@id='Diagnosis'] ensures we get the correct nested one
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
                
                self.element_registry.update_usage(domain, page, name)
                return selector
            
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
            locator = self.page.locator(selector).nth(0)
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
            locator = self.page.locator(selector).nth(0)
            validation_result["locator"] = locator  # Preserve locator reference
            validation_result["selector"] = selector  # Preserve selector for post-click reconstruction
            
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
                    # DISABLED: Highlighting was causing accordions to auto-expand
                    # logger.info(f"  📍 Scrolling element into view...")
                    # await locator.scroll_into_view_if_needed()
                    # await self.page.wait_for_timeout(500)  # Let scroll animation complete
                    
                    # DISABLED: Add thick red outline - causes accordion auto-expansion
                    # await locator.evaluate("el => el.style.outline = '5px solid red'")
                    # await locator.evaluate("el => el.style.outlineOffset = '2px'")
                    # await self.page.wait_for_timeout(1000)  # Wait for browser to render highlight
                    
                    # Take screenshot showing element (without highlighting to avoid auto-expansion)
                    self.screenshot_counter += 1
                    safe_name = self._sanitize_filename(element_description)
                    filename = f"{self.screenshot_counter:03d}_pre_click_{safe_name}.png"
                    filepath = self.screenshots_dir / filename
                    
                    # Take full page screenshot (element is in current view)
                    await self.page.screenshot(path=str(filepath), full_page=False)
                    
                    # Store screenshot info
                    if filepath.exists():
                        size = filepath.stat().st_size
                        validation_result["screenshot_taken"] = True
                        validation_result["screenshot_file"] = filename
                        validation_result["screenshot_size"] = size
                        logger.info(f"  ✅ Pre-validation: Element visible in screenshot (no highlighting): {filename} ({size} bytes)")
                    
                    # DISABLED: Keep highlight visible briefly, then remove
                    # await self.page.wait_for_timeout(200)
                    # await locator.evaluate("el => el.style.outline = ''")
                    # await locator.evaluate("el => el.style.outlineOffset = ''")
                    
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
                # CASE 1: Element still visible - NO highlighting (could affect element behavior)
                # DISABLED: await locator.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(300)
                
                # DISABLED: Apply GREEN highlight - could trigger element interactions
                # await locator.evaluate("el => el.style.outline = '5px solid lime'")
                # await locator.evaluate("el => el.style.outlineOffset = '2px'")
                await self.page.wait_for_timeout(1000)
                
                # Screenshot
                self.screenshot_counter += 1
                sanitized_element = self._sanitize_filename(element_name)
                filename = f"{self.screenshot_counter:03d}_post_click_{sanitized_element}.png"
                filepath = self.screenshots_dir / filename
                await self.page.screenshot(path=str(filepath))
                
                # DISABLED: Remove highlight
                # await self.page.wait_for_timeout(200)
                # await locator.evaluate("el => el.style.outline = ''")
                # await locator.evaluate("el => el.style.outlineOffset = ''")
                
                result["screenshot_taken"] = True
                result["screenshot_file"] = filename
                result["screenshot_size"] = filepath.stat().st_size
                logger.info(f"  📸 ✅ Post-click screenshot: {filename} ({result['screenshot_size']} bytes)")
                logger.info(f"  📸 Post-click screenshot captured (no highlighting)")
                
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
                            
                            # DISABLED: Highlight result in green - could trigger element interactions
                            # await elem.evaluate("el => el.style.outline = '5px solid lime'")
                            # await elem.evaluate("el => el.style.outlineOffset = '2px'")
                            await self.page.wait_for_timeout(1000)
                            
                            # Screenshot
                            self.screenshot_counter += 1
                            sanitized_element = self._sanitize_filename(element_name)
                            filename = f"{self.screenshot_counter:03d}_post_click_result_{sanitized_element}.png"
                            filepath = self.screenshots_dir / filename
                            await self.page.screenshot(path=str(filepath))
                            
                            # DISABLED: Remove highlight
                            # await elem.evaluate("el => el.style.outline = ''")
                            # await elem.evaluate("el => el.style.outlineOffset = ''")
                            
                            result["screenshot_taken"] = True
                            result["screenshot_file"] = filename
                            result["screenshot_size"] = filepath.stat().st_size
                            logger.info(f"  📸 ✅ Post-click result screenshot: {filename} ({result['screenshot_size']} bytes)")
                            logger.info(f"  📸 Post-click result screenshot captured (no highlighting)")
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
                    count_text = await count_locator.nth(0).text_content()
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
    
    async def _extract_element_attributes(self, locator) -> Dict:
        """Extract all attributes from a Playwright locator or ElementHandle for XPath generation"""
        try:
            # Handle both Locator and ElementHandle types
            # Check if it's already an ElementHandle
            from playwright.async_api import ElementHandle, Locator
            
            if isinstance(locator, ElementHandle):
                # Already an ElementHandle, use directly
                element = locator
            elif isinstance(locator, Locator):
                # It's a Locator, get the element handle
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
    
    def _extract_xpath_from_result(self, result_string: str) -> str:
        """Extract XPath from AI result string (e.g., '✅ Clicked xpath=//div[...] - Verified')"""
        if not result_string or 'Clicked' not in result_string:
            return None
        
        clicked_match = re.search(r'(?:✅\s*)?Clicked\s+(.+?)(?:\s+-\s+|$)', result_string)
        if clicked_match:
            selector_raw = clicked_match.group(1).strip().rstrip('.,;').strip()
            # Extract XPath if it's an xpath= selector
            if selector_raw.startswith('xpath='):
                return selector_raw.replace('xpath=', '').strip()
            elif selector_raw.startswith('//') or ('[@' in selector_raw and ']' in selector_raw):
                return selector_raw
        return None
    
    async def _track_discovery(self, element_name: str, original_query: str, final_selector: str, 
                         discovery_method: str, metadata: dict, clicked_xpath: str = None, clicked_element=None):
        """Track a successful discovery for later registry update - Use clicked XPath if available"""
        
        # PRIORITY: Use clicked XPath from result string (what AI actually clicked)
        xpath_to_use = clicked_xpath
        uniqueness_method = "clicked_xpath" if clicked_xpath else None
        
        # CRITICAL FIX: If tree climbing found a parent, generate XPath from PARENT element, not child
        # Check if this was a tree climbing discovery with parent relationship
        relationship = metadata.get('relationship', '')
        if relationship == 'parent' and not xpath_to_use:
            # Tree climbing found parent - we need XPath for the PARENT, not child
            # Try to extract XPath from final_selector (e.g., "button[name='button']")
            if final_selector and ('button' in final_selector or 'input' in final_selector or 'a' in final_selector):
                try:
                    # Convert selector to XPath format
                    # e.g., "button[name='button']" -> "//button[@name='button']"
                    if final_selector.startswith('button['):
                        # Extract attribute and value
                        attr_match = re.search(r"\[([^\]]+)\]", final_selector)
                        if attr_match:
                            attr_part = attr_match.group(1)
                            # Handle name='value' or name="value"
                            name_match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", attr_part)
                            if name_match:
                                name_value = name_match.group(1)
                                xpath_to_use = f"//button[@name='{name_value}']"
                                uniqueness_method = "parent_selector_conversion"
                                logger.info(f"  🔧 Converted parent selector to XPath: {xpath_to_use}")
                    elif final_selector.startswith('text='):
                        # text=Grant -> //button[normalize-space(.)='Grant']
                        text_value = final_selector.replace('text=', '').strip().strip("'\"")
                        xpath_to_use = f"//button[normalize-space(.)='{text_value}']"
                        uniqueness_method = "parent_text_conversion"
                        logger.info(f"  🔧 Converted parent text selector to XPath: {xpath_to_use}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Failed to convert parent selector to XPath: {e}")
            
            # If conversion failed, try to generate XPath from clicked_element if provided
            if not xpath_to_use and clicked_element:
                try:
                    logger.info(f"  🔨 Building XPath for parent element '{element_name}' using clicked element...")
                    parent_attrs = await self._extract_element_attributes(clicked_element)
                    if parent_attrs:
                        xpath_builder = XPathBuilder(self.page)
                        xpath_result = await xpath_builder.build_unique_xpath(parent_attrs, element_name)
                        xpath_to_use = xpath_result['xpath']
                        uniqueness_method = xpath_result['uniqueness_method']
                        logger.info(f"  ✅ Generated unique XPath from parent element: {xpath_to_use}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Failed to generate XPath from parent element: {e}")
        
        # Fallback: Generate XPath from the discovered element (child)
        if not xpath_to_use:
            xpath_result = None
            try:
                element_attrs = metadata.get('element_attrs', {})
                if element_attrs:
                    logger.info(f"  🔨 Building XPath for '{element_name}' using LIVE Playwright DOM...")
                    xpath_builder = XPathBuilder(self.page)
                    xpath_result = await xpath_builder.build_unique_xpath(element_attrs, element_name)
                    xpath_to_use = xpath_result['xpath']
                    uniqueness_method = xpath_result['uniqueness_method']
                    logger.info(f"  ✅ Generated unique XPath: {xpath_to_use}")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to generate XPath: {e}")
        
        # Look up element_id from registry if element exists (try multiple strategies)
        element_id = None
        try:
            domain, page = self._get_domain_and_page(self.current_url)
            
            # Strategy 1: Try exact name match
            registry_element = self.element_registry.get_element(domain, page, element_name)
            if registry_element:
                element_id = registry_element.get('element_id')
                if element_id:
                    logger.info(f"  🆔 Found element_id in registry (by name): {element_id}")
            
            # Strategy 2: If not found and we have XPath, search by XPath
            if not element_id and xpath_to_use:
                element_map = self.element_registry.load_map(domain, page)
                if element_map:
                    for key, elem_data in element_map.get('elements', {}).items():
                        if elem_data.get('xpath') == xpath_to_use:
                            element_id = elem_data.get('element_id')
                            if element_id:
                                logger.info(f"  🆔 Found element_id in registry (by XPath): {element_id}")
                                break
        except Exception as e:
            logger.debug(f"  ⚠️ Could not lookup element_id: {e}")
        
        # Store discovery with XPath and element_id
        discovery = {
            "name": element_name,
            "element_id": element_id,  # ← NEW: Unique ID from registry
            "original_query": original_query,
            "final_selector": final_selector,
            "xpath": xpath_to_use,
            "uniqueness_method": uniqueness_method,
            "discovery_method": discovery_method,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.discoveries.append(discovery)
        logger.info(f"  📝 Tracked discovery: {element_name} via {discovery_method}")
        if element_id:
            logger.info(f"     Element ID: {element_id}")
        logger.info(f"     Query: {original_query}")
        if xpath_to_use:
            logger.info(f"     XPath: {xpath_to_use}")
        else:
            logger.info(f"     Selector: {final_selector}")
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute tool - Direct Playwright calls!"""
        import re  # Ensure re is available as local variable throughout this function
        
        # Increment step number for every tool execution
        self.current_step_number += 1
        logger.info(f"🔢 Executing Step {self.current_step_number}")
        
        if tool_name == "browser_navigate":
            url = tool_input['url']
            logger.info(f"Navigate: {url}")
            
            # Track current URL and page for element registry
            self.current_url = url
            
            # Execute
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(1000)  # Allow page to settle
            
            # Set wide viewport and zoom out to show all tabs (avoid "More" button)
            try:
                # Viewport is already 1920x1080 from initialization
                # Zoom out to 80% for maximum tab visibility
                await self.page.evaluate("document.body.style.zoom = '0.8'")
                logger.info(f"  🔍 Zoom set to 80% (viewport: 1920x1080)")
                
                # Wait for layout to adjust
                await self.page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(f"  ⚠️ Could not adjust viewport/zoom: {e}")
            
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
            
            # Check element registry using current step metadata
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
            original_element_for_xpath = None  # Track original nested element for XPath generation
            
            # TRY optimized selector first, with fallback to original query if it fails
            try:
                all_matches = await self.page.locator(selector).all()
                
                # ✅ VERIFY XPATH UNIQUENESS during execution (not just during parsing!)
                if optimized_selector_used and selector.startswith("xpath="):
                    xpath_count = len(all_matches)
                    logger.info(f"  🔍 XPath verification: {xpath_count} match(es) found in live DOM")
                    
                    if xpath_count == 0:
                        logger.warning(f"  ⚠️ XPath returned 0 matches (element may be hidden/not in DOM yet)")
                        logger.info(f"  ⚙️ Falling back to discovery: {original_selector}")
                        selector = original_selector
                        optimized_selector_used = False
                        all_matches = await self.page.locator(selector).all()
                    elif xpath_count > 1:
                        logger.warning(f"  ⚠️ XPath returned {xpath_count} matches (not unique in current DOM state)")
                        logger.info(f"  ⚙️ Continuing with AI disambiguation for {xpath_count} matches")
                        # Continue with normal AI disambiguation flow
                    else:
                        logger.info(f"  ✅ XPath is unique (1 match) - proceeding with click")
                        
                        # 🔍 DEBUG: Log the actual element attributes that were matched
                        try:
                            matched_elem = all_matches[0]
                            elem_debug_info = await matched_elem.evaluate("""el => ({
                                tagName: el.tagName.toLowerCase(),
                                id: el.id,
                                role: el.getAttribute('role'),
                                ariaExpanded: el.getAttribute('aria-expanded'),
                                text: el.textContent?.substring(0, 80),
                                className: el.className,
                                parentId: el.parentElement?.id || null
                            })""")
                            logger.info(f"  🔍 DEBUG - Matched element attributes:")
                            logger.info(f"      tag={elem_debug_info['tagName']}, id='{elem_debug_info['id']}', role='{elem_debug_info['role']}'")
                            logger.info(f"      aria-expanded={elem_debug_info['ariaExpanded']}, parent_id='{elem_debug_info['parentId']}'")
                            logger.info(f"      text='{elem_debug_info['text'][:60] if elem_debug_info['text'] else 'N/A'}...'")
                        except Exception as debug_err:
                            logger.warning(f"  ⚠️ Could not extract debug info: {debug_err}")
                        
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
                    
                    # Describe each VISIBLE candidate AND check for tree climbing
                    for i, match in enumerate(visible_matches):
                        description = await self._describe_element(match)
                        
                        # Check if THIS element is interactive
                        element_props = await match.evaluate("""el => ({
                            tagName: el.tagName.toLowerCase(),
                            role: el.getAttribute('role'),
                            ariaExpanded: el.getAttribute('aria-expanded'),
                            ariaSelected: el.getAttribute('aria-selected'),
                            type: el.getAttribute('type'),
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
                            "description": description
                        })
                        
                        # Log candidate summary for debugging
                        summary = description.split('\n')[0] if '\n' in description else description[:100]
                        logger.info(f"    Candidate {len(candidates)-1}: {summary}")
                        
                        # If element is NOT directly interactive, climb DOM tree to find interactive ancestor
                        if not is_interactive:
                            logger.info(f"  🔍 Candidate {i}: Element not interactive (tag={element_props['tagName']}), climbing tree...")
                            
                            current_elem = match
                            max_depth = 5
                            
                            for depth in range(1, max_depth + 1):
                                try:
                                    parent_handle = await current_elem.evaluate_handle("el => el.parentElement")
                                    if not parent_handle:
                                        break
                                    
                                    parent_elem = parent_handle.as_element()
                                    if not parent_elem or not await parent_elem.is_visible():
                                        break
                                    
                                    # Check ancestor properties
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
                                        logger.info(f"  ✅ Found interactive ancestor at depth {depth}: tag={parent_props['tagName']}, role={parent_props['role']}")
                                        
                                        parent_desc = await self._describe_element(parent_elem)
                                        candidates.append({
                                            "index": len(candidates),
                                            "element": parent_elem,
                                            "description": parent_desc + f"\n(PARENT at depth {depth})"
                                        })
                                        break
                                    else:
                                        logger.info(f"  ⬆️ Depth {depth}: tag={parent_props['tagName']}, role={parent_props['role']} - not interactive, continuing...")
                                        current_elem = parent_elem
                                        
                                except Exception as e:
                                    logger.debug(f"  Error climbing at depth {depth}: {e}")
                                    break
                
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
                    
                    # Log all candidates for debugging
                    for i, candidate in enumerate(candidates):
                        summary = candidate['description'].split('\n')[0] if '\n' in candidate['description'] else candidate['description'][:120]
                        logger.info(f"    Candidate {i}: {summary}")
                    
                    # Ask LLM to choose based on story context
                    best_index = await self._llm_choose_element(candidates, selector)
                    
                    # Use the chosen element for clicking
                    logger.info(f"  🎯 LLM chose element {best_index} of {len(candidates)}")
                    chosen_locator = candidates[best_index]["element"]
                    
                    # 🔍 DEBUG: Log the LLM-chosen element's attributes
                    try:
                        llm_chosen_debug = await chosen_locator.evaluate("""el => ({
                            tagName: el.tagName.toLowerCase(),
                            id: el.id,
                            role: el.getAttribute('role'),
                            ariaExpanded: el.getAttribute('aria-expanded'),
                            text: el.textContent?.substring(0, 80),
                            parentId: el.parentElement?.id || null
                        })""")
                        logger.info(f"  🔍 DEBUG - LLM chose element with attributes:")
                        logger.info(f"      tag={llm_chosen_debug['tagName']}, id='{llm_chosen_debug['id']}', role='{llm_chosen_debug['role']}'")
                        logger.info(f"      aria-expanded={llm_chosen_debug['ariaExpanded']}, parent_id='{llm_chosen_debug['parentId']}'")
                        logger.info(f"      text='{llm_chosen_debug['text'][:60] if llm_chosen_debug['text'] else 'N/A'}...'")
                    except Exception as debug_err:
                        logger.warning(f"  ⚠️ Could not extract LLM-chosen element debug info: {debug_err}")
                    
                    # IMPORTANT: Preserve the original nested element (candidates[0]) for XPath generation
                    # When tree climbing finds a parent, we click the parent but generate XPath for the nested element
                    original_element_for_xpath = candidates[0]["element"]
                    if best_index > 0:
                        logger.info(f"  📍 Using element {best_index} for clicking, but element 0 (nested) for XPath")
                
                elif len(candidates) == 1:
                    # Single candidate that looks appropriate, use it
                    logger.info(f"  ✅ Single appropriate element found")
                    chosen_locator = candidates[0]["element"]
                    original_element_for_xpath = candidates[0]["element"]
                    
                    # 🔍 DEBUG: Log the chosen element's attributes AND verify it's the same as XPath match
                    try:
                        chosen_debug_info = await chosen_locator.evaluate("""el => ({
                            tagName: el.tagName.toLowerCase(),
                            id: el.id,
                            role: el.getAttribute('role'),
                            ariaExpanded: el.getAttribute('aria-expanded'),
                            text: el.textContent?.substring(0, 80),
                            parentId: el.parentElement?.id || null
                        })""")
                        logger.info(f"  🔍 DEBUG - Chosen element for click (candidates[0]):")
                        logger.info(f"      tag={chosen_debug_info['tagName']}, id='{chosen_debug_info['id']}', role='{chosen_debug_info['role']}'")
                        logger.info(f"      aria-expanded={chosen_debug_info['ariaExpanded']}, parent_id='{chosen_debug_info['parentId']}'")
                        logger.info(f"      text='{chosen_debug_info['text'][:60] if chosen_debug_info['text'] else 'N/A'}...'")
                        
                        # Verify this is the same element from all_matches[0]
                        first_match_debug = await all_matches[0].evaluate("""el => ({
                            id: el.id,
                            text: el.textContent?.substring(0, 80)
                        })""")
                        if first_match_debug['id'] == chosen_debug_info['id']:
                            logger.info(f"  ✅ Confirmed: chosen_locator matches all_matches[0] (both id='{chosen_debug_info['id']}')")
                        else:
                            logger.warning(f"  ⚠️ MISMATCH: chosen_locator id='{chosen_debug_info['id']}' != all_matches[0] id='{first_match_debug['id']}'")
                    except Exception as debug_err:
                        logger.warning(f"  ⚠️ Could not extract chosen element debug info: {debug_err}")
                    
            except Exception as e:
                # If we can't check for multiple matches, continue with original selector
                logger.warning(f"  ⚠️ Could not check element context: {e}")
            
            # Initialize tab detection variables BEFORE both code paths
            is_tab_click = False
            initial_tab_state = None
            
            # If we have a chosen locator from AI disambiguation, prepare it for the common flow
            if chosen_locator:
                # TAB DETECTION: Check if this is a tab by element role or story context
                element_name = original_selector.replace("text=", "").replace("_", " ")
                
                try:
                    element_role = await chosen_locator.get_attribute('role')
                    aria_selected = await chosen_locator.get_attribute('aria-selected')
                    
                    # Check if this is a tab (by role attribute or aria-selected)
                    if element_role == 'tab' or aria_selected is not None:
                        is_tab_click = True
                        logger.info(f"  🎯 Tab detected (role={element_role}, aria-selected={aria_selected})")
                    else:
                        # Fallback: Check if selector indicates tab (for cases where role is on parent)
                        if '[role="tab"]' in original_selector or 'aria-selected' in original_selector:
                            is_tab_click = True
                            logger.info(f"  🎯 Tab detected (by selector string: {original_selector})")
                except Exception as e:
                    logger.debug(f"  Could not check element role: {e}")
                    # Last resort: Check selector string
                    if '[role="tab"]' in original_selector or 'aria-selected' in original_selector:
                        is_tab_click = True
                        logger.info(f"  🎯 Tab detected (fallback to selector string)")
                
                # Validate the chosen locator with screenshot
                try:
                    # DISABLED: DEBUG element extraction - was causing accordion auto-expansion
                    # The evaluate() call was triggering the accordion to expand before the click
                    # logger.info(f"  🔍 DEBUG - About to highlight element for pre-click screenshot:")
                    # try:
                    #     highlight_debug = await chosen_locator.evaluate("""el => ({
                    #         tagName: el.tagName.toLowerCase(),
                    #         id: el.id,
                    #         role: el.getAttribute('role'),
                    #         ariaExpanded: el.getAttribute('aria-expanded'),
                    #         text: el.textContent?.substring(0, 80),
                    #         parentId: el.parentElement?.id || null
                    #     })""")
                    #     logger.info(f"      tag={highlight_debug['tagName']}, id='{highlight_debug['id']}', role='{highlight_debug['role']}'")
                    #     logger.info(f"      aria-expanded={highlight_debug['ariaExpanded']}, parent_id='{highlight_debug['parentId']}'")
                    #     logger.info(f"      text='{highlight_debug['text'][:60] if highlight_debug['text'] else 'N/A'}...'")
                    # except Exception as dbg_err:
                    #     logger.warning(f"  ⚠️ Could not extract pre-highlight debug info: {dbg_err}")
                    
                    # DISABLED: Scroll into view and highlight - causes accordion auto-expansion
                    # await chosen_locator.scroll_into_view_if_needed()
                    # await self.page.wait_for_timeout(500)
                    # await chosen_locator.evaluate("el => el.style.outline = '5px solid red'")
                    # await chosen_locator.evaluate("el => el.style.outlineOffset = '2px'")
                    # await self.page.wait_for_timeout(1000)
                    
                    # Take screenshot (no highlighting to avoid auto-expansion)
                    self.screenshot_counter += 1
                    safe_name = self._sanitize_filename(element_name)
                    filename = f"{self.screenshot_counter:03d}_pre_click_{safe_name}.png"
                    filepath = self.screenshots_dir / filename
                    await self.page.screenshot(path=str(filepath), full_page=False)
                    
                    screenshot_taken = filepath.exists()
                    screenshot_size = filepath.stat().st_size if screenshot_taken else 0
                    
                    # DISABLED: Remove highlight
                    # await self.page.wait_for_timeout(200)
                    # await chosen_locator.evaluate("el => el.style.outline = ''")
                    # await chosen_locator.evaluate("el => el.style.outlineOffset = ''")
                    
                    logger.info(f"  ✅ Pre-validation: Element visible in screenshot (no highlighting): {filename} ({screenshot_size} bytes)")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not capture pre-click screenshot: {e}")
                    screenshot_taken = False
                    filename = None
                    screenshot_size = None
                
                # Generate selector from chosen_locator for reconstruction (used for clicking)
                try:
                    final_selector = await self._generate_final_selector(chosen_locator)
                except:
                    # Fallback to original selector if generation fails
                    final_selector = original_selector
                
                # Generate selector for post-click screenshots from nested element (if different)
                nested_selector_for_screenshot = None
                if original_element_for_xpath and original_element_for_xpath != chosen_locator:
                    try:
                        nested_selector_for_screenshot = await self._generate_final_selector(original_element_for_xpath)
                        logger.info(f"  📸 Will use nested element selector for post-click screenshots")
                    except:
                        logger.warning(f"  ⚠️ Could not generate selector for nested element, using parent")
                        nested_selector_for_screenshot = None
                
                # Create validation result and set preserved_selector to use common click flow
                validation_result = {
                    "exists": True,
                    "visible": await chosen_locator.is_visible(),
                    "enabled": await chosen_locator.is_enabled(),
                    "text_content": await chosen_locator.text_content() or "",
                    "location": {},
                    "screenshot_taken": screenshot_taken,
                    "screenshot_file": filename,
                    "screenshot_size": screenshot_size,
                    "locator": chosen_locator,
                    "selector": final_selector,  # Selector for clicking (parent)
                    "nested_selector": nested_selector_for_screenshot  # Selector for post-click screenshots (nested)
                }
                pre_validation = validation_result
                # IMPORTANT: Set preserved_selector so we use the common click loop below
                # This ensures tab-specific logic, accordion validation, etc. all work
            else:
                # Normal selector-based flow
                # Smart retry strategy for complex UI elements (dropdowns, accordions, etc.)
                strategies = [
                    {"desc": "direct click", "method": lambda: self.page.click(selector)},
                    {"desc": "clickable parent/sibling", "method": lambda: self._click_parent_or_sibling(selector)},
                    {"desc": "force click", "method": lambda: self.page.click(selector, force=True)},
                ]
                
                # Try to find the element - be forgiving with selectors
                # STEP 1: Find element in DOM (even if hidden)
                element_found_in_dom = False
                try:
                    await self.page.wait_for_selector(selector, state='attached', timeout=5000)
                    logger.info(f"  ✅ Element found in DOM: {selector}")
                    element_found_in_dom = True
                    
                    # STEP 2: Try to scroll into view if hidden
                    try:
                        locator = self.page.locator(selector).first
                        logger.info(f"  📜 Attempting to scroll element into view...")
                        await locator.scroll_into_view_if_needed(timeout=3000)
                        await self.page.wait_for_timeout(500)  # Let scroll animation complete
                        logger.info(f"  ✅ Scrolled element into view")
                    except Exception as scroll_error:
                        logger.warning(f"  ⚠️ Could not scroll element: {scroll_error}")
                    
                    # STEP 3: Now wait for visibility (should work after scroll)
                    # For checkboxes from registry, skip visibility check (virtual scrolling makes them "hidden")
                    if selector.startswith('input[type') or '[type=' in selector:
                        logger.info(f"  ✅ Checkbox element found - skipping visibility check (virtual scrolling)")
                    else:
                        await self.page.wait_for_selector(selector, state='visible', timeout=5000)
                        logger.info(f"  ✅ Element is now visible")
                    
                except Exception as e:
                    # FALLBACK: Only fall back if element was NOT found in DOM
                    # If element WAS found and scrolled, proceed to click (don't fall back to text selector)
                    if not element_found_in_dom and optimized_selector_used and selector != original_selector:
                        logger.warning(f"  ⚠️ Optimized selector not found (likely dynamic CSS classes)")
                        logger.info(f"  ⚙️ Falling back to original query + discovery method: {original_selector}")
                        selector = original_selector
                        optimized_selector_used = False
                        # Retry with scroll-first strategy
                        await self.page.wait_for_selector(selector, state='attached', timeout=5000)
                        try:
                            locator = self.page.locator(selector).first
                            await locator.scroll_into_view_if_needed(timeout=3000)
                            await self.page.wait_for_timeout(500)
                        except:
                            pass
                        # For checkboxes, don't require visibility
                        if not (selector.startswith('input[type') or '[type=' in selector):
                            await self.page.wait_for_selector(selector, state='visible', timeout=5000)
                    # If registry gave us a bad ID selector that failed, try the original query
                    elif selector.startswith("#") and not original_selector.startswith("#"):
                        logger.info(f"  Registry ID selector failed, trying original: {original_selector}")
                        selector = original_selector
                        await self.page.wait_for_selector(selector, state='attached', timeout=5000)
                        try:
                            locator = self.page.locator(selector).first
                            await locator.scroll_into_view_if_needed(timeout=3000)
                            await self.page.wait_for_timeout(500)
                        except:
                            pass
                        await self.page.wait_for_selector(selector, state='visible', timeout=5000)
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
            
            # Get selector to reconstruct locator for post-click (avoid stale references)
            preserved_selector = pre_validation.get("selector")
            clicked_text = pre_validation.get("text_content", "")
            
            # ENHANCED TAB DETECTION: If not already detected via selector, check actual element role
            if not is_tab_click and preserved_selector:
                try:
                    temp_locator = self.page.locator(preserved_selector).nth(0)
                    element_role = await temp_locator.get_attribute('role')
                    aria_selected = await temp_locator.get_attribute('aria-selected')
                    
                    if element_role == 'tab' or aria_selected is not None:
                        is_tab_click = True
                        logger.info(f"  🎯 Tab detected post-validation (role={element_role}, aria-selected={aria_selected})")
                        
                        # Capture initial tab state
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
                    logger.debug(f"  Could not check preserved_selector role: {e}")
            
            # STORY CONTEXT: Check if story mentions this element as a "tab"
            # Use the CURRENT step context (already extracted above as story_context)
            # Capture initial state (for verification)
            initial_html = await self.page.content()
            initial_url = self.page.url
            
            # Capture initial count for validation (generic - any element with count)
            initial_count = None
            try:
                # Generic: matches Cases(50), Products(100), Files(20), etc.
                count_locator = self.page.locator('text=/\\w+\\s*\\(\\d+\\)/')
                if await count_locator.count() > 0:
                    count_text = await count_locator.nth(0).text_content()
                    match = re.search(r'\\((\\d+)\\)', count_text)
                    if match:
                        initial_count = int(match.group(1))
                        logger.info(f"  📊 Initial count: {initial_count}")
            except:
                pass
            
            # ACCORDION DETECTION: Check if element is an accordion/expandable
            is_accordion = False
            initial_aria_expanded = None
            current_aria_expanded = None  # Initialize here for later access
            accordion_opened = False  # Initialize here for later access
            accordion_locator = None
            try:
                # CRITICAL FIX: Reuse existing locator from pre_validation to avoid re-querying the element
                # Creating a new locator was causing the accordion to auto-expand on some pages
                if pre_validation.get("locator"):
                    accordion_locator = pre_validation["locator"]
                    logger.info(f"  ♻️ Reusing existing locator for accordion detection (avoids re-query)")
                elif preserved_selector:
                    accordion_locator = self.page.locator(preserved_selector).nth(0)
                else:
                    accordion_locator = self.page.locator(selector)
                
                initial_aria_expanded = await accordion_locator.get_attribute("aria-expanded")
                if initial_aria_expanded is not None:
                    is_accordion = True
                    logger.info(f"  🎯 Accordion detected: aria-expanded={initial_aria_expanded}")
                    
                    # ✨ FIX: If accordion is ALREADY OPEN, don't click it (prevents closing)
                    if initial_aria_expanded == 'true':
                        logger.info(f"  ✅ Accordion is already expanded - skipping click to avoid toggling it closed")
                        result_text = f"✅ Accordion already open: {element_description}"
                        return result_text
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
            
            # TAB-SPECIFIC: Fallback check via selector if not already detected
            try:
                # Check if selector indicates tab interaction (fallback for non-chosen_locator path)
                if not is_tab_click and ('[role="tab"]' in original_selector or ':nth-child' in original_selector):
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
            
            # CRITICAL: Extract element properties BEFORE click (element still in DOM)
            # This ensures discovery can be tracked even if element is detached after click
            pre_click_final_selector = None
            pre_click_element_attrs = {}
            if chosen_locator:
                try:
                    logger.info(f"  📝 Extracting element properties before click...")
                    pre_click_final_selector = await self._generate_final_selector(chosen_locator)
                    
                    # Extract element attributes BEFORE click (for XPath generation)
                    element_for_xpath = original_element_for_xpath if original_element_for_xpath else chosen_locator
                    pre_click_element_attrs = await self._extract_element_attributes(element_for_xpath)
                    logger.info(f"  ✅ Extracted properties before click: final_selector={pre_click_final_selector[:80] if pre_click_final_selector else 'None'}")
                except Exception as pre_click_error:
                    logger.warning(f"  ⚠️ Could not extract properties before click: {pre_click_error}")
                    # Will fallback to original_selector after click
            
            # Updated strategies - use validated locator directly to avoid selector ambiguity
            async def javascript_click():
                """Strategy 1: JavaScript click (for accordions that respond to JS but not Playwright clicks)"""
                # Use the exact locator we already validated - no information loss
                if pre_validation.get("locator"):
                    await pre_validation["locator"].evaluate("el => el.click()")
                elif preserved_selector:
                    temp_loc = self.page.locator(preserved_selector).nth(0)
                    await temp_loc.evaluate("el => el.click()")
                else:
                    await self.page.eval_on_selector(selector, "el => el.click()")
            
            async def click_with_preserved_locator():
                """Strategy 2: Direct click using validated locator"""
                # Use the exact locator we already validated
                if pre_validation.get("locator"):
                    await pre_validation["locator"].click()
                elif preserved_selector:
                    temp_loc = self.page.locator(preserved_selector).nth(0)
                    await temp_loc.click()
                else:
                    await self.page.click(selector)
            
            async def click_at_exact_coordinates():
                """Strategy 3: Click at exact element center coordinates"""
                # Use the exact locator we already validated
                if pre_validation.get("locator"):
                    box = await pre_validation["locator"].bounding_box()
                    if box:
                        center_x = box['x'] + box['width'] / 2
                        center_y = box['y'] + box['height'] / 2
                        await self.page.mouse.click(center_x, center_y)
                    else:
                        await self._click_parent_or_sibling(selector)
                elif preserved_selector:
                    temp_loc = self.page.locator(preserved_selector).nth(0)
                    box = await temp_loc.bounding_box()
                    if box:
                        center_x = box['x'] + box['width'] / 2
                        center_y = box['y'] + box['height'] / 2
                        await self.page.mouse.click(center_x, center_y)
                    else:
                        await self._click_parent_or_sibling(selector)
                else:
                    await self._click_parent_or_sibling(selector)
            
            async def force_click_with_preserved():
                """Strategy 4: Force click using validated locator"""
                # Use the exact locator we already validated
                if pre_validation.get("locator"):
                    await pre_validation["locator"].click(force=True)
                elif preserved_selector:
                    temp_loc = self.page.locator(preserved_selector).nth(0)
                    await temp_loc.click(force=True)
                else:
                    await self.page.click(selector, force=True)
            
            # Use JavaScript click first for accordions and checkboxes (bypasses visibility issues)
            is_checkbox = selector.startswith('input[type=\'checkbox\']') or 'checkbox' in selector.lower()
            
            if is_accordion or is_checkbox:
                strategies = [
                    {"desc": "javascript click", "method": javascript_click},
                    {"desc": "force click", "method": force_click_with_preserved},
                    {"desc": "direct click", "method": click_with_preserved_locator},
                    {"desc": "exact coordinates", "method": click_at_exact_coordinates},
                ]
            else:
                strategies = [
                    {"desc": "direct click", "method": click_with_preserved_locator},
                    {"desc": "exact coordinates", "method": click_at_exact_coordinates},
                    {"desc": "force click", "method": force_click_with_preserved},
                ]
            
            # TOTP Submission Detection: Check if this is a TOTP submission step
            step_metadata = self.parsed_steps.get(self.current_step_number, {})
            step_text = step_metadata.get('text', '')
            is_totp_submission = False
            
            # Check for TOTP submission keywords in step text or selector
            totp_submit_keywords = ["submit", "click submit", "press submit", "continue", "verify"]
            submit_has_totp = any(keyword in step_text.lower() for keyword in totp_submit_keywords)
            selector_is_submit = "submit" in selector.lower() or "button[type='submit']" in selector.lower()
            
            # Check if there's a TOTP field on the page (indicates TOTP form submission)
            has_totp_field = False
            try:
                totp_field_check = await self.page.evaluate("""
                    () => {
                        const selectors = ['input[name="code"]', 'input[type="text"][name*="code"]', 
                                          'input[type="tel"][name*="code"]', 'input.one-time-code',
                                          'input#one-time-code', 'input[autocomplete="one-time-code"]'];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el && el.offsetWidth > 0 && el.offsetHeight > 0 && el.type !== 'hidden') {
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                has_totp_field = totp_field_check
            except:
                pass
            
            is_totp_submission = (submit_has_totp or selector_is_submit) and has_totp_field
            
            if is_totp_submission:
                logger.info(f"  [TOTP_SUBMIT] Step {self.current_step_number} Detected TOTP submission - regenerating fresh TOTP code")
                
                # Extract secret key from story
                import os
                from utils.otp_helper import generate_otp
                
                secret_key = None
                secret_pattern = r'(?:secret\s+key|key)\s+([A-Z0-9]{20,})'
                
                if self.story:
                    match = re.search(secret_pattern, self.story, re.IGNORECASE)
                    if match:
                        secret_key = match.group(1)
                        logger.info(f"  [TOTP_SUBMIT] Extracted secret key from story: {secret_key[:10]}...")
                
                if not secret_key:
                    long_alnum_pattern = r'\b([A-Z0-9]{20,})\b'
                    matches = re.findall(long_alnum_pattern, self.story if self.story else '')
                    if matches:
                        secret_key = max(matches, key=len)
                        logger.info(f"  [TOTP_SUBMIT] Extracted potential secret key: {secret_key[:10]}...")
                
                if not secret_key:
                    secret_key = os.getenv("TOTP_SECRET_KEY")
                    if secret_key:
                        logger.info(f"  [TOTP_SUBMIT] Using TOTP_SECRET_KEY from environment")
                
                if secret_key:
                    try:
                        # Generate fresh TOTP code RIGHT BEFORE submission
                        fresh_totp_code = generate_otp(secret_key)
                        logger.info(f"  [TOTP_SUBMIT] Generated fresh TOTP code: {fresh_totp_code} (right before Submit click)")
                        
                        # Find and update the TOTP field with fresh code
                        totp_field_selectors = [
                            "input[name='code']",
                            "input[type='text'][name*='code']",
                            "input[type='tel'][name*='code']",
                            "input.one-time-code",
                            "input#one-time-code",
                            "input[autocomplete='one-time-code']"
                        ]
                        
                        totp_updated = False
                        for totp_selector in totp_field_selectors:
                            try:
                                totp_field = self.page.locator(totp_selector).first
                                if await totp_field.count() > 0:
                                    # Check if visible
                                    is_visible = await totp_field.is_visible()
                                    if is_visible:
                                        await totp_field.fill('')
                                        await totp_field.type(fresh_totp_code, delay=10)
                                        await self.page.wait_for_timeout(200)
                                        
                                        # Verify
                                        actual_value = await totp_field.input_value()
                                        if actual_value == fresh_totp_code:
                                            logger.info(f"  [TOTP_SUBMIT] ✅ Updated TOTP field with fresh code: {totp_selector}")
                                            totp_updated = True
                                            break
                            except:
                                continue
                        
                        if not totp_updated:
                            logger.warning(f"  [TOTP_SUBMIT] ⚠️ Could not update TOTP field, proceeding with click anyway")
                    except Exception as e:
                        logger.error(f"  [TOTP_SUBMIT] Failed to regenerate TOTP: {e}")
            
            last_error = None
            # Log if we're using the validated locator (better precision)
            if pre_validation.get("locator"):
                logger.info(f"  🎯 Using validated locator directly (avoids selector ambiguity)")
            elif preserved_selector:
                logger.info(f"  ⚙️ Using preserved selector: {preserved_selector[:100]}")
            
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
                    dom_shrank = len(new_html) < len(initial_html) * 0.97  # 3% shrinkage (popup dismissed)
                    
                    # DEBUG: Log DOM size changes
                    initial_size = len(initial_html)
                    new_size = len(new_html)
                    size_change = new_size - initial_size
                    size_change_pct = (size_change / initial_size * 100) if initial_size > 0 else 0
                    logger.info(f"  📏 DOM size: {initial_size} → {new_size} ({size_change:+d} bytes, {size_change_pct:+.1f}%)")
                    logger.info(f"  🔍 Checks: dom_changed={dom_changed}, dom_grew={dom_grew}, dom_shrank={dom_shrank}")
                    
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
                            if preserved_selector:
                                temp_loc = self.page.locator(preserved_selector).nth(0)
                                if await temp_loc.count() > 0:
                                    attr = await temp_loc.get_attribute('aria-expanded')
                            if attr == 'true':
                                aria_expanded = True
                            else:
                                # Check parent elements
                                parent_locator = temp_loc.locator('..')
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
                        # Strategy 1: Require URL change OR significant DOM growth/shrinkage OR state change OR accordion opened
                        click_succeeded = url_changed or dom_grew or dom_shrank or state_changed or aria_expanded or accordion_opened
                    else:
                        # Strategy 2+: Allow DOM change as fallback
                        click_succeeded = url_changed or dom_grew or dom_shrank or aria_expanded or accordion_opened or state_changed or dom_changed
                    
                    if click_succeeded:
                        reasons = []
                        if url_changed: reasons.append("page navigated")
                        if dom_grew: reasons.append(f"content expanded ({len(new_html) - len(initial_html)} bytes)")
                        if dom_shrank: reasons.append(f"popup dismissed ({len(initial_html) - len(new_html)} bytes removed)")
                        if accordion_opened: reasons.append("accordion expanded (aria-expanded: false→true)")
                        elif aria_expanded: reasons.append("dropdown/section expanded")
                        if state_changed: reasons.append("element state changed")
                        if dom_changed and not reasons: reasons.append("DOM changed")
                        
                        logger.info(f"  ✅ Click verified: {', '.join(reasons)}")
                        
                        # ✨ Track last clicked element for parent-child relationship matching
                        self.last_clicked_element = element_name
                        logger.debug(f"  📝 Tracked last clicked: {element_name}")
                        
                                # POST-CLICK GREEN SCREENSHOT: Use clicked element for screenshot
                        # (For tree climbing, this is the parent button that was actually clicked)
                        if preserved_selector:
                            fresh_locator = self.page.locator(preserved_selector).nth(0)
                            post_click_result = await self._capture_post_click_screenshot(
                                fresh_locator, 
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
                                
                                # Use pre-extracted properties (extracted BEFORE click when element was still in DOM)
                                final_selector = pre_click_final_selector
                                element_attrs = pre_click_element_attrs
                                
                                # IMPORTANT: Preserve original selector if it's a simple text selector
                                # to maintain case sensitivity (e.g., text=TREATMENT vs text=Treatment)
                                if original_selector.startswith('text=') and final_selector and final_selector.startswith('text='):
                                    logger.info(f"  📝 Preserving original text selector for case sensitivity: {original_selector}")
                                    final_selector = original_selector
                                
                                # FALLBACK: Use original_selector if final_selector generation failed
                                # This ensures discovery is ALWAYS tracked, even if element was detached
                                if not final_selector:
                                    logger.warning(f"  ⚠️ Could not generate final selector, using original: {original_selector}")
                                    final_selector = original_selector
                                
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
                                
                                # Add element attributes to metadata (use pre-extracted, or try after click if missing)
                                if element_attrs:
                                    metadata["element_attrs"] = element_attrs
                                else:
                                    # Fallback: Try to extract attributes after click (may fail if element detached)
                                    try:
                                        element_for_xpath = original_element_for_xpath if original_element_for_xpath else chosen_locator
                                        element_attrs = await self._extract_element_attributes(element_for_xpath)
                                        metadata["element_attrs"] = element_attrs
                                    except Exception as attr_error:
                                        logger.warning(f"  ⚠️ Could not extract element attributes after click: {attr_error}")
                                        metadata["element_attrs"] = {}
                                
                                # ALWAYS track discovery (never skip, even if final_selector is original_selector)
                                # Pass clicked_element if tree climbing found a parent (for correct XPath generation)
                                clicked_element_for_tracking = None
                                if discovery_method == "tree_climbing" and chosen_locator:
                                    # For tree climbing, the clicked element is the parent, not the child
                                    try:
                                        clicked_element_for_tracking = await chosen_locator.element_handle()
                                    except:
                                        pass
                                
                                await self._track_discovery(
                                    element_name=element_name,
                                    original_query=original_selector,
                                    final_selector=final_selector,
                                    discovery_method=discovery_method,
                                    metadata=metadata,
                                    clicked_element=clicked_element_for_tracking
                                )
                                logger.info(f"  ✅ Discovery tracked: {element_name} (final_selector: {final_selector[:80] if len(final_selector) > 80 else final_selector})")
                            
                            except Exception as e:
                                logger.warning(f"  ⚠️ Failed to track discovery: {e}")
                                # Last resort: Try to track with minimal info
                                try:
                                    await self._track_discovery(
                                        element_name=element_name,
                                        original_query=original_selector,
                                        final_selector=original_selector,  # Use original as absolute fallback
                                        discovery_method="unknown",
                                        metadata={}
                                    )
                                    logger.info(f"  ✅ Discovery tracked with fallback: {element_name}")
                                except Exception as fallback_error:
                                    logger.error(f"  ❌ Failed to track discovery even with fallback: {fallback_error}")
                        
                        # POST-CLICK VALIDATION: Accordion takes priority over tab
                        # If accordion was detected AND it expanded, skip tab validation (even if tab was also detected)
                        accordion_expanded_successfully = (
                            accordion_opened or 
                            (current_aria_expanded and initial_aria_expanded and current_aria_expanded != initial_aria_expanded)
                        )
                        
                        # POST-CLICK VALIDATION: Tab-specific validation (only if not an accordion)
                        if is_tab_click and initial_tab_state and not accordion_expanded_successfully:
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
                                    # No semantic tabs or no change detected
                                    # If both initial and current are None, this is a non-semantic tab - use DOM changes
                                    if initial_tab_state.get('selected_tab') is None and new_selected_tab is None:
                                        # Non-semantic tabs: rely on DOM changes as validation
                                        if dom_changed or dom_grew:
                                            tab_switch_verified = True
                                            logger.info(f"  ✅ Tab switch verified (non-semantic tabs, DOM changed)")
                                            reasons.append(f"tab content changed")
                                            
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
                                                element_name = original_selector.replace("text=", "").replace("_", " ")
                                                safe_name = self._sanitize_filename(f"{element_name}_content")
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
                                            logger.warning(f"  ⚠️ Tab validation: DOM unchanged for non-semantic tab")
                                            click_succeeded = False
                                            logger.error(f"  ❌ Tab switch FAILED - page content unchanged")
                                            continue  # Try next strategy
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
                        
                        # Extract XPath from result and update discovery if tracking was done
                        clicked_xpath = self._extract_xpath_from_result(result_msg)
                        if clicked_xpath and self.discoveries:
                            # Update most recent discovery for this element with clicked XPath
                            for discovery in reversed(self.discoveries):
                                if discovery.get('name') == element_name:
                                    discovery['xpath'] = clicked_xpath
                                    discovery['uniqueness_method'] = 'clicked_xpath'
                                    logger.info(f"  ✅ Updated discovery with clicked XPath: {clicked_xpath[:100]}")
                                    break
                        
                        return result_msg
                    
                    # First strategy always gets a chance, others need verification
                    if i == 0 and not click_succeeded:
                        logger.warning(f"  ⚠️ Click executed but no obvious result detected, trying next strategy...")
                        continue
                    
                except Exception as e:
                    last_error = e
                    logger.info(f"  Strategy {i+1} failed: {str(e)[:100]}")
                    continue
            
            # Special handling for UI-only buttons (CSS changes, dropdowns, etc)
            ui_only_patterns = ['collapse view', 'expand view', 'more', 'show more', 'show less']
            is_ui_only = any(pattern in selector.lower() for pattern in ui_only_patterns)
            
            if is_ui_only and not click_succeeded:
                # Check if click executed without throwing fatal error
                # For UI-only buttons, we consider it successful if no exception was thrown
                if last_error is None:
                    logger.info(f"  ✅ UI-only button clicked successfully: {selector}")
                    click_succeeded = True
                    
                    # For "More" button, wait for and verify dropdown menu appears
                    if 'more' in selector.lower():
                        await self.page.wait_for_timeout(1000)  # Wait for animation
                        logger.info(f"  ⏳ Waiting for dropdown menu to appear...")
                        
                        # Check if dropdown menu appeared
                        dropdown_appeared = False
                        dropdown_selectors = [
                            '[role="menu"]',
                            '[role="listbox"]',
                            '.dropdown-menu',
                            '[class*="dropdown"][class*="open"]',
                            '[class*="popover"]',
                            '[class*="menu"][class*="open"]'
                        ]
                        
                        for dropdown_sel in dropdown_selectors:
                            try:
                                count = await self.page.locator(dropdown_sel).count()
                                if count > 0:
                                    # Check if it's actually visible
                                    is_visible = await self.page.locator(dropdown_sel).nth(0).is_visible()
                                    if is_visible:
                                        logger.info(f"  ✅ Dropdown menu appeared: {dropdown_sel}")
                                        dropdown_appeared = True
                                        break
                            except Exception as e:
                                continue
                        
                        if not dropdown_appeared:
                            logger.warning(f"  ⚠️ Dropdown menu may not have appeared after clicking More")
                            # Take screenshot for debugging
                            try:
                                self.screenshot_counter += 1
                                filename = f"{self.screenshot_counter:03d}_more_clicked_no_dropdown.png"
                                filepath = self.screenshots_dir / filename
                                await self.page.screenshot(path=str(filepath), full_page=False)
                                logger.info(f"  📸 Debug screenshot: {filename}")
                            except:
                                pass
                    
                    # Return success message
                    return f"✅ UI button clicked: {selector} (CSS-only change)"
            
            # If all strategies tried and none verified
            logger.error(f"  ❌ All click strategies failed to produce expected result")
            return f"❌ Click FAILED: {selector} - No strategies produced verifiable result"
        
        elif tool_name == "browser_fill":
            selector = tool_input['selector']
            text = tool_input['text']
            logger.info(f"Fill: {selector} = {text}")
            
            # TOTP Detection: Check if this is a TOTP step
            step_metadata = self.parsed_steps.get(self.current_step_number, {})
            step_text = step_metadata.get('text', '')
            
            # Look for TOTP-related keywords
            totp_keywords = ["totp", "one-time", "one time", "2fa", "two-factor", "authenticator code", "security code"]
            step_has_totp = any(keyword in step_text.lower() for keyword in totp_keywords)
            text_has_totp = any(keyword in str(text).lower() for keyword in totp_keywords)
            is_totp_step = step_has_totp or text_has_totp
            
            if is_totp_step:
                logger.info(f"  [TOTP] Step {self.current_step_number} TOTP detected - generating code")
                
                # Extract secret key from step text or text parameter
                import os
                from utils.otp_helper import generate_otp
                # Note: re is already imported at module level (line 15)
                
                secret_key = None
                
                # Pattern 1: "secret key LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX"
                secret_pattern = r'(?:secret\s+key|key)\s+([A-Z0-9]{20,})'
                
                # Try to extract from original story (not lowercased parsed_steps)
                if self.story:
                    match = re.search(secret_pattern, self.story, re.IGNORECASE)
                    if match:
                        secret_key = match.group(1)
                        logger.info(f"  [TOTP] Extracted secret key from story: {secret_key[:10]}...")
                
                # Pattern 2: Look for long alphanumeric strings in step text
                if not secret_key:
                    long_alnum_pattern = r'\b([A-Z0-9]{20,})\b'
                    matches = re.findall(long_alnum_pattern, self.story if self.story else '')
                    if matches:
                        secret_key = max(matches, key=len)
                        logger.info(f"  [TOTP] Extracted potential secret key: {secret_key[:10]}...")
                
                # Try text parameter
                if not secret_key:
                    match = re.search(secret_pattern, str(text), re.IGNORECASE)
                    if match:
                        secret_key = match.group(1)
                        logger.info(f"  [TOTP] Extracted secret key from text parameter: {secret_key[:10]}...")
                
                # Generate TOTP code
                try:
                    if secret_key:
                        logger.info(f"  [TOTP] Generating TOTP code using secret key: {secret_key[:10]}...")
                        totp_code = generate_otp(secret_key)
                    else:
                        # Use environment variable
                        logger.info(f"  [TOTP] Generating TOTP code using TOTP_SECRET_KEY from environment")
                        totp_code = generate_otp()
                    
                    logger.info(f"  [TOTP] Generated TOTP code: {totp_code} (length: {len(totp_code)})")
                    original_text = text
                    text = totp_code
                    logger.info(f"  [TOTP] Replaced text '{original_text[:50]}...' with TOTP code")
                except Exception as e:
                    logger.error(f"  [TOTP] Failed to generate TOTP code: {e}")
                    # Continue with original text if TOTP generation fails
            
            # For TOTP fields, improve selector to exclude hidden inputs
            if is_totp_step:
                # CRITICAL FIX: Also trigger fallback for input[type="text"] (generic selector)
                # Successful runs used input[type="text"], but fallback only ran for input[name='code']
                selector_needs_fallback = (
                    selector == "input[name='code']" or 
                    selector == 'input[name="code"]' or 
                    "input[name='code']" in selector or
                    selector == 'input[type="text"]' or
                    selector == "input[type='text']"
                )
                
                if selector_needs_fallback:
                    # Try multiple selectors for visible TOTP input (prioritized by specificity)
                    totp_selectors = [
                        "input.one-time-code-input__input",  # Most specific: class from login.gov
                        "input[autocomplete='one-time-code']",  # Autocomplete attribute
                        "input[type='text'][name='code']",  # Explicit text input with name
                        "input[name='code']:not([type='hidden'])",  # Exclude hidden inputs
                        "lg-one-time-code-input input[type='text']",  # Inside custom component, text type
                        "lg-validated-field input[type='text']",  # Inside validated field, text type
                        "lg-one-time-code-input input",  # Inside custom component (any input)
                        "input.one-time-code",  # Alternative class name
                    ]
                    
                    # Try each selector until one works
                    selector_found = False
                    for totp_selector in totp_selectors:
                        try:
                            # Check if this selector finds a visible input
                            locator = self.page.locator(totp_selector).first
                            is_visible = await locator.is_visible(timeout=2000)
                            if is_visible:
                                selector = totp_selector
                                selector_found = True
                                logger.info(f"  [TOTP] Found visible input with selector: {selector}")
                                break
                        except Exception as e:
                            logger.debug(f"  [TOTP] Selector {totp_selector} failed: {e}")
                            continue
                    
                    if not selector_found:
                        logger.warning(f"  [TOTP] Could not find visible input with fallback selectors, using original: {selector}")
                        # Last resort: try to find any visible input with name='code'
                        try:
                            all_code_inputs = await self.page.locator("input[name='code']").all()
                            for inp in all_code_inputs:
                                if await inp.is_visible(timeout=1000):
                                    selector = "input[name='code']"
                                    logger.info(f"  [TOTP] Found visible input by iterating through all code inputs")
                                    break
                        except:
                            pass
            
            # Execute
            # For TOTP fields, use longer timeout (OTP valid for 10 minutes, no need to rush)
            timeout_ms = 60000 if is_totp_step else 10000
            await self.page.wait_for_selector(selector, state='visible', timeout=timeout_ms)
            
            # Check if field is editable using Playwright locator (avoids JS string escaping issues)
            try:
                locator = self.page.locator(selector).first
                is_readonly = await locator.evaluate("el => el.readOnly || el.disabled")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not check readonly status: {e}, proceeding anyway")
                is_readonly = False
            
            if is_readonly:
                logger.warning(f"  ⚠️ Field {selector} is readonly or disabled")
                return f"⚠️ Fill FAILED: {selector} is readonly/disabled"
            
            # For TOTP fields, use type() method for better reliability
            if is_totp_step:
                try:
                    await self.page.locator(selector).fill('')  # Clear first
                    await self.page.locator(selector).type(text, delay=10)  # Fast typing for TOTP
                    await self.page.wait_for_timeout(200)
                    logger.info(f"  [TOTP] Used type() method for TOTP field")
                except Exception as e:
                    logger.warning(f"  [TOTP] type() failed, using fill(): {e}")
                    await self.page.fill(selector, text)
            else:
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
        
        elif tool_name == "browser_verify_table":
            table_selector = tool_input.get('table_selector', 'visible_table')
            column_name = tool_input['column_name']
            expected_value = tool_input['expected_value']
            
            logger.info(f"Verify Table: Column '{column_name}' contains '{expected_value}'")
            
            try:
                # Take a pre-verification screenshot
                self.screenshot_counter += 1
                filename = f"{self.screenshot_counter:03d}_verify_table.png"
                filepath = self.screenshots_dir / filename
                await self.page.screenshot(path=str(filepath), full_page=False)
                screenshot_path = filename
                logger.info(f"  📸 Verification screenshot: {filename}")
                
                # Find the table
                if table_selector == 'visible_table':
                    # Auto-detect: Find first visible table
                    table = self.page.locator('table').nth(0)
                else:
                    table = self.page.locator(table_selector).nth(0)
                
                # Wait for table to be visible
                await table.wait_for(state='visible', timeout=10000)
                
                # Find column index by header text using shared utility
                from utils.table_verification import find_column_index
                
                headers = await table.locator('thead th, thead td').all_text_contents()
                column_index = find_column_index(headers, column_name)
                
                if column_index != -1:
                    # Log whether it was exact or partial match
                    if column_name.lower() == headers[column_index].lower().strip():
                        logger.info(f"  ✅ Found exact column match: '{headers[column_index].strip()}' at index {column_index}")
                    else:
                        logger.info(f"  ⚠️ Found partial column match: '{headers[column_index].strip()}' at index {column_index}")
                
                if column_index == -1:
                    logger.warning(f"  ⚠️ Column '{column_name}' not found in table headers: {headers}")
                    
                    # Store verification discovery
                    await self._track_discovery(
                        element_name=f"verify_table_{column_name}",
                        original_query=f"verify column {column_name}",
                        final_selector=table_selector,
                        discovery_method="table_verification",
                        metadata={
                            "verification_type": "table_column",
                            "column_name": column_name,
                            "expected_value": expected_value,
                            "result": "FAIL",
                            "reason": f"Column not found. Available: {headers}",
                            "screenshot": screenshot_path
                        }
                    )
                    
                    return f"❌ VERIFICATION FAILED: Column '{column_name}' not found. Available columns: {', '.join(headers)}"
                
                # Get all rows in that column
                rows = await table.locator('tbody tr').all()
                total_rows = len(rows)
                matching_rows = 0
                mismatches = []
                sample_values = []
                
                for row_idx, row in enumerate(rows):
                    cells = await row.locator('td').all()
                    if column_index < len(cells):
                        cell_text = await cells[column_index].inner_text()
                        cell_text = cell_text.strip()
                        
                        # Store sample values (first 3)
                        if len(sample_values) < 3:
                            sample_values.append(cell_text)
                        
                        # Check if expected value is in the cell text
                        if expected_value.lower() in cell_text.lower():
                            matching_rows += 1
                        else:
                            if len(mismatches) < 3:  # Store first 3 mismatches
                                mismatches.append(f"Row {row_idx + 1}: '{cell_text}'")
                
                # Determine pass/fail
                success = matching_rows == total_rows
                
                if success:
                    logger.info(f"  ✅ Verification PASSED: {matching_rows}/{total_rows} rows match")
                    
                    # Store verification discovery
                    await self._track_discovery(
                        element_name=f"verify_table_{column_name}",
                        original_query=f"verify column {column_name} = {expected_value}",
                        final_selector=table_selector,
                        discovery_method="table_verification",
                        metadata={
                            "verification_type": "table_column",
                            "column_name": column_name,
                            "expected_value": expected_value,
                            "result": "PASS",
                            "total_rows": total_rows,
                            "matching_rows": matching_rows,
                            "sample_values": sample_values,
                            "screenshot": screenshot_path
                        }
                    )
                    
                    return f"✅ VERIFICATION PASSED: All {total_rows} rows in '{column_name}' contain '{expected_value}'"
                else:
                    logger.warning(f"  ⚠️ Verification FAILED: {matching_rows}/{total_rows} rows match")
                    
                    # Store verification discovery
                    await self._track_discovery(
                        element_name=f"verify_table_{column_name}",
                        original_query=f"verify column {column_name} = {expected_value}",
                        final_selector=table_selector,
                        discovery_method="table_verification",
                        metadata={
                            "verification_type": "table_column",
                            "column_name": column_name,
                            "expected_value": expected_value,
                            "result": "FAIL",
                            "total_rows": total_rows,
                            "matching_rows": matching_rows,
                            "mismatches": mismatches,
                            "sample_values": sample_values,
                            "screenshot": screenshot_path
                        }
                    )
                    
                    mismatch_details = "; ".join(mismatches) if mismatches else "See screenshot"
                    return f"❌ VERIFICATION FAILED: {matching_rows}/{total_rows} rows match. Mismatches: {mismatch_details}"
                    
            except Exception as e:
                logger.error(f"  ❌ Table verification error: {e}")
                
                # Store verification discovery with error
                await self._track_discovery(
                    element_name=f"verify_table_{column_name}",
                    original_query=f"verify column {column_name} = {expected_value}",
                    final_selector=table_selector if table_selector != 'visible_table' else 'table',
                    discovery_method="table_verification",
                    metadata={
                        "verification_type": "table_column",
                        "column_name": column_name,
                        "expected_value": expected_value,
                        "result": "ERROR",
                        "error": str(e)
                    }
                )
                
                return f"❌ VERIFICATION ERROR: {str(e)}"
        
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
                    count_text = await count_locator.nth(0).text_content()
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
            },
            {
                "toolSpec": {
                    "name": "browser_verify_table",
                    "description": "Verify that all rows in a table column contain a specific value. Use this for data validation in tables.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "table_selector": {"type": "string", "description": "CSS selector for the table or 'visible_table' to auto-detect"},
                                "column_name": {"type": "string", "description": "Name of the column to verify (will match header text)"},
                                "expected_value": {"type": "string", "description": "Expected value that should appear in all rows"}
                            },
                            "required": ["column_name", "expected_value"]
                        }
                    }
                }
            }
        ]
    
    async def execute_story(self, story: str, max_iterations: int = 50) -> Dict[str, Any]:
        """
        AGENTIC LOOP - LLM makes real-time decisions
        """
        # Parse story and extract metadata for each step
        self.parse_story_metadata(story)
        
        logger.info(f"Execution {self.execution_id} starting")
        logger.info(f"Story: {story}")
        
        await self.start_browser()
        
        # Format story with action hints from parsed metadata
        enhanced_story = []
        for i, line in enumerate(story.strip().split('\n'), 1):
            metadata = self.parsed_steps.get(i, {})
            action_hint = ""
            if metadata.get('type') == 'checkbox':
                action_hint = " [ACTION: Click checkbox]"
            elif metadata.get('type') == 'accordion':
                action_hint = " [ACTION: Click to expand]"
            elif metadata.get('type') == 'tab':
                action_hint = " [ACTION: Click tab]"
            elif 'wait' in line.lower():
                action_hint = " [ACTION: Wait/No click]"
            elif 'verify' in line.lower():
                action_hint = " [ACTION: Use browser_verify_table]"
            enhanced_story.append(line + action_hint)
        
        formatted_story = '\n'.join(enhanced_story)
        logger.info(f"📝 Enhanced story with action hints:\n{formatted_story}")
        
        messages = [{
            "role": "user",
            "content": [{"text": f"Execute this test scenario:\n\n{formatted_story}\n\nFollow the [ACTION] hints for each step."}]
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

CRITICAL: EXTRACT EXACT ELEMENT NAMES
Read each step carefully and extract the EXACT element name to click:

Examples:
- Step: "Select the Acute leukemia, NOS checkbox" → Click: text=Acute leukemia, NOS
- Step: "Click on DIAGNOSIS to expand" → Click: text=DIAGNOSIS  
- Step: "Click on Diagnosis tab" → Click: text=Diagnosis
- Step: "Click Continue button" → Click: text=Continue

DO NOT use words from previous steps or context. ONLY use the exact element name in the current step.

ACTION HINTS:
- [ACTION: Click checkbox] → Extract checkbox name, use browser_click("text=<exact name>")
- [ACTION: Click to expand] → Extract accordion name, use browser_click("text=<exact name>")
- [ACTION: Click tab] → Extract tab name, use browser_click("text=<exact name>")
- [ACTION: Wait/No click] → Use browser_evaluate to wait (e.g., await new Promise(r => setTimeout(r, 2000)))
- [ACTION: Use browser_verify_table] → Use browser_verify_table(column_name="<name>", expected_value="<value>")

ELEMENT SELECTION:
- Always use text= selectors with the EXACT element name from the step
- System validates and finds the correct element automatically
- If element not found, system will use discovery methods

Take screenshots at key moments (after clicks, before verification)."""
        
        logger.info("🔄 Starting agentic loop...")
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
                            "result": result_text,
                            "screenshots": []  # Track screenshots for this action
                        }
                        
                        # Add page context for click actions
                        if tool_name == "browser_click":
                            try:
                                action_entry["page_url"] = self.page.url
                                action_entry["page_title"] = await self.page.title()
                            except:
                                pass
                        
                        # Extract screenshot filenames from result text
                        if "screenshot:" in result_text.lower() or ".png" in result_text:
                            import re
                            screenshot_matches = re.findall(r'(\d+_[\w\-]+\.png)', result_text)
                            if screenshot_matches:
                                action_entry["screenshots"] = screenshot_matches
                        
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
            
            # Save discovered XPaths to registry FIRST (this backfills element_id)
            if self.discoveries and self.current_url:
                try:
                    logger.info(f"  💾 Updating element registry with {len(self.discoveries)} discovered XPaths...")
                    
                    # Extract domain and page from URL
                    domain = self.current_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
                    
                    # Determine page name (use 'explore' for explore page, keep other paths as-is)
                    url_path = self.current_url.split('/')[-1].split('#')[0]
                    if url_path == 'explore':
                        page = 'explore'
                    elif not url_path or url_path == '':
                        page = 'home'
                    else:
                        page = url_path
                    
                    # Load existing registry or create new one
                    element_map = self.element_registry.load_map(domain, page)
                    if not element_map:
                        # Auto-create registry file if it doesn't exist
                        logger.info(f"  📝 Creating new registry for {domain}/{page}")
                        element_map = {
                            "page": page,
                            "url": f"https://{domain}/{page}" if page != 'home' else f"https://{domain}/",
                            "version": "1.0",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "elements": {},
                            "id_index": {},
                            "statistics": {
                                "total_elements": 0,
                                "parsed_elements": 0,
                                "discovered_elements": 0
                            }
                        }
                        # Save empty registry file first
                        self.element_registry.save_map(domain, page, element_map)
                        logger.info(f"  ✅ Created new registry file for {domain}/{page}")
                    
                    if element_map:
                        added_count = 0
                        for discovery in self.discoveries:
                            if discovery.get('xpath'):
                                element_name = discovery['name']
                                element_id = discovery.get('element_id')  # Get element_id from discovery
                                
                                # Create element entry
                                element_entry = {
                                    "selector": discovery['final_selector'],
                                    "xpath": discovery['xpath'],
                                    "uniqueness_method": discovery.get('uniqueness_method', 'unknown'),
                                    "type": discovery.get('metadata', {}).get('type', 'unknown'),
                                    "description": f"Discovered by AI in test {self.execution_id}",
                                    "source": "ai_discovery",
                                    "discovery_method": discovery['discovery_method'],
                                    "usage_count": 1,
                                    "alternatives": []
                                }
                                
                                # Assign element_id if not present
                                if element_id:
                                    element_entry['element_id'] = element_id
                                elif discovery['xpath']:
                                    # Generate ID if missing (using name + xpath for stability)
                                    element_entry['element_id'] = self.element_registry._generate_element_id(element_name, discovery['xpath'])
                                
                                # Check registry by XPath value (not just name)
                                xpath_value = discovery['xpath']
                                existing_key = None
                                
                                # Strategy 1: Check by element_id if available
                                if element_entry.get('element_id'):
                                    element_id_to_find = element_entry['element_id']
                                    for key, elem_data in element_map.get('elements', {}).items():
                                        if elem_data.get('element_id') == element_id_to_find:
                                            existing_key = key
                                            logger.info(f"    🎯 Found existing entry by element_id: {key} (ID: {element_id_to_find})")
                                            break
                                
                                # Strategy 2: Check by XPath value
                                if not existing_key and xpath_value:
                                    for key, elem_data in element_map.get('elements', {}).items():
                                        if elem_data.get('xpath') == xpath_value:
                                            existing_key = key
                                            logger.info(f"    🎯 Found existing entry by XPath: {key}")
                                            break
                                
                                # Strategy 3: Check by name (fallback)
                                if not existing_key and element_name in element_map.get('elements', {}):
                                    existing_key = element_name
                                    logger.info(f"    🎯 Found existing entry by name: {element_name}")
                                
                                if existing_key:
                                    # Update existing entry with clicked XPath and element_id
                                    existing_element = element_map['elements'][existing_key]
                                    
                                    # BACKFILL: If discovery is missing element_id, get it from registry
                                    if not element_id and existing_element.get('element_id'):
                                        element_id = existing_element.get('element_id')
                                        discovery['element_id'] = element_id  # Update discovery in-place
                                        logger.info(f"    🔄 Backfilled element_id into discovery: {element_id}")
                                    
                                    # PRESERVE MORE SPECIFIC XPATH: Don't overwrite manually updated XPaths
                                    existing_xpath = existing_element.get('xpath', '')
                                    discovery_xpath = element_entry.get('xpath', '')
                                    
                                    # Check if existing XPath is more specific than discovery XPath
                                    # More specific = contains element type (button, input, etc.) vs generic (*)
                                    existing_is_more_specific = False
                                    if existing_xpath and discovery_xpath:
                                        # Existing is more specific if it has element type and discovery doesn't
                                        # e.g., //button[...] is more specific than (//*[...])[1]
                                        if '//button' in existing_xpath or '//input' in existing_xpath or '//a' in existing_xpath:
                                            if '//*' in discovery_xpath or '(//*' in discovery_xpath:
                                                existing_is_more_specific = True
                                                logger.info(f"    🔒 Preserving more specific XPath: {existing_xpath[:80]}...")
                                    
                                    # Update registry entry, but preserve XPath if existing is more specific
                                    if existing_is_more_specific:
                                        # Keep existing XPath, update other fields
                                        preserved_xpath = existing_xpath
                                        existing_element.update(element_entry)
                                        existing_element['xpath'] = preserved_xpath  # Restore preserved XPath
                                        logger.info(f"    ✅ Preserved existing XPath (more specific): {preserved_xpath[:80]}...")
                                    else:
                                        # Update normally (discovery XPath is same or more specific)
                                        existing_element.update(element_entry)
                                    
                                    # Ensure element_id is preserved from registry if it exists
                                    if existing_element.get('element_id'):
                                        element_entry['element_id'] = existing_element['element_id']
                                        element_map['elements'][existing_key]['element_id'] = existing_element['element_id']
                                    logger.info(f"    📝 Updated registry entry: {existing_key}")
                                else:
                                    # Add new entry
                                    element_map['elements'][element_name] = element_entry
                                    added_count += 1
                                    logger.info(f"    ✅ Added to registry: {element_name} (ID: {element_entry.get('element_id', 'N/A')})")
                        
                        if added_count > 0:
                            # Update statistics
                            element_map['statistics']['total_elements'] = len(element_map['elements'])
                            element_map['statistics']['discovered_elements'] = element_map['statistics'].get('discovered_elements', 0) + added_count
                            
                            # Save updated registry
                            self.element_registry.save_map(domain, page, element_map)
                            logger.info(f"  ✅ Registry updated: Added {added_count} new XPath entries")
                        else:
                            logger.info(f"  ℹ️ No new entries added (all already in registry)")
                            
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not update registry: {e}")
            
            # NOW save discoveries to results and file (AFTER backfill, so element_ids are included)
            results["discoveries"] = self.discoveries
            
            # Also save to a separate JSON file for reference (AFTER backfill)
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
                
                logger.info(f"  💾 Discovery metadata saved to: {discovery_file} (with backfilled element_ids)")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not save discovery file: {e}")
        
        await self.close_browser()
        logger.info(f"Finished: {results['status']}")
        return results
