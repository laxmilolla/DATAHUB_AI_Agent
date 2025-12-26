"""
Flask API for AI Agent QA
Pure Python Architecture 2
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routes
from routes import bp as api_bp

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
    
    # Home route - render UI
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/element-maps')
    def element_maps_page():
        return render_template('element_maps.html')
    
    @app.route('/results/<execution_id>')
    def results(execution_id):
        return render_template('results.html', execution_id=execution_id)
    
    return app


if __name__ == '__main__':
    app = create_app()
    print('\n' + '='*60)
    print('🚀 AI Agent QA - Architecture 2 (Pure Python)')
    print('='*60)
    print(f'Web UI: http://0.0.0.0:5000')
    print(f'API: http://0.0.0.0:5000/api/health')
    print('='*60 + '\n')
    app.run(host='0.0.0.0', port=5000, debug=True)

