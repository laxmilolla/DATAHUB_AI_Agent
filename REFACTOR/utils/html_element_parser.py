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
            # Wrap in a container to parse single element
            wrapped_html = f"<div>{html_string}</div>"
            soup = BeautifulSoup(wrapped_html, 'html.parser')
            
            # Get the first element (our target)
            element = soup.find()
            if not element:
                return {'tag': 'unknown', 'attributes': {}, 'text_content': '', 'inner_html': ''}
            
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
    def infer_label_from_attributes(attributes: Dict) -> Optional[str]:
        """
        Infer label text from attributes
        
        Priority:
        1. data-testid: "submission-name-input" → "Submission Name"
        2. name: "submissionName" → "Submission Name"
        3. placeholder: Use as-is
        4. aria-labelledby: Can't resolve without full page HTML
        
        Returns:
            Label text or None
        """
        # Strategy 1: data-testid → infer label
        if attributes.get('data-testid'):
            testid = attributes['data-testid']
            # "submission-name-input" → "Submission Name"
            label = testid.replace('-input', '').replace('-field', '').replace('-button', '').replace('-', ' ')
            return ' '.join(word.capitalize() for word in label.split())
        
        # Strategy 2: name → infer label
        if attributes.get('name'):
            name = attributes['name']
            # "submissionName" → "Submission Name"
            label = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            return label.title()
        
        # Strategy 3: placeholder → use as-is (if reasonable)
        if attributes.get('placeholder'):
            placeholder = attributes['placeholder']
            # Only use if it's not too long and looks like a label
            if len(placeholder) < 50 and not placeholder.startswith('Enter') and not placeholder.startswith('Type'):
                return placeholder
        
        return None

