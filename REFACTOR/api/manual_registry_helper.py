"""
Manual Registry Helper - Core logic for manual element registration
Simple utility to register elements from HTML + URL
"""
import re
from typing import Dict, Optional
from datetime import datetime
from urllib.parse import urlparse

from REFACTOR.utils.html_element_parser import HTMLElementParser


class ManualRegistryHelper:
    """Helper for manual element registration"""
    
    def __init__(self, element_registry):
        self.element_registry = element_registry
        self.html_parser = HTMLElementParser()
    
    def register_element(
        self,
        html_string: str,
        url: str,
        element_name: str = None
    ) -> Dict:
        """
        Main registration function
        
        Steps:
        1. Parse HTML → extract attributes
        2. Extract domain/page from URL
        3. Infer element name (from label or attributes)
        4. Generate XPath (priority: data-testid → id → name → aria-labelledby)
        5. Generate selector (best available)
        6. Create discovery object
        7. Update Registry JSON
        8. Return results
        
        Returns:
        {
            'success': True,
            'element_name': 'Submission Name',
            'xpath': '//input[@data-testid="submission-name-input"]',
            'selector': 'input[data-testid="submission-name-input"]',
            'label_text': 'Submission Name',
            'registry_path': 'element_maps/.../data-submissions_page.json',
            'element_id': 'ID_abc12345'
        }
        """
        try:
            # Step 1: Parse HTML
            parsed = self.html_parser.parse_element(html_string)
            if parsed.get('error'):
                return {'success': False, 'error': f'HTML parsing failed: {parsed["error"]}'}
            
            tag = parsed['tag']
            attributes = parsed['attributes']
            
            # Step 2: Extract domain/page from URL
            domain, page = self._extract_domain_page(url)
            
            # Step 3: Infer element name
            label_text = self.html_parser.infer_label_from_attributes(attributes)
            if not element_name:
                element_name = label_text or attributes.get('name') or attributes.get('data-testid') or 'Unknown Element'
            
            # Step 4: Generate XPath
            xpath_result = self._generate_xpath(attributes, tag)
            xpath = xpath_result['xpath']
            uniqueness_method = xpath_result['uniqueness_method']
            
            # Step 5: Generate selector
            selector = self._generate_selector(attributes, tag)
            
            # Step 6: Create discovery object
            discovery = self._create_discovery_object(
                element_name=element_name,
                selector=selector,
                xpath=xpath,
                attributes=attributes,
                url=url,
                uniqueness_method=uniqueness_method,
                tag=tag,
                label_text=label_text
            )
            
            # Step 7: Update Registry JSON
            registry_result = self._update_registry(domain, page, discovery)
            
            return {
                'success': True,
                'element_name': element_name,
                'xpath': xpath,
                'selector': selector,
                'label_text': label_text,
                'element_id': registry_result['element_id'],
                'registry_path': registry_result['registry_path'],
                'uniqueness_method': uniqueness_method
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'details': traceback.format_exc()
            }
    
    def _extract_domain_page(self, url: str) -> tuple:
        """Extract domain and page from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0] if parsed.path else 'unknown'
        
        # Extract page name from path
        path = parsed.path.strip('/')
        if not path:
            page = 'home'
        else:
            # Use last segment as page name
            page = path.split('/')[-1] or 'home'
            # Sanitize
            page = re.sub(r'[<>:"/\\|?*]', '_', page)
        
        return domain, page
    
    def _generate_xpath(self, attributes: Dict, tag: str) -> Dict:
        """
        Generate XPath with priority:
        1. data-testid
        2. id (if stable)
        3. name (for form elements)
        4. aria-labelledby
        5. placeholder
        6. Positional (fallback)
        """
        # Priority 1: data-testid
        if attributes.get('data-testid'):
            return {
                'xpath': f"//{tag}[@data-testid='{attributes['data-testid']}']",
                'uniqueness_method': 'data-testid'
            }
        
        # Priority 2: id (if not dynamic)
        if attributes.get('id'):
            id_value = attributes['id']
            # Skip dynamic IDs (contain numbers at end or MUI prefixes)
            if not re.search(r'-\d+$', id_value) and not id_value.startswith(('mui-', 'Mui')):
                return {
                    'xpath': f"//{tag}[@id='{id_value}']",
                    'uniqueness_method': 'id'
                }
        
        # Priority 3: name (for form elements)
        if attributes.get('name') and tag in ['input', 'select', 'textarea', 'button']:
            return {
                'xpath': f"//{tag}[@name='{attributes['name']}']",
                'uniqueness_method': 'name'
            }
        
        # Priority 4: aria-labelledby
        if attributes.get('aria-labelledby'):
            return {
                'xpath': f"//{tag}[@aria-labelledby='{attributes['aria-labelledby']}']",
                'uniqueness_method': 'aria-labelledby'
            }
        
        # Priority 5: placeholder
        if attributes.get('placeholder'):
            return {
                'xpath': f"//{tag}[@placeholder='{attributes['placeholder']}']",
                'uniqueness_method': 'placeholder'
            }
        
        # Fallback: positional
        return {
            'xpath': f"(//{tag})[1]",
            'uniqueness_method': 'positional'
        }
    
    def _generate_selector(self, attributes: Dict, tag: str) -> str:
        """
        Generate CSS selector with priority:
        1. data-testid
        2. id
        3. name
        4. aria-labelledby
        5. placeholder
        """
        # Priority 1: data-testid
        if attributes.get('data-testid'):
            return f"{tag}[data-testid='{attributes['data-testid']}']"
        
        # Priority 2: id
        if attributes.get('id'):
            id_value = attributes['id']
            if not re.search(r'-\d+$', id_value) and not id_value.startswith(('mui-', 'Mui')):
                return f"#{id_value}"
        
        # Priority 3: name
        if attributes.get('name') and tag in ['input', 'select', 'textarea', 'button']:
            return f"{tag}[name='{attributes['name']}']"
        
        # Priority 4: aria-labelledby
        if attributes.get('aria-labelledby'):
            return f"{tag}[aria-labelledby='{attributes['aria-labelledby']}']"
        
        # Priority 5: placeholder
        if attributes.get('placeholder'):
            return f"{tag}[placeholder='{attributes['placeholder']}']"
        
        # Fallback
        return f"{tag}"
    
    def _create_discovery_object(
        self,
        element_name: str,
        selector: str,
        xpath: str,
        attributes: Dict,
        url: str,
        uniqueness_method: str,
        tag: str,
        label_text: Optional[str]
    ) -> Dict:
        """Create discovery object matching DiscoveryTracker format"""
        
        # Extract unique attributes
        unique_attributes = {}
        if attributes.get('id'):
            unique_attributes['id'] = attributes['id']
        if attributes.get('data-testid'):
            unique_attributes['data_testid'] = attributes['data-testid']
        if attributes.get('name'):
            unique_attributes['name'] = attributes['name']
        if attributes.get('aria-labelledby'):
            unique_attributes['aria_labelledby'] = attributes['aria-labelledby']
        
        # Determine element type
        element_type = tag
        if tag == 'input':
            element_type = attributes.get('type', 'input')
        elif tag in ['button', 'a']:
            element_type = 'button'
        elif tag == 'select':
            element_type = 'select'
        elif tag == 'textarea':
            element_type = 'textarea'
        
        return {
            'name': element_name,
            'final_selector': selector,
            'xpath': xpath,
            'uniqueness_method': uniqueness_method,
            'discovery_method': 'manual_registration',
            'metadata': {
                'type': element_type,
                'tag': tag,
                'element_attrs': attributes
            },
            'unique_attributes': unique_attributes if unique_attributes else None,
            'discovery_url': url,
            'context': 'main-page',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    def _update_registry(self, domain: str, page: str, discovery: Dict) -> Dict:
        """Update Registry JSON file"""
        
        # Load existing registry
        element_map = self.element_registry.load_map(domain, page)
        
        if not element_map:
            # Create new registry
            element_map = {
                "page": page,
                "url": f"https://{domain}/{page}" if page != 'home' else f"https://{domain}/",
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "elements": {},
                "id_index": {},
                "statistics": {
                    "total_elements": 0,
                    "parsed_elements": 0,
                    "discovered_elements": 0
                }
            }
        
        element_name = discovery['name']
        
        # Generate element_id
        element_id = self.element_registry._generate_element_id(
            element_name,
            discovery['xpath']
        )
        
        # Create element entry
        element_entry = {
            "selector": discovery['final_selector'],
            "xpath": discovery['xpath'],
            "uniqueness_method": discovery['uniqueness_method'],
            "type": discovery['metadata']['type'],
            "description": "Manually registered element",
            "source": "manual_registration",
            "discovery_method": "manual",
            "usage_count": 0,
            "alternatives": [],
            "discovery_url": discovery['discovery_url'],
            "unique_attributes": discovery['unique_attributes'],
            "context": "main-page",
            "element_id": element_id
        }
        
        # Add to elements dict
        element_map["elements"][element_name] = element_entry
        
        # Update id_index
        element_map["id_index"][element_id] = element_name
        
        # Update statistics
        element_map["statistics"]["total_elements"] = len(element_map["elements"])
        element_map["statistics"]["discovered_elements"] += 1
        
        # Update timestamp
        element_map["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        # Save registry
        self.element_registry.save_map(domain, page, element_map)
        
        return {
            'element_id': element_id,
            'registry_path': str(self.element_registry.get_map_path(domain, page))
        }

