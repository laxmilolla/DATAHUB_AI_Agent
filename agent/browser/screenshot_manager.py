"""
Screenshot Manager - Manage screenshot capture and storage
Extracted from bedrock_playwright_agent.py lines 47-49, 452-465, 584-686
"""
import logging
from pathlib import Path
from typing import Dict, Any
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Manage screenshot capture and storage"""
    
    def __init__(self, screenshots_dir: Path):
        """
        Initialize screenshot manager
        Args:
            screenshots_dir: Directory to save screenshots
        """
        self.screenshots_dir = screenshots_dir
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_counter = 0
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Remove special characters from filename that could cause issues
        """
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
    
    async def capture(self, page: Page, name: str = None) -> Dict[str, str]:
        """
        Capture screenshot
        Args:
            page: Playwright page object
            name: Optional name for screenshot file
        Returns: {path, filename}
        """
        self.screenshot_counter += 1
        if name:
            sanitized_name = self._sanitize_filename(name)
            filename = f"{self.screenshot_counter:03d}_{sanitized_name}.png"
        else:
            filename = f"{self.screenshot_counter:03d}_screenshot.png"
        
        filepath = self.screenshots_dir / filename
        await page.screenshot(path=str(filepath))
        
        return {
            "path": str(filepath),
            "filename": filename
        }
    
    async def capture_post_click(self, page: Page, locator: Locator, 
                                 element_name: str, clicked_text: str = "") -> Dict[str, Any]:
        """
        Capture screenshot after click
        Generic post-click green screenshot - handles elements that stay or disappear
        """
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
                await page.wait_for_timeout(300)
                await page.wait_for_timeout(1000)
                
                # Screenshot
                self.screenshot_counter += 1
                sanitized_element = self._sanitize_filename(element_name)
                filename = f"{self.screenshot_counter:03d}_post_click_{sanitized_element}.png"
                filepath = self.screenshots_dir / filename
                await page.screenshot(path=str(filepath))
                
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
                new_elements = page.locator(f'text="{search_text}"')
                element_found = False
                
                for i in range(await new_elements.count()):
                    elem = new_elements.nth(i)
                    try:
                        box = await elem.bounding_box()
                        # Heuristic: Top of page (y < 200) likely = result area (filter chips, headers)
                        if box and box['y'] < 200:
                            await elem.scroll_into_view_if_needed()
                            await page.wait_for_timeout(300)
                            await page.wait_for_timeout(1000)
                            
                            # Screenshot
                            self.screenshot_counter += 1
                            sanitized_element = self._sanitize_filename(element_name)
                            filename = f"{self.screenshot_counter:03d}_post_click_result_{sanitized_element}.png"
                            filepath = self.screenshots_dir / filename
                            await page.screenshot(path=str(filepath))
                            
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
                    await page.screenshot(path=str(filepath))
                    
                    result["screenshot_taken"] = True
                    result["screenshot_file"] = filename
                    result["screenshot_size"] = filepath.stat().st_size
                    logger.info(f"  📸 ✅ Post-click page screenshot: {filename} ({result['screenshot_size']} bytes)")
            
            return result
            
        except Exception as e:
            logger.warning(f"  ⚠️ Could not capture post-click screenshot: {e}")
            return result





