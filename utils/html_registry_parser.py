"""
HTML Registry Parser - Parse HTML string and generate element registry JSON
Extracts interactive elements (inputs, buttons, links, selects) with XPaths
"""
import re
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class HTMLRegistryParser:
    """Parse HTML and generate element registry JSON"""
    
    def __init__(self):
        self.element_counter = {}
    
    def generate_xpath(self, element, soup) -> str:
        """
        Generate XPath for an element
        Priority: id > data-testid > name > type + attributes > text > position
        """
        # Strategy 1: ID (most stable)
        if element.get('id'):
            element_id = element.get('id')
            # Skip dynamic IDs (ending with numbers or starting with mui-)
            if not re.search(r'-\d+$', element_id) and not element_id.startswith(('mui-', 'Mui', 'css-')):
                return f"//{element.name}[@id='{element_id}']"
        
        # Strategy 2: data-testid (purpose-built for testing)
        if element.get('data-testid'):
            testid = element.get('data-testid')
            return f"//{element.name}[@data-testid='{testid}']"
        
        # Strategy 3: name attribute (for form elements)
        if element.get('name') and element.name in ['input', 'select', 'textarea', 'button']:
            name = element.get('name')
            return f"//{element.name}[@name='{name}']"
        
        # Strategy 4: type + unique attributes
        if element.name == 'input' and element.get('type'):
            input_type = element.get('type')
            # Try to combine with other attributes
            if element.get('name'):
                name = element.get('name')
                return f"//input[@type='{input_type}' and @name='{name}']"
            elif element.get('placeholder'):
                placeholder = element.get('placeholder')
                return f"//input[@type='{input_type}' and @placeholder='{placeholder}']"
            elif element.get('class'):
                # Use first meaningful class
                classes = element.get('class', [])
                if isinstance(classes, list) and classes:
                    # Find first non-framework class
                    for cls in classes:
                        if not cls.startswith(('Mui', 'css-', 'makeStyles')):
                            return f"//input[@type='{input_type}' and contains(@class, '{cls}')]"
                    # If all are framework classes, use first one anyway
                    return f"//input[@type='{input_type}' and contains(@class, '{classes[0]}')]"
            return f"//input[@type='{input_type}']"
        
        # Strategy 5: Text content (for buttons, links)
        text = element.get_text(strip=True)
        if text and len(text) < 100 and element.name in ['button', 'a', 'label']:
            # Escape quotes in text
            text_escaped = text.replace("'", "\\'").replace('"', '\\"')
            return f"(//{element.name}[normalize-space(.)='{text_escaped}'])[1]"
        
        # Strategy 6: Role attribute
        if element.get('role'):
            role = element.get('role')
            if element.get('aria-label'):
                aria_label = element.get('aria-label')
                return f"//{element.name}[@role='{role}' and @aria-label='{aria_label}']"
            return f"//{element.name}[@role='{role}']"
        
        # Strategy 7: Class-based (last resort, less stable)
        if element.get('class'):
            classes = element.get('class', [])
            if isinstance(classes, list) and classes:
                # Use first non-framework class
                for cls in classes:
                    if not cls.startswith(('Mui', 'css-', 'makeStyles')):
                        # Escape special characters in class name
                        cls_escaped = cls.replace("'", "\\'")
                        return f"//{element.name}[contains(@class, '{cls_escaped}')]"
                # If all are framework classes, use first one anyway (better than nothing)
                if classes:
                    cls_escaped = classes[0].replace("'", "\\'")
                    return f"//{element.name}[contains(@class, '{cls_escaped}')]"
        
        # Strategy 8: Position-based (least stable)
        # Count previous siblings of same tag
        parent = element.parent
        if parent:
            siblings = [s for s in parent.children if hasattr(s, 'name') and s.name == element.name]
            if element in siblings:
                index = siblings.index(element) + 1
                return f"(//{element.name})[{index}]"
        
        # Last resort: tag name only
        return f"//{element.name}"
    
    def generate_element_name(self, element, index: int) -> str:
        """Generate a unique element name"""
        tag = element.name.lower()
        
        # Try to get meaningful name from attributes
        if element.get('data-testid'):
            testid = element.get('data-testid')
            # "submission-name-input" -> "submission_name_input"
            name = testid.replace('-', '_')
            if name not in self.element_counter:
                self.element_counter[name] = 0
            else:
                self.element_counter[name] += 1
                name = f"{name}_{self.element_counter[name]}"
            return name
        
        if element.get('id'):
            element_id = element.get('id')
            if not re.search(r'-\d+$', element_id) and not element_id.startswith(('mui-', 'Mui')):
                name = element_id.replace('-', '_')
                if name not in self.element_counter:
                    self.element_counter[name] = 0
                else:
                    self.element_counter[name] += 1
                    name = f"{name}_{self.element_counter[name]}"
                return name
        
        if element.get('name'):
            name = element.get('name').replace('-', '_')
            if name not in self.element_counter:
                self.element_counter[name] = 0
            else:
                self.element_counter[name] += 1
                name = f"{name}_{self.element_counter[name]}"
            return name
        
        # Fallback: tag + index
        if tag not in self.element_counter:
            self.element_counter[tag] = 0
        else:
            self.element_counter[tag] += 1
        
        counter = self.element_counter[tag]
        return f"{tag}_{counter}" if counter > 0 else tag
    
    def generate_element_id(self, xpath: str, element_name: str) -> str:
        """Generate unique element ID from xpath and name"""
        hash_input = f"{element_name}|{xpath}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"ID_{hash_value}"
    
    def determine_action(self, element) -> str:
        """Determine action type based on element"""
        tag = element.name.lower()
        
        if tag == 'input':
            input_type = element.get('type', 'text').lower()
            if input_type in ['submit', 'button', 'image']:
                return 'click'
            elif input_type in ['checkbox', 'radio']:
                return 'click'
            else:
                return 'fill'
        elif tag == 'textarea':
            return 'fill'
        elif tag == 'select':
            return 'select'
        elif tag == 'button':
            return 'click'
        elif tag == 'a':
            return 'click'
        else:
            # Check role
            role = element.get('role', '').lower()
            if role == 'button':
                return 'click'
            elif role == 'link':
                return 'click'
            return 'click'  # Default
    
    def parse_html(self, html_string: str, url: str, page_name: str) -> Dict[str, Any]:
        """
        Parse HTML string and generate element registry JSON
        
        Args:
            html_string: HTML content
            url: Page URL
            page_name: Page name (e.g., 'home', 'login')
        
        Returns:
            Element registry JSON in the exact format
        """
        # Reset counter
        self.element_counter = {}
        
        # Parse HTML - wrap if needed for fragments
        original_html = html_string
        if not html_string.strip().startswith('<html'):
            html_string = f"<html><body>{html_string}</body></html>"
        
        soup = BeautifulSoup(html_string, 'html.parser')
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Parsing HTML: {len(original_html)} characters")
        
        elements = {}
        id_index = {}
        processed_elements = set()  # Track processed elements to avoid duplicates
        
        # Find all interactive elements using multiple methods
        # Method 1: Use find_all for basic tags (more reliable than select)
        basic_tags = ['input', 'textarea', 'select', 'button', 'a']
        for tag in basic_tags:
            found_elements = soup.find_all(tag)
            logger.info(f"Found {len(found_elements)} {tag} elements")
            for element in found_elements:
                try:
                    # Skip if already processed (element might match multiple selectors)
                    # Use element's unique identifier: id > data-testid > position in DOM
                    element_unique_id = None
                    if element.get('id'):
                        element_unique_id = f"id:{element.get('id')}"
                    elif element.get('data-testid'):
                        element_unique_id = f"testid:{element.get('data-testid')}"
                    else:
                        # Use element's position in the document as fallback
                        try:
                            parent = element.parent
                            if parent:
                                siblings = list(parent.children)
                                index = siblings.index(element)
                                element_unique_id = f"pos:{id(parent)}:{index}:{element.name}"
                            else:
                                element_unique_id = f"root:{element.name}"
                        except:
                            element_unique_id = f"fallback:{id(element)}"
                    
                    if element_unique_id in processed_elements:
                        continue
                    processed_elements.add(element_unique_id)
                    
                    tag = element.name.lower()
                    
                    # Generate element name
                    element_name = self.generate_element_name(element, len(elements))
                    
                    # Skip if already exists (double check)
                    if element_name in elements:
                        continue
                    
                    # Generate XPath
                    xpath = self.generate_xpath(element, soup)
                    
                    # Generate element ID
                    element_id = self.generate_element_id(xpath, element_name)
                    
                    # Determine action
                    action = self.determine_action(element)
                    
                    # Determine object type
                    object_type = tag
                    if element.get('role'):
                        object_type = element.get('role')
                    elif tag == 'input':
                        object_type = element.get('type', 'input')
                    
                    # Build element entry
                    element_entry = {
                        "xpath": xpath,
                        "selector": xpath,  # Same as xpath for consistency
                        "url": url,
                        "element_id": element_id,
                        "usage_count": 0,
                        "last_used": None,
                        "source": "parser",
                        "object_type": object_type,
                        "action": action,
                        "discovered_at": datetime.utcnow().isoformat() + 'Z',
                        "last_updated": datetime.utcnow().isoformat() + 'Z'
                    }
                    
                    elements[element_name] = element_entry
                    id_index[element_id] = element_name
                    
                except Exception as e:
                    # Skip elements that cause errors
                    import logging
                    logging.debug(f"Error parsing element: {e}")
                    continue
        
        # Method 2: Find elements by role attribute
        role_elements = soup.find_all(attrs={'role': ['button', 'link', 'tab', 'option']})
        for element in role_elements:
            try:
                # Skip if already processed
                element_unique_id = None
                if element.get('id'):
                    element_unique_id = f"id:{element.get('id')}"
                elif element.get('data-testid'):
                    element_unique_id = f"testid:{element.get('data-testid')}"
                else:
                    try:
                        parent = element.parent
                        if parent:
                            siblings = list(parent.children)
                            index = siblings.index(element)
                            element_unique_id = f"pos:{id(parent)}:{index}:{element.name}"
                        else:
                            element_unique_id = f"root:{element.name}"
                    except:
                        element_unique_id = f"fallback:{id(element)}"
                
                if element_unique_id in processed_elements:
                    continue
                processed_elements.add(element_unique_id)
                
                tag = element.name.lower() if element.name else 'div'
                
                # Generate element name
                element_name = self.generate_element_name(element, len(elements))
                
                if element_name in elements:
                    continue
                
                # Generate XPath
                xpath = self.generate_xpath(element, soup)
                
                # Generate element ID
                element_id = self.generate_element_id(xpath, element_name)
                
                # Determine action
                action = self.determine_action(element)
                
                # Determine object type
                object_type = element.get('role', tag)
                if tag == 'input':
                    object_type = element.get('type', 'input')
                
                # Build element entry
                element_entry = {
                    "xpath": xpath,
                    "selector": xpath,
                    "url": url,
                    "element_id": element_id,
                    "usage_count": 0,
                    "last_used": None,
                    "source": "parser",
                    "object_type": object_type,
                    "action": action,
                    "discovered_at": datetime.utcnow().isoformat() + 'Z',
                    "last_updated": datetime.utcnow().isoformat() + 'Z'
                }
                
                elements[element_name] = element_entry
                id_index[element_id] = element_name
                
            except Exception as e:
                import logging
                logging.debug(f"Error parsing role element: {e}")
                continue
        
        # Method 3: Find elements with data-testid
        testid_elements = soup.find_all(attrs={'data-testid': True})
        for element in testid_elements:
            try:
                # Skip if already processed
                element_unique_id = f"testid:{element.get('data-testid')}"
                if element_unique_id in processed_elements:
                    continue
                processed_elements.add(element_unique_id)
                
                tag = element.name.lower() if element.name else 'div'
                
                # Generate element name
                element_name = self.generate_element_name(element, len(elements))
                
                if element_name in elements:
                    continue
                
                # Generate XPath
                xpath = self.generate_xpath(element, soup)
                
                # Generate element ID
                element_id = self.generate_element_id(xpath, element_name)
                
                # Determine action
                action = self.determine_action(element)
                
                # Determine object type
                object_type = tag
                if element.get('role'):
                    object_type = element.get('role')
                elif tag == 'input':
                    object_type = element.get('type', 'input')
                
                # Build element entry
                element_entry = {
                    "xpath": xpath,
                    "selector": xpath,
                    "url": url,
                    "element_id": element_id,
                    "usage_count": 0,
                    "last_used": None,
                    "source": "parser",
                    "object_type": object_type,
                    "action": action,
                    "discovered_at": datetime.utcnow().isoformat() + 'Z',
                    "last_updated": datetime.utcnow().isoformat() + 'Z'
                }
                
                elements[element_name] = element_entry
                id_index[element_id] = element_name
                
            except Exception as e:
                import logging
                logging.debug(f"Error parsing testid element: {e}")
                continue
        
        # Build registry JSON
        registry = {
            "page": page_name,
            "url": url,
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "elements": elements,
            "id_index": id_index,
            "statistics": {
                "total_elements": len(elements),
                "parsed_elements": len(elements),
                "discovered_elements": 0
            },
            "last_updated": datetime.utcnow().isoformat() + 'Z'
        }
        
        return registry
