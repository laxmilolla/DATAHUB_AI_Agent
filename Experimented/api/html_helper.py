"""
HTML Helper - Parse HTML and extract element information for Agent
Helps Agent find elements by pre-parsing HTML content
"""
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class HTMLHelper:
    """Helper to parse HTML and extract element information"""
    
    @staticmethod
    def extract_elements_from_html(html: str, search_text: str = None) -> List[Dict]:
        """
        Extract elements from HTML that match search criteria
        
        Args:
            html: HTML content
            search_text: Optional text to search for (e.g., "Submission Name")
        
        Returns:
            List of element dictionaries with selectors and attributes
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            elements = []
            
            # Search for input fields
            inputs = soup.find_all('input')
            for inp in inputs:
                inp_type = inp.get('type', 'text')
                inp_name = inp.get('name', '')
                inp_id = inp.get('id', '')
                inp_placeholder = inp.get('placeholder', '')
                inp_class = ' '.join(inp.get('class', []))
                
                # Check if this matches search text
                matches = False
                if search_text:
                    search_lower = search_text.lower()
                    matches = (
                        search_lower in (inp_name or '').lower() or
                        search_lower in (inp_placeholder or '').lower() or
                        search_lower in (inp_id or '').lower()
                    )
                
                # Generate selectors
                selectors = []
                if inp_name:
                    selectors.append(f"input[name='{inp_name}']")
                if inp_id:
                    selectors.append(f"input#{inp_id}")
                if inp_placeholder:
                    selectors.append(f"input[placeholder='{inp_placeholder}']")
                if inp_type:
                    selectors.append(f"input[type='{inp_type}']")
                
                if selectors or matches:
                    elements.append({
                        'type': 'input',
                        'tag': 'input',
                        'name': inp_name,
                        'id': inp_id,
                        'placeholder': inp_placeholder,
                        'input_type': inp_type,
                        'class': inp_class,
                        'selectors': selectors,
                        'best_selector': selectors[0] if selectors else f"input[type='{inp_type}']",
                        'matches_search': matches
                    })
            
            # Search for buttons
            buttons = soup.find_all(['button', 'a'], role='button')
            for btn in buttons:
                btn_text = btn.get_text(strip=True)
                btn_id = btn.get('id', '')
                btn_class = ' '.join(btn.get('class', []))
                
                matches = False
                if search_text:
                    search_lower = search_text.lower()
                    matches = search_lower in btn_text.lower() or search_lower in (btn_id or '').lower()
                
                if btn_text or matches:
                    selectors = []
                    if btn_id:
                        selectors.append(f"#{btn_id}")
                    if btn_text:
                        selectors.append(f"text={btn_text}")
                    
                    elements.append({
                        'type': 'button',
                        'tag': btn.name,
                        'text': btn_text,
                        'id': btn_id,
                        'class': btn_class,
                        'selectors': selectors,
                        'best_selector': selectors[0] if selectors else f"text={btn_text}",
                        'matches_search': matches
                    })
            
            # Search for labels (to find associated inputs)
            labels = soup.find_all('label')
            for label in labels:
                label_text = label.get_text(strip=True)
                label_for = label.get('for', '')
                
                if search_text and search_text.lower() in label_text.lower():
                    # Find associated input
                    associated_input = None
                    if label_for:
                        associated_input = soup.find(id=label_for)
                    if not associated_input:
                        # Try to find input near label
                        associated_input = label.find_next('input')
                    
                    if associated_input:
                        inp_name = associated_input.get('name', '')
                        inp_id = associated_input.get('id', '')
                        inp_placeholder = associated_input.get('placeholder', '')
                        
                        selectors = []
                        if inp_name:
                            selectors.append(f"input[name='{inp_name}']")
                        if inp_id:
                            selectors.append(f"input#{inp_id}")
                        if inp_placeholder:
                            selectors.append(f"input[placeholder='{inp_placeholder}']")
                        
                        if selectors:
                            elements.append({
                                'type': 'input',
                                'tag': 'input',
                                'name': inp_name,
                                'id': inp_id,
                                'placeholder': inp_placeholder,
                                'label_text': label_text,
                                'selectors': selectors,
                                'best_selector': selectors[0],
                                'matches_search': True,
                                'found_via_label': True
                            })
            
            return elements
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []
    
    @staticmethod
    def find_element_by_text(html: str, search_text: str) -> Optional[Dict]:
        """
        Find element in HTML that matches search text
        
        Args:
            html: HTML content
            search_text: Text to search for (e.g., "Submission Name")
        
        Returns:
            Element dictionary with best selector, or None
        """
        elements = HTMLHelper.extract_elements_from_html(html, search_text)
        
        # Return best match (prefer matches_search=True)
        matches = [e for e in elements if e.get('matches_search')]
        if matches:
            return matches[0]
        
        # Return first element if no matches
        return elements[0] if elements else None
    
    @staticmethod
    def extract_html_from_instruction(instruction: str) -> Optional[str]:
        """
        Extract HTML content from instruction text
        
        Looks for patterns like:
        - "Here's the HTML: <html>..."
        - "HTML: <html>..."
        - HTML between <html> tags
        
        Args:
            instruction: Instruction text that may contain HTML
        
        Returns:
            Extracted HTML string, or None
        """
        # Pattern 1: "Here's the HTML:" or "HTML:" followed by HTML
        pattern1 = r'(?:Here\'?s\s+the\s+)?HTML\s*:?\s*(<html[\s\S]*?</html>)'
        match1 = re.search(pattern1, instruction, re.IGNORECASE)
        if match1:
            return match1.group(1)
        
        # Pattern 2: HTML between <html> tags anywhere in text
        pattern2 = r'(<html[\s\S]*?</html>)'
        match2 = re.search(pattern2, instruction, re.IGNORECASE)
        if match2:
            return match2.group(1)
        
        # Pattern 3: HTML fragment (div, form, etc.)
        pattern3 = r'(<(?:div|form|section|main)[\s\S]*?</(?:div|form|section|main)>)'
        match3 = re.search(pattern3, instruction, re.IGNORECASE)
        if match3:
            return match3.group(1)
        
        return None

