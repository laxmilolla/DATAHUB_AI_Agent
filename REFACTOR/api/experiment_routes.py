"""
Experiment Area API Routes
API endpoints for interactive browser experiment sessions
"""
from flask import Blueprint, request, jsonify, current_app, send_file, render_template
import json
import sys
import threading
import uuid
from pathlib import Path
from datetime import datetime
import asyncio

# Add paths
refactor_dir = Path(__file__).parent.parent
sys.path.insert(0, str(refactor_dir.parent))

from REFACTOR.experiment.experiment_runner import ExperimentRunner
from REFACTOR.generator.excel_generator import generate_playwright_from_excel
import pandas as pd

bp_experiment = Blueprint('experiment_api', __name__)

# Store active sessions
experiment_sessions = {}


@bp_experiment.route('/experiment', methods=['GET'])
def experiment_page():
    """Render experiment area page"""
    return render_template('experiment.html')


@bp_experiment.route('/api/experiment/start', methods=['POST'])
def start_experiment():
    """
    Start a new experiment browser session
    
    Options:
    1. Local browser (if Flask runs locally): Browser visible on user's screen
    2. Server browser: Browser runs on server (not visible)
    3. CDP connection: Connect to user's Chrome browser (if cdp_url provided)
    
    Expected JSON (optional):
    {
        "cdp_url": "http://localhost:9222"  // Connect to user's Chrome browser
    }
    
    Returns:
        JSON with session_id and browser_location info
    """
    try:
        data = request.get_json() or {}
        cdp_url = data.get('cdp_url', '').strip()
        
        session_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Detect if running locally
        request_host = request.headers.get('Host', '')
        is_local = 'localhost' in request_host or '127.0.0.1' in request_host or request_host.startswith('localhost')
        
        # Determine browser mode
        if cdp_url:
            browser_mode = 'cdp'
            browser_location = 'user_browser'
        elif is_local:
            browser_mode = 'local'
            browser_location = 'local'
        else:
            browser_mode = 'server'
            browser_location = 'server'
        
        # Create experiment runner
        runner = ExperimentRunner(session_id)
        
        # Start browser in background thread
        browser_result = {'success': False, 'error': 'Unknown error'}
        
        def start_browser_async():
            nonlocal browser_result
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if cdp_url:
                    browser_result = loop.run_until_complete(runner.start_browser(cdp_url=cdp_url))
                else:
                    browser_result = loop.run_until_complete(runner.start_browser())
            except Exception as e:
                browser_result = {'success': False, 'error': str(e)}
            finally:
                loop.close()
        
        thread = threading.Thread(target=start_browser_async, daemon=True)
        thread.start()
        thread.join(timeout=10)  # Wait up to 10 seconds for browser to start
        
        # Check if browser started successfully
        if not browser_result.get('success'):
            error_msg = browser_result.get('error', 'Unknown error')
            if 'ECONNREFUSED' in error_msg or 'localhost:9222' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'CDP connection failed',
                    'message': '❌ Cannot connect to Chrome browser. When Flask runs on a server, it cannot connect to localhost:9222 on your machine. Options: 1) Use SSH port forwarding: ssh -L 9222:localhost:9222 user@server, then start Chrome locally, OR 2) Uncheck "Use My Chrome Browser" to use server browser (screenshots only).',
                    'browser_mode': browser_mode
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Browser startup failed',
                    'message': f'❌ Failed to start browser: {error_msg}',
                    'browser_mode': browser_mode
                }), 500
        
        # Store session only if browser started successfully
        experiment_sessions[session_id] = {
            'runner': runner,
            'started_at': datetime.now().isoformat(),
            'status': 'running',
            'actions': [],
            'screenshots': [],
            'is_local': is_local,
            'browser_mode': browser_mode,
            'cdp_url': cdp_url if cdp_url else None
        }
        
        # Generate appropriate message
        if browser_mode == 'cdp':
            message = '✅ Connected to your Chrome browser! You can interact with it directly.'
        elif browser_mode == 'local':
            message = '✅ Browser running locally - you should see it on your screen!'
        else:
            message = '⚠️ Browser runs on server (not visible). Screenshots will be shown in real-time. To use your browser, start Chrome with: chrome --remote-debugging-port=9222'
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'browser_location': browser_location,
            'browser_mode': browser_mode,
            'message': message,
            'cdp_instructions': None if browser_mode != 'server' else {
                'step1': 'Start Chrome with remote debugging:',
                'command_mac': '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug',
                'command_linux': 'google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug',
                'command_windows': 'chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\\chrome-debug',
                'step2': 'Then refresh this page and click "Start Browser" again'
            }
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error starting experiment: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_experiment.route('/api/experiment/<session_id>/execute', methods=['POST'])
def execute_experiment(session_id):
    """
    Execute test instructions in experiment session
    
    Expected JSON:
    {
        "instructions": "Fill form and click submit"
    }
    
    Returns:
        JSON with execution status
    """
    try:
        if session_id not in experiment_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        data = request.get_json()
        instructions = data.get('instructions', '').strip()
        
        if not instructions:
            return jsonify({'error': 'Instructions required'}), 400
        
        session = experiment_sessions[session_id]
        runner = session['runner']
        
        # Execute in background thread
        def execute_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(runner.execute_instructions(instructions))
            loop.close()
            
            # Update session with results
            if result.get('success'):
                session['actions'] = result.get('actions', [])
                session['screenshots'] = result.get('screenshots', [])
                session['status'] = result.get('status', 'completed')
                session['results'] = result.get('results')
        
        thread = threading.Thread(target=execute_async, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Execution started'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error executing experiment: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_experiment.route('/api/experiment/<session_id>/status', methods=['GET'])
def get_experiment_status(session_id):
    """
    Get execution status for experiment session
    
    Returns:
        JSON with status, current_step, total_steps, etc.
    """
    try:
        if session_id not in experiment_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = experiment_sessions[session_id]
        runner = session['runner']
        
        status = runner.get_status()
        
        return jsonify({
            'success': True,
            'status': status.get('status', 'unknown'),
            'current_step': status.get('current_step', 0),
            'total_steps': status.get('total_steps', 0),
            'step_description': status.get('step_description', ''),
            'screenshots_count': status.get('screenshots_count', 0)
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error getting status: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_experiment.route('/api/experiment/<session_id>/screenshots', methods=['GET'])
def get_experiment_screenshots(session_id):
    """
    Get list of screenshots for experiment session
    
    Returns:
        JSON with screenshots array
    """
    try:
        if session_id not in experiment_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = experiment_sessions[session_id]
        runner = session['runner']
        
        screenshots = runner.get_screenshots()
        
        return jsonify({
            'success': True,
            'screenshots': screenshots
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error getting screenshots: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_experiment.route('/api/experiment/<session_id>/excel', methods=['GET'])
def download_experiment_excel(session_id):
    """
    Generate and download Excel file from experiment session
    
    Returns:
        Excel file download
    """
    try:
        if session_id not in experiment_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = experiment_sessions[session_id]
        runner = session['runner']
        results = runner.get_results()
        
        if not results:
            return jsonify({'error': 'No execution results available'}), 400
        
        # Convert actions to Excel format
        actions = results.get('actions_taken', [])
        if not actions:
            return jsonify({'error': 'No actions to export'}), 400
        
        # Create DataFrame from actions
        rows = []
        for idx, action in enumerate(actions, 1):
            tool = action.get('tool', 'unknown')
            input_data = action.get('input', {})
            result = action.get('result', '')
            
            # Determine action type
            action_type = 'click'
            if tool == 'browser_navigate':
                action_type = 'navigate'
            elif tool == 'browser_fill':
                action_type = 'fill'
            elif tool == 'browser_verify':
                action_type = 'verify'
            elif tool == 'browser_evaluate':
                action_type = 'wait'
            
            # Extract URL, XPath, text_value
            url = input_data.get('url', '')
            xpath = input_data.get('selector', '') or input_data.get('xpath', '')
            text_value = input_data.get('text', '') or input_data.get('value', '')
            object_type = input_data.get('object_type', '')
            
            rows.append({
                'Step': idx,
                'URL': url if url else 'N/A',
                'XPath': xpath if xpath else 'N/A',
                'Action': action_type,
                'Object Type': object_type if object_type else '',
                'Text Value': text_value if text_value else '',
                'Wait Time': '',
                'Functions': '',
                'Optional': 'false'
            })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Save to temporary file
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        excel_dir = project_root / 'storage' / 'experiment_excel'
        excel_dir.mkdir(parents=True, exist_ok=True)
        
        excel_file = excel_dir / f"experiment_{session_id}.xlsx"
        df.to_excel(excel_file, index=False, engine='openpyxl')
        
        return send_file(
            str(excel_file),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"experiment_{session_id}.xlsx"
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating Excel: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_experiment.route('/api/experiment/<session_id>/stop', methods=['POST'])
def stop_experiment(session_id):
    """
    Stop experiment browser session
    
    Returns:
        JSON with success status
    """
    try:
        if session_id not in experiment_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = experiment_sessions[session_id]
        runner = session['runner']
        
        # Stop browser in background
        def stop_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(runner.stop_browser())
            loop.close()
        
        thread = threading.Thread(target=stop_async, daemon=True)
        thread.start()
        
        # Remove session
        del experiment_sessions[session_id]
        
        return jsonify({
            'success': True,
            'message': 'Session stopped'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error stopping experiment: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_experiment.route('/api/experiment/<session_id>/browser', methods=['GET'])
def get_browser_viewport(session_id):
    """
    Get browser viewport (for iframe embedding)
    Note: This is a placeholder - actual browser display would need VNC or similar
    For now, return a message indicating browser is running
    """
    if session_id not in experiment_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Browser Viewport</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
                background: #f5f5f5;
            }
            .message {
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
        </style>
    </head>
    <body>
        <div class="message">
            <h2>🌐 Browser Running</h2>
            <p>Browser is running in headful mode on the server.</p>
            <p>You can interact with it directly or view screenshots below.</p>
        </div>
    </body>
    </html>
    """

