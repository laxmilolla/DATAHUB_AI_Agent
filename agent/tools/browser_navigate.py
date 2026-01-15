"""
Browser Navigate Tool - Handle browser_navigate tool
Extracted from bedrock_playwright_agent.py lines 1202-1220
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BrowserNavigateTool:
    """Handle browser_navigate tool"""
    
    def __init__(self, playwright_manager, execution_context, discovery_tracker=None):
        """
        Initialize navigate tool
        Args:
            playwright_manager: PlaywrightManager instance
            execution_context: ExecutionContext instance
            discovery_tracker: DiscoveryTracker instance (optional, for URL tracking)
        """
        self.playwright_manager = playwright_manager
        self.context = execution_context
        self.discovery_tracker = discovery_tracker
    
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
        
        # Update discovery tracker URL if available
        if self.discovery_tracker:
            self.discovery_tracker.update_url(url)
        
        # Execute navigation
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1000)  # Allow page to settle
        
        # Update URL again after navigation (in case of redirects)
        actual_url = page.url
        if actual_url != url:
            self.playwright_manager.set_current_url(actual_url)
            self.context.current_url = actual_url
            if self.discovery_tracker:
                self.discovery_tracker.update_url(actual_url)
        
        # Set wide viewport and zoom out to show all tabs
        try:
            # Viewport is already 1920x1080 from initialization
            # Zoom out to 80% for maximum tab visibility
            await page.evaluate("document.body.style.zoom = '0.8'")
        except:
            pass
        
        return f"✅ Navigated to {url} - Verified"


