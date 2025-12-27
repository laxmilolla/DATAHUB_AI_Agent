"""API Routes"""
from flask import Blueprint, request, jsonify, current_app, send_file, render_template
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import threading

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.bedrock_playwright_agent import BedrockPlaywrightAgent

bp = Blueprint('api', __name__)
active_executions = {}


@bp.route('/execute', methods=['POST'])
def execute_story():
    try:
        data = request.get_json()
        story = data.get('story', '').strip()
        
        if not story:
            return jsonify({'error': 'Story required'}), 400
        
        agent = BedrockPlaywrightAgent()
        execution_id = agent.execution_id
        
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
                active_executions[execution_id]['status'] = 'error'
                active_executions[execution_id]['error'] = str(e)
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
        if 'results' in exec_data:
            results = exec_data['results']
            response.update({
                'actions_count': len(results.get('actions_taken', [])),
                'screenshots_count': len(results.get('screenshots', [])),
                'summary': results.get('summary'),
                'error': results.get('error')
            })
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
    # Return live results from active executions (even if still running)
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
    
    project_root = current_app.config['PROJECT_ROOT']
    results_file = project_root / 'storage' / 'executions' / f'{execution_id}.json'
    
    if results_file.exists():
        with open(results_file) as f:
            return jsonify(json.load(f)), 200
    
    return jsonify({'error': 'Not found'}), 404


@bp.route('/executions', methods=['GET'])
def list_executions():
    project_root = current_app.config['PROJECT_ROOT']
    results_dir = project_root / 'storage' / 'executions'
    executions = []
    
    if results_dir.exists():
        for f in sorted(results_dir.glob('*.json'), reverse=True):
            try:
                with open(f) as file:
                    r = json.load(file)
                executions.append({
                    'execution_id': r['execution_id'],
                    'story': r['story'][:100],
                    'status': r['status'],
                    'actions_count': len(r.get('actions_taken', [])),
                    'screenshots_count': len(r.get('screenshots', []))
                })
            except:
                continue
    
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
@bp.route('/parse-html', methods=['POST'])
def parse_html():
    """Parse HTML and return extracted elements"""
    try:
        data = request.json
        html = data.get('html', '')
        url = data.get('url', '')
        
        if not html or not url:
            return jsonify({'error': 'HTML and URL are required'}), 400
        
        # Import parser
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(current_app.config['PROJECT_ROOT'])))
        from utils.html_parser import parse_html_to_element_map
        
        # Parse HTML
        element_map = parse_html_to_element_map(html, url)
        
        return jsonify({
            'success': True,
            'element_map': element_map
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        return jsonify({'error': str(e)}), 500

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

