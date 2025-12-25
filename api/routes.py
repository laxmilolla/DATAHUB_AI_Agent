"""
API Routes for AI Agent QA
"""
from flask import Blueprint, request, jsonify, current_app, send_file
import json
import sys
from pathlib import Path
from datetime import datetime
import threading

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.bedrock_agent import BedrockAgentQA

bp = Blueprint('api', __name__)

# Store active executions
active_executions = {}


@bp.route('/execute', methods=['POST'])
def execute_story():
    """
    Execute test story with autonomous agent
    
    Body:
    {
        "story": "Go to amazon.com and search for tooth brushes"
    }
    """
    try:
        data = request.get_json()
        story = data.get('story', '').strip()
        
        if not story:
            return jsonify({'error': 'Story is required'}), 400
        
        # Create agent
        agent = BedrockAgentQA()
        
        # Start MCP server
        agent.start_mcp_server()
        
        # Store in active executions
        execution_id = agent.execution_id
        active_executions[execution_id] = {
            'agent': agent,
            'status': 'running',
            'story': story,
            'started_at': datetime.now().isoformat()
        }
        
        # Execute in background thread
        def run_execution():
            try:
                results = agent.execute_story(story)
                
                # Save results
                project_root = current_app.config['PROJECT_ROOT']
                results_dir = project_root / 'storage' / 'executions'
                results_dir.mkdir(parents=True, exist_ok=True)
                
                results_file = results_dir / f'{execution_id}.json'
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                # Update status
                active_executions[execution_id]['status'] = results['status']
                active_executions[execution_id]['results'] = results
                
            except Exception as e:
                active_executions[execution_id]['status'] = 'error'
                active_executions[execution_id]['error'] = str(e)
            finally:
                agent.close()
        
        thread = threading.Thread(target=run_execution, daemon=True)
        thread.start()
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'started',
            'message': 'Agent is executing the story'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<execution_id>/status', methods=['GET'])
def get_execution_status(execution_id):
    """Get execution status"""
    
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
    
    # Try loading from file
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
    
    return jsonify({'error': 'Execution not found'}), 404


@bp.route('/executions/<execution_id>/results', methods=['GET'])
def get_execution_results(execution_id):
    """Get full execution results"""
    
    # Try active executions first
    if execution_id in active_executions and 'results' in active_executions[execution_id]:
        return jsonify(active_executions[execution_id]['results']), 200
    
    # Try loading from file
    project_root = current_app.config['PROJECT_ROOT']
    results_file = project_root / 'storage' / 'executions' / f'{execution_id}.json'
    
    if results_file.exists():
        with open(results_file) as f:
            results = json.load(f)
        return jsonify(results), 200
    
    return jsonify({'error': 'Results not found'}), 404


@bp.route('/executions', methods=['GET'])
def list_executions():
    """List all executions"""
    
    project_root = current_app.config['PROJECT_ROOT']
    results_dir = project_root / 'storage' / 'executions'
    
    executions = []
    
    if results_dir.exists():
        for results_file in sorted(results_dir.glob('*.json'), reverse=True):
            try:
                with open(results_file) as f:
                    results = json.load(f)
                
                executions.append({
                    'execution_id': results['execution_id'],
                    'story': results['story'][:100] + '...' if len(results['story']) > 100 else results['story'],
                    'status': results['status'],
                    'started_at': results.get('started_at'),
                    'duration': results.get('duration'),
                    'actions_count': len(results.get('actions_taken', [])),
                    'screenshots_count': len(results.get('screenshots', []))
                })
            except Exception:
                continue
    
    return jsonify({'executions': executions}), 200


@bp.route('/screenshots/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    """Serve screenshot file"""
    
    project_root = current_app.config['PROJECT_ROOT']
    screenshot_path = project_root / 'storage' / 'screenshots' / filename
    
    if screenshot_path.exists():
        return send_file(screenshot_path, mimetype='image/png')
    
    return jsonify({'error': 'Screenshot not found'}), 404


@bp.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'}), 200

