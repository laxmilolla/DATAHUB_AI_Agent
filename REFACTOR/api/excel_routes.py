"""
Excel API Routes
API endpoints for Excel file upload, test generation, and template download.
All endpoints follow generic patterns - no application-specific hard-coding.
"""
from flask import Blueprint, request, jsonify, current_app, send_file
import json
import sys
import threading
from pathlib import Path
from datetime import datetime
import uuid

# Add REFACTOR directory to path
refactor_dir = Path(__file__).parent.parent
sys.path.insert(0, str(refactor_dir.parent))

from REFACTOR.generator.excel_generator import generate_playwright_from_excel
from REFACTOR.generator.excel_generator_ts import generate_playwright_ts_from_excel
from REFACTOR.generator.excel_validator import validate_excel_file, get_validation_summary
from REFACTOR.generator.excel_template import generate_excel_template, get_template_path
from REFACTOR.generator.excel_registry_helper import extract_elements_from_excel, compare_with_registry

bp_excel = Blueprint('excel_api', __name__)
active_excel_generations = {}


@bp_excel.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    """
    Upload and validate Excel file.
    
    Expected form data:
    - file: Excel file (.xlsx or .xls)
    
    Returns:
        JSON with excel_id and validation results
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file type. Expected .xlsx or .xls'}), 400
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Generate unique Excel ID
        excel_id = f"excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create storage directories
        excel_files_dir = project_root / 'storage' / 'excel_files'
        excel_files_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_dir = excel_files_dir / 'metadata'
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        excel_filename = f"{excel_id}.xlsx"
        excel_path = excel_files_dir / excel_filename
        file.save(str(excel_path))
        
        # Validate Excel file
        validation_result = validate_excel_file(excel_path)
        
        # Save metadata
        metadata = {
            'excel_id': excel_id,
            'filename': file.filename,
            'saved_filename': excel_filename,
            'uploaded_at': datetime.now().isoformat(),
            'validation': validation_result,
            'file_path': str(excel_path.relative_to(project_root))
        }
        
        metadata_file = metadata_dir / f"{excel_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Return response
        response = {
            'success': validation_result['valid'],
            'excel_id': excel_id,
            'filename': file.filename,
            'validation': validation_result,
            'uploaded_at': metadata['uploaded_at']
        }
        
        if not validation_result['valid']:
            response['error'] = 'Excel file validation failed'
            response['validation_summary'] = get_validation_summary(validation_result)
            return jsonify(response), 400
        
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        print(f"Error uploading Excel file: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/generate', methods=['POST'])
def generate_from_excel():
    """
    Generate Playwright test from Excel file.
    
    Expected JSON:
    {
        "excel_id": "excel_...",
        "test_name": "optional_test_name"
    }
    
    Returns:
        JSON with generation status and test file info
    """
    try:
        data = request.get_json()
        excel_id = data.get('excel_id')
        
        if not excel_id:
            return jsonify({'error': 'excel_id required'}), 400
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load Excel metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Get Excel file path
        excel_path = project_root / metadata['file_path']
        
        if not excel_path.exists():
            return jsonify({'error': f'Excel file not found: {excel_path}'}), 404
        
        # Generate test name
        test_name = data.get('test_name') or f"test_excel_{excel_id}"
        
        # Create output directory
        output_dir = project_root / 'storage' / 'excel_tests'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{test_name}.py"
        
        # Track generation
        active_excel_generations[excel_id] = {
            'status': 'generating',
            'started_at': datetime.now().isoformat(),
            'excel_id': excel_id,
            'test_name': test_name
        }
        
        # Generate Playwright code
        try:
            generation_result = generate_playwright_from_excel(excel_path, output_file)
        except Exception as e:
            active_excel_generations[excel_id]['status'] = 'error'
            active_excel_generations[excel_id]['error'] = str(e)
            return jsonify({
                'success': False,
                'error': str(e),
                'excel_id': excel_id
            }), 500
        
        # Create execution ID for this Excel test
        execution_id = f"excel_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{excel_id.split('_')[-1][:8]}"
        
        # Create execution metadata (similar to existing system)
        executions_dir = project_root / 'storage' / 'executions'
        executions_dir.mkdir(parents=True, exist_ok=True)
        
        execution_data = {
            'execution_id': execution_id,
            'excel_id': excel_id,
            'source': 'excel',
            'story': f"Excel test case: {metadata.get('filename', 'test_case.xlsx')}",
            'test_name': test_name,
            'test_file': str(output_file.relative_to(project_root)),
            'status': 'running',
            'created_at': datetime.now().isoformat(),
            'excel_metadata': {
                'excel_id': excel_id,
                'filename': metadata.get('filename'),
                'uploaded_at': metadata.get('uploaded_at'),
                'validation': metadata.get('validation', {})
            },
            'actions_taken': [],
            'screenshots': [],
            'playwright_validation': {
                'status': 'running',
                'test_running': True
            }
        }
        
        # Save initial execution data
        execution_file = executions_dir / f"{execution_id}.json"
        with open(execution_file, 'w') as f:
            json.dump(execution_data, f, indent=2)
        
        # Update metadata
        metadata['generated_test'] = {
            'test_name': test_name,
            'test_file': str(output_file.relative_to(project_root)),
            'generated_at': datetime.now().isoformat(),
            'generation_result': generation_result,
            'execution_id': execution_id
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update generation status
        active_excel_generations[excel_id]['status'] = 'completed'
        active_excel_generations[excel_id]['test_file'] = str(output_file.relative_to(project_root))
        active_excel_generations[excel_id]['execution_id'] = execution_id
        
        # Run test automatically in background thread
        def run_excel_test_background():
            try:
                # Import TestRunner (from BACKUP when available)
                try:
                    from validator.test_runner import TestRunner
                except ImportError as e:
                    print(f"⚠️ TestRunner not available - test will not be executed automatically: {e}")
                    import traceback
                    traceback.print_exc()
                    # Update execution with error
                    execution_data['status'] = 'error'
                    execution_data['error'] = f'TestRunner not available: {str(e)}'
                    execution_data['completed_at'] = datetime.now().isoformat()
                    with open(execution_file, 'w') as f:
                        json.dump(execution_data, f, indent=2)
                    return
                
                # TestRunner expects tests in tests/generated/ directory
                # Copy test file to that location
                tests_generated_dir = project_root / 'tests' / 'generated'
                tests_generated_dir.mkdir(parents=True, exist_ok=True)
                
                import shutil
                test_filename = f"{test_name}.py"
                test_dest = tests_generated_dir / test_filename
                shutil.copy2(output_file, test_dest)
                
                # TestRunner expects just the filename
                test_filename_to_run = test_filename
                
                # Run the test
                runner = TestRunner(project_root)
                test_result = runner.run(test_filename_to_run, execution_id=execution_id)
                
                # Update execution data with test results
                execution_data['status'] = 'completed' if test_result.get('status') == 'passed' else 'failed'
                execution_data['playwright_screenshots'] = test_result.get('screenshots', [])
                execution_data['screenshots'] = [s['filename'] for s in test_result.get('screenshots', [])]
                execution_data['playwright_validation'] = {
                    'status': test_result.get('status'),
                    'duration': test_result.get('duration'),
                    'assertions_passed': test_result.get('assertions_passed', 0),
                    'assertions_failed': test_result.get('assertions_failed', 0),
                    'test_file': test_result.get('test_file'),
                    'timestamp': test_result.get('timestamp'),
                    'stdout': test_result.get('stdout', ''),
                    'stderr': test_result.get('stderr', ''),
                    'exit_code': test_result.get('exit_code', 0)
                }
                execution_data['completed_at'] = datetime.now().isoformat()
                
                # Save updated execution data
                with open(execution_file, 'w') as f:
                    json.dump(execution_data, f, indent=2)
                
                # Update Excel metadata with execution results
                excel_metadata = metadata.copy()
                if 'test_executions' not in excel_metadata:
                    excel_metadata['test_executions'] = []
                
                excel_metadata['test_executions'].append({
                    'execution_id': execution_id,
                    'status': test_result.get('status'),
                    'duration': test_result.get('duration'),
                    'executed_at': datetime.now().isoformat()
                })
                excel_metadata['last_execution'] = excel_metadata['test_executions'][-1]
                
                with open(metadata_file, 'w') as f:
                    json.dump(excel_metadata, f, indent=2)
                
                print(f"✅ Excel test execution completed: {execution_id}")
                
            except Exception as e:
                import traceback
                print(f"❌ Error running Excel test: {e}")
                print(traceback.format_exc())
                
                # Update execution with error
                execution_data['status'] = 'error'
                execution_data['error'] = str(e)
                execution_data['completed_at'] = datetime.now().isoformat()
                
                with open(execution_file, 'w') as f:
                    json.dump(execution_data, f, indent=2)
        
        # Start background thread to run test
        thread = threading.Thread(target=run_excel_test_background)
        thread.daemon = True
        thread.start()
        
        # Return response with execution_id
        response = {
            'success': generation_result.get('success', True),
            'excel_id': excel_id,
            'execution_id': execution_id,
            'test_name': test_name,
            'test_file': str(output_file.relative_to(project_root)),
            'rows_processed': generation_result.get('rows_processed', 0),
            'generated_at': datetime.now().isoformat(),
            'test_running': True,
            'results_url': f'/results/{execution_id}'
        }
        
        if generation_result.get('errors'):
            response['warnings'] = generation_result['errors']
            # If generation failed, include error message
            if not generation_result.get('success', True):
                response['error'] = '; '.join(generation_result['errors']) if generation_result['errors'] else 'Generation failed'
        
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        print(f"Error generating test from Excel: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/status', methods=['GET'])
def get_excel_status(excel_id):
    """
    Get Excel file generation status.
    
    Returns:
        JSON with Excel file status and metadata
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Get generation status if available
        generation_status = active_excel_generations.get(excel_id, {})
        
        response = {
            'excel_id': excel_id,
            'filename': metadata.get('filename'),
            'uploaded_at': metadata.get('uploaded_at'),
            'validation': metadata.get('validation', {}),
            'generation_status': generation_status.get('status', 'not_started')
        }
        
        if 'generated_test' in metadata:
            response['generated_test'] = metadata['generated_test']
        
        if 'error' in generation_status:
            response['error'] = generation_status['error']
        
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        print(f"Error getting Excel status: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/template', methods=['GET'])
def download_excel_template():
    """
    Download Excel template file.
    
    Query params:
    - include_examples: true/false (default: true)
    
    Returns:
        Excel template file download
    """
    try:
        include_examples = request.args.get('include_examples', 'true').lower() == 'true'
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Generate template using project root
        template_path = get_template_path("test_case_template.xlsx", project_root=project_root)
        generate_excel_template(template_path, include_examples=include_examples)
        
        if not template_path.exists():
            return jsonify({'error': 'Failed to generate template'}), 500
        
        return send_file(
            str(template_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='test_case_template.xlsx'
        )
        
    except Exception as e:
        import traceback
        print(f"Error downloading template: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/metadata', methods=['GET'])
def get_excel_metadata(excel_id):
    """
    Get Excel file metadata.
    
    Returns:
        JSON with Excel file metadata
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        return jsonify(metadata), 200
        
    except Exception as e:
        import traceback
        print(f"Error getting Excel metadata: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/download', methods=['GET'])
def download_excel_file(excel_id):
    """
    Download uploaded Excel file.
    
    Returns:
        Excel file download
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        excel_path = project_root / metadata['file_path']
        
        if not excel_path.exists():
            return jsonify({'error': f'Excel file not found: {excel_path}'}), 404
        
        return send_file(
            str(excel_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=metadata.get('filename', 'test_case.xlsx')
        )
        
    except Exception as e:
        import traceback
        print(f"Error downloading Excel file: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/generate-ts', methods=['POST'])
def generate_ts_from_excel():
    """
    Generate TypeScript Playwright test from Excel file.
    
    Expected JSON:
    {
        "excel_id": "excel_...",
        "test_name": "optional_test_name"
    }
    
    Returns:
        JSON with generation status and test file info
    """
    try:
        data = request.get_json()
        excel_id = data.get('excel_id')
        
        if not excel_id:
            return jsonify({'error': 'excel_id required'}), 400
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load Excel metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Get Excel file path
        excel_path = project_root / metadata['file_path']
        
        if not excel_path.exists():
            return jsonify({'error': f'Excel file not found: {excel_path}'}), 404
        
        # Generate test name
        test_name = data.get('test_name') or f"test_excel_{excel_id}"
        
        # Create output directory
        output_dir = project_root / 'storage' / 'excel_tests'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{test_name}.spec.ts"  # .spec.ts extension
        
        # Generate TypeScript code
        try:
            generation_result = generate_playwright_ts_from_excel(excel_path, output_file)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'excel_id': excel_id
            }), 500
        
        # Update metadata with TypeScript test info
        if 'generated_test_ts' not in metadata:
            metadata['generated_test_ts'] = {}
        
        metadata['generated_test_ts'] = {
            'test_name': test_name,
            'test_file': str(output_file.relative_to(project_root)),
            'generated_at': datetime.now().isoformat(),
            'generation_result': generation_result
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Check if we should run the test (default: True)
        run_test = data.get('run_test', True)
        
        response_data = {
            'success': True,
            'test_file': str(output_file.relative_to(project_root)),
            'test_name': test_name,
            'excel_id': excel_id,
            'download_url': f'/api/excel/{excel_id}/test-ts',
            'zip_download_url': f'/api/excel/{excel_id}/test-ts-zip',
            'generation_result': generation_result
        }
        
        # Run test in background if requested
        if run_test:
            # Find or create execution_id for this Excel file
            # Check if there's an existing execution for this Excel
            executions_dir = project_root / 'storage' / 'executions'
            execution_id = None
            
            # Look for existing execution with this excel_id
            if executions_dir.exists():
                for exec_file in executions_dir.glob('*.json'):
                    try:
                        with open(exec_file, 'r') as f:
                            exec_data = json.load(f)
                        if exec_data.get('excel_id') == excel_id:
                            execution_id = exec_data.get('execution_id') or exec_file.stem
                            break
                    except:
                        continue
            
            # Create new execution if not found
            if not execution_id:
                execution_id = f"excel_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                execution_file = executions_dir / f'{execution_id}.json'
                executions_dir.mkdir(parents=True, exist_ok=True)
                
                # Create execution data
                exec_data = {
                    'execution_id': execution_id,
                    'excel_id': excel_id,
                    'source': 'excel',
                    'status': 'running',
                    'created_at': datetime.now().isoformat(),
                    'test_file': str(output_file.relative_to(project_root)),
                    'test_name': test_name
                }
                
                with open(execution_file, 'w') as f:
                    json.dump(exec_data, f, indent=2)
            
            # Run test in background thread
            def run_test_background():
                try:
                    from validator.typescript_test_runner import TypeScriptTestRunner
                    
                    runner = TypeScriptTestRunner(project_root)
                    test_result = runner.run(str(output_file), execution_id)
                    
                    # Update execution with test results
                    execution_file = executions_dir / f'{execution_id}.json'
                    if execution_file.exists():
                        with open(execution_file, 'r') as f:
                            exec_data = json.load(f)
                        
                        exec_data['playwright_validation'] = {
                            'status': test_result.get('status'),
                            'duration': test_result.get('duration'),
                            'assertions_passed': test_result.get('assertions_passed', 0),
                            'assertions_failed': test_result.get('assertions_failed', 0),
                            'test_file': test_result.get('test_file'),
                            'timestamp': test_result.get('timestamp'),
                            'stdout': test_result.get('stdout', ''),
                            'stderr': test_result.get('stderr', ''),
                            'exit_code': test_result.get('exit_code', 0)
                        }
                        exec_data['playwright_screenshots'] = test_result.get('screenshots', [])
                        exec_data['status'] = 'completed'
                        exec_data['completed_at'] = datetime.now().isoformat()
                        
                        with open(execution_file, 'w') as f:
                            json.dump(exec_data, f, indent=2)
                        
                        print(f"✅ TypeScript test execution completed for {execution_id}")
                except Exception as e:
                    print(f"Error running TypeScript test in background: {e}")
                    import traceback
                    traceback.print_exc()
            
            thread = threading.Thread(target=run_test_background)
            thread.daemon = True
            thread.start()
            
            response_data['execution_id'] = execution_id
            response_data['test_running'] = True
            response_data['message'] = 'TypeScript test generation completed. Test is running in background. Screenshots will be available shortly.'
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        print(f"Error generating TypeScript test: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/test-ts', methods=['GET'])
def download_ts_test(excel_id):
    """
    Download generated TypeScript Playwright test file.
    
    Returns:
        TypeScript test file download
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        if 'generated_test_ts' not in metadata:
            return jsonify({'error': 'TypeScript test not generated yet'}), 404
        
        test_file_path = project_root / metadata['generated_test_ts']['test_file']
        
        if not test_file_path.exists():
            return jsonify({'error': f'TypeScript test file not found: {test_file_path}'}), 404
        
        return send_file(
            str(test_file_path),
            mimetype='text/typescript',
            as_attachment=True,
            download_name=metadata['generated_test_ts']['test_name'] + '.spec.ts'
        )
        
    except Exception as e:
        import traceback
        print(f"Error downloading TypeScript test file: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/test-ts-zip', methods=['GET'])
def download_ts_test_zip(excel_id):
    """
    Download TypeScript test file (.spec.ts), package.json, README, and all required registry JSON files bundled as a zip file (excludes .env for security)
    
    Returns:
        Zip file download
    """
    try:
        from flask import send_file
        from io import BytesIO
        import zipfile
        import re
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        if 'generated_test_ts' not in metadata:
            return jsonify({'error': 'TypeScript test not generated yet'}), 404
        
        test_file_path = project_root / metadata['generated_test_ts']['test_file']
        test_name = metadata['generated_test_ts']['test_name']
        
        if not test_file_path.exists():
            return jsonify({'error': f'TypeScript test file not found: {test_file_path}'}), 404
        
        # Read TypeScript test file to extract REGISTRY_PATHS
        with open(test_file_path, 'r') as f:
            ts_content = f.read()
        
        # Extract REGISTRY_PATHS from TypeScript file
        registry_paths = []
        # Match: const REGISTRY_PATHS = [\n    'path1',\n    'path2',\n]
        match = re.search(r"const\s+REGISTRY_PATHS\s*=\s*\[(.*?)\]", ts_content, re.DOTALL)
        if match:
            paths_str = match.group(1)
            # Extract all quoted strings
            path_matches = re.findall(r"['\"]([^'\"]+)['\"]", paths_str)
            registry_paths = [p.strip() for p in path_matches if p.strip()]
        
        # Create package.json content
        package_json_content = '''{
  "name": "playwright-test",
  "version": "1.0.0",
  "scripts": {
    "test": "playwright test"
  },
  "dependencies": {
    "@playwright/test": "^1.40.0",
    "dotenv": "^16.0.0",
    "otplib": "^12.0.0"
  }
}'''
        
        # Create README content
        readme_content = f'''# Playwright TypeScript Test Setup

## Prerequisites
- Node.js (v16 or higher)
- npm

## Setup Instructions

1. Extract all files from this zip
2. Create a `.env` file with your environment variables (e.g., `TOTP_SECRET_KEY=your_secret_key`)
3. Run: `npm install`
4. Run: `npx playwright install chromium`
5. Run: `npx playwright test {test_name}.spec.ts`

## Files Included
- `{test_name}.spec.ts` - Main test file
- `package.json` - Dependencies
- `element_maps/` - JSON registry files with element XPath mappings

## Important
- **`.env` file is NOT included** for security reasons. You must create your own `.env` file with appropriate credentials.
- Registry JSON files are included in the `element_maps/` directory structure

## Notes
- Screenshots saved to `storage/screenshots/`
- Test uses registry-based element lookup (no hard-coded XPaths)
'''
        
        # Create zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add TypeScript test file
            ts_filename = f'{test_name}.spec.ts'
            zip_file.write(test_file_path, ts_filename)
            print(f"✅ Added TypeScript test file to zip: {ts_filename}")
            
            # Note: .env file is NOT included for security reasons
            
            # Add package.json
            zip_file.writestr('package.json', package_json_content)
            print(f"✅ Added package.json to zip")
            
            # Add README.md
            zip_file.writestr('README.md', readme_content)
            print(f"✅ Added README.md to zip")
            
            # Add all registry JSON files with proper directory structure
            for registry_path in registry_paths:
                # registry_path is like 'element_maps/domain/page_page.json'
                full_registry_path = project_root / registry_path
                
                if full_registry_path.exists():
                    # Preserve the full path structure as the test expects it
                    zip_path = registry_path
                    zip_file.write(full_registry_path, zip_path)
                    print(f"✅ Added registry file to zip: {zip_path}")
                else:
                    print(f"⚠️  Registry file not found: {full_registry_path}")
        
        # Verify zip contents
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, 'r') as verify_zip:
            file_list = verify_zip.namelist()
            print(f"📦 Zip contains {len(file_list)} files:")
            for name in file_list:
                print(f"   - {name}")
        
        zip_buffer.seek(0)
        
        # Create zip filename
        zip_filename = f'{test_name}_typescript_complete.zip'
        
        # Send zip file
        response = send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
        response.headers['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error creating TypeScript zip file: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/test', methods=['GET'])
def download_generated_test(excel_id):
    """
    Download generated Playwright test file.
    
    Returns:
        Python test file download
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        if 'generated_test' not in metadata:
            return jsonify({'error': 'Test not generated yet'}), 404
        
        test_file_path = project_root / metadata['generated_test']['test_file']
        
        if not test_file_path.exists():
            return jsonify({'error': f'Test file not found: {test_file_path}'}), 404
        
        return send_file(
            str(test_file_path),
            mimetype='text/x-python',
            as_attachment=True,
            download_name=metadata['generated_test']['test_name'] + '.py'
        )
        
    except Exception as e:
        import traceback
        print(f"Error downloading test file: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/registry/compare', methods=['GET'])
def compare_excel_with_registry(excel_id):
    """
    Compare Excel file elements with registry to find new/updated elements.
    
    Returns:
        JSON with new_elements, updated_elements, unchanged_elements
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Get Excel file path
        excel_path = project_root / metadata['file_path']
        
        if not excel_path.exists():
            return jsonify({'error': f'Excel file not found: {excel_path}'}), 404
        
        # Extract elements from Excel
        elements = extract_elements_from_excel(excel_path)
        
        # Load registry
        from utils.element_registry import get_registry
        registry = get_registry()
        
        # Compare with registry
        comparison = compare_with_registry(elements, registry)
        
        return jsonify({
            'success': True,
            'comparison': comparison,
            'excel_id': excel_id
        }), 200
    
    except Exception as e:
        import traceback
        print(f"Error comparing Excel with registry: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/registry/update', methods=['POST'])
def update_registry_from_excel(excel_id):
    """
    Update registry with elements from Excel file.
    
    Expected JSON:
    {
        "new_elements": [...],  # Elements to add
        "updated_elements": [...]  # Elements to update
    }
    
    Returns:
        JSON with update status
    """
    try:
        data = request.get_json()
        new_elements = data.get('new_elements', [])
        updated_elements = data.get('updated_elements', [])
        
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        # Load registry
        from utils.element_registry import get_registry
        registry = get_registry()
        
        added_count = 0
        updated_count = 0
        errors = []
        
        # Add new elements
        for elem in new_elements:
            try:
                domain = elem['domain']
                page = elem['page']
                element_name = elem['element_name']
                xpath = elem['xpath']
                
                # Load or create element map
                element_map = registry.load_map(domain, page)
                if not element_map:
                    from datetime import datetime
                    element_map = {
                        "page": page,
                        "url": elem['url'],
                        "version": "1.0",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "elements": {},
                        "id_index": {},
                        "statistics": {
                            "total_elements": 0,
                            "parsed_elements": 0,
                            "discovered_elements": 0
                        }
                    }
                
                # Add element
                if element_name not in element_map['elements']:
                    element_map['elements'][element_name] = {
                        'xpath': xpath,
                        'selector': xpath,
                        'element_id': registry._generate_element_id(element_name, xpath),
                        'usage_count': 0,
                        'last_used': None,
                        'source': 'excel',
                        'object_type': elem.get('object_type', ''),
                        'action': elem.get('action', '')
                    }
                    element_map['statistics']['total_elements'] = len(element_map['elements'])
                    registry.save_map(domain, page, element_map)
                    added_count += 1
            except Exception as e:
                errors.append(f"Failed to add {elem.get('element_name', 'unknown')}: {str(e)}")
        
        # Update existing elements
        for elem in updated_elements:
            try:
                domain = elem['domain']
                page = elem['page']
                element_name = elem['element_name']
                new_xpath = elem['new_xpath']
                
                # Load element map
                element_map = registry.load_map(domain, page)
                if not element_map:
                    errors.append(f"Registry not found for {domain}/{page}")
                    continue
                
                # Update element
                if element_name in element_map['elements']:
                    element_map['elements'][element_name]['xpath'] = new_xpath
                    element_map['elements'][element_name]['selector'] = new_xpath
                    element_map['elements'][element_name]['source'] = 'excel_updated'
                    registry.save_map(domain, page, element_map)
                    updated_count += 1
                else:
                    errors.append(f"Element {element_name} not found in registry")
            except Exception as e:
                errors.append(f"Failed to update {elem.get('element_name', 'unknown')}: {str(e)}")
        
        return jsonify({
            'success': True,
            'added_count': added_count,
            'updated_count': updated_count,
            'errors': errors,
            'excel_id': excel_id
        }), 200
    
    except Exception as e:
        import traceback
        print(f"Error updating registry from Excel: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp_excel.route('/api/excel/<excel_id>/steps', methods=['GET'])
def get_excel_steps(excel_id):
    """
    Get test steps from Excel file.
    
    Returns:
        JSON with steps array
    """
    try:
        project_root = current_app.config.get('PROJECT_ROOT', Path.cwd())
        
        # Load metadata
        metadata_dir = project_root / 'storage' / 'excel_files' / 'metadata'
        metadata_file = metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return jsonify({'error': f'Excel file not found: {excel_id}'}), 404
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Get Excel file path
        excel_path = project_root / metadata['file_path']
        
        if not excel_path.exists():
            return jsonify({'error': f'Excel file not found: {excel_path}'}), 404
        
        # Read Excel file and extract steps
        import pandas as pd
        df = pd.read_excel(excel_path)
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        steps = []
        for idx, row in df.iterrows():
            step = str(row.get('step', idx + 1)).strip()
            url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else ''
            xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else ''
            action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else ''
            object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
            text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else ''
            wait_time = row.get('wait_time', None)
            functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else ''
            is_optional = str(row.get('optional', '')).strip().lower() in ['true', 'yes', '1', 'y']
            
            steps.append({
                'step': step,
                'url': url if url and url.upper() != 'N/A' else None,
                'xpath': xpath if xpath and xpath.upper() != 'N/A' else None,
                'action': action,
                'object_type': object_type,
                'text_value': text_value if text_value else None,
                'wait_time': wait_time,
                'functions': functions if functions else None,
                'optional': is_optional
            })
        
        return jsonify({
            'success': True,
            'steps': steps,
            'excel_id': excel_id
        }), 200
    
    except Exception as e:
        import traceback
        print(f"Error getting Excel steps: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

