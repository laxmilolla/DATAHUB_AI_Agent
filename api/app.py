"""
Flask API for AI Agent QA
Pure Python Architecture 2
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import routes
from api.routes import bp as api_bp


def get_git_branch():
    """Get current git branch name"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return 'unknown'

# Instructions routes moved to Experimented folder - no longer used
# Excel Execution routes moved to Experimented folder - no longer used

def create_app():
    """Create and configure Flask app"""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    app = Flask(
        __name__,
        template_folder=str(project_root / 'web' / 'templates'),
        static_folder=str(project_root / 'web' / 'static')
    )
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    app.config['PROJECT_ROOT'] = project_root
    
    # Get git branch for UI display
    git_branch = get_git_branch()
    print(f"🌿 Current git branch: {git_branch}")
    
    # CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    print("✅ API routes registered (includes Excel routes)")
    
    # Make git branch available to all templates
    @app.context_processor
    def inject_git_branch():
        return {'git_branch': git_branch}
    
    # Instructions blueprint moved to Experimented folder - no longer registered
    # Excel Execution blueprint moved to Experimented folder - no longer registered
    
    # Home route - render UI
    @app.route('/')
    def index():
        return render_template('index.html', timestamp=int(time.time()), git_branch=git_branch)
    
    # Parser, element-maps, and instructions routes moved to BACKUP/Experiment - no longer available
    
    @app.route('/results/<execution_id>')
    def results(execution_id):
        response = app.make_response(render_template('results.html', execution_id=execution_id, timestamp=int(time.time()), git_branch=git_branch))
        # Prevent browser caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    @app.route('/excel-upload')
    def excel_upload_page():
        return render_template('excel_upload.html', timestamp=int(time.time()), git_branch=git_branch)
    
    @app.route('/parser')
    def parser_page():
        return render_template('parser_ai.html', timestamp=int(time.time()))
    
    @app.route('/instructions')
    def instructions_page():
        return render_template('instructions.html', timestamp=int(time.time()))
    
    # Excel Execution route moved to Experimented folder - no longer available
    
    return app


if __name__ == '__main__':
    app = create_app()
    print('\n' + '='*60)
    print('🚀 AI Agent QA - Architecture 2 (Pure Python)')
    print('='*60)
    print(f'Web UI: http://0.0.0.0:5000')
    print(f'API: http://0.0.0.0:5000/api/health')
    print('='*60 + '\n')
    # Disable debug mode in production to avoid reload loops with generated tests
    app.run(host='0.0.0.0', port=5000, debug=False)

