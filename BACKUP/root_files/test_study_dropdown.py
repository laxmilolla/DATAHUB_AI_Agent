"""
Test script to debug Study dropdown access and list options
"""
import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_study_dropdown():
    """Test accessing Study dropdown and listing options"""
    async with async_playwright() as p:
        # Connect to existing browser (user will have browser open with page already loaded)
        logger.info("Connecting to existing browser on port 9222...")
        logger.info("Make sure Chrome is running with: chrome --remote-debugging-port=9222")
        
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            contexts = browser.contexts
            if not contexts:
                logger.error("❌ No browser contexts found. Please open Chrome with remote debugging.")
                return
            
            context = contexts[0]
            pages = context.pages
            if not pages:
                logger.error("❌ No pages found. Please open a page in Chrome.")
                return
            
            # Use the first open page
            page = pages[0]
            current_url = page.url
            logger.info(f"✅ Connected to existing browser")
            logger.info(f"📄 Using page: {current_url}")
            
            # Wait a moment for page to be ready
            await page.wait_for_timeout(1000)
            
        except Exception as e:
            logger.error(f"❌ Could not connect to existing browser: {e}")
            logger.info("Please start Chrome with: chrome --remote-debugging-port=9222")
            return
        
        try:
            # Check if we're on the right page
            current_url = page.url
            logger.info(f"Current page URL: {current_url}")
            
            if "data-submissions" not in current_url:
                logger.warning(f"⚠️ Not on data-submissions page. Current URL: {current_url}")
                logger.info("Please navigate to: https://hub-stage.datacommons.cancer.gov/data-submissions")
                logger.info("Waiting 5 seconds for you to navigate...")
                await page.wait_for_timeout(5000)
                current_url = page.url
                logger.info(f"Current URL after wait: {current_url}")
            
            logger.info("Step 1: Check if modal is already open")
            modal = page.locator('[data-testid="create-submission-dialog"]').first
            if await modal.count() > 0 and await modal.is_visible():
                logger.info("✅ Modal is already open")
            else:
                logger.error("❌ Modal is not open. Please open the 'Create a Data Submission' modal first.")
                await page.screenshot(path="test_modal_not_open.png", full_page=True)
                return
            
            logger.info("Step 2: Find Study dropdown button in the modal")
            # CRITICAL: Scope all selectors to the modal first
            modal_scope = '[data-testid="create-submission-dialog"]'
            
            # Material-UI Select: Find the actual clickable div button (not the hidden input)
            # The actual button has id="mui-component-select-studyID" and role="button"
            study_selectors = [
                # Direct ID match - most reliable
                f'{modal_scope} #mui-component-select-studyID',
                f'{modal_scope} [id="mui-component-select-studyID"]',
                # Material-UI Select button pattern - the actual clickable element
                f'{modal_scope} div[role="button"][aria-haspopup="listbox"][id*="studyID"]',
                f'{modal_scope} div[role="button"][aria-haspopup="listbox"]',
                f'{modal_scope} .MuiSelect-select[id*="studyID"]',
                f'{modal_scope} [class*="MuiSelect-select"][id*="studyID"]',
                f'{modal_scope} [id*="mui-component-select-studyID"]',
            ]
            
            study_button = None
            for selector in study_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() > 0:
                        is_visible = await locator.is_visible()
                        logger.info(f"  Found selector: {selector}, visible: {is_visible}")
                        if is_visible:
                            study_button = locator
                            break
                except Exception as e:
                    logger.debug(f"  Selector {selector} failed: {e}")
            
            if not study_button:
                logger.error("❌ Could not find Study dropdown button")
                logger.info("Taking screenshot...")
                await page.screenshot(path="test_study_dropdown_error.png", full_page=True)
                return
            
            logger.info("Step 3: Get Study button details")
            study_text = await study_button.text_content()
            study_id = await study_button.get_attribute('id')
            study_role = await study_button.get_attribute('role')
            study_class = await study_button.get_attribute('class')
            study_aria_label = await study_button.get_attribute('aria-labelledby')
            study_aria_haspopup = await study_button.get_attribute('aria-haspopup')
            logger.info(f"  Study button text: {study_text}")
            logger.info(f"  Study button ID: {study_id}")
            logger.info(f"  Study button role: {study_role}")
            logger.info(f"  Study button class: {study_class}")
            logger.info(f"  Study button aria-labelledby: {study_aria_label}")
            logger.info(f"  Study button aria-haspopup: {study_aria_haspopup}")
            
            # Verify it's actually in the modal
            is_in_modal = await study_button.locator('xpath=ancestor::*[@data-testid="create-submission-dialog"]').count() > 0
            logger.info(f"  Is Study button inside modal: {is_in_modal}")
            
            logger.info("Step 4: Click Study dropdown")
            await study_button.click()
            await page.wait_for_timeout(2000)
            
            logger.info("Step 5: Look for dropdown menu portal")
            # Material-UI dropdowns render in a portal
            menu_selectors = [
                '.MuiPopover-root [role="listbox"]',
                '[role="listbox"]',
                '.MuiMenu-root',
                '.MuiPopover-root .MuiMenu-list',
                '[data-testid="create-submission-dialog"] [role="listbox"]'
            ]
            
            menu_found = False
            for selector in menu_selectors:
                try:
                    menu = page.locator(selector).first
                    if await menu.count() > 0:
                        is_visible = await menu.is_visible()
                        logger.info(f"  Found menu selector: {selector}, visible: {is_visible}")
                        if is_visible:
                            menu_found = True
                            
                            logger.info("Step 6: List all options in dropdown")
                            options = menu.locator('[role="option"]')
                            option_count = await options.count()
                            logger.info(f"  Found {option_count} options:")
                            
                            for i in range(option_count):
                                option = options.nth(i)
                                option_text = await option.text_content()
                                option_id = await option.get_attribute('id')
                                option_value = await option.get_attribute('data-value')
                                logger.info(f"    Option {i+1}: '{option_text}' (id: {option_id}, value: {option_value})")
                            
                            # Take screenshot
                            await page.screenshot(path="test_study_dropdown_open.png", full_page=True)
                            logger.info("✅ Screenshot saved: test_study_dropdown_open.png")
                            break
                except Exception as e:
                    logger.debug(f"  Menu selector {selector} failed: {e}")
            
            if not menu_found:
                logger.error("❌ Could not find dropdown menu after clicking")
                logger.info("Taking screenshot...")
                await page.screenshot(path="test_study_dropdown_no_menu.png", full_page=True)
                
                # Try to find any open menus/popovers
                logger.info("Checking for any open popovers/menus...")
                popovers = await page.locator('.MuiPopover-root').all()
                for i, popover in enumerate(popovers):
                    is_visible = await popover.is_visible()
                    logger.info(f"  Popover {i+1}: visible={is_visible}")
                    if is_visible:
                        popover_html = await popover.inner_html()
                        logger.info(f"    HTML: {popover_html[:200]}")
            
            logger.info("Step 7: Check Study button state after click")
            study_text_after = await study_button.text_content()
            study_aria_expanded = await study_button.get_attribute('aria-expanded')
            logger.info(f"  Study button text after click: {study_text_after}")
            logger.info(f"  Study button aria-expanded: {study_aria_expanded}")
            
            # Close Study dropdown if still open
            if study_aria_expanded == "true":
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            
            logger.info("\n" + "="*60)
            logger.info("TESTING DATACOMMONS DROPDOWN")
            logger.info("="*60)
            
            logger.info("Step 8: Find Datacommons dropdown button in the modal")
            # Try to find all dropdowns first to see what IDs exist
            logger.info("  Searching for all Material-UI Select components in modal...")
            all_selects = await modal.locator('[id*="mui-component-select"]').all()
            logger.info(f"  Found {len(all_selects)} Material-UI Select components:")
            for i, select in enumerate(all_selects):
                select_id = await select.get_attribute('id')
                select_role = await select.get_attribute('role')
                select_text = await select.text_content()
                select_aria = await select.get_attribute('aria-labelledby')
                logger.info(f"    Select {i+1}: id='{select_id}', role='{select_role}', text='{select_text}', aria-labelledby='{select_aria}'")
            
            datacommons_selectors = [
                f'{modal_scope} #mui-component-select-datacommonsID',
                f'{modal_scope} [id="mui-component-select-datacommonsID"]',
                f'{modal_scope} div[role="button"][aria-haspopup="listbox"][id*="datacommons"]',
                f'{modal_scope} [id*="mui-component-select"][id*="datacommons"]',
                f'{modal_scope} [aria-labelledby*="datacommons"]',
                f'{modal_scope} [aria-labelledby*="Data Commons"]',
                # Try finding by text content "GC" or "Select"
                f'{modal_scope} div[role="button"]:has-text("GC")',
                f'{modal_scope} div[role="button"]:has-text("Select")',
            ]
            
            datacommons_button = None
            for selector in datacommons_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() > 0:
                        is_visible = await locator.is_visible()
                        logger.info(f"  Found selector: {selector}, visible: {is_visible}")
                        if is_visible:
                            datacommons_button = locator
                            break
                except Exception as e:
                    logger.debug(f"  Selector {selector} failed: {e}")
            
            if datacommons_button:
                logger.info("Step 9: Get Datacommons button details")
                datacommons_text = await datacommons_button.text_content()
                datacommons_id = await datacommons_button.get_attribute('id')
                datacommons_role = await datacommons_button.get_attribute('role')
                datacommons_class = await datacommons_button.get_attribute('class')
                logger.info(f"  Datacommons button text: '{datacommons_text}'")
                logger.info(f"  Datacommons button ID: {datacommons_id}")
                logger.info(f"  Datacommons button role: {datacommons_role}")
                logger.info(f"  Datacommons button class: {datacommons_class}")
                
                logger.info("Step 10: Click Datacommons dropdown")
                await datacommons_button.click()
                await page.wait_for_timeout(2000)
                
                logger.info("Step 11: Look for Datacommons dropdown menu")
                menu_found_dc = False
                for selector in menu_selectors:
                    try:
                        menu = page.locator(selector).first
                        if await menu.count() > 0:
                            is_visible = await menu.is_visible()
                            if is_visible:
                                menu_found_dc = True
                                logger.info("Step 12: List all Datacommons options")
                                options = menu.locator('[role="option"]')
                                option_count = await options.count()
                                logger.info(f"  Found {option_count} options:")
                                
                                for i in range(option_count):
                                    option = options.nth(i)
                                    option_text = await option.text_content()
                                    option_id = await option.get_attribute('id')
                                    option_value = await option.get_attribute('data-value')
                                    logger.info(f"    Option {i+1}: '{option_text}' (id: {option_id}, value: {option_value})")
                                break
                    except Exception as e:
                        logger.debug(f"  Menu selector {selector} failed: {e}")
                
                if not menu_found_dc:
                    logger.warning("  ⚠️ Could not find Datacommons dropdown menu")
                
                # Close dropdown
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            else:
                logger.warning("  ⚠️ Could not find Datacommons dropdown button")
            
            logger.info("\n" + "="*60)
            logger.info("TESTING SUBMISSION NAME INPUT FIELD")
            logger.info("="*60)
            
            logger.info("Step 13: Find Submission Name input field in the modal")
            submission_name_selectors = [
                f'{modal_scope} input[name="submissionName"]',
                f'{modal_scope} input[name="submissionName"]',
                f'{modal_scope} input[type="text"][name*="submission"]',
                f'{modal_scope} input[id*="submissionName"]',
                f'{modal_scope} input[placeholder*="25 characters"]',
            ]
            
            submission_name_input = None
            for selector in submission_name_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() > 0:
                        is_visible = await locator.is_visible()
                        logger.info(f"  Found selector: {selector}, visible: {is_visible}")
                        if is_visible:
                            submission_name_input = locator
                            break
                except Exception as e:
                    logger.debug(f"  Selector {selector} failed: {e}")
            
            if submission_name_input:
                logger.info("Step 14: Get Submission Name input details")
                input_name = await submission_name_input.get_attribute('name')
                input_id = await submission_name_input.get_attribute('id')
                input_type = await submission_name_input.get_attribute('type')
                input_placeholder = await submission_name_input.get_attribute('placeholder')
                input_value = await submission_name_input.get_attribute('value')
                input_class = await submission_name_input.get_attribute('class')
                logger.info(f"  Input name: {input_name}")
                logger.info(f"  Input ID: {input_id}")
                logger.info(f"  Input type: {input_type}")
                logger.info(f"  Input placeholder: {input_placeholder}")
                logger.info(f"  Input value: {input_value}")
                logger.info(f"  Input class: {input_class}")
                
                logger.info("Step 15: Test typing into Submission Name field")
                await submission_name_input.click()
                await page.wait_for_timeout(500)
                # Try multiple methods to fill
                await submission_name_input.clear()
                await page.wait_for_timeout(200)
                await submission_name_input.type("Test Submission Name", delay=50)
                await page.wait_for_timeout(500)
                new_value = await submission_name_input.input_value()
                logger.info(f"  Value after type: '{new_value}'")
                if not new_value:
                    # Try fill method
                    await submission_name_input.fill("Test Submission Name 2")
                    await page.wait_for_timeout(500)
                    new_value = await submission_name_input.input_value()
                    logger.info(f"  Value after fill: '{new_value}'")
                if new_value:
                    logger.info(f"  ✅ Successfully typed. New value: '{new_value}'")
                else:
                    logger.warning(f"  ⚠️ Typing didn't work. Trying evaluate...")
                    await page.evaluate('''(selector) => {
                        const input = document.querySelector(selector);
                        if (input) {
                            input.value = "Test Submission Name 3";
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }''', f'{modal_scope} input[name="name"]')
                    await page.wait_for_timeout(500)
                    new_value = await submission_name_input.input_value()
                    logger.info(f"  Value after evaluate: '{new_value}'")
                
                # Clear it
                await submission_name_input.clear()
                await page.wait_for_timeout(500)
                logger.info("  ✅ Cleared the field")
            else:
                logger.error("  ❌ Could not find Submission Name input field")
            
            await page.wait_for_timeout(2000)
            
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}", exc_info=True)
            await page.screenshot(path="test_study_dropdown_exception.png", full_page=True)
        
        finally:
            # Don't close browser - user is using it
            logger.info("Test complete. Browser remains open.")


if __name__ == "__main__":
    asyncio.run(test_study_dropdown())

