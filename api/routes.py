"""API Routes"""
from flask import Blueprint, request, jsonify, current_app, send_file, render_template
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import threading

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.core.agent import Agent
from utils.html_parser import parse_html_to_element_map
from utils.element_registry import get_registry

bp = Blueprint('api', __name__)
active_executions = {}


@bp.route('/execute', methods=['POST'])
def execute_story():
    try:
        data = request.get_json()
        story = data.get('story', '').strip()
        
        if not story:
            return jsonify({'error': 'Story required'}), 400
        
        agent = Agent()
        execution_id = agent.context.execution_id
        
        # Get project root before threading
        project_root = current_app.config['PROJECT_ROOT']
        
        active_executions[execution_id] = {
            'agent': agent,
            'status': 'running',
            'story': story,
            'started_at': datetime.now().isoformat()
        }
        
        def run_execution():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(agent.execute_story(story))
                
                # Use project_root from closure
                results_dir = project_root / 'storage' / 'executions'
                results_dir.mkdir(parents=True, exist_ok=True)
                
                results_file = results_dir / f'{execution_id}.json'
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                active_executions[execution_id]['status'] = results['status']
                active_executions[execution_id]['results'] = results
            except Exception as e:
                import traceback
                import logging
                logger = logging.getLogger(__name__)
                active_executions[execution_id]['status'] = 'error'
                active_executions[execution_id]['error'] = str(e)
                logger.error(f"❌ Error in run_execution: {e}")
                logger.error(traceback.format_exc())
                print(f"Error in run_execution: {e}")
                print(traceback.format_exc())
        
        thread = threading.Thread(target=run_execution, daemon=True)
        thread.start()
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'started'
        }), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<execution_id>/status', methods=['GET'])
def get_execution_status(execution_id):
    if execution_id in active_executions:
        exec_data = active_executions[execution_id]
        response = {
            'execution_id': execution_id,
            'status': exec_data['status'],
            'story': exec_data['story'],
            'started_at': exec_data['started_at']
        }
        if 'error' in exec_data:
            response['error'] = exec_data['error']
        if 'results' in exec_data:
            results = exec_data['results']
            response.update({
                'actions_count': len(results.get('actions_taken', [])),
                'screenshots_count': len(results.get('screenshots', [])),
                'summary': results.get('summary'),
                'error': results.get('error')
            })
        elif 'agent' in exec_data:
            # Get live progress from agent context while running
            agent = exec_data['agent']
            if agent and hasattr(agent, 'context'):
                response['actions_count'] = len(agent.context.actions_taken)
                response['screenshots_count'] = len(agent.context.screenshots)
        return jsonify(response), 200
    
    project_root = current_app.config['PROJECT_ROOT']
    results_file = project_root / 'storage' / 'executions' / f'{execution_id}.json'
    
    if results_file.exists():
        with open(results_file) as f:
            results = json.load(f)
        return jsonify({
            'execution_id': execution_id,
            'status': results['status'],
            'story': results['story'],
            'actions_count': len(results.get('actions_taken', [])),
            'screenshots_count': len(results.get('screenshots', [])),
            'summary': results.get('summary'),
            'error': results.get('error')
        }), 200
    
    return jsonify({'error': 'Not found'}), 404


@bp.route('/executions/<execution_id>/results', methods=['GET'])
def get_execution_results(execution_id):
    # ALWAYS load from file first (to get latest Playwright data if it was added)
    project_root = current_app.config['PROJECT_ROOT']
    results_file = project_root / 'storage' / 'executions' / f'{execution_id}.json'
    
    if results_file.exists():
        with open(results_file) as f:
            return jsonify(json.load(f)), 200
    
    # Fallback to live results from active executions (for in-progress tests)
    if execution_id in active_executions:
        exec_data = active_executions[execution_id]
        if 'results' in exec_data:
            return jsonify(exec_data['results']), 200
        elif 'agent' in exec_data:
            # Return partial results while running
            agent = exec_data['agent']
            return jsonify({
                'execution_id': execution_id,
                'status': exec_data['status'],
                'story': exec_data['story'],
                'actions_taken': [],
                'screenshots': []
            }), 200
    
    return jsonify({'error': 'Not found'}), 404


@bp.route('/executions', methods=['GET'])
def list_executions():
    project_root = current_app.config['PROJECT_ROOT']
    results_dir = project_root / 'storage' / 'executions'
    executions = []
    
    if results_dir.exists():
        for f in results_dir.glob('*.json'):
            try:
                with open(f) as file:
                    r = json.load(file)
                executions.append({
                    'execution_id': r['execution_id'],
                    'story': r['story'][:100],
                    'status': r['status'],
                    'actions_count': len(r.get('actions_taken', [])),
                    'screenshots_count': len(r.get('screenshots', [])),
                    'started_at': r.get('started_at'),
                    'completed_at': r.get('completed_at'),
                    'duration': r.get('duration')
                })
            except:
                continue
        
        # Sort by started_at timestamp (most recent first)
        executions.sort(key=lambda x: x.get('started_at') or 0, reverse=True)
    
    return jsonify({'executions': executions}), 200


@bp.route('/screenshots/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    project_root = current_app.config['PROJECT_ROOT']
    path = project_root / 'storage' / 'screenshots' / filename
    if path.exists():
        return send_file(path, mimetype='image/png')
    return jsonify({'error': 'Not found'}), 404


@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'architecture': 'Pure Python + Playwright'}), 200


# Element Map Manager Routes
@bp.route('/fetch-html', methods=['POST'])
def fetch_html():
    """Fetch HTML from URL using Playwright"""
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Import Playwright fetcher
        import asyncio
        from playwright.async_api import async_playwright
        
        async def fetch_page_html(url):
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until='networkidle', timeout=30000)
                html = await page.content()
                await browser.close()
                return html
        
        html = asyncio.run(fetch_page_html(url))
        
        return jsonify({
            'success': True,
            'html': html
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/parse-html', methods=['POST'])
def parse_html():
    """Parse HTML using Playwright parser with live DOM (for XPath testing)"""
    try:
        data = request.json
        url = data.get('url', '')
        page_name = data.get('page_name', '')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Import Playwright parser
        import sys
        import asyncio
        from pathlib import Path
        sys.path.insert(0, str(Path(current_app.config['PROJECT_ROOT'])))
        from playwright.async_api import async_playwright
        from utils.playwright_tree_parser import parse_with_tree
        
        async def parse_with_playwright(url, page_name):
            """Parse page using Playwright with live DOM"""
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Set larger viewport to ensure all tabs and elements are visible
                page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
                
                # Navigate to URL
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Dismiss any popups
                try:
                    continue_btn = page.locator("text='Continue'").first
                    if await continue_btn.is_visible(timeout=2000):
                        await continue_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Parse using tree-based parser with live DOM
                element_map = await parse_with_tree(page)
                
                await browser.close()
                
                # Override page name if provided
                if page_name:
                    element_map["page"] = page_name
                
                return element_map
        
        # Run async parser
        element_map = asyncio.run(parse_with_playwright(url, page_name))
        
        return jsonify({
            'success': True,
            'element_map': element_map
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@bp.route('/save-element-map', methods=['POST'])
def save_element_map():
    """Save parsed element map to registry"""
    try:
        data = request.json
        element_map = data.get('element_map')
        
        if not element_map:
            return jsonify({'error': 'Element map is required'}), 400
        
        # Import registry
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(current_app.config['PROJECT_ROOT'])))
        from utils.element_registry import get_registry
        
        registry = get_registry(str(Path(current_app.config['PROJECT_ROOT']) / 'element_maps'))
        
        # Extract domain and page from URL
        url = element_map.get('url', '')
        domain = url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
        page = element_map.get('page', 'unknown')
        
        # Sanitize page name (remove URL components if present)
        if page.startswith('http://') or page.startswith('https://'):
            # Page is a full URL, extract the page name from it
            page_clean = page.replace('https://', '').replace('http://', '')
            page_clean = page_clean.split('/')[0].split('#')[0]  # Remove domain
            # Extract last path segment or use 'home' if root
            page_parts = page.split('/')[-1].split('#')
            if page_parts and page_parts[0]:
                page = page_parts[0]
            else:
                page = 'home'
        
        # Remove any invalid filesystem characters from page name
        page = page.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # If page is still empty or too long, use default
        if not page or len(page) > 100:
            page = 'home'
        
        # Update element_map with cleaned page name
        element_map['page'] = page
        
        # Save to registry
        registry.save_map(domain, page, element_map)
        
        # Create baseline
        registry.create_baseline(domain, page)
        
        map_path = registry.get_map_path(domain, page)
        
        return jsonify({
            'success': True,
            'message': f'Element map saved successfully',
            'path': str(map_path),
            'domain': domain,
            'page': page
        })
        
    except Exception as e:
        import traceback
        import logging
        error_details = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"❌ ERROR in save_element_map: {e}")
        logger.error(f"Full traceback:\n{error_details}")
        current_app.logger.error(f"❌ ERROR in save_element_map: {e}")
        current_app.logger.error(f"Full traceback:\n{error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500

@bp.route('/element-maps/list')
def list_element_maps():
    """List all existing element maps"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(current_app.config['PROJECT_ROOT'])))
        
        maps_dir = Path(current_app.config['PROJECT_ROOT']) / 'element_maps'
        
        maps = []
        for domain_dir in maps_dir.iterdir():
            if domain_dir.is_dir() and domain_dir.name not in ['versions', '__pycache__']:
                domain = domain_dir.name
                for map_file in domain_dir.glob('*_page.json'):
                    if map_file.is_file():
                        import json
                        with open(map_file, 'r') as f:
                            map_data = json.load(f)
                        
                        maps.append({
                            'domain': domain,
                            'page': map_data.get('page'),
                            'url': map_data.get('url'),
                            'version': map_data.get('version'),
                            'total_elements': map_data.get('statistics', {}).get('total_elements', 0),
                            'last_updated': map_data.get('last_updated'),
                            'file': str(map_file)
                        })
        
        return jsonify({'maps': maps})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/element-maps/<domain>/<page>')
def get_element_map(domain, page):
    """Get specific element map"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(current_app.config['PROJECT_ROOT'])))
        from utils.element_registry import get_registry
        
        registry = get_registry(str(Path(current_app.config['PROJECT_ROOT']) / 'element_maps'))
        element_map = registry.load_map(domain, page)
        
        if not element_map:
            return jsonify({'error': 'Map not found'}), 404
        
        return jsonify(element_map)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<execution_id>/approve-discoveries', methods=['POST'])
def approve_discoveries(execution_id):
    """
    User approved test execution - update element registry with discoveries
    
    This commits the discovered selectors to the registry so future tests
    can use the optimized selectors instead of repeating discovery.
    """
    try:
        import sys
        from pathlib import Path
        from urllib.parse import urlparse
        sys.path.insert(0, str(Path(current_app.config['PROJECT_ROOT'])))
        from utils.element_registry import get_registry
        
        project_root = current_app.config['PROJECT_ROOT']
        
        # Load discoveries from file
        discoveries_dir = project_root / 'storage' / 'discoveries'
        discovery_file = discoveries_dir / f'{execution_id}_discoveries.json'
        
        if not discovery_file.exists():
            return jsonify({
                'error': 'Discovery file not found',
                'execution_id': execution_id
            }), 404
        
        with open(discovery_file, 'r') as f:
            discovery_data = json.load(f)
        
        discoveries = discovery_data.get('discoveries', [])
        
        if not discoveries:
            return jsonify({
                'error': 'No discoveries found in this execution',
                'execution_id': execution_id
            }), 400
        
        # Get registry
        registry = get_registry(str(project_root / 'element_maps'))
        
        # Extract domain from execution results
        results_file = project_root / 'storage' / 'executions' / f'{execution_id}.json'
        
        if not results_file.exists():
            return jsonify({'error': 'Execution results not found'}), 404
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Get domain from story or first action
        story = results.get('story', '')
        domain = None
        
        # Try to extract domain from story URL
        if 'https://' in story or 'http://' in story:
            import re
            url_match = re.search(r'https?://([^\s/]+)', story)
            if url_match:
                domain = url_match.group(1)
        
        if not domain:
            return jsonify({'error': 'Could not determine domain from test execution'}), 400
        
        page = "home"  # Default page name
        
        # Update registry with each discovery
        updated_count = 0
        for discovery in discoveries:
            try:
                registry.update_with_discovery(domain, page, discovery)
                updated_count += 1
            except Exception as e:
                print(f"Warning: Failed to update discovery {discovery.get('name')}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Registry updated with {updated_count} discoveries',
            'execution_id': execution_id,
            'discoveries_updated': updated_count,
            'domain': domain,
            'page': page
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error approving discoveries: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<exec_id>/generate-and-validate', methods=['POST'])
def generate_and_validate(exec_id):
    """Generate Playwright test and validate it"""
    try:
        # Force reload to ensure latest code
        import importlib
        if 'generator.playwright_generator' in sys.modules:
            importlib.reload(sys.modules['generator.playwright_generator'])
        from generator.playwright_generator import PlaywrightGenerator
        from validator.test_runner import TestRunner
        from validator.comparator import Comparator
        
        # Handle empty body gracefully
        data = request.get_json(silent=True) or {}
        test_name = data.get('test_name')
        validate_selectors = data.get('validate_selectors', True)  # Pre-generation selector validation
        
        project_root = current_app.config['PROJECT_ROOT']
        
        # Step 1: Generate Playwright code (with pre-validation)
        try:
            generator = PlaywrightGenerator(project_root)
            generation_result = generator.generate(exec_id, test_name, validate_selectors=validate_selectors)
        except Exception as e:
            # If selector validation fails, return detailed error
            error_msg = str(e)
            if "Selector Validation Failed" in error_msg:
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'error_type': 'selector_validation_failed',
                    'execution_id': exec_id
                }), 400
            # Re-raise other errors
            raise
        
        result = {
            'success': True,
            'execution_id': exec_id,
            'test_file': generation_result['filename'],
            'test_path': generation_result['filepath'],
            'code_preview': generation_result['code'][:500] + '...',  # Preview only
            'generated_at': generation_result['metadata']['generated_at'],
            'test_running': True  # Indicate test is running
        }
        
        # Step 2: Run test in background thread (automatic, no separate button needed)
        def run_test_background():
            try:
                runner = TestRunner(project_root)
                test_result = runner.run(generation_result['filename'], exec_id)
                
                # Step 3: Compare results
                comparator = Comparator(project_root)
                comparison = comparator.compare(exec_id, test_result)
                
                # Step 4: Save Playwright results back to execution file for UI display
                results_file = project_root / 'storage' / 'executions' / f'{exec_id}.json'
                if results_file.exists():
                    with open(results_file, 'r') as f:
                        exec_data = json.load(f)
                    
                    # Add Playwright test results to execution data
                    exec_data['playwright_screenshots'] = test_result.get('screenshots', [])
                    exec_data['playwright_validation'] = {
                        'status': test_result.get('status'),
                        'duration': test_result.get('duration'),
                        'assertions_passed': test_result.get('assertions_passed'),
                        'assertions_failed': test_result.get('assertions_failed'),
                        'test_file': test_result.get('test_file'),
                        'timestamp': test_result.get('timestamp'),
                        'stdout': test_result.get('stdout', ''),
                        'stderr': test_result.get('stderr', ''),
                        'exit_code': test_result.get('exit_code', 0)
                    }
                    exec_data['playwright_comparison'] = comparison
                    
                    # Write back to file
                    with open(results_file, 'w') as f:
                        json.dump(exec_data, f, indent=2)
            except Exception as e:
                print(f"Error running test in background: {e}")
                import traceback
                traceback.print_exc()
        
        # Start background thread to run test
        thread = threading.Thread(target=run_test_background)
        thread.daemon = True
        thread.start()
        
        return jsonify(result), 200
        
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        import traceback
        print(f"Error generating/validating test: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<exec_id>/generated-test', methods=['GET'])
def get_generated_test(exec_id):
    """Get generated test code"""
    try:
        project_root = current_app.config['PROJECT_ROOT']
        metadata_file = project_root / 'storage' / 'generated_tests' / f'{exec_id}_test.json'
        
        if not metadata_file.exists():
            return jsonify({'error': 'No generated test found for this execution'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Read the generated code
        test_file = Path(metadata['filename'])
        if test_file.exists():
            with open(test_file, 'r') as f:
                code = f.read()
            metadata['code'] = code
        
        return jsonify(metadata), 200
        
    except Exception as e:
        print(f"Error retrieving generated test: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<exec_id>/run-test', methods=['POST'])
def run_test(exec_id):
    """Run generated Playwright test in background to generate screenshots"""
    try:
        from validator.test_runner import TestRunner
        from validator.comparator import Comparator
        
        project_root = current_app.config['PROJECT_ROOT']
        metadata_file = project_root / 'storage' / 'generated_tests' / f'{exec_id}_test.json'
        
        if not metadata_file.exists():
            return jsonify({'error': 'No generated test found for this execution'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        test_filename = metadata.get('filename')
        if not test_filename:
            return jsonify({'error': 'Test filename not found in metadata'}), 404
        
        # Run test in background thread to avoid timeout
        def run_test_background():
            try:
                runner = TestRunner(project_root)
                test_result = runner.run(test_filename, exec_id)
                
                # Compare results
                comparator = Comparator(project_root)
                comparison = comparator.compare(exec_id, test_result)
                
                # Save results to execution file
                results_file = project_root / 'storage' / 'executions' / f'{exec_id}.json'
                if results_file.exists():
                    with open(results_file, 'r') as f:
                        exec_data = json.load(f)
                    
                    exec_data['playwright_screenshots'] = test_result.get('screenshots', [])
                    exec_data['playwright_validation'] = {
                        'status': test_result.get('status'),
                        'duration': test_result.get('duration'),
                        'assertions_passed': test_result.get('assertions_passed'),
                        'assertions_failed': test_result.get('assertions_failed'),
                        'test_file': test_result.get('test_file'),
                        'timestamp': test_result.get('timestamp'),
                        'stdout': test_result.get('stdout', ''),
                        'stderr': test_result.get('stderr', ''),
                        'exit_code': test_result.get('exit_code', 0)
                    }
                    exec_data['playwright_comparison'] = comparison
                    
                    with open(results_file, 'w') as f:
                        json.dump(exec_data, f, indent=2)
            except Exception as e:
                print(f"Error running test in background: {e}")
                import traceback
                traceback.print_exc()
        
        # Start background thread
        thread = threading.Thread(target=run_test_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Test execution started in background. Screenshots will be available shortly.',
            'execution_id': exec_id
        }), 202  # 202 Accepted (async processing)
        
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        import traceback
        print(f"Error starting test execution: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<exec_id>/download-test', methods=['GET'])
def download_generated_test(exec_id):
    """Download generated test code as .py file for standalone execution"""
    try:
        from flask import send_file
        project_root = current_app.config['PROJECT_ROOT']
        metadata_file = project_root / 'storage' / 'generated_tests' / f'{exec_id}_test.json'
        
        if not metadata_file.exists():
            return jsonify({'error': 'No generated test found for this execution'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Get the test file path
        test_file = Path(metadata['filename'])
        if not test_file.exists():
            return jsonify({'error': 'Generated test file not found'}), 404
        
        # Extract just the filename for download
        filename = test_file.name
        
        # Send file with proper headers for download
        # Convert Path to string for Flask compatibility
        response = send_file(
            str(test_file),
            as_attachment=True,
            download_name=filename,
            mimetype='text/x-python'
        )
        # Prevent browser caching - force fresh download every time
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        print(f"Error downloading generated test: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/registry/<domain>/<page>/download', methods=['GET'])
def download_registry_json(domain, page):
    """Download registry JSON file"""
    try:
        from flask import send_file
        project_root = current_app.config['PROJECT_ROOT']
        
        # Try both naming conventions: {page}_page.json and {page}.json
        registry_file = project_root / 'element_maps' / domain / f'{page}_page.json'
        if not registry_file.exists():
            registry_file = project_root / 'element_maps' / domain / f'{page}.json'
        
        if not registry_file.exists():
            return jsonify({'error': f'Registry file not found: {domain}/{page}'}), 404
        
        # Use page name from URL for download filename (e.g., "home.json" instead of "home_page.json")
        download_filename = f'{page}.json'
        
        # Send file with proper headers for download
        response = send_file(
            str(registry_file),
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/json'
        )
        
        # Prevent browser caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"Error downloading registry JSON: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/registry', methods=['GET'])
def list_registries():
    """List all available registries (domains/pages)"""
    try:
        project_root = current_app.config['PROJECT_ROOT']
        registry_dir = project_root / 'element_maps'
        
        if not registry_dir.exists():
            return jsonify({'registries': []}), 200
        
        registries = []
        for domain_dir in registry_dir.iterdir():
            if domain_dir.is_dir() and not domain_dir.name.startswith('.'):
                domain = domain_dir.name
                for page_file in domain_dir.glob('*.json'):
                    page = page_file.stem.replace('_page', '')
                    registries.append({
                        'domain': domain,
                        'page': page,
                        'file': str(page_file)
                    })
        
        return jsonify({'registries': registries}), 200
        
    except Exception as e:
        print(f"Error listing registries: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/registry/<domain>/<page>', methods=['GET'])
def get_registry_for_page(domain, page):
    """Get registry content for a specific domain/page"""
    try:
        project_root = current_app.config['PROJECT_ROOT']
        registry_file = project_root / 'element_maps' / domain / f'{page}_page.json'
        
        if not registry_file.exists():
            return jsonify({'error': 'Registry not found'}), 404
        
        with open(registry_file, 'r') as f:
            registry = json.load(f)
        
        return jsonify(registry), 200
        
    except Exception as e:
        print(f"Error getting registry: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/registry/<domain>/<page>/element', methods=['PUT'])
def update_registry_element(domain, page):
    """Update an element in the registry"""
    try:
        data = request.get_json()
        element_key = data.get('element_key')
        new_selector = data.get('selector')
        
        if not element_key or not new_selector:
            return jsonify({'error': 'element_key and selector required'}), 400
        
        project_root = current_app.config['PROJECT_ROOT']
        registry_file = project_root / 'element_maps' / domain / f'{page}_page.json'
        
        if not registry_file.exists():
            return jsonify({'error': 'Registry not found'}), 404
        
        with open(registry_file, 'r') as f:
            registry = json.load(f)
        
        if element_key not in registry.get('elements', {}):
            return jsonify({'error': 'Element not found in registry'}), 404
        
        # Update the selector
        registry['elements'][element_key]['selector'] = new_selector
        registry['last_updated'] = datetime.now().isoformat() + 'Z'
        
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Element updated'}), 200
        
    except Exception as e:
        print(f"Error updating registry element: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/registry/<domain>/<page>', methods=['DELETE'])
def delete_registry(domain, page):
    """Delete an entire registry (JSON file)"""
    try:
        project_root = current_app.config['PROJECT_ROOT']
        registry_file = project_root / 'element_maps' / domain / f'{page}_page.json'
        
        if not registry_file.exists():
            return jsonify({'error': 'Registry not found'}), 404
        
        # Create backup before deleting
        backup_file = registry_file.parent / f'{page}_page.json.deleted_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        import shutil
        shutil.copy(registry_file, backup_file)
        
        # Delete the registry file
        registry_file.unlink()
        
        return jsonify({
            'status': 'success',
            'message': f'Registry deleted successfully',
            'backup': str(backup_file)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/registry/<domain>/<page>/element', methods=['DELETE'])
def delete_registry_element(domain, page):
    """Delete an element from the registry"""
    try:
        data = request.get_json()
        element_key = data.get('element_key')
        
        if not element_key:
            return jsonify({'error': 'element_key required'}), 400
        
        project_root = current_app.config['PROJECT_ROOT']
        registry_file = project_root / 'element_maps' / domain / f'{page}_page.json'
        
        if not registry_file.exists():
            return jsonify({'error': 'Registry not found'}), 404
        
        with open(registry_file, 'r') as f:
            registry = json.load(f)
        
        if element_key not in registry.get('elements', {}):
            return jsonify({'error': 'Element not found in registry'}), 404
        
        # Delete the element
        del registry['elements'][element_key]
        registry['statistics']['total_elements'] = len(registry['elements'])
        registry['last_updated'] = datetime.now().isoformat() + 'Z'
        
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Element deleted'}), 200
        
    except Exception as e:
        print(f"Error deleting registry element: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/parser/registry', methods=['GET'])
def get_registry_tree():
    """Load registry for tree viewer"""
    try:
        domain = request.args.get('domain')
        page = request.args.get('page')
        
        if not domain or not page:
            return jsonify({'error': 'Missing domain or page parameter'}), 400
        
        project_root = current_app.config['PROJECT_ROOT']
        registry = get_registry(str(project_root / 'element_maps'))
        
        element_map = registry.load_map(domain, page)
        
        if not element_map:
            return jsonify({'error': 'Registry not found'}), 404
        
        return jsonify(element_map), 200
        
    except Exception as e:
        import traceback
        print(f"Error loading registry: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp.route('/parser/registry', methods=['PUT'])
def update_registry_tree():
    """Save updated registry from tree viewer"""
    try:
        domain = request.args.get('domain')
        page = request.args.get('page')
        data = request.get_json()
        
        if not domain or not page:
            return jsonify({'error': 'Missing domain or page parameter'}), 400
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_root = current_app.config['PROJECT_ROOT']
        registry = get_registry(str(project_root / 'element_maps'))
        
        # Validate data structure
        if 'elements' not in data:
            return jsonify({'error': 'Invalid registry format'}), 400
        
        # Create backup before saving
        existing_map = registry.load_map(domain, page)
        if existing_map:
            backup_dir = project_root / 'element_maps' / domain / 'versions'
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'{page}_backup_{timestamp}.json'
            
            with open(backup_file, 'w') as f:
                json.dump(existing_map, f, indent=2)
            
            print(f"Created backup: {backup_file}")
        
        # Save updated registry
        data['updated_at'] = datetime.now().isoformat()
        data['updated_by'] = 'tree_editor'
        
        registry.save_map(domain, page, data)
        
        return jsonify({
            'success': True,
            'message': 'Registry updated successfully',
            'elements_count': len(data.get('elements', {}))
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error saving registry: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

