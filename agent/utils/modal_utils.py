"""
Modal Utilities - Shared modal detection and selector scoping logic
Eliminates code duplication between browser_click and browser_fill
"""
import logging
from typing import Tuple, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ModalUtils:
    """Shared utilities for modal detection and selector scoping"""
    
    @staticmethod
    async def is_modal_open(page: Page) -> Tuple[bool, Optional[str]]:
        """
        Check if a modal/dialog is currently open using generic patterns (no hard-coded selectors)
        Args:
            page: Playwright page object
        Returns: (is_open, modal_selector) tuple
        """
        try:
            # Check for standard ARIA dialog (generic pattern)
            dialog = page.locator('[role="dialog"]').first
            if await dialog.count() > 0:
                is_visible = await dialog.is_visible()
                if is_visible:
                    # Try to get a more specific selector if possible
                    try:
                        # Check if it has a data-testid (more specific)
                        data_testid = await dialog.get_attribute('data-testid')
                        if data_testid:
                            specific_selector = f'[data-testid="{data_testid}"]'
                            logger.info(f"  ✅ Modal detected: {specific_selector}")
                            return True, specific_selector
                    except Exception:
                        pass
                    
                    logger.info(f"  ✅ Modal detected: role=\"dialog\"")
                    return True, '[role="dialog"]'
            
            # Check for Material-UI dialog classes (generic pattern)
            mui_dialog = page.locator('.MuiDialog-root.MuiModal-root').first
            if await mui_dialog.count() > 0:
                is_visible = await mui_dialog.is_visible()
                if is_visible:
                    # Try to get a more specific selector if possible
                    try:
                        data_testid = await mui_dialog.get_attribute('data-testid')
                        if data_testid:
                            specific_selector = f'[data-testid="{data-testid}"]'
                            logger.info(f"  ✅ Modal detected: {specific_selector}")
                            return True, specific_selector
                    except Exception:
                        pass
                    
                    logger.info(f"  ✅ Modal detected: MuiDialog-root")
                    return True, '.MuiDialog-root.MuiModal-root'
            
            return False, None
        except Exception as e:
            logger.debug(f"  ⚠️ Modal detection failed: {e}")
            return False, None
    
    @staticmethod
    def should_check_modal(is_modal_open: bool, step_text: str, step_location: str = '', 
                          step_parent_hint: str = '') -> bool:
        """
        Determine if we should check modal context based on step metadata
        Args:
            is_modal_open: Whether modal is currently open
            step_text: Step text (lowercase)
            step_location: Step location metadata
            step_parent_hint: Step parent hint metadata
        Returns: True if modal context should be checked
        """
        if not is_modal_open:
            return False
        
        step_text_lower = step_text.lower() if step_text else ''
        step_location_lower = step_location.lower() if step_location else ''
        step_parent_hint_lower = step_parent_hint.lower() if step_parent_hint else ''
        
        return (
            'pop up' in step_text_lower or 'popup' in step_text_lower or 
            'dialog' in step_text_lower or 'modal' in step_text_lower or 
            step_location_lower == 'table' or
            'submission' in step_parent_hint_lower or 'form' in step_parent_hint_lower
        )
    
    @staticmethod
    def scope_selector_to_modal(selector: str, modal_selector: str) -> str:
        """
        Scope a selector to modal context
        Args:
            selector: Original selector
            modal_selector: Modal CSS selector (e.g., '[data-testid="create-submission-dialog"]')
        Returns: Scoped selector
        """
        if selector.startswith("xpath="):
            # For XPath, wrap with modal context check
            original_xpath = selector.replace("xpath=", "")
            scoped_selector = f"xpath=({modal_selector})//{original_xpath.lstrip('/')}"
            logger.info(f"  🔍 Scoping XPath selector to modal: {scoped_selector}")
            return scoped_selector
        elif selector.startswith("text="):
            # For text= selectors, use >> operator (Playwright chain syntax)
            text_content = selector.replace("text=", "")
            scoped_selector = f"{modal_selector} >> text={text_content}"
            logger.info(f"  🔍 Scoping text= selector to modal: {scoped_selector}")
            return scoped_selector
        else:
            # For CSS selectors, use Playwright chain syntax for ID selectors
            # ID selectors (#id) need >> operator, not CSS descendant
            if selector.startswith("#"):
                # For ID selectors, use Playwright chain syntax
                scoped_selector = f"{modal_selector} >> {selector}"
                logger.info(f"  🔍 Scoping ID selector to modal (using chain): {scoped_selector}")
                return scoped_selector
            else:
                # For other CSS selectors, use CSS descendant (space)
                scoped_selector = f"{modal_selector} {selector}"
                logger.info(f"  🔍 Scoping CSS selector to modal: {scoped_selector}")
                return scoped_selector

