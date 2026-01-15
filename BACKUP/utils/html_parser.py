"""
HTML Parser for Element Extraction
Extracts interactive elements from HTML and generates optimal selectors
"""

from bs4 import BeautifulSoup
from typing import Dict, List, Any
import re
from datetime import datetime


class HTMLElementParser:
    """Parse HTML and extract actionable elements with optimal selectors"""
    
    def __init__(self, html: str, page_url: str = ""):
        self.soup = BeautifulSoup(html, 'html.parser')
        self.page_url = page_url
        self.elements = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse HTML and extract all interactive elements"""
        
        # Extract different types of elements
        self._extract_buttons()
        self._extract_links()
        self._extract_accordions()
        self._extract_inputs()
        self._extract_checkboxes()
        self._extract_dropdowns()
        self._extract_tables()
        
        return {
            "page": self._get_page_name(),
            "url": self.page_url,
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "elements": self.elements,
            "statistics": {
                "total_elements": len(self.elements),
                "parsed_elements": len(self.elements),
                "discovered_elements": 0
            }
        }
    
    def _get_page_name(self) -> str:
        """Extract page name from URL"""
        if not self.page_url:
            return "unknown"
        
        # Extract last part of URL path
        match = re.search(r'/#/(\w+)', self.page_url)
        if match:
            return match.group(1)
        return "home"
    
    def _extract_accordions(self):
        """Extract accordion/expansion panel elements"""
        # Find elements with role="button" and aria-expanded
        accordions = self.soup.find_all(
            lambda tag: tag.get('role') == 'button' and tag.get('aria-expanded') is not None
        )
        
        for accordion in accordions:
            element_id = accordion.get('id')
            if not element_id:
                continue
                
            # Get text content
            text_elem = accordion.find(class_='sectionSummaryText')
            if text_elem:
                text = text_elem.get_text(strip=True)
            else:
                text = accordion.get_text(strip=True)[:50]
            
            name = f"{text} dropdown"
            
            # Generate multiple selector options
            selectors = [
                f"#{element_id}[role='button']",  # Best: specific + semantic
                f"[role='button'][aria-expanded]:has-text('{text}')",  # Semantic
                f".customExpansionPanelSummaryRoot:has-text('{text}')"  # Class-based
            ]
            
            self.elements[name] = {
                "selector": selectors[0],
                "type": "accordion",
                "aria_expanded": accordion.get('aria-expanded'),
                "description": f"Accordion section for {text}",
                "alternatives": selectors[1:],
                "source": "initial_parse",
                "usage_count": 0
            }
    
    def _extract_buttons(self):
        """Extract button elements"""
        buttons = self.soup.find_all('button')
        
        for button in buttons:
            # Skip if part of accordion (already extracted)
            if button.get('role') == 'button' and button.get('aria-expanded'):
                continue
            
            text = button.get_text(strip=True)
            if not text or len(text) > 50:
                continue
            
            name = f"{text} button"
            
            # Generate selectors
            selectors = []
            if button.get('id'):
                selectors.append(f"#{button.get('id')}")
            if button.get('data-testid'):
                selectors.append(f"[data-testid='{button.get('data-testid')}']")
            selectors.append(f"button:has-text('{text}')")
            
            if selectors:
                self.elements[name] = {
                    "selector": selectors[0],
                    "type": "button",
                    "description": f"Button: {text}",
                    "alternatives": selectors[1:] if len(selectors) > 1 else [],
                    "source": "initial_parse",
                    "usage_count": 0
                }
    
    def _extract_links(self):
        """Extract clickable links"""
        links = self.soup.find_all('a', href=True)
        
        for link in links:
            text = link.get_text(strip=True)
            if not text or len(text) > 50:
                continue
            
            name = f"{text} link"
            href = link.get('href')
            
            # Generate selectors
            selectors = []
            if link.get('id'):
                selectors.append(f"#{link.get('id')}")
            selectors.append(f"a[href='{href}']")
            selectors.append(f"a:has-text('{text}')")
            
            self.elements[name] = {
                "selector": selectors[0],
                "type": "link",
                "href": href,
                "description": f"Link to {text}",
                "alternatives": selectors[1:],
                "source": "initial_parse",
                "usage_count": 0
            }
    
    def _extract_checkboxes(self):
        """Extract checkbox inputs"""
        checkboxes = self.soup.find_all('input', {'type': 'checkbox'})
        
        for checkbox in checkboxes:
            value = checkbox.get('value') or checkbox.get('id') or checkbox.get('name')
            if not value:
                continue
            
            # Try to find associated label
            label_text = self._find_label_for_input(checkbox)
            name = f"{label_text or value} checkbox"
            
            # Generate selectors
            selectors = []
            if checkbox.get('id'):
                selectors.append(f"#{checkbox.get('id')}")
            if checkbox.get('value'):
                selectors.append(f"input[type='checkbox'][value='{checkbox.get('value')}']")
            if checkbox.get('name'):
                selectors.append(f"input[type='checkbox'][name='{checkbox.get('name')}']")
            
            if selectors:
                self.elements[name] = {
                    "selector": selectors[0],
                    "type": "checkbox",
                    "value": value,
                    "description": f"Checkbox for {label_text or value}",
                    "alternatives": selectors[1:],
                    "source": "initial_parse",
                    "usage_count": 0
                }
    
    def _extract_inputs(self):
        """Extract text input fields"""
        inputs = self.soup.find_all('input', {'type': ['text', 'email', 'password', 'search']})
        
        for input_elem in inputs:
            label_text = self._find_label_for_input(input_elem)
            placeholder = input_elem.get('placeholder')
            name = label_text or placeholder or input_elem.get('name') or input_elem.get('id')
            
            if not name:
                continue
            
            name = f"{name} input"
            
            # Generate selectors
            selectors = []
            if input_elem.get('id'):
                selectors.append(f"#{input_elem.get('id')}")
            if input_elem.get('name'):
                selectors.append(f"input[name='{input_elem.get('name')}']")
            if placeholder:
                selectors.append(f"input[placeholder='{placeholder}']")
            
            if selectors:
                self.elements[name] = {
                    "selector": selectors[0],
                    "type": "input",
                    "input_type": input_elem.get('type', 'text'),
                    "description": f"Input field for {name}",
                    "alternatives": selectors[1:],
                    "source": "initial_parse",
                    "usage_count": 0
                }
    
    def _extract_dropdowns(self):
        """Extract select dropdowns"""
        selects = self.soup.find_all('select')
        
        for select in selects:
            label_text = self._find_label_for_input(select)
            name = label_text or select.get('name') or select.get('id')
            
            if not name:
                continue
            
            name = f"{name} dropdown"
            
            # Generate selectors
            selectors = []
            if select.get('id'):
                selectors.append(f"#{select.get('id')}")
            if select.get('name'):
                selectors.append(f"select[name='{select.get('name')}']")
            
            # Get options
            options = [opt.get('value') for opt in select.find_all('option') if opt.get('value')]
            
            if selectors:
                self.elements[name] = {
                    "selector": selectors[0],
                    "type": "select",
                    "options": options[:10],  # First 10 options
                    "description": f"Dropdown for {name}",
                    "alternatives": selectors[1:],
                    "source": "initial_parse",
                    "usage_count": 0
                }
    
    def _extract_tables(self):
        """Extract tables"""
        tables = self.soup.find_all('table')
        
        for idx, table in enumerate(tables):
            # Try to find table caption or nearby heading
            caption = table.find('caption')
            name = f"Data table {idx + 1}"
            
            if caption:
                name = f"{caption.get_text(strip=True)} table"
            
            # Generate selector
            selector = ""
            if table.get('id'):
                selector = f"#{table.get('id')}"
            elif table.get('class'):
                classes = ' '.join(table.get('class'))
                selector = f"table.{table.get('class')[0]}"
            else:
                selector = f"table:nth-of-type({idx + 1})"
            
            self.elements[name] = {
                "selector": selector,
                "type": "table",
                "description": f"Data table",
                "alternatives": ["table"],
                "source": "initial_parse",
                "usage_count": 0
            }
    
    def _find_label_for_input(self, input_elem) -> str:
        """Find associated label for an input element"""
        input_id = input_elem.get('id')
        
        # Try to find label by 'for' attribute
        if input_id:
            label = self.soup.find('label', {'for': input_id})
            if label:
                return label.get_text(strip=True)
        
        # Try to find parent label
        parent_label = input_elem.find_parent('label')
        if parent_label:
            return parent_label.get_text(strip=True)
        
        return ""


def parse_html_to_element_map(html: str, page_url: str = "") -> Dict[str, Any]:
    """
    Main function to parse HTML and generate element map
    
    Args:
        html: HTML string to parse
        page_url: URL of the page
        
    Returns:
        Dictionary containing parsed elements in standard format
    """
    parser = HTMLElementParser(html, page_url)
    return parser.parse()
