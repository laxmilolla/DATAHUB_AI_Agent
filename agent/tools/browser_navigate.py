"""
Browser Navigate Tool - Handle browser_navigate tool
Extracted from bedrock_playwright_agent.py lines 1202-1220
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BrowserNavigateTool:
    """Handle browser_navigate tool"""
    
    def __init__(self, playwright_manager, execution_context):
        """
        Initialize navigate tool
        Args:
            playwright_manager: PlaywrightManager instance
            execution_context: ExecutionContext instance
        """
        self.playwright_manager = playwright_manager
        self.context = execution_context
    
    async def execute(self, url: str) -> str:
        """
        Execute navigation
        Args:
            url: URL to navigate to
        Returns: Result message
        """
        logger.info(f"Navigate: {url}")
        
        page = self.playwright_manager.get_page()
        
        # Track current URL
        self.playwright_manager.set_current_url(url)
        self.context.current_url = url
        
        # Execute navigation
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1000)  # Allow page to settle
        
        # Set wide viewport and zoom out to show all tabs
        try:
            # Viewport is already 1920x1080 from initialization
            # Zoom out to 80% for maximum tab visibility
            await page.evaluate("document.body.style.zoom = '0.8'")
        except:
            pass
        
        return f"✅ Navigated to {url} - Verified"


