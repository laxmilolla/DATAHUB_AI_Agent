"""API Routes"""
from flask import Blueprint, request, jsonify, current_app, send_file
from pathlib import Path
import sys
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.html_parser import parse_html_to_element_map
from utils.element_registry import get_registry

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


@bp.route('/fetch-html', methods=['POST'])
def fetch_html():
    """Fetch HTML from URL using Playwright"""
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Import Playwright fetcher
        from playwright.async_api import async_playwright
        
        async def fetch_page_html(url):
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until='networkidle', timeout=30000)
                html = await page.content()
                await browser.close()
                return html
        
        html = asyncio.run(fetch_page_html(url))
        
        return jsonify({
            'success': True,
            'html': html
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/parse-html', methods=['POST'])
def parse_html():
    """Parse HTML using Playwright parser with live DOM"""
    try:
        data = request.json
        url = data.get('url', '')
        page_name = data.get('page_name', '')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Import Playwright parser
        from playwright.async_api import async_playwright
        from utils.playwright_tree_parser import parse_with_tree
        
        async def parse_with_playwright(url, page_name):
            """Parse page using Playwright with live DOM"""
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
                
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Dismiss any popups
                try:
                    continue_btn = page.locator("text='Continue'").first
                    if await continue_btn.is_visible(timeout=2000):
                        await continue_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Parse using tree-based parser
                element_map = await parse_with_tree(page)
                
                await browser.close()
                
                if page_name:
                    element_map["page"] = page_name
                
                return element_map
        
        element_map = asyncio.run(parse_with_playwright(url, page_name))
        
        return jsonify({
            'success': True,
            'element_map': element_map
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/manual-register', methods=['POST'])
def manual_register_element():
    """Manually register element from HTML"""
    try:
        data = request.get_json()
        html_string = data.get('html', '').strip()
        url = data.get('url', '').strip()
        element_name = data.get('element_name', '').strip() or None
        
        if not html_string:
            return jsonify({'success': False, 'error': 'HTML element required'}), 400
        if not url:
            return jsonify({'success': False, 'error': 'URL required'}), 400
        
        element_registry = get_registry()
        
        from REFACTOR.api.manual_registry_helper import ManualRegistryHelper
        helper = ManualRegistryHelper(element_registry)
        
        result = helper.register_element(
            html_string=html_string,
            url=url,
            element_name=element_name
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'details': traceback.format_exc()
        }), 500


@bp.route('/save-element-map', methods=['POST'])
def save_element_map():
    """Save parsed element map to registry"""
    try:
        data = request.json
        element_map = data.get('element_map')
        
        if not element_map:
            return jsonify({'error': 'Element map is required'}), 400
        
        registry = get_registry(str(Path(current_app.config['PROJECT_ROOT']) / 'element_maps'))
        
        url = element_map.get('url', '')
        domain = url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
        page = element_map.get('page', 'unknown')
        
        if page.startswith('http://') or page.startswith('https://'):
            page_parts = page.split('/')[-1].split('#')
            if page_parts and page_parts[0]:
                page = page_parts[0]
            else:
                page = 'home'
        
        page = page.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        if not page or len(page) > 100:
            page = 'home'
        
        element_map['page'] = page
        
        registry.save_map(domain, page, element_map)
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
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500


@bp.route('/element-maps/list')
def list_element_maps():
    """List all existing element maps"""
    try:
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
        registry = get_registry(str(Path(current_app.config['PROJECT_ROOT']) / 'element_maps'))
        element_map = registry.load_map(domain, page)
        
        if not element_map:
            return jsonify({'error': 'Map not found'}), 404
        
        return jsonify(element_map)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
