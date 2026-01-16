"""
Test script to run Excel steps and then add specific instructions
"""
import asyncio
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import os
from datetime import datetime
from dotenv import load_dotenv

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'BACKUP'))

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f'✅ Loaded environment variables from {env_path}')

def run_excel_steps():
    """Run the Excel-generated test steps and return browser/page"""
    print("\n" + "="*80)
    print("PHASE 1: Running Excel Test Steps")
    print("="*80)
    
    try:
        # Import the generator and run Excel steps directly
        from REFACTOR.generator.excel_generator import generate_playwright_from_excel
        
        excel_file = Path('test_case.xlsx')
        if not excel_file.exists():
            print(f"❌ Excel file not found: {excel_file}")
            return None, None
        
        # Read Excel and execute steps directly
        import pandas as pd
        df = pd.read_excel(excel_file)
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Create browser
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            
            TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
            critical_failures = []
            current_url = None
            
            # Execute each step
            for idx, row in df.iterrows():
                step = str(row.get('step', idx + 1)).strip()
                url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else None
                xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
                action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else 'click'
                object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
                functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else ''
                text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else ''
                wait_time = row.get('wait_time', None)
                is_optional = str(row.get('optional', '')).strip().lower() in ['true', 'yes', '1', 'y']
                
                # Update current URL
                if url and url != 'N/A':
                    current_url = url
                
                page.wait_for_timeout(3000)  # Wait 3 seconds before each step
                
                try:
                    if action == 'navigate':
                        if url:
                            page.goto(url)
                            page.wait_for_load_state('networkidle')
                            print(f'📍 Step {step}: Navigated to {url}')
                            page.screenshot(path=f'storage/screenshots/pw_step{step}_navigate.png')
                    
                    elif action == 'wait':
                        wait_ms = int(wait_time) if wait_time else 1000
                        page.wait_for_timeout(wait_ms)
                        print(f'⏱️  Step {step}: Waited {wait_ms}ms')
                    
                    elif action == 'click':
                        if xpath and xpath != 'N/A':
                            selector = f'xpath={xpath}'
                            element = page.locator(selector).nth(0)
                            element.wait_for(state='visible', timeout=10000)
                            element.click()
                            page.wait_for_timeout(1000)
                            print(f'✅ Step {step}: Clicked {object_type or "element"}')
                            page.screenshot(path=f'storage/screenshots/pw_step{step}_{object_type or "element"}.png')
                    
                    elif action == 'fill':
                        if xpath and xpath != 'N/A':
                            # Handle TOTP with multiple selector fallbacks
                            if 'TOTP' in str(functions).upper():
                                # TOTP field - try multiple selectors (fallback approach)
                                totp_selectors = [
                                    'input.one-time-code-input__input',
                                    "input[autocomplete='one-time-code']",
                                    "input[type='text'][name='code']",
                                    "input[name='code']:not([type='hidden'])",
                                    'lg-one-time-code-input input[type="text"]',
                                    'lg-validated-field input[type="text"]',
                                    'lg-one-time-code-input input',
                                    'input.one-time-code',
                                    f'xpath={xpath}',  # Fallback to provided XPath
                                ]
                                selector_found = False
                                element = None
                                for totp_sel in totp_selectors:
                                    try:
                                        test_elem = page.locator(totp_sel).first
                                        if test_elem.is_visible(timeout=2000):
                                            element = test_elem
                                            selector_found = True
                                            print(f'✅ Step {step}: Found TOTP field with selector: {totp_sel}')
                                            break
                                    except:
                                        continue
                                if not selector_found:
                                    # Fallback to original selector
                                    selector = f'xpath={xpath}'
                                    element = page.locator(selector).nth(0)
                                    element.wait_for(state='visible', timeout=10000)
                                    print(f'⚠️  Step {step}: TOTP field not found with fallback selectors, using original selector')
                                
                                try:
                                    import pyotp
                                except ImportError:
                                    # Auto-install pyotp if missing
                                    import subprocess
                                    import sys
                                    print('⚠️  pyotp not found. Attempting to install...')
                                    try:
                                        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyotp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                        import pyotp
                                        print('✅ pyotp installed successfully')
                                    except Exception as install_error:
                                        raise Exception('pyotp library not installed and auto-install failed. Please install manually with: pip3 install pyotp')
                                
                                try:
                                    secret_key = os.getenv('TOTP_SECRET_KEY')
                                    if not secret_key:
                                        raise ValueError('TOTP_SECRET_KEY not found in environment variables')
                                    totp = pyotp.TOTP(secret_key)
                                    totp_code = totp.now()
                                    print(f'🔐 Step {step}: Generated TOTP code: {totp_code[:2]}****')
                                    
                                    # For TOTP: clear field first, then use type() with delay (more reliable than fill())
                                    element.fill('')
                                    element.type(totp_code, delay=10)
                                    page.wait_for_timeout(200)
                                    print(f'✅ Step {step}: Filled TOTP code using type() method')
                                except Exception as e:
                                    print(f'❌ Step {step}: Failed to generate/fill TOTP code: {e}')
                                    # Try fallback fill() method
                                    try:
                                        element.fill(totp_code)
                                        print(f'✅ Step {step}: Filled TOTP code using fill() fallback')
                                    except Exception as fill_error:
                                        print(f'❌ Step {step}: fill() fallback also failed: {fill_error}')
                                        raise
                            else:
                                # Non-TOTP field - use XPath directly
                                selector = f'xpath={xpath}'
                                element = page.locator(selector).nth(0)
                                element.wait_for(state='visible', timeout=10000)
                                
                                # Handle fill value
                                if '${TIMESTAMP}' in text_value:
                                    fill_value = text_value.replace('${TIMESTAMP}', TIMESTAMP)
                                    element.fill(fill_value)
                                    print(f'✅ Step {step}: Filled with {fill_value}')
                                else:
                                    element.fill(text_value)
                                    print(f'✅ Step {step}: Filled with {text_value}')
                            
                            page.wait_for_timeout(500)
                            page.screenshot(path=f'storage/screenshots/pw_step{step}_{object_type or "input"}.png')
                
                except Exception as e:
                    if is_optional:
                        print(f'ℹ️  Step {step}: Element not found (optional) - continuing')
                    else:
                        print(f'❌ Step {step}: Failed - {e}')
                        critical_failures.append(f'Step {step}: {action} failed')
            
            if critical_failures:
                print(f"\n⚠️  Completed with {len(critical_failures)} failure(s)")
            else:
                print("\n✅ Phase 1 Complete: All Excel steps executed successfully")
            
            print("Browser will remain open for additional instructions...")
            
            # Return browser and page (keep browser open)
            return browser, page
            
    except Exception as e:
        print(f"❌ Error running Excel steps: {e}")
        import traceback
        traceback.print_exc()
        return None, None


async def run_additional_instructions(page, instructions: str):
    """Run additional instructions using Agent"""
    print("\n" + "="*80)
    print("PHASE 2: Running Additional Instructions")
    print("="*80)
    print(f"Instructions: {instructions}")
    print("="*80)
    
    try:
        from agent.core.agent import Agent
        
        # Create Agent
        agent = Agent()
        
        # Get current URL from page
        current_url = page.url
        
        # Create async playwright and connect to existing browser
        # Since we have sync page, we'll create a new async browser and navigate to same URL
        playwright_async = await async_playwright().start()
        browser_async = await playwright_async.chromium.launch(headless=False)
        page_async = await browser_async.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Navigate to current page URL to maintain state
        await page_async.goto(current_url)
        await page_async.wait_for_load_state('networkidle')
        
        # Set up agent with async page
        from agent.browser.playwright_manager import PlaywrightManager
        agent.playwright_manager = PlaywrightManager()
        agent.playwright_manager.playwright = playwright_async
        agent.playwright_manager.browser = browser_async
        agent.playwright_manager.page = page_async
        
        # Initialize agent components
        from agent.discovery.xpath_generator import XPathGenerator
        from agent.browser.action_executor import ActionExecutor
        from agent.discovery.discovery_tracker import DiscoveryTracker
        from agent.browser.element_locator import ElementLocator
        from agent.utils.story_parser import StoryParser
        from agent.utils.step_matcher import StepMatcher
        from agent.llm.llm_helper import LLMHelper
        
        agent.xpath_generator = XPathGenerator(page_async)
        agent.action_executor = ActionExecutor(page_async, agent.screenshot_manager)
        agent.discovery_tracker = DiscoveryTracker(
            page_async, agent.xpath_generator, agent.element_registry, current_url, agent.context
        )
        
        parsed_steps = agent.story_parser.parse(instructions)
        agent.context.set_story(instructions)
        agent.context.set_parsed_steps(parsed_steps)
        agent.step_matcher = StepMatcher(parsed_steps, instructions)
        agent.llm_helper = LLMHelper(agent.bedrock_client, instructions)
        agent.element_locator = ElementLocator(
            page_async, agent.element_registry, parsed_steps, agent.context.current_step_number, agent.context
        )
        
        # Initialize tool handlers
        from agent.tools.browser_navigate import BrowserNavigateTool
        from agent.tools.browser_click import BrowserClickTool
        from agent.tools.browser_fill import BrowserFillTool
        from agent.tools.browser_evaluate import BrowserEvaluateTool
        from agent.tools.browser_verify import BrowserVerifyTool
        
        agent.navigate_tool = BrowserNavigateTool(agent.playwright_manager, agent.context, agent.discovery_tracker)
        agent.click_tool = BrowserClickTool(agent.playwright_manager, agent.context, agent.discovery_tracker, agent.action_executor, agent.xpath_generator, agent.element_registry, agent.registry_manager)
        agent.fill_tool = BrowserFillTool(agent.playwright_manager, agent.context, agent.discovery_tracker, agent.action_executor, agent.xpath_generator, agent.element_registry, agent.registry_manager, agent.totp_handler)
        agent.evaluate_tool = BrowserEvaluateTool(agent.playwright_manager, agent.context)
        agent.verify_tool = BrowserVerifyTool(agent.playwright_manager, agent.context, agent.discovery_tracker)
        
        # Execute instructions
        results = await agent.execute_story(instructions)
        
        print("\n✅ Phase 2 Complete: Additional instructions executed")
        print(f"Status: {results.get('status', 'unknown')}")
        print(f"Actions taken: {len(results.get('actions_taken', []))}")
        
        # Close async browser (sync browser stays open)
        await browser_async.close()
        await playwright_async.stop()
        
        return results
        
    except Exception as e:
        print(f"❌ Error running additional instructions: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main experiment flow"""
    print("\n" + "="*80)
    print("EXTENDED TEST EXPERIMENT - WITH SPECIFIC INSTRUCTIONS")
    print("="*80)
    
    # Phase 1: Run Excel steps (sync)
    browser, page = run_excel_steps()
    
    if not browser or not page:
        print("❌ Failed to run Excel steps. Exiting.")
        return
    
    # Phase 2: Run specific instructions
    instructions = "Go to the data submissions page, click on the Program dropdown, and select NCI"
    
    print(f"\n📝 Running instructions: {instructions}")
    
    # Run additional instructions (async)
    results = asyncio.run(run_additional_instructions(page, instructions))
    
    if results:
        print("\n✅ All steps completed!")
        print(f"Status: {results.get('status', 'unknown')}")
        print(f"Actions: {len(results.get('actions_taken', []))}")
    else:
        print("\n❌ Instructions execution failed")
    
    # Keep browser open for inspection
    print("\n⏸️  Browser will remain open for 30 seconds for inspection...")
    import time
    time.sleep(30)
    
    # Close browser
    try:
        browser.close()
        print("✅ Browser closed")
    except:
        pass


if __name__ == '__main__':
    main()


