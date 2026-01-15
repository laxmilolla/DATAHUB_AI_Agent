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

# Add paths
refactor_dir = Path(__file__).parent.parent
sys.path.insert(0, str(refactor_dir.parent))

from agent.core.agent import Agent
from REFACTOR.generator.excel_generator import generate_playwright_from_excel

bp_instructions = Blueprint('instructions_api', __name__)

# Store active executions
instructions_executions = {}


@bp_instructions.route('/instructions', methods=['GET'])
def instructions_page():
    """Render instructions page"""
    return render_template('instructions.html')


@bp_instructions.route('/api/instructions/execute', methods=['POST'])
def execute_instructions():
    """
    Execute instructions and generate test cases with XPaths
    
    Expected JSON:
    {
        "instructions": "Go to X, click Y, fill Z..."
    }
    
    Returns:
        JSON with execution_id and status
    """
    try:
        data = request.get_json()
        instructions = data.get('instructions', '').strip()
        
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
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Create Agent
                agent = Agent()
                
                # Execute instructions
                results = loop.run_until_complete(agent.execute_story(instructions))
                
                # Extract steps and XPaths from execution
                actions = results.get('actions_taken', [])
                discoveries = results.get('discoveries', [])
                current_url = ''
                if hasattr(agent, 'discovery_tracker') and agent.discovery_tracker:
                    current_url = agent.discovery_tracker.current_url
                
                steps_data = []
                
                # Create a map of discoveries by element name for quick lookup
                discovery_map = {}
                for disc in discoveries:
                    element_name = disc.get('element_name', '')
                    if element_name:
                        discovery_map[element_name] = disc
                
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
                    
                    # Try to extract XPath from result text (tools often include it)
                    if 'XPath:' in result_text:
                        xpath_match = re.search(r'XPath:\s*([^\n]+)', result_text)
                        if xpath_match:
                            xpath = xpath_match.group(1).strip()
                    
                    # Try to find XPath from discoveries
                    if not xpath and selector:
                        # Try to match selector to discovery
                        for disc in discoveries:
                            if disc.get('final_selector') == selector or disc.get('original_query') == selector:
                                xpath = disc.get('xpath', '')
                                break
                    
                    # Extract text value for fill actions
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
                    
                    # Update current URL for next iteration
                    if tool_name == 'browser_navigate' and url:
                        current_url = url
                
                # Update execution record
                instructions_executions[execution_id]['status'] = results.get('status', 'completed')
                instructions_executions[execution_id]['steps'] = steps_data
                instructions_executions[execution_id]['screenshots'] = results.get('screenshots', [])
                instructions_executions[execution_id]['completed_at'] = datetime.now().isoformat()
                
                # Generate Excel file from execution data
                excel_file = _generate_excel_from_steps(execution_id, steps_data, instructions)
                instructions_executions[execution_id]['excel_file'] = excel_file
                
                loop.close()
                
            except Exception as e:
                import traceback
                print(f"Error executing instructions: {e}")
                print(traceback.format_exc())
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
    """Get execution status"""
    if execution_id not in instructions_executions:
        return jsonify({'error': 'Execution not found'}), 404
    
    exec_data = instructions_executions[execution_id]
    
    return jsonify({
        'success': True,
        'status': exec_data['status'],
        'steps': exec_data.get('steps', []),
        'screenshots': exec_data.get('screenshots', []),
        'excel_file': str(exec_data.get('excel_file', '')) if exec_data.get('excel_file') else None,
        'error': exec_data.get('error')
    }), 200


@bp_instructions.route('/api/instructions/<execution_id>/excel', methods=['GET'])
def download_excel(execution_id):
    """Download generated Excel file"""
    if execution_id not in instructions_executions:
        return jsonify({'error': 'Execution not found'}), 404
    
    excel_file = instructions_executions[execution_id].get('excel_file')
    if not excel_file or not Path(excel_file).exists():
        return jsonify({'error': 'Excel file not generated yet'}), 404
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=f"test_cases_{execution_id}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

