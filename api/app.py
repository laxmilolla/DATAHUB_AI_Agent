"""
Flask API for AI Agent QA
Pure Python Architecture 2
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import routes
from api.routes import bp as api_bp

# Import Excel routes
try:
    from REFACTOR.api.excel_routes import bp_excel
    EXCEL_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Excel routes not available: {e}")
    EXCEL_ROUTES_AVAILABLE = False

# Import Experiment routes
try:
    from REFACTOR.api.experiment_routes import bp_experiment
    EXPERIMENT_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Experiment routes not available: {e}")
    EXPERIMENT_ROUTES_AVAILABLE = False

# Import Instructions routes
try:
    from REFACTOR.api.instructions_routes import bp_instructions
    INSTRUCTIONS_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Instructions routes not available: {e}")
    INSTRUCTIONS_ROUTES_AVAILABLE = False

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
    
    # CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register Excel blueprint if available
    if EXCEL_ROUTES_AVAILABLE:
        app.register_blueprint(bp_excel)
        print("✅ Excel API routes registered")
    
    # Register Experiment blueprint if available
    if EXPERIMENT_ROUTES_AVAILABLE:
        app.register_blueprint(bp_experiment)
        print("✅ Experiment API routes registered")
    
    # Register Instructions blueprint if available
    if INSTRUCTIONS_ROUTES_AVAILABLE:
        app.register_blueprint(bp_instructions)
        print("✅ Instructions API routes registered")
    
    # Home route - render UI
    @app.route('/')
    def index():
        return render_template('index.html', timestamp=int(time.time()))
    
    @app.route('/parser')
    def parser_page():
        return render_template('parser.html')
    
    @app.route('/element-maps')
    def element_maps_page():
        return render_template('element_maps.html')
    
    @app.route('/results/<execution_id>')
    def results(execution_id):
        response = app.make_response(render_template('results.html', execution_id=execution_id, timestamp=int(time.time())))
        # Prevent browser caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    @app.route('/excel-upload')
    def excel_upload_page():
        return render_template('excel_upload.html', timestamp=int(time.time()))
    
    @app.route('/instructions')
    def instructions_page():
        return render_template('instructions.html', timestamp=int(time.time()))
    
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

