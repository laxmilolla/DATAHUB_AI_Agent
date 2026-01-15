"""
Experiment Runner - Thin wrapper around Agent for Experiment Area
Runs in headful mode and records actions/screenshots
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Import Agent from BACKUP (will be copied to root later)
import sys
from pathlib import Path as PathLib
backup_path = PathLib(__file__).parent.parent.parent / 'BACKUP'
sys.path.insert(0, str(backup_path))

from agent.core.agent import Agent
from agent.browser.playwright_manager import PlaywrightManager

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Experiment runner - wraps Agent for headful execution"""
    
    def __init__(self, session_id: str):
        """
        Initialize experiment runner
        Args:
            session_id: Unique session ID
        """
        self.session_id = session_id
        self.agent = None
        self.playwright_manager = None
        self.results = None
    
    async def start_browser(self, cdp_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Start browser in headful mode or connect to user's browser via CDP
        
        Args:
            cdp_url: Chrome DevTools Protocol URL (e.g., 'http://localhost:9222')
                    If provided, connects to user's browser instead of starting new one
        
        Returns:
            Dict with browser info
        """
        try:
            # Create PlaywrightManager
            self.playwright_manager = PlaywrightManager()
            
            # If CDP URL provided, connect to user's browser
            if cdp_url:
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                
                # Connect to user's Chrome browser via CDP
                browser = await playwright.chromium.connect_over_cdp(cdp_url)
                
                # Get pages from browser contexts (CDP connection requires accessing contexts first)
                contexts = browser.contexts
                if contexts and len(contexts) > 0:
                    context = contexts[0]
                    pages = context.pages
                    if pages and len(pages) > 0:
                        # Use existing page from the browser
                        page = pages[0]
                    else:
                        # Create new page in existing context
                        page = await context.new_page()
                else:
                    # No contexts found, create new context and page
                    context = await browser.new_context()
                    page = await context.new_page()
                
                # Set playwright_manager's browser/page
                self.playwright_manager.playwright = playwright
                self.playwright_manager.browser = browser
                self.playwright_manager.page = page
            else:
                # Start new browser in headful mode
                await self.playwright_manager.start(headless=False)  # Headful mode
            
            page = self.playwright_manager.get_page()
            
            # Initialize Agent with existing browser
            self.agent = Agent()
            # Replace agent's playwright_manager with ours (so it uses our browser)
            self.agent.playwright_manager = self.playwright_manager
            
            # Monkey-patch playwright_manager.start to skip if browser already exists
            original_start = self.playwright_manager.start
            async def start_if_needed(headless=True):
                """Only start browser if it doesn't already exist"""
                if self.playwright_manager.browser is None:
                    await original_start(headless=headless)
                # Otherwise, browser already exists, do nothing
            self.playwright_manager.start = start_if_needed
            
            return {
                'success': True,
                'session_id': self.session_id,
                'browser_url': page.url,
                'mode': 'cdp' if cdp_url else 'local'
            }
            
        except Exception as e:
            logger.error(f"Error starting browser: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_instructions(self, instructions: str) -> Dict[str, Any]:
        """
        Execute test instructions using Agent
        Args:
            instructions: Test instructions text
        Returns:
            Dict with execution results
        """
        try:
            if not self.agent:
                return {'success': False, 'error': 'Browser not started'}
            
            # Execute using Agent
            self.results = await self.agent.execute_story(instructions)
            
            return {
                'success': True,
                'results': self.results,
                'actions': self.results.get('actions_taken', []),
                'screenshots': self.results.get('screenshots', []),
                'status': self.results.get('status', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error executing instructions: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }
    
    async def stop_browser(self):
        """Stop browser session"""
        try:
            if self.playwright_manager:
                await self.playwright_manager.close()
                self.playwright_manager = None
            self.agent = None
        except Exception as e:
            logger.error(f"Error stopping browser: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current execution status
        Returns:
            Dict with status info
        """
        if not self.agent:
            return {'status': 'not_started'}
        
        context = self.agent.context
        actions = context.actions_taken
        
        return {
            'status': context.status,
            'current_step': len(actions),
            'total_steps': len(actions),  # Will be updated as execution progresses
            'step_description': actions[-1].get('tool', 'Unknown') if actions else 'Waiting...',
            'screenshots_count': len(context.screenshots)
        }
    
    def get_screenshots(self) -> list:
        """Get list of screenshot filenames"""
        if not self.agent:
            return []
        return self.agent.context.screenshots
    
    def get_results(self) -> Optional[Dict[str, Any]]:
        """Get execution results"""
        return self.results

