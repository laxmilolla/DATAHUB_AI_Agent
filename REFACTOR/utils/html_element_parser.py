"""
HTML Element Parser - Parse HTML element string and extract attributes
Simple utility for manual element registration
"""
import re
from typing import Dict, Optional
from bs4 import BeautifulSoup


class HTMLElementParser:
    """Parse HTML element string and extract all attributes"""
    
    @staticmethod
    def parse_element(html_string: str) -> Dict:
        """
        Parse HTML element string and extract all attributes
        
        Args:
            html_string: HTML element string (e.g., '<input name="name" data-testid="submission-name-input"...>')
        
        Returns:
            {
                'tag': 'input',
                'attributes': {
                    'name': 'name',
                    'id': None,
                    'data-testid': 'submission-name-input',
                    'aria-labelledby': 'submission-name-filter',
                    'placeholder': 'Minimum 3 characters required',
                    'type': 'text',
                    'class': 'MuiInputBase-input...',
                    ...
                },
                'text_content': '',
                'inner_html': ''
            }
        """
        try:
            # Clean HTML string (remove extra whitespace, ensure it's valid)
            html_string = html_string.strip()
            
            # If HTML doesn't start with <, try to find the first tag
            if not html_string.startswith('<'):
                # Try to extract first HTML tag
                import re
                tag_match = re.search(r'<[^>]+>', html_string)
                if tag_match:
                    html_string = tag_match.group(0)
                else:
                    return {
                        'tag': 'unknown',
                        'attributes': {},
                        'text_content': '',
                        'inner_html': '',
                        'error': 'No valid HTML tag found in input'
                    }
            
            # Wrap in a container to parse single element
            wrapped_html = f"<div>{html_string}</div>"
            soup = BeautifulSoup(wrapped_html, 'html.parser')
            
            # Get the first element (our target)
            element = soup.find()
            if not element:
                return {
                    'tag': 'unknown',
                    'attributes': {},
                    'text_content': '',
                    'inner_html': '',
                    'error': 'Could not parse HTML element'
                }
            
            # SMART DETECTION: If the element has nested structure and inner elements have better attributes,
            # check if we should use the outer element instead
            # Priority: outer element with data-testid > inner element with id > inner element with text
            if element.find():
                # Check if outer element has data-testid (best selector)
                outer_data_testid = element.get('data-testid')
                if outer_data_testid:
                    # Use outer element - it has the best selector
                    pass  # Keep using outer element
                else:
                    # Check inner elements for better attributes
                    inner_elements = element.find_all(recursive=False)  # Direct children only
                    for inner in inner_elements:
                        inner_data_testid = inner.get('data-testid')
                        inner_id = inner.get('id')
                        # If inner has data-testid and outer doesn't, consider using inner
                        # But for now, we'll stick with outer to maintain structure
                        pass
            
            # Extract tag
            tag = element.name.lower() if element.name else 'unknown'
            
            # Extract all attributes
            attributes = {}
            if element.attrs:
                for attr_name, attr_value in element.attrs.items():
                    # Handle list attributes (like class)
                    if isinstance(attr_value, list):
                        attributes[attr_name] = ' '.join(attr_value)
                    else:
                        attributes[attr_name] = attr_value
            
            # Extract text content
            text_content = element.get_text(strip=True)
            
            # Extract inner HTML
            inner_html = str(element) if element else ''
            
            return {
                'tag': tag,
                'attributes': attributes,
                'text_content': text_content,
                'inner_html': inner_html
            }
        except Exception as e:
            return {
                'tag': 'unknown',
                'attributes': {},
                'text_content': '',
                'inner_html': '',
                'error': str(e)
            }
    
    @staticmethod
    def infer_label_from_attributes(attributes: Dict, text_content: str = '') -> Optional[str]:
        """
        Infer label text from attributes and text content
        
        Priority:
        1. aria-label: Use directly
        2. data-testid: "submission-name-input" → "Submission Name"
        3. name: "submissionName" → "Submission Name"
        4. id: Extract meaningful part
        5. placeholder: Use as-is (if reasonable)
        6. text_content: Use if meaningful
        7. aria-labelledby: Can't resolve without full page HTML
        
        Returns:
            Label text or None
        """
        # Strategy 1: aria-label → use directly
        if attributes.get('aria-label'):
            aria_label = attributes['aria-label'].strip()
            if aria_label:
                return aria_label
        
        # Strategy 2: data-testid → infer label
        if attributes.get('data-testid'):
            testid = attributes['data-testid']
            # "submission-name-input" → "Submission Name"
            # Remove common suffixes
            label = testid.replace('-input', '').replace('-field', '').replace('-button', '').replace('-dropdown', '').replace('-select', '').replace('-', ' ')
            return ' '.join(word.capitalize() for word in label.split())
        
        # Strategy 3: name → infer label
        if attributes.get('name'):
            name = attributes['name']
            # "submissionName" → "Submission Name"
            label = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            return label.title()
        
        # Strategy 4: id → extract meaningful part (if not dynamic)
        if attributes.get('id'):
            id_value = attributes['id']
            # Skip dynamic IDs
            if not re.search(r'-\d+$', id_value) and not id_value.startswith(('mui-', 'Mui', 'css-')):
                # Extract meaningful part
                # "program-dropdown" → "Program Dropdown"
                label = id_value.replace('-', ' ')
                return ' '.join(word.capitalize() for word in label.split())
        
        # Strategy 5: placeholder → use as-is (if reasonable)
        if attributes.get('placeholder'):
            placeholder = attributes['placeholder']
            # Only use if it's not too long and looks like a label
            if len(placeholder) < 50 and not placeholder.startswith(('Enter', 'Type', 'Select', 'Choose')):
                return placeholder
        
        # Strategy 6: text_content → use if meaningful (for buttons, links, etc.)
        if text_content:
            text_clean = text_content.strip()
            # Use if it's short and looks like a label/button text
            if text_clean and 2 < len(text_clean) < 50:
                # Skip if it's just numbers or special chars
                if re.search(r'[a-zA-Z]', text_clean):
                    return text_clean
        
        return None

