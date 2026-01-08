"""
Action Executor - Execute browser actions with validation
Extracted from bedrock_playwright_agent.py lines 493-776, 1973-2044
"""
import re
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Execute browser actions with validation"""
    
    def __init__(self, page: Page, screenshot_manager):
        """
        Initialize action executor
        Args:
            page: Playwright page object
            screenshot_manager: ScreenshotManager instance
        """
        self.page = page
        self.screenshot_manager = screenshot_manager
    
    async def validate_visibility(self, selector: str, element_description: str = "") -> Dict[str, Any]:
        """
        Pre-click validation: Verify element exists and is visible
        Returns: Validation result dict with locator preserved
        """
        validation_result = {
            "exists": False,
            "visible": False,
            "enabled": False,
            "text_content": "",
            "location": {},
            "screenshot_taken": False,
            "screenshot_file": None,
            "screenshot_size": None,
            "locator": None,
            "selector": selector
        }
        
        try:
            locator = self.page.locator(selector).nth(0)
            validation_result["locator"] = locator
            validation_result["selector"] = selector
            
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
                validation_result["text_content"] = await locator.text_content() or ""
            except:
                pass
            
            # Get location
            try:
                box = await locator.bounding_box()
                if box:
                    validation_result["location"] = {"x": box["x"], "y": box["y"]}
            except:
                pass
            
            # Take screenshot (no highlighting to avoid auto-expansion)
            if validation_result["visible"]:
                try:
                    screenshot_result = await self.screenshot_manager.capture(
                        self.page, f"pre_click_{element_description}"
                    )
                    validation_result["screenshot_taken"] = True
                    validation_result["screenshot_file"] = screenshot_result.get("filename")
                    validation_result["screenshot_size"] = screenshot_result.get("size", 0)
                    logger.info(f"  ✅ Pre-validation: Element visible in screenshot: {validation_result['screenshot_file']}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not capture screenshot: {e}")
            
            return validation_result
        except Exception as e:
            logger.warning(f"  ⚠️ Pre-validation error: {e}")
            return validation_result
    
    async def validate_filter_applied(self, filter_name: str, initial_state: Dict) -> Dict[str, Any]:
        """
        Post-click validation: Verify filter was actually applied
        Returns: Validation result dict
        """
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
            
            # Check 2: Visual indicator
            try:
                selected_elements = await self.page.locator('[aria-checked="true"], [aria-selected="true"], .selected, .active').count()
                if selected_elements > 0:
                    validation_result["visual_indicator"] = True
                    logger.info(f"  ✓ Found {selected_elements} selected/active elements")
            except:
                pass
            
            # Check 3: Count changed
            try:
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
            except Exception as e:
                logger.warning(f"  ⚠️ Could not check count: {e}")
            
            # Check 4: Data filtered
            try:
                new_html = await self.page.content()
                if filter_name.upper() in new_html or filter_name.lower() in new_html:
                    validation_result["data_filtered"] = True
                    logger.info(f"  ✓ Filter name '{filter_name}' appears in page content")
            except:
                pass
            
            # Determine verdict
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
    
    async def click(self, locator: Locator, force: bool = False) -> None:
        """
        Execute click on locator
        Args:
            locator: Playwright locator
            force: Force click if needed
        """
        if force:
            await locator.click(force=True)
        else:
            await locator.click()
    
    async def fill(self, locator: Locator, text: str) -> None:
        """
        Execute fill on locator
        Args:
            locator: Playwright locator
            text: Text to fill
        """
        await locator.fill(text)
    
    async def type_text(self, locator: Locator, text: str, delay: int = 10) -> None:
        """
        Type text character by character
        Args:
            locator: Playwright locator
            text: Text to type
            delay: Delay between characters (ms)
        """
        await locator.type(text, delay=delay)


