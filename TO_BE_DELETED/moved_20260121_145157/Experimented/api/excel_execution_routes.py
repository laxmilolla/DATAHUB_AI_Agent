"""
Excel-Driven Execution with UI Instructions
Runs Excel steps sequentially, then waits for UI instruction, executes with Agent, captures XPaths
"""
from flask import Blueprint, request, jsonify, current_app, send_file
import json
import sys
import asyncio
import threading
from pathlib import Path
from datetime import datetime
import pandas as pd
import re
import uuid

# Add paths
refactor_dir = Path(__file__).parent.parent
sys.path.insert(0, str(refactor_dir.parent))

from agent.core.agent import Agent
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

bp_excel_execution = Blueprint('excel_execution_api', __name__)

# Store active executions
excel_executions = {}


def _run_excel_steps_sequential(excel_file_path: Path, max_steps: int = None):
    """
    Run Excel steps sequentially (no iterations, just for loop)
    Returns: (browser, page, steps_data, playwright) - sync Playwright objects
    """
    steps_data = []
    
    try:
        if not excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
        
        # Read Excel
        df = pd.read_excel(excel_file_path)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Limit steps if specified
        if max_steps:
            df = df.head(max_steps)
        
        # Create sync browser with CDP enabled so async can connect to it later
        playwright_sync = sync_playwright().start()
        # Launch browser with CDP (remote debugging) enabled
        # This allows async Playwright to connect to the same browser instance
        browser = playwright_sync.chromium.launch(
            headless=False,
            args=['--remote-debugging-port=9222']  # Enable CDP on port 9222
        )
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_url = None
        
        # Execute steps sequentially (for loop, no iterations)
        for idx, row in df.iterrows():
            step_num = str(row.get('step', idx + 1)).strip()
            url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else None
            xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
            action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else 'click'
            object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
            functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else ''
            text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else ''
            wait_time = row.get('wait_time', None)
            is_optional = str(row.get('optional', '')).strip().lower() in ['true', 'yes', '1', 'y']
            
            if url and url != 'N/A' and url != 'nan':
                current_url = url
            
            page.wait_for_timeout(3000)
            
            try:
                if action == 'navigate':
                    if url and url != 'N/A' and url != 'nan':
                        page.goto(url)
                        page.wait_for_load_state('networkidle')
                        steps_data.append({
                            'step_number': len(steps_data) + 1,
                            'action': 'browser_navigate',
                            'url': url,
                            'xpath': 'N/A',
                            'selector': '',
                            'text_value': '',
                            'description': f'Navigate to {url}',
                            'success': True
                        })
                
                elif action == 'wait':
                    wait_ms = int(wait_time) if wait_time else 1000
                    page.wait_for_timeout(wait_ms)
                    steps_data.append({
                        'step_number': len(steps_data) + 1,
                        'action': 'wait',
                        'url': current_url or 'N/A',
                        'xpath': 'N/A',
                        'selector': '',
                        'text_value': '',
                        'description': f'Wait {wait_ms}ms',
                        'success': True
                    })
                
                elif action == 'click':
                    if xpath and xpath != 'N/A':
                        selector = f'xpath={xpath}'
                        element = page.locator(selector).nth(0)
                        element.wait_for(state='visible', timeout=10000)
                        element.scroll_into_view_if_needed()
                        element.click()
                        page.wait_for_timeout(1000)
                        steps_data.append({
                            'step_number': len(steps_data) + 1,
                            'action': 'browser_click',
                            'url': current_url or 'N/A',
                            'xpath': xpath,
                            'selector': selector,
                            'text_value': '',
                            'description': f'Click {object_type or "element"}',
                            'success': True
                        })
                
                elif action == 'fill':
                    if xpath and xpath != 'N/A':
                        # Handle TOTP
                        if 'TOTP' in str(functions).upper():
                            totp_selectors = [
                                'input.one-time-code-input__input',
                                "input[autocomplete='one-time-code']",
                                "input[type='text'][name='code']",
                                "input[name='code']:not([type='hidden'])",
                                'lg-one-time-code-input input[type="text"]',
                                'lg-validated-field input[type="text"]',
                                'lg-one-time-code-input input',
                                'input.one-time-code',
                                f'xpath={xpath}',
                            ]
                            selector_found = False
                            element = None
                            for totp_sel in totp_selectors:
                                try:
                                    test_elem = page.locator(totp_sel).first
                                    if test_elem.is_visible(timeout=2000):
                                        element = test_elem
                                        selector_found = True
                                        break
                                except:
                                    continue
                            if not selector_found:
                                selector = f'xpath={xpath}'
                                element = page.locator(selector).nth(0)
                                element.wait_for(state='visible', timeout=10000)
                            
                            import pyotp
                            import os
                            secret_key = os.getenv('TOTP_SECRET_KEY')
                            if not secret_key:
                                raise ValueError('TOTP_SECRET_KEY not found')
                            totp = pyotp.TOTP(secret_key)
                            totp_code = totp.now()
                            element.fill('')
                            element.type(totp_code, delay=10)
                            page.wait_for_timeout(200)
                            steps_data.append({
                                'step_number': len(steps_data) + 1,
                                'action': 'browser_fill',
                                'url': current_url or 'N/A',
                                'xpath': xpath,
                                'selector': selector if selector_found else f'xpath={xpath}',
                                'text_value': 'TOTP_CODE',
                                'description': 'Fill TOTP code',
                                'success': True
                            })
                        else:
                            selector = f'xpath={xpath}'
                            element = page.locator(selector).nth(0)
                            element.wait_for(state='visible', timeout=10000)
                            fill_val = text_value.replace('${TIMESTAMP}', TIMESTAMP) if '${TIMESTAMP}' in text_value else text_value
                            element.fill(fill_val)
                            steps_data.append({
                                'step_number': len(steps_data) + 1,
                                'action': 'browser_fill',
                                'url': current_url or 'N/A',
                                'xpath': xpath,
                                'selector': selector,
                                'text_value': fill_val,
                                'description': f'Fill {object_type or "input"}',
                                'success': True
                            })
                
                page.wait_for_timeout(500)
                
            except Exception as e:
                if not is_optional:
                    steps_data.append({
                        'step_number': len(steps_data) + 1,
                        'action': action,
                        'url': current_url or 'N/A',
                        'xpath': xpath or 'N/A',
                        'selector': '',
                        'text_value': text_value,
                        'description': f'Failed: {str(e)[:50]}',
                        'success': False
                    })
        
        return browser, page, steps_data, playwright_sync
        
    except Exception as e:
        import traceback
        print(f"Error running Excel steps: {e}")
        print(traceback.format_exc())
        return None, None, [], None


@bp_excel_execution.route('/api/excel-execution/start', methods=['POST'])
def start_excel_execution():
    """
    Start Excel-driven execution
    Runs Excel steps sequentially, keeps browser open, waits for instruction
    
    Expected JSON:
    {
        "excel_file": "test_case.xlsx" (optional, defaults to test_case.xlsx),
        "max_steps": null (optional, null = all steps)
    }
    
    Returns:
        JSON with execution_id and status
    """
    try:
        data = request.get_json() or {}
        excel_filename = data.get('excel_file', 'test_case.xlsx')
        max_steps = data.get('max_steps', None)
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        excel_file = project_root / excel_filename
        
        if not excel_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_filename}'}), 404
        
        # Create execution ID
        execution_id = f"excel_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Initialize execution record
        excel_executions[execution_id] = {
            'status': 'running_excel',
            'excel_file': str(excel_file),
            'max_steps': max_steps,
            'excel_steps': [],
            'instruction_steps': [],
            'xpaths': [],
            'screenshots': [],
            'browser': None,
            'page': None,
            'playwright': None,
            'started_at': datetime.now().isoformat()
        }
        
        # Run Excel steps in background thread
        def run_excel_background():
            try:
                browser, page, steps_data, playwright_sync = _run_excel_steps_sequential(excel_file, max_steps)
                
                if not browser or not page:
                    excel_executions[execution_id]['status'] = 'failed'
                    excel_executions[execution_id]['error'] = 'Failed to run Excel steps'
                    return
                
                # Store browser/page for later instruction execution
                excel_executions[execution_id]['browser'] = browser
                excel_executions[execution_id]['page'] = page
                excel_executions[execution_id]['playwright'] = playwright_sync
                excel_executions[execution_id]['excel_steps'] = steps_data
                excel_executions[execution_id]['status'] = 'waiting_for_instruction'
                excel_executions[execution_id]['current_url'] = page.url
                excel_executions[execution_id]['cookies'] = page.context.cookies()
                # Store CDP endpoint URL for async Playwright to connect
                excel_executions[execution_id]['cdp_endpoint'] = 'http://localhost:9222'
                
                print(f"✅ Excel execution completed. Waiting for instruction. Execution ID: {execution_id}")
                
            except Exception as e:
                import traceback
                print(f"Error in Excel execution: {e}")
                print(traceback.format_exc())
                excel_executions[execution_id]['status'] = 'failed'
                excel_executions[execution_id]['error'] = str(e)
        
        thread = threading.Thread(target=run_excel_background, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Excel execution started. Will wait for instruction when complete.',
            'status': 'running_excel'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error starting Excel execution: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel_execution.route('/api/excel-execution/<execution_id>/execute-instruction', methods=['POST'])
def execute_instruction(execution_id):
    """
    Execute user instruction using Agent
    Captures XPaths automatically
    
    Expected JSON:
    {
        "instruction": "Click Program dropdown, select NCI"
    }
    
    Returns:
        JSON with status and captured XPaths
    """
    try:
        if execution_id not in excel_executions:
            return jsonify({'error': 'Execution not found'}), 404
        
        exec_data = excel_executions[execution_id]
        
        if exec_data['status'] != 'waiting_for_instruction':
            return jsonify({
                'error': f'Execution not ready for instruction. Current status: {exec_data["status"]}'
            }), 400
        
        data = request.get_json()
        instruction = data.get('instruction', '').strip()
        html_content = data.get('html', '').strip()  # Optional HTML content
        
        if not instruction:
            return jsonify({'error': 'Instruction required'}), 400
        
        # Extract HTML from instruction if provided inline
        from REFACTOR.api.html_helper import HTMLHelper
        html_from_instruction = HTMLHelper.extract_html_from_instruction(instruction)
        if html_from_instruction:
            html_content = html_from_instruction
            # Remove HTML from instruction text for cleaner execution
            instruction = re.sub(r'(?:Here\'?s\s+the\s+)?HTML\s*:?\s*<html[\s\S]*?</html>', '', instruction, flags=re.IGNORECASE).strip()
        
        # Parse HTML if provided to extract element hints
        html_elements = []
        if html_content:
            try:
                # Extract elements from HTML that might help with the instruction
                # Look for keywords in instruction (e.g., "Submission Name")
                keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', instruction)
                for keyword in keywords:
                    elements = HTMLHelper.extract_elements_from_html(html_content, keyword)
                    html_elements.extend(elements)
                
                # Also extract all inputs/buttons for general reference
                all_elements = HTMLHelper.extract_elements_from_html(html_content)
                html_elements.extend(all_elements)
                
                print(f"📄 Parsed HTML: Found {len(html_elements)} elements")
            except Exception as e:
                print(f"⚠️  Error parsing HTML: {e}")
        
        # Update status
        exec_data['status'] = 'executing_instruction'
        exec_data['instruction'] = instruction
        exec_data['html_elements'] = html_elements  # Store parsed elements
        
        # Get browser/page from Excel execution
        page_sync = exec_data.get('page')
        browser_sync = exec_data.get('browser')
        # Use stored URL (captured when Excel execution completed)
        current_url_after_excel = exec_data.get('current_url', '')
        
        if not page_sync or not browser_sync:
            return jsonify({'error': 'Browser session not available'}), 400
        
        if not current_url_after_excel:
            return jsonify({'error': 'Current URL not available'}), 400
        
        # Execute instruction in background thread
        def execute_instruction_background():
            loop = None
            playwright_async = None
            browser_async = None
            
            try:
                # Create new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Use stored URL (already captured when Excel execution completed)
                current_url_after_excel = exec_data.get('current_url', '')
                
                if not current_url_after_excel:
                    raise ValueError("Current URL not available from Excel execution")
                
                # Connect async Playwright to the EXISTING sync browser via CDP
                # This keeps the same browser window open
                async def connect_to_existing_browser():
                    playwright_async = await async_playwright().start()
                    
                    # Get CDP endpoint URL (stored when Excel execution started)
                    cdp_endpoint_url = exec_data.get('cdp_endpoint', 'http://localhost:9222')
                    
                    try:
                        # Connect async Playwright to existing browser via CDP
                        # Note: connect_over_cdp expects the HTTP endpoint, not WebSocket
                        import sys
                        print(f"🔗 Attempting to connect to existing browser via CDP: {cdp_endpoint_url}", file=sys.stderr)
                        print(f"🔗 Attempting to connect to existing browser via CDP: {cdp_endpoint_url}")
                        
                        # Wait a bit before connecting to ensure CDP endpoint is ready
                        import asyncio
                        await asyncio.sleep(1.0)
                        
                        browser_async = await playwright_async.chromium.connect_over_cdp(cdp_endpoint_url)
                        
                        # Wait a bit for CDP connection to stabilize
                        await asyncio.sleep(0.5)
                        
                        # Get existing contexts from the connected browser
                        contexts = browser_async.contexts
                        print(f"📋 Found {len(contexts)} contexts in connected browser", file=sys.stderr)
                        
                        page_async = None
                        
                        if contexts:
                            # Use existing context (same browser window)
                            context_async = contexts[0]
                            # Get existing page (the one Excel execution used)
                            pages = context_async.pages
                            print(f"📄 Found {len(pages)} pages in context", file=sys.stderr)
                            
                            if pages:
                                # Try to use existing pages, but check if they're closed
                                for page in pages:
                                    try:
                                        # Check if page is closed by trying to get URL
                                        _ = page.url
                                        # Page is still open, use it
                                        page_async = page
                                        print(f"✅ Using existing page: {page_async.url}", file=sys.stderr)
                                        print(f"✅ Using existing page: {page_async.url}")
                                        break
                                    except Exception as page_check_error:
                                        print(f"⚠️  Page is closed, trying next: {page_check_error}", file=sys.stderr)
                                        continue
                            
                            # If no valid page found, create new page in same browser
                            if not page_async:
                                print("⚠️  No valid pages found, creating new page in same browser", file=sys.stderr)
                                try:
                                    page_async = await context_async.new_page()
                                    await page_async.goto(current_url_after_excel)
                                    await page_async.wait_for_load_state('networkidle')
                                except Exception as new_page_error:
                                    print(f"⚠️  Error creating new page: {new_page_error}", file=sys.stderr)
                                    raise
                        else:
                            # No contexts, create new context in same browser
                            print("⚠️  No contexts found, creating new context in same browser", file=sys.stderr)
                            context_async = await browser_async.new_context(viewport={'width': 1920, 'height': 1080})
                            page_async = await context_async.new_page()
                            await page_async.goto(current_url_after_excel)
                            await page_async.wait_for_load_state('networkidle')
                        
                        # Final check: ensure we have a valid page
                        if not page_async:
                            raise Exception("Failed to get or create a valid page via CDP")
                        
                        # Navigate to current URL if needed (but check if page is already there)
                        try:
                            current_page_url = page_async.url
                            if current_page_url != current_url_after_excel and current_url_after_excel:
                                print(f"🔄 Navigating from {current_page_url} to {current_url_after_excel}", file=sys.stderr)
                                await page_async.goto(current_url_after_excel, wait_until='domcontentloaded', timeout=30000)
                                await page_async.wait_for_load_state('networkidle', timeout=10000)
                        except Exception as nav_error:
                            print(f"⚠️  Navigation error (page might already be there): {nav_error}", file=sys.stderr)
                            # Try to continue anyway - page might already be on the right URL
                        
                        print("✅ Connected to existing browser via CDP - using SAME browser window!", file=sys.stderr)
                        print("✅ Connected to existing browser via CDP - using SAME browser window!")
                        return playwright_async, browser_async, page_async
                        
                    except Exception as cdp_error:
                        import sys
                        import traceback
                        error_msg = f"⚠️  Could not connect via CDP: {cdp_error}"
                        print(error_msg, file=sys.stderr)
                        print(error_msg)
                        traceback.print_exc()
                        print(traceback.format_exc(), file=sys.stderr)
                        # Fallback: Create new browser with cookies (sync browser stays open)
                        fallback_msg = "⚠️  Creating new browser with cookies (sync browser stays open)"
                        print(fallback_msg, file=sys.stderr)
                        print(fallback_msg)
                        cookies_after_excel = exec_data.get('cookies', [])
                        browser_async = await playwright_async.chromium.launch(headless=False)
                        context_async = await browser_async.new_context(viewport={'width': 1920, 'height': 1080})
                        
                        if cookies_after_excel:
                            await context_async.add_cookies(cookies_after_excel)
                        
                        page_async = await context_async.new_page()
                        await page_async.goto(current_url_after_excel)
                        await page_async.wait_for_load_state('networkidle')
                        
                        return playwright_async, browser_async, page_async
                
                playwright_async, browser_async, page_async = loop.run_until_complete(connect_to_existing_browser())
                
                # Create Agent
                agent = Agent()
                
                # Set up agent with async browser
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
                from agent.utils.llm_helper import LLMHelper
                
                agent.xpath_generator = XPathGenerator(page_async)
                agent.action_executor = ActionExecutor(page_async, agent.screenshot_manager)
                agent.discovery_tracker = DiscoveryTracker(
                    page_async, agent.xpath_generator, agent.element_registry, current_url_after_excel, agent.context
                )
                
                # Enhance instruction with HTML element hints if available
                enhanced_instruction = instruction
                html_elements = exec_data.get('html_elements', [])
                if html_elements:
                    # Create element hints for LLM
                    element_hints = []
                    for elem in html_elements[:10]:  # Limit to first 10 to avoid token bloat
                        if elem.get('matches_search') or elem.get('found_via_label'):
                            hint = f"Found element: {elem.get('type', 'element')} with selector '{elem.get('best_selector', '')}'"
                            if elem.get('name'):
                                hint += f" (name: {elem.get('name')})"
                            if elem.get('placeholder'):
                                hint += f" (placeholder: {elem.get('placeholder')})"
                            element_hints.append(hint)
                    
                    if element_hints:
                        enhanced_instruction = f"{instruction}\n\nElement hints from HTML:\n" + "\n".join(element_hints)
                        print(f"📋 Enhanced instruction with {len(element_hints)} element hints from HTML")
                
                parsed_steps = agent.story_parser.parse(enhanced_instruction)
                agent.context.set_story(enhanced_instruction)
                agent.context.set_parsed_steps(parsed_steps)
                agent.step_matcher = StepMatcher(parsed_steps, enhanced_instruction)
                agent.llm_helper = LLMHelper(agent.bedrock_client, enhanced_instruction)
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
                agent.click_tool = BrowserClickTool(
                    page_async, agent.element_locator, agent.action_executor, agent.discovery_tracker,
                    agent.registry_manager, agent.xpath_generator, agent.llm_helper, agent.totp_handler,
                    agent.screenshot_manager, agent.context, parsed_steps, instruction
                )
                agent.fill_tool = BrowserFillTool(
                    page_async, agent.element_locator, agent.action_executor, agent.totp_handler,
                    agent.discovery_tracker, agent.context, parsed_steps, instruction
                )
                agent.evaluate_tool = BrowserEvaluateTool(agent.playwright_manager)
                agent.verify_tool = BrowserVerifyTool(agent.playwright_manager, agent.discovery_tracker, agent.screenshot_manager, agent.element_locator)
                
                # Execute instruction
                results = loop.run_until_complete(agent.execute_story(instruction))
                
                # Extract steps and XPaths from execution
                actions = results.get('actions_taken', [])
                discoveries = results.get('discoveries', [])
                current_url = ''
                if hasattr(agent, 'discovery_tracker') and agent.discovery_tracker:
                    current_url = agent.discovery_tracker.current_url
                
                # Extract instruction steps with XPaths
                instruction_steps = []
                excel_steps_count = len(exec_data['excel_steps'])
                
                for idx, action in enumerate(actions, 1):
                    tool_name = action.get('tool', 'unknown')
                    tool_input = action.get('input', {})
                    result_text = action.get('result', '')
                    
                    # Extract URL
                    url = current_url
                    if tool_name == 'browser_navigate':
                        url = tool_input.get('url', '')
                    
                    # Extract selector/XPath
                    selector = tool_input.get('selector', '')
                    xpath = ''
                    
                    # Strategy 1: Extract XPath directly from selector
                    if selector:
                        if selector.startswith('xpath='):
                            xpath = selector.replace('xpath=', '').strip()
                        elif selector.startswith('//') or ('[@' in selector and ']' in selector):
                            xpath = selector
                    
                    # Strategy 2: Extract from result text
                    if not xpath and 'XPath:' in result_text:
                        xpath_match = re.search(r'XPath:\s*([^\n]+)', result_text)
                        if xpath_match:
                            xpath = xpath_match.group(1).strip()
                    
                    # Strategy 3: Find from discoveries
                    if not xpath:
                        # Try matching by selector
                        for disc in discoveries:
                            if disc.get('final_selector') == selector or disc.get('original_query') == selector:
                                xpath = disc.get('xpath', '')
                                if xpath:
                                    break
                        
                        # Try matching by element name
                        if not xpath:
                            element_name = tool_input.get('element_description', '') or tool_input.get('element_name', '')
                            if not element_name and result_text:
                                name_match = re.search(r'(?:Clicked|Filled|Verified)\s+([^-\n]+)', result_text)
                                if name_match:
                                    element_name = name_match.group(1).strip()
                            
                            if element_name:
                                for disc in discoveries:
                                    if disc.get('element_name', '').lower() == element_name.lower():
                                        xpath = disc.get('xpath', '')
                                        if xpath:
                                            break
                        
                        # Strategy 4: Use most recent discovery
                        if not xpath and selector:
                            for disc in reversed(discoveries):
                                disc_selector = disc.get('final_selector', '') or disc.get('original_query', '')
                                if selector and disc_selector:
                                    if 'text=' in selector:
                                        selector_text = selector.split('text=')[1].strip().strip("'\"")
                                        if selector_text in disc_selector or selector_text in str(disc.get('xpath', '')):
                                            xpath = disc.get('xpath', '')
                                            if xpath:
                                                break
                    
                    # Extract text value for fill actions
                    text_value = ''
                    if tool_name == 'browser_fill':
                        text_value = tool_input.get('text', '')
                    
                    step_info = {
                        'step_number': excel_steps_count + idx,
                        'action': tool_name,
                        'description': result_text[:100] if result_text else f"{tool_name} action",
                        'url': url,
                        'xpath': xpath,
                        'selector': selector,
                        'text_value': text_value,
                        'success': 'success' in result_text.lower() or '✅' in result_text
                    }
                    instruction_steps.append(step_info)
                    
                    if tool_name == 'browser_navigate' and url:
                        current_url = url
                
                # Extract screenshots
                screenshots = results.get('screenshots', [])
                if not screenshots and hasattr(agent, 'context'):
                    screenshots = agent.context.screenshots if hasattr(agent.context, 'screenshots') else []
                
                # Close async browser ONLY if it was newly created (not connected via CDP)
                # If connected via CDP, browser_async is connected to sync browser, so don't close it
                # Sync browser stays open - user wants to continue in same browser
                try:
                    # Only close if it's a newly created browser (not CDP-connected)
                    # CDP-connected browsers should not be closed as they're connected to sync browser
                    if browser_async and hasattr(browser_async, '_connection'):
                        # Check if this is a CDP connection (connected browser)
                        # If it's connected via CDP, don't close - sync browser manages it
                        # If it's a new browser, close it
                        try:
                            # Try to determine if it's CDP-connected
                            # CDP-connected browsers have different connection type
                            # For now, we'll close async browser but keep sync browser open
                            # Sync browser is stored in exec_data and stays open
                            if browser_async:
                                # Don't close if connected via CDP (would close sync browser)
                                # But we can't easily detect this, so let's be safe:
                                # Only close playwright_async, not browser_async if it might be CDP-connected
                                # Actually, let's just close playwright_async and let sync browser manage browser_async
                                pass
                        except:
                            pass
                    
                    # Close playwright_async (this won't close sync browser)
                    if playwright_async:
                        loop.run_until_complete(playwright_async.stop())
                except Exception as cleanup_error:
                    print(f"Warning during async cleanup: {cleanup_error}")
                
                # NOTE: Sync browser stays open - user wants to continue in same browser
                # Sync browser (browser_sync) is NOT closed here
                
                # Close event loop
                try:
                    if loop and not loop.is_closed():
                        try:
                            pending = asyncio.all_tasks(loop)
                            for task in pending:
                                task.cancel()
                            if pending:
                                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except:
                            pass
                        loop.close()
                except Exception as loop_error:
                    print(f"Warning during loop cleanup: {loop_error}")
                
                # Update execution record
                exec_data['status'] = 'completed'
                exec_data['instruction_steps'] = instruction_steps
                exec_data['xpaths'] = [step.get('xpath') for step in instruction_steps if step.get('xpath')]
                exec_data['screenshots'] = screenshots
                exec_data['completed_at'] = datetime.now().isoformat()
                
                print(f"✅ Instruction execution completed. Execution ID: {execution_id}")
                
            except Exception as e:
                import traceback
                print(f"Error executing instruction: {e}")
                print(traceback.format_exc())
                exec_data['status'] = 'failed'
                exec_data['error'] = str(e)
        
        thread = threading.Thread(target=execute_instruction_background, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Instruction execution started',
            'status': 'executing_instruction'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error executing instruction: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel_execution.route('/api/excel-execution/<execution_id>/generate-excel', methods=['POST'])
def generate_excel_from_execution(execution_id):
    """
    Generate Excel file from execution (Excel steps + instruction steps)
    
    Returns:
        JSON with excel file path
    """
    try:
        if execution_id not in excel_executions:
            return jsonify({'error': 'Execution not found'}), 404
        
        exec_data = excel_executions[execution_id]
        
        if exec_data['status'] != 'completed':
            return jsonify({
                'error': f'Execution not completed. Current status: {exec_data["status"]}'
            }), 400
        
        # Combine Excel steps + instruction steps
        all_steps = exec_data['excel_steps'] + exec_data['instruction_steps']
        
        # Generate Excel file
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        excel_dir = project_root / 'storage' / 'excel_execution_results'
        excel_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for Excel
        excel_rows = []
        for step in all_steps:
            # Map action types
            action_type = step['action']
            if 'navigate' in action_type.lower():
                object_type = 'URL'
                action = 'Navigate'
            elif 'click' in action_type.lower():
                object_type = 'Button/Link'
                action = 'Click'
            elif 'fill' in action_type.lower():
                object_type = 'Input'
                action = 'Fill'
            elif 'wait' in action_type.lower():
                object_type = 'Page'
                action = 'Wait'
            else:
                object_type = 'Element'
                action = action_type
            
            excel_rows.append({
                'Step': step['step_number'],
                'URL': step['url'] or 'N/A',
                'XPath': step['xpath'] or step.get('selector', 'N/A'),
                'Object Type': object_type,
                'Action': action,
                'Functions': '',
                'Text Value': step.get('text_value', '') or '',
                'Wait Time': 3000,
                'Optional': ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(excel_rows)
        
        # Save Excel file
        excel_file = excel_dir / f"{execution_id}.xlsx"
        df.to_excel(excel_file, index=False, sheet_name='Test Steps')
        
        exec_data['excel_file'] = str(excel_file.relative_to(project_root))
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'excel_file': str(excel_file.relative_to(project_root)),
            'excel_path': str(excel_file),
            'steps_count': len(all_steps),
            'xpaths_count': len([s for s in all_steps if s.get('xpath') and s.get('xpath') != 'N/A'])
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error generating Excel: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel_execution.route('/api/excel-execution/<execution_id>/status', methods=['GET'])
def get_execution_status(execution_id):
    """Get execution status"""
    if execution_id not in excel_executions:
        return jsonify({'error': 'Execution not found'}), 404
    
    exec_data = excel_executions[execution_id]
    
    response = {
        'execution_id': execution_id,
        'status': exec_data['status'],
        'excel_steps_count': len(exec_data.get('excel_steps', [])),
        'instruction_steps_count': len(exec_data.get('instruction_steps', [])),
        'xpaths_count': len(exec_data.get('xpaths', [])),
        'started_at': exec_data.get('started_at'),
        'completed_at': exec_data.get('completed_at'),
        'excel_file': exec_data.get('excel_file')
    }
    
    if 'error' in exec_data:
        response['error'] = exec_data['error']
    
    if exec_data['status'] == 'completed':
        response['excel_steps'] = exec_data.get('excel_steps', [])
        response['instruction_steps'] = exec_data.get('instruction_steps', [])
        response['xpaths'] = exec_data.get('xpaths', [])
    
    return jsonify(response), 200


@bp_excel_execution.route('/api/excel-execution/<execution_id>/excel', methods=['GET'])
def download_excel(execution_id):
    """Download generated Excel file"""
    if execution_id not in excel_executions:
        return jsonify({'error': 'Execution not found'}), 404
    
    exec_data = excel_executions[execution_id]
    excel_file = exec_data.get('excel_file')
    
    if not excel_file:
        return jsonify({'error': 'Excel file not generated yet'}), 404
    
    project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
    excel_path = project_root / excel_file
    
    if not excel_path.exists():
        return jsonify({'error': 'Excel file not found'}), 404
    
    return send_file(
        str(excel_path),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"{execution_id}.xlsx"
    )

