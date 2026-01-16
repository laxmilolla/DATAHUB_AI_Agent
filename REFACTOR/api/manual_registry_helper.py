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
            
            # Step 3: Infer element name (pass text_content for better inference)
            text_content = parsed.get('text_content', '')
            label_text = self.html_parser.infer_label_from_attributes(attributes, text_content)
            if not element_name:
                element_name = label_text or attributes.get('name') or attributes.get('data-testid') or attributes.get('id') or text_content[:30] or 'Unknown Element'
            
            # Step 4: Generate XPath (pass text_content for better XPath generation)
            text_content = parsed.get('text_content', '')
            xpath_result = self._generate_xpath(attributes, tag, text_content)
            xpath = xpath_result['xpath']
            uniqueness_method = xpath_result['uniqueness_method']
            warning = xpath_result.get('warning', None)
            
            # Step 5: Generate selector (pass text_content for better selector generation)
            selector = self._generate_selector(attributes, tag, text_content)
            
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
            
            result = {
                'success': True,
                'element_name': element_name,
                'xpath': xpath,
                'selector': selector,
                'label_text': label_text,
                'element_id': registry_result['element_id'],
                'registry_path': registry_result['registry_path'],
                'uniqueness_method': uniqueness_method,
                'attributes_found': list(attributes.keys()),
                'all_attributes': attributes,  # Include full attributes dict
                'text_content': text_content[:100] if text_content else None,
                'tag': tag
            }
            
            if warning:
                result['warning'] = warning
            
            return result
            
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
    
    def _generate_xpath(self, attributes: Dict, tag: str, text_content: str = '') -> Dict:
        """
        Generate XPath with priority:
        1. data-testid
        2. id (if stable)
        3. name (for form elements)
        4. aria-labelledby
        5. aria-label
        6. role + text content
        7. placeholder
        8. class (if stable, not MUI-generated)
        9. text content (if available and unique)
        10. Positional (fallback - warn user)
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
        if attributes.get('name') and tag in ['input', 'select', 'textarea', 'button', 'option']:
            # For radio buttons and checkboxes, include value if available
            if tag == 'input' and attributes.get('type') in ['radio', 'checkbox']:
                if attributes.get('value'):
                    return {
                        'xpath': f"//{tag}[@name='{attributes['name']}' and @value='{attributes['value']}']",
                        'uniqueness_method': 'name+value'
                    }
                else:
                    # For radio/checkbox without value, use name + text content
                    if text_content:
                        text_escaped = text_content.strip()[:50].replace("'", "\\'")
                        return {
                            'xpath': f"//{tag}[@name='{attributes['name']}' and contains(text(), '{text_escaped}')]",
                            'uniqueness_method': 'name+text'
                        }
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
        
        # Priority 5: aria-label
        if attributes.get('aria-label'):
            aria_label = attributes['aria-label'].strip()
            if aria_label:
                return {
                    'xpath': f"//{tag}[@aria-label='{aria_label}']",
                    'uniqueness_method': 'aria-label'
                }
        
        # Priority 6: role + text content (especially useful for dropdown options, table cells)
        if attributes.get('role') and text_content:
            text_clean = text_content.strip()[:50]  # Limit length
            if text_clean:
                # Escape quotes in text
                text_escaped = text_clean.replace("'", "\\'")
                # For option role, also check aria-selected or value
                if attributes.get('role') == 'option':
                    if attributes.get('value'):
                        return {
                            'xpath': f"//{tag}[@role='option' and @value='{attributes['value']}']",
                            'uniqueness_method': 'role+value'
                        }
                    elif attributes.get('aria-labelledby'):
                        return {
                            'xpath': f"//{tag}[@role='option' and @aria-labelledby='{attributes['aria-labelledby']}' and contains(text(), '{text_escaped}')]",
                            'uniqueness_method': 'role+aria-labelledby+text'
                        }
                return {
                    'xpath': f"//{tag}[@role='{attributes['role']}' and contains(text(), '{text_escaped}')]",
                    'uniqueness_method': 'role+text'
                }
        
        # Priority 6.5: Special handling for table cells (td/th) - use text + position
        if tag in ['td', 'th'] and text_content:
            text_clean = text_content.strip()[:50]
            if text_clean:
                text_escaped = text_clean.replace("'", "\\'")
                # Try to find by text in specific column (if we have parent table context)
                if attributes.get('data-column') or attributes.get('aria-colindex'):
                    col_index = attributes.get('data-column') or attributes.get('aria-colindex')
                    return {
                        'xpath': f"//{tag}[contains(text(), '{text_escaped}') and (@data-column='{col_index}' or @aria-colindex='{col_index}')]",
                        'uniqueness_method': 'table-cell+column+text'
                    }
                return {
                    'xpath': f"//{tag}[contains(text(), '{text_escaped}')]",
                    'uniqueness_method': 'table-cell+text'
                }
        
        # Priority 7: placeholder
        if attributes.get('placeholder'):
            return {
                'xpath': f"//{tag}[@placeholder='{attributes['placeholder']}']",
                'uniqueness_method': 'placeholder'
            }
        
        # Priority 8: class (if stable, not MUI-generated)
        if attributes.get('class'):
            class_value = attributes['class']
            # Skip MUI classes (they're dynamic)
            if not any(mui in class_value.lower() for mui in ['mui', 'css-']):
                # Use class if it looks stable (has meaningful name)
                # Extract first meaningful class
                classes = class_value.split()
                for cls in classes:
                    if cls and not cls.startswith('css-') and len(cls) > 3:
                        return {
                            'xpath': f"//{tag}[contains(@class, '{cls}')]",
                            'uniqueness_method': 'class'
                        }
        
        # Priority 9: text content (if available and meaningful)
        if text_content:
            text_clean = text_content.strip()
            if text_clean and len(text_clean) > 2 and len(text_clean) < 100:
                # Escape quotes
                text_escaped = text_clean.replace("'", "\\'")
                return {
                    'xpath': f"//{tag}[contains(text(), '{text_escaped}')]",
                    'uniqueness_method': 'text'
                }
        
        # Fallback: positional (warn user this is not ideal)
        return {
            'xpath': f"(//{tag})[1]",
            'uniqueness_method': 'positional',
            'warning': 'Generic positional XPath - element lacks unique attributes. Consider providing element with data-testid, id, or aria-label.'
        }
    
    def _generate_selector(self, attributes: Dict, tag: str, text_content: str = '') -> str:
        """
        Generate CSS selector with priority:
        1. data-testid
        2. id
        3. name
        4. aria-labelledby
        5. aria-label
        6. role + text
        7. placeholder
        8. class (if stable)
        9. text (if available)
        """
        # Priority 1: data-testid
        if attributes.get('data-testid'):
            return f"{tag}[data-testid='{attributes['data-testid']}']"
        
        # Priority 2: id
        if attributes.get('id'):
            id_value = attributes['id']
            if not re.search(r'-\d+$', id_value) and not id_value.startswith(('mui-', 'Mui')):
                return f"#{id_value}"
        
        # Priority 3: name (with special handling for radio/checkbox)
        if attributes.get('name') and tag in ['input', 'select', 'textarea', 'button', 'option']:
            # For radio buttons and checkboxes, include value if available
            if tag == 'input' and attributes.get('type') in ['radio', 'checkbox']:
                if attributes.get('value'):
                    return f"{tag}[name='{attributes['name']}'][value='{attributes['value']}']"
                elif text_content:
                    text_clean = text_content.strip()[:30]
                    if text_clean:
                        return f"{tag}[name='{attributes['name']}']:has-text('{text_clean}')"
            return f"{tag}[name='{attributes['name']}']"
        
        # Priority 4: aria-labelledby
        if attributes.get('aria-labelledby'):
            return f"{tag}[aria-labelledby='{attributes['aria-labelledby']}']"
        
        # Priority 5: aria-label
        if attributes.get('aria-label'):
            aria_label = attributes['aria-label'].strip()
            if aria_label:
                return f"{tag}[aria-label='{aria_label}']"
        
        # Priority 6: role + text (with special handling for options)
        if attributes.get('role') and text_content:
            text_clean = text_content.strip()[:30]
            if text_clean:
                # For option role, prefer value attribute
                if attributes.get('role') == 'option' and attributes.get('value'):
                    return f"{tag}[role='option'][value='{attributes['value']}']"
                return f"{tag}[role='{attributes['role']}']:has-text('{text_clean}')"
        
        # Priority 7: placeholder
        if attributes.get('placeholder'):
            return f"{tag}[placeholder='{attributes['placeholder']}']"
        
        # Priority 8: class (if stable)
        if attributes.get('class'):
            class_value = attributes['class']
            if not any(mui in class_value.lower() for mui in ['mui', 'css-']):
                classes = class_value.split()
                for cls in classes:
                    if cls and not cls.startswith('css-') and len(cls) > 3:
                        return f"{tag}.{cls}"
        
        # Priority 9: text (if available)
        if text_content:
            text_clean = text_content.strip()
            if text_clean and len(text_clean) > 2 and len(text_clean) < 50:
                return f"{tag}:has-text('{text_clean}')"
        
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
        
        # Determine element type with special handling for different input types and complex elements
        element_type = tag
        if tag == 'input':
            input_type = attributes.get('type', 'text')
            if input_type == 'radio':
                element_type = 'radio'
                # For radio buttons, include value
                if attributes.get('value'):
                    unique_attributes['value'] = attributes['value']
            elif input_type == 'checkbox':
                element_type = 'checkbox'
                # For checkboxes, include value
                if attributes.get('value'):
                    unique_attributes['value'] = attributes['value']
            else:
                element_type = input_type  # text, email, password, etc.
        elif tag == 'select':
            element_type = 'select'
        elif tag == 'option':
            element_type = 'option'
            # For dropdown options, include value and parent info
            if attributes.get('value'):
                unique_attributes['value'] = attributes['value']
            if attributes.get('aria-labelledby'):
                unique_attributes['parent_dropdown_id'] = attributes['aria-labelledby']
        elif tag == 'textarea':
            element_type = 'textarea'
        elif tag in ['button', 'a']:
            element_type = 'button'
        elif tag == 'table':
            element_type = 'table'
            # For tables, include data-testid or id for the table itself
            if attributes.get('data-testid'):
                unique_attributes['table_testid'] = attributes['data-testid']
            if attributes.get('id'):
                unique_attributes['table_id'] = attributes['id']
        elif tag == 'tr':
            element_type = 'table-row'
        elif tag in ['td', 'th']:
            element_type = 'table-cell'
            # For table cells, include column index if available
            if attributes.get('data-column'):
                unique_attributes['column_index'] = attributes['data-column']
            elif attributes.get('aria-colindex'):
                unique_attributes['column_index'] = attributes['aria-colindex']
        elif tag == 'thead' or tag == 'tbody' or tag == 'tfoot':
            element_type = 'table-section'
        # Check for dropdown button (role="button" with aria-expanded or MuiSelect)
        elif attributes.get('role') == 'button' and (
            attributes.get('aria-expanded') is not None or
            'MuiSelect' in attributes.get('class', '') or
            'select' in (attributes.get('class', '') or '').lower()
        ):
            element_type = 'dropdown-button'
            # For dropdown buttons, extract hidden input name if available
            if attributes.get('name'):
                unique_attributes['hidden_input_name'] = attributes['name']
        # Check for dropdown option (role="option")
        elif attributes.get('role') == 'option':
            element_type = 'option'
            if attributes.get('value'):
                unique_attributes['value'] = attributes['value']
            if attributes.get('aria-labelledby'):
                unique_attributes['parent_dropdown_id'] = attributes['aria-labelledby']
        
        # Determine element type with special handling for different input types and complex elements
        element_type = tag
        if tag == 'input':
            input_type = attributes.get('type', 'text')
            if input_type == 'radio':
                element_type = 'radio'
            elif input_type == 'checkbox':
                element_type = 'checkbox'
            else:
                element_type = input_type  # text, email, password, etc.
        elif tag == 'select':
            element_type = 'select'
        elif tag == 'option':
            element_type = 'option'
        elif tag == 'textarea':
            element_type = 'textarea'
        elif tag in ['button', 'a']:
            element_type = 'button'
        elif tag == 'table':
            element_type = 'table'
        elif tag == 'tr':
            element_type = 'table-row'
        elif tag in ['td', 'th']:
            element_type = 'table-cell'
        elif tag == 'thead' or tag == 'tbody' or tag == 'tfoot':
            element_type = 'table-section'
        # Check for dropdown button (role="button" with aria-expanded or MuiSelect)
        elif attributes.get('role') == 'button' and (
            attributes.get('aria-expanded') is not None or
            'MuiSelect' in attributes.get('class', '') or
            'select' in (attributes.get('class', '') or '').lower()
        ):
            element_type = 'dropdown-button'
        # Check for dropdown option (role="option")
        elif attributes.get('role') == 'option':
            element_type = 'option'
        
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

