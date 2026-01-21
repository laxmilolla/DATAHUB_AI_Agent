"""
Instructions → Playwright → XPath/Test Case Generator
Simple endpoint: Give instructions, get XPaths and Excel test cases
"""
from flask import Blueprint, request, jsonify, send_file, render_template
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
from REFACTOR.generator.excel_generator import generate_playwright_from_excel
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

bp_instructions = Blueprint('instructions_api', __name__)

# Store active executions
instructions_executions = {}


def _run_login_steps_from_excel(excel_file_path: Path, max_steps: int = 12):
    """
    Run login steps from Excel file (typically steps 1-12)
    Returns: (browser, page, login_steps_data) - browser and page are sync Playwright objects
    """
    login_steps_data = []
    
    try:
        if not excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
        
        # Read Excel
        df = pd.read_excel(excel_file_path)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Limit to login steps (first max_steps)
        login_df = df.head(max_steps)
        
        # Create sync browser
        playwright_sync = sync_playwright().start()
        browser = playwright_sync.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_url = None
        
        # Execute login steps
        for idx, row in login_df.iterrows():
            step_num = str(row.get('step', idx + 1)).strip()
            url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else None
            xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
            action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else 'click'
            object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
            functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else ''
            text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else ''
            wait_time = row.get('wait_time', None)
            is_optional = str(row.get('optional', '')).strip().lower() in ['true', 'yes', '1', 'y']
            
            if url and url != 'N/A':
                current_url = url
            
            page.wait_for_timeout(3000)
            
            try:
                if action == 'navigate':
                    if url:
                        page.goto(url)
                        page.wait_for_load_state('networkidle')
                        login_steps_data.append({
                            'step_number': len(login_steps_data) + 1,
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
                    login_steps_data.append({
                        'step_number': len(login_steps_data) + 1,
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
                        element.click()
                        page.wait_for_timeout(1000)
                        login_steps_data.append({
                            'step_number': len(login_steps_data) + 1,
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
                            login_steps_data.append({
                                'step_number': len(login_steps_data) + 1,
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
                            login_steps_data.append({
                                'step_number': len(login_steps_data) + 1,
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
                    login_steps_data.append({
                        'step_number': len(login_steps_data) + 1,
                        'action': action,
                        'url': current_url or 'N/A',
                        'xpath': xpath or 'N/A',
                        'selector': '',
                        'text_value': text_value,
                        'description': f'Failed: {str(e)[:50]}',
                        'success': False
                    })
        
        return browser, page, login_steps_data, playwright_sync
        
    except Exception as e:
        import traceback
        print(f"Error running login steps: {e}")
        print(traceback.format_exc())
        return None, None, [], None


@bp_instructions.route('/instructions', methods=['GET'])
def instructions_page():
    """Render instructions page"""
    return render_template('instructions.html')


@bp_instructions.route('/api/instructions/start-browser', methods=['POST'])
def start_browser_for_preconditions():
    """
    Start browser for manual precondition setup
    
    Returns:
        JSON with session_id
    """
    try:
        from agent.browser.playwright_manager import PlaywrightManager
        import asyncio
        
        session_id = f"precond_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create playwright manager
        playwright_manager = PlaywrightManager()
        
        # Start browser in background thread
        def start_browser_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(playwright_manager.start(headless=False))
            loop.close()
        
        thread = threading.Thread(target=start_browser_async, daemon=True)
        thread.start()
        thread.join(timeout=10)
        
        # Store session
        instructions_executions[session_id] = {
            'playwright_manager': playwright_manager,
            'status': 'precondition_setup',
            'browser_started': True,
            'started_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Browser started. Set up your preconditions (login, TOTP), then click Continue.'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error starting browser: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_instructions.route('/api/instructions/<session_id>/continue', methods=['POST'])
def continue_after_preconditions(session_id):
    """
    Continue execution after manual precondition setup
    
    Expected JSON:
    {
        "instructions": "Go to X, click Y, fill Z..."
    }
    """
    try:
        if session_id not in instructions_executions:
            return jsonify({'error': 'Session not found'}), 404
        
        data = request.get_json()
        instructions = data.get('instructions', '').strip()
        
        if not instructions:
            return jsonify({'error': 'Instructions required'}), 400
        
        # Get playwright manager from session
        exec_data = instructions_executions[session_id]
        playwright_manager = exec_data.get('playwright_manager')
        
        if not playwright_manager:
            return jsonify({'error': 'Browser not started'}), 400
        
        # Create Agent
        agent = Agent()
        agent.playwright_manager = playwright_manager
        
        # Create execution ID for the actual test
        execution_id = f"inst_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(instructions) % 10000}"
        
        # Update session with execution ID
        exec_data['execution_id'] = execution_id
        exec_data['instructions'] = instructions
        exec_data['status'] = 'running'
        
        # ALSO store execution_id directly in instructions_executions for status endpoint lookup
        instructions_executions[execution_id] = exec_data
        
        # Execute instructions using existing browser
        def execute_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(runner.execute_instructions(instructions))
                loop.close()
                
                # Extract steps and generate Excel (same as execute_instructions)
                actions = results.get('actions_taken', [])
                discoveries = results.get('discoveries', [])
                current_url = ''
                if runner.agent and hasattr(runner.agent, 'discovery_tracker') and runner.agent.discovery_tracker:
                    current_url = runner.agent.discovery_tracker.current_url
                
                steps_data = []
                for idx, action in enumerate(actions, 1):
                    tool_name = action.get('tool', 'unknown')
                    tool_input = action.get('input', {})
                    result_text = action.get('result', '')
                    
                    url = current_url
                    if tool_name == 'browser_navigate':
                        url = tool_input.get('url', '')
                    
                    selector = tool_input.get('selector', '')
                    xpath = ''
                    
                    if 'XPath:' in result_text:
                        xpath_match = re.search(r'XPath:\s*([^\n]+)', result_text)
                        if xpath_match:
                            xpath = xpath_match.group(1).strip()
                    
                    if not xpath and selector:
                        for disc in discoveries:
                            if disc.get('final_selector') == selector or disc.get('original_query') == selector:
                                xpath = disc.get('xpath', '')
                                break
                    
                    text_value = ''
                    if tool_name == 'browser_fill':
                        text_value = tool_input.get('text', '')
                    
                    step_info = {
                        'step_number': idx,
                        'action': tool_name,
                        'description': result_text[:100] if result_text else f"{tool_name} action",
                        'url': url,
                        'xpath': xpath,
                        'selector': selector,
                        'text_value': text_value,
                        'success': 'success' in result_text.lower() or '✅' in result_text
                    }
                    steps_data.append(step_info)
                    
                    if tool_name == 'browser_navigate' and url:
                        current_url = url
                
                # Extract screenshots from results
                screenshots = results.get('screenshots', [])
                if not screenshots and agent.context:
                    screenshots = agent.context.screenshots if hasattr(agent.context, 'screenshots') else []
                
                exec_data['status'] = results.get('status', 'completed')
                exec_data['steps'] = steps_data
                exec_data['screenshots'] = screenshots
                exec_data['completed_at'] = datetime.now().isoformat()
                
                # Generate Excel
                excel_file = _generate_excel_from_steps(execution_id, steps_data, instructions)
                exec_data['excel_file'] = excel_file
                
            except Exception as e:
                import traceback
                print(f"Error executing instructions: {e}")
                print(traceback.format_exc())
                exec_data['status'] = 'failed'
                exec_data['error'] = str(e)
        
        thread = threading.Thread(target=execute_async, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Execution started'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error in continue_after_preconditions: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_instructions.route('/api/instructions/execute', methods=['POST'])
def execute_instructions():
    """
    Execute instructions and generate test cases with XPaths
    
    Expected JSON:
    {
        "instructions": "Go to X, click Y, fill Z...",
        "manual_preconditions": false  // If true, browser starts first for manual setup
    }
    
    Returns:
        JSON with execution_id and status
    """
    try:
        data = request.get_json()
        instructions = data.get('instructions', '').strip()
        manual_preconditions = data.get('manual_preconditions', False)
        
        if not instructions:
            return jsonify({'error': 'Instructions required'}), 400
        
        # Create execution ID
        execution_id = f"inst_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(instructions) % 10000}"
        
        # Initialize execution record
        instructions_executions[execution_id] = {
            'status': 'running',
            'instructions': instructions,
            'steps': [],
            'xpaths': [],
            'screenshots': [],
            'excel_file': None,
            'started_at': datetime.now().isoformat()
        }
        
        # Execute in background thread
        def execute_async():
            loop = None
            playwright_sync = None
            browser_sync = None
            playwright_async = None
            browser_async = None
            
            try:
                # CRITICAL: Create new event loop in this thread
                # Check if there's already a loop running
                try:
                    existing_loop = asyncio.get_running_loop()
                    if existing_loop:
                        # If there's a running loop, we need to use a different approach
                        raise RuntimeError("Cannot create new event loop - one is already running")
                except RuntimeError:
                    # No running loop - safe to create new one
                    pass
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # PHASE 1: Run login steps from Excel (SYNC Playwright)
                instructions_executions[execution_id]['status'] = 'phase1_login'
                instructions_executions[execution_id]['phase'] = 'Running login steps...'
                
                project_root = Path(__file__).parent.parent.parent
                excel_file = project_root / 'test_case.xlsx'
                
                browser_sync, page_sync, login_steps_data, playwright_sync = _run_login_steps_from_excel(excel_file, max_steps=12)
                
                if not browser_sync or not page_sync:
                    raise Exception("Failed to run login steps")
                
                # Get current URL and cookies after login
                current_url_after_login = page_sync.url
                cookies = page_sync.context.cookies()
                
                # CRITICAL: Close sync browser and ensure complete cleanup
                # Sync Playwright creates internal event loops that must be fully released
                try:
                    browser_sync.close()
                    playwright_sync.stop()
                    browser_sync = None
                    playwright_sync = None
                    
                    # CRITICAL: Force garbage collection to ensure sync Playwright releases all resources
                    import gc
                    gc.collect()
                    
                    # Wait to ensure cleanup completes
                    import time
                    time.sleep(2.0)  # Longer delay to ensure sync playwright fully releases
                except Exception as e:
                    print(f"Warning: Error closing sync browser: {e}")
                
                # CRITICAL: Completely reset event loop state before starting async Playwright
                # The issue is that sync Playwright may leave event loop state that conflicts
                try:
                    # Remove any existing event loop
                    try:
                        asyncio.set_event_loop(None)
                    except:
                        pass
                    
                    # Wait a bit more after removing loop
                    import time
                    time.sleep(0.5)
                    
                    # Create completely fresh event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    print("✅ Created fresh event loop for async Playwright")
                except Exception as loop_reset_error:
                    print(f"Warning during loop reset: {loop_reset_error}")
                    # Ensure we have a valid loop
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    except:
                        # Last resort - try to get existing loop
                        try:
                            loop = asyncio.get_event_loop()
                        except:
                            raise RuntimeError("Could not create or get event loop")
                
                # PHASE 2: Execute user instructions with Agent (ASYNC Playwright)
                instructions_executions[execution_id]['status'] = 'phase2_instructions'
                instructions_executions[execution_id]['phase'] = 'Executing your instructions...'
                
                # Create Agent
                agent = Agent()
                
                # Detect if running locally (for headful browser)
                try:
                    request_host = request.headers.get('Host', '') if hasattr(request, 'headers') else ''
                    is_local = 'localhost' in request_host or '127.0.0.1' in request_host
                except:
                    is_local = True  # Default to local for instructions feature
                
                # Start async browser and navigate to same URL (maintains session)
                async def start_browser_with_session():
                    playwright_async = await async_playwright().start()
                    browser_async = await playwright_async.chromium.launch(headless=False)
                    context_async = await browser_async.new_context(viewport={'width': 1920, 'height': 1080})
                    
                    # Add cookies from sync browser to maintain session
                    if cookies:
                        await context_async.add_cookies(cookies)
                    
                    page_async = await context_async.new_page()
                    await page_async.goto(current_url_after_login)
                    await page_async.wait_for_load_state('networkidle')
                    
                    return playwright_async, browser_async, page_async
                
                # Start async browser (now that sync browser is closed)
                playwright_async, browser_async, page_async = loop.run_until_complete(start_browser_with_session())
                
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
                    page_async, agent.xpath_generator, agent.element_registry, current_url_after_login, agent.context
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
                agent.click_tool = BrowserClickTool(
                    page_async, agent.element_locator, agent.action_executor, agent.discovery_tracker,
                    agent.registry_manager, agent.xpath_generator, agent.llm_helper, agent.totp_handler,
                    agent.screenshot_manager, agent.context, parsed_steps, instructions
                )
                agent.fill_tool = BrowserFillTool(
                    page_async, agent.element_locator, agent.action_executor, agent.totp_handler,
                    agent.discovery_tracker, agent.context, parsed_steps, instructions
                )
                agent.evaluate_tool = BrowserEvaluateTool(agent.playwright_manager)
                agent.verify_tool = BrowserVerifyTool(agent.playwright_manager, agent.discovery_tracker, agent.screenshot_manager, agent.element_locator)
                
                # Execute instructions
                results = loop.run_until_complete(agent.execute_story(instructions))
                
                # Sync browser already closed earlier (before async browser started)
                # No need to close again
                
                # Extract steps and XPaths from execution
                actions = results.get('actions_taken', [])
                discoveries = results.get('discoveries', [])
                current_url = ''
                if hasattr(agent, 'discovery_tracker') and agent.discovery_tracker:
                    current_url = agent.discovery_tracker.current_url
                
                # Combine login steps (Phase 1) with user instruction steps (Phase 2)
                steps_data = login_steps_data.copy()  # Start with login steps
                login_steps_count = len(login_steps_data)
                
                # Create a map of discoveries by element name for quick lookup
                discovery_map = {}
                for disc in discoveries:
                    element_name = disc.get('element_name', '')
                    if element_name:
                        discovery_map[element_name] = disc
                
                # Add user instruction steps (Phase 2) - step numbers continue from login steps
                for idx, action in enumerate(actions, 1):
                    tool_name = action.get('tool', 'unknown')
                    tool_input = action.get('input', {})
                    result_text = action.get('result', '')
                    
                    # Extract URL from action or use current URL
                    url = current_url
                    if tool_name == 'browser_navigate':
                        url = tool_input.get('url', '')
                    
                    # Extract selector/XPath from tool input or result
                    selector = tool_input.get('selector', '')
                    xpath = ''
                    
                    # Strategy 1: Extract XPath directly from selector if it's already an XPath
                    if selector:
                        if selector.startswith('xpath='):
                            xpath = selector.replace('xpath=', '').strip()
                        elif selector.startswith('//') or ('[@' in selector and ']' in selector):
                            xpath = selector
                    
                    # Strategy 2: Try to extract XPath from result text (tools might include it)
                    if not xpath and 'XPath:' in result_text:
                        xpath_match = re.search(r'XPath:\s*([^\n]+)', result_text)
                        if xpath_match:
                            xpath = xpath_match.group(1).strip()
                    
                    # Strategy 3: Try to find XPath from discoveries (multiple matching strategies)
                    if not xpath:
                        # Try matching by selector (exact match)
                        for disc in discoveries:
                            if disc.get('final_selector') == selector or disc.get('original_query') == selector:
                                xpath = disc.get('xpath', '')
                                if xpath:
                                    break
                        
                        # Try matching by element name from action description
                        if not xpath:
                            # Extract element name from result text or tool input
                            element_name = tool_input.get('element_description', '') or tool_input.get('element_name', '')
                            if not element_name and result_text:
                                # Try to extract from result text like "Clicked Login button"
                                name_match = re.search(r'(?:Clicked|Filled|Verified)\s+([^-\n]+)', result_text)
                                if name_match:
                                    element_name = name_match.group(1).strip()
                            
                            if element_name:
                                for disc in discoveries:
                                    if disc.get('element_name', '').lower() == element_name.lower():
                                        xpath = disc.get('xpath', '')
                                        if xpath:
                                            break
                        
                        # Strategy 4: Use most recent discovery if selector contains part of it
                        if not xpath and selector:
                            # Try partial match - selector might be text=Login but discovery has full XPath
                            for disc in reversed(discoveries):  # Most recent first
                                disc_selector = disc.get('final_selector', '') or disc.get('original_query', '')
                                # Check if selector text appears in discovery selector or vice versa
                                if selector and disc_selector:
                                    # Extract text from text= selector
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
                        'step_number': login_steps_count + idx,  # Continue numbering from login steps
                        'action': tool_name,
                        'description': result_text[:100] if result_text else f"{tool_name} action",
                        'url': url,
                        'xpath': xpath,
                        'selector': selector,
                        'text_value': text_value,
                        'success': 'success' in result_text.lower() or '✅' in result_text
                    }
                    steps_data.append(step_info)
                    
                    # Update current URL for next iteration
                    if tool_name == 'browser_navigate' and url:
                        current_url = url
                
                # Extract screenshots from results
                screenshots = results.get('screenshots', [])
                # Screenshots are stored as filenames in context.screenshots
                if not screenshots and hasattr(agent, 'context'):
                    screenshots = agent.context.screenshots if hasattr(agent.context, 'screenshots') else []
                
                # Update execution record
                instructions_executions[execution_id]['status'] = results.get('status', 'completed')
                instructions_executions[execution_id]['steps'] = steps_data
                instructions_executions[execution_id]['screenshots'] = screenshots
                instructions_executions[execution_id]['completed_at'] = datetime.now().isoformat()
                instructions_executions[execution_id]['phase'] = 'Completed'
                
                # Generate Excel file from execution data (includes both login and user instructions)
                excel_file = _generate_excel_from_steps(execution_id, steps_data, instructions)
                instructions_executions[execution_id]['excel_file'] = excel_file
                
                # Cleanup async browser
                try:
                    if browser_async:
                        loop.run_until_complete(browser_async.close())
                    if playwright_async:
                        loop.run_until_complete(playwright_async.stop())
                except Exception as cleanup_error:
                    print(f"Warning during async cleanup: {cleanup_error}")
                
                # Close event loop
                try:
                    if loop and not loop.is_closed():
                        # Cancel any pending tasks
                        try:
                            pending = asyncio.all_tasks(loop)
                            for task in pending:
                                task.cancel()
                            # Run until all tasks are cancelled
                            if pending:
                                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except:
                            pass
                        loop.close()
                except Exception as loop_error:
                    print(f"Warning during loop cleanup: {loop_error}")
                
            except Exception as e:
                import traceback
                print(f"Error executing instructions: {e}")
                print(traceback.format_exc())
                
                # Ensure cleanup on error
                try:
                    # Cleanup sync browser if still open
                    if browser_sync:
                        try:
                            browser_sync.close()
                        except:
                            pass
                    if playwright_sync:
                        try:
                            playwright_sync.stop()
                        except:
                            pass
                    
                    # Cleanup async browser if created
                    if browser_async and loop:
                        try:
                            loop.run_until_complete(browser_async.close())
                        except:
                            pass
                    if playwright_async and loop:
                        try:
                            loop.run_until_complete(playwright_async.stop())
                        except:
                            pass
                    
                    # Close event loop
                    if loop and not loop.is_closed():
                        try:
                            loop.close()
                        except:
                            pass
                except Exception as cleanup_error:
                    print(f"Error during cleanup: {cleanup_error}")
                
                instructions_executions[execution_id]['status'] = 'failed'
                instructions_executions[execution_id]['error'] = str(e)
        
        thread = threading.Thread(target=execute_async, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Execution started'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error in execute_instructions: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


def _generate_excel_from_steps(execution_id: str, steps_data: list, instructions: str) -> Path:
    """Generate Excel file from execution steps"""
    project_root = Path(__file__).parent.parent.parent
    excel_dir = project_root / 'storage' / 'instructions_excel'
    excel_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare data for Excel
    excel_rows = []
    for step in steps_data:
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
        else:
            object_type = 'Element'
            action = action_type
        
        excel_rows.append({
            'Step': step['step_number'],
            'URL': step['url'] or 'N/A',
            'XPath': step['xpath'] or step['selector'] or 'N/A',
            'Object Type': object_type,
            'Action': action,
            'Functions': '',
            'Text Value': step['text_value'] or '',
            'Wait Time': 3000,
            'Optional': ''
        })
    
    # Create DataFrame
    df = pd.DataFrame(excel_rows)
    
    # Save Excel file
    excel_file = excel_dir / f"{execution_id}.xlsx"
    df.to_excel(excel_file, index=False, sheet_name='Test Steps')
    
    return excel_file


@bp_instructions.route('/api/instructions/<execution_id>/status', methods=['GET'])
def get_instructions_status(execution_id):
    """Get execution status (works for both execution_id and session_id)"""
    # Check if it's a session_id (precondition setup) or execution_id
    if execution_id not in instructions_executions:
        return jsonify({'error': 'Execution not found'}), 404
    
    exec_data = instructions_executions[execution_id]
    
    # If it's a precondition session, check if execution_id exists
    if exec_data.get('status') == 'precondition_setup':
        return jsonify({
            'success': True,
            'status': 'precondition_setup',
            'message': 'Browser started. Set up preconditions and click Continue.',
            'browser_started': exec_data.get('browser_started', False)
        }), 200
    
    return jsonify({
        'success': True,
        'status': exec_data['status'],
        'phase': exec_data.get('phase', ''),
        'steps': exec_data.get('steps', []),
        'screenshots': exec_data.get('screenshots', []),
        'excel_file': str(exec_data.get('excel_file', '')) if exec_data.get('excel_file') else None,
        'error': exec_data.get('error'),
        'execution_id': exec_data.get('execution_id')
    }), 200


@bp_instructions.route('/api/instructions/<execution_id>/excel', methods=['GET'])
def download_excel(execution_id):
    """Download generated Excel file"""
    if execution_id not in instructions_executions:
        return jsonify({'error': 'Execution not found'}), 404
    
    exec_data = instructions_executions[execution_id]
    
    # If it's a session, get the actual execution_id
    actual_execution_id = exec_data.get('execution_id', execution_id)
    
    excel_file = exec_data.get('excel_file')
    if not excel_file or not Path(excel_file).exists():
        return jsonify({'error': 'Excel file not generated yet'}), 404
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=f"test_cases_{actual_execution_id}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

