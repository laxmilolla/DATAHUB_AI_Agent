"""API Routes - Excel-Only Version
Minimal routes required for Excel functionality.
Non-Excel routes have been moved to BACKUP/ or Experimented/.
"""
from flask import Blueprint, jsonify, current_app, send_file
from pathlib import Path

bp = Blueprint('api', __name__)


@bp.route('/screenshots/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    """Serve screenshot files for Excel test results"""
    project_root = current_app.config['PROJECT_ROOT']
    
    # Try main screenshots directory first
    path = project_root / 'storage' / 'screenshots' / filename
    if path.exists():
        return send_file(path, mimetype='image/png')
    
    # Also check test directory screenshots (for Excel tests)
    test_path = project_root / 'storage' / 'excel_tests' / 'storage' / 'screenshots' / filename
    if test_path.exists():
        return send_file(test_path, mimetype='image/png')
    
    return jsonify({'error': 'Not found'}), 404


@bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'architecture': 'Pure Python + Playwright'}), 200
