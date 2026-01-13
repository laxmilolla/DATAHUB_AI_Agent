"""
Playwright Manager - Manage Playwright browser lifecycle
Extracted from bedrock_playwright_agent.py lines 34-42, 137-196
"""
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page, Playwright

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """Manage Playwright browser lifecycle"""
    
    def __init__(self):
        """Initialize Playwright manager"""
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_url: str = ""
    
    async def start(self, headless: bool = True) -> None:
        """
        Start browser
        Args:
            headless: Run browser in headless mode
        """
        logger.info("Launching Chromium browser...")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        # Set larger viewport to ensure all tabs and elements are visible
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        logger.info("Browser ready")
    
    async def close(self) -> None:
        """Cleanup browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def get_page(self) -> Page:
        """
        Get current page
        Returns: Playwright Page object
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page
    
    def get_current_url(self) -> str:
        """
        Get current page URL
        Returns: Current URL string
        """
        if self.page:
            # URL is updated via _get_domain_and_page when needed
            return self.current_url
        return ""
    
    def set_current_url(self, url: str) -> None:
        """
        Set current URL
        Args:
            url: URL to set
        """
        self.current_url = url
    
    async def get_domain_and_page(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract domain and page from current URL - always fetch live from browser
        Returns: (domain, page_name) tuple
        """
        if not self.page:
            return None, None
        
        try:
            # Always get live URL from browser (don't cache)
            current_url = self.page.url
            self.current_url = current_url
            
            # Parse URL
            from urllib.parse import urlparse
            parsed = urlparse(current_url)
            domain = parsed.netloc or parsed.path.split('/')[0] if parsed.path else None
            
            # Extract page name from path
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                page_name = path_parts[-1].replace('.html', '').replace('.php', '')
                if not page_name:
                    page_name = path_parts[0] if path_parts else 'home'
            else:
                page_name = 'home'
            
            return domain, page_name
        except Exception as e:
            logger.warning(f"Failed to extract domain/page from URL: {e}")
            return None, None





