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
from REFACTOR.generator.excel_validator import validate_excel_file, get_validation_summary
from REFACTOR.generator.excel_template import generate_excel_template, get_template_path

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
        
        # Update metadata
        metadata['generated_test'] = {
            'test_name': test_name,
            'test_file': str(output_file.relative_to(project_root)),
            'generated_at': datetime.now().isoformat(),
            'generation_result': generation_result
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update generation status
        active_excel_generations[excel_id]['status'] = 'completed'
        active_excel_generations[excel_id]['test_file'] = str(output_file.relative_to(project_root))
        
        # Return response
        response = {
            'success': generation_result.get('success', True),
            'excel_id': excel_id,
            'test_name': test_name,
            'test_file': str(output_file.relative_to(project_root)),
            'rows_processed': generation_result.get('rows_processed', 0),
            'generated_at': datetime.now().isoformat()
        }
        
        if generation_result.get('errors'):
            response['warnings'] = generation_result['errors']
        
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

