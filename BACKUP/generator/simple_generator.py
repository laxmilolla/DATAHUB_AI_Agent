"""
Simple Playwright Generator - Direct XPath from Registry
No discovery JSON, no element_id lookup - just name → XPath → Playwright code
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def load_registry_files(element_maps_dir: Path) -> Dict[str, Dict]:
    """Load all registry files and index by domain/page"""
    registries = {}
    
    for domain_dir in element_maps_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        
        domain = domain_dir.name
        registries[domain] = {}
        
        for registry_file in domain_dir.glob("*_page.json"):
            page_name = registry_file.stem.replace("_page", "")
            
            try:
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                    registries[domain][page_name] = registry_data
                    logger.info(f"✅ Loaded registry: {domain}/{page_name}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load {registry_file}: {e}")
    
    return registries


def find_element_in_registries(element_name: str, registries: Dict[str, Dict], url: Optional[str] = None) -> Optional[Dict]:
    """
    Find element by name in registries
    Returns: {'xpath': '...', 'url': '...', 'element_name': '...'}
    """
    # If URL provided, try that domain first
    if url:
        parsed = urlparse(url)
        domain = parsed.netloc.split(':')[0]
        
        if domain in registries:
            # Try to find in domain's registries FIRST (exact match)
            for page_name, registry_data in registries[domain].items():
                elements = registry_data.get('elements', {})
                if element_name in elements:
                    elem = elements[element_name]
                    return {
                        'xpath': elem.get('xpath'),
                        'url': elem.get('discovery_url') or url,
                        'element_name': element_name,
                        'selector': elem.get('selector', '')
                    }
            
            # Then try fuzzy match in domain's registries
            for page_name, registry_data in registries[domain].items():
                elements = registry_data.get('elements', {})
                best_match = None
                best_score = 0
                
                for reg_name, reg_elem in elements.items():
                    reg_name_lower = reg_name.lower()
                    element_name_lower = element_name.lower()
                    score = 0
                    
                    if element_name_lower == reg_name_lower:
                        score = 100
                    elif element_name_lower in reg_name_lower:
                        score = 80
                    elif reg_name_lower in element_name_lower:
                        score = 60
                    elif any(word in reg_name_lower for word in element_name_lower.split() if len(word) > 3):
                        score = 40
                    
                    if score > best_score:
                        best_score = score
                        best_match = {
                            'xpath': reg_elem.get('xpath'),
                            'url': reg_elem.get('discovery_url') or url,
                            'element_name': reg_name,
                            'selector': reg_elem.get('selector', '')
                        }
                
                if best_match and best_score >= 60:
                    return best_match
    
    # Search all registries (fuzzy match)
    for domain, pages in registries.items():
        for page_name, registry_data in pages.items():
            elements = registry_data.get('elements', {})
            
            # Exact match
            if element_name in elements:
                elem = elements[element_name]
                return {
                    'xpath': elem.get('xpath'),
                    'url': elem.get('discovery_url') or registry_data.get('url', ''),
                    'element_name': element_name,
                    'selector': elem.get('selector', '')
                }
            
            # Fuzzy match (case-insensitive, partial) - but prioritize exact word matches
            element_name_lower = element_name.lower()
            best_match = None
            best_score = 0
            
            for reg_name, reg_elem in elements.items():
                reg_name_lower = reg_name.lower()
                score = 0
                
                # Exact word match gets highest score
                if element_name_lower == reg_name_lower:
                    score = 100
                # Exact word contained in registry name
                elif element_name_lower in reg_name_lower:
                    score = 80
                # Registry name contained in element name
                elif reg_name_lower in element_name_lower:
                    score = 60
                # Partial word match
                elif any(word in reg_name_lower for word in element_name_lower.split() if len(word) > 3):
                    score = 40
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        'xpath': reg_elem.get('xpath'),
                        'url': reg_elem.get('discovery_url') or registry_data.get('url', ''),
                        'element_name': reg_name,
                        'selector': reg_elem.get('selector', '')
                    }
            
            # Only return if score is high enough (avoid false matches)
            if best_match and best_score >= 60:
                return best_match
    
    return None


def parse_story(story: str) -> List[Dict]:
    """Parse story into steps"""
    steps = []
    lines = story.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Extract step number and text
        step_match = re.match(r'[Ss]tep\s+(\d+)\s*[a-z]?\s*:?\s*(.+)', line, re.IGNORECASE)
        if step_match:
            step_num = int(step_match.group(1))
            step_text = step_match.group(2).strip()
            steps.append({
                'step_number': step_num,
                'step_text': step_text
            })
    
    return steps


def detect_action_type(step_text: str) -> str:
    """Detect action type from step text"""
    step_lower = step_text.lower()
    
    if 'go to' in step_lower or 'navigate' in step_lower or step_text.startswith('http'):
        return 'navigate'
    elif 'wait' in step_lower:
        return 'wait'
    elif 'enter' in step_lower or 'fill' in step_lower or 'type' in step_lower or 'input' in step_lower:
        return 'fill'
    elif 'click' in step_lower or 'press' in step_lower or 'select' in step_lower or 'pick' in step_lower:
        return 'click'
    elif 'verify' in step_lower or 'check' in step_lower:
        return 'verify'
    else:
        return 'click'  # Default


def extract_url_from_step(step_text: str) -> Optional[str]:
    """Extract URL from step text"""
    url_match = re.search(r'https?://[^\s\)]+', step_text)
    if url_match:
        return url_match.group(0)
    return None


def extract_element_name(step_text: str, action_type: str) -> Optional[str]:
    """Extract element name from step text"""
    step_lower = step_text.lower()
    
    if action_type == 'navigate':
        return None
    
    if action_type == 'fill':
        # "Enter Username as ..." → "email" or "Username" (check registry)
        # "Enter Password as ..." → "password"
        # "Enter Timestamp in Submission name" → "Submission Name"
        
        # Check for password FIRST (before splitting on 'as' since 'password' contains 'as')
        if 'password' in step_lower:
            return 'password'
        
        if 'in' in step_lower:
            # "Enter X in Y text box" → "Submission Name"
            parts = step_lower.split('in')
            if len(parts) > 1:
                element_part = parts[-1].strip()
                # Remove common suffixes
                element_part = element_part.replace('text box', '').replace('textbox', '').replace('field', '').replace('input', '').replace('on the pop up form', '').strip()
                # Capitalize first letter of each word
                words = [w for w in element_part.split() if w and w not in ['the', 'pop', 'up', 'form']]
                if words:
                    return ' '.join([w.capitalize() for w in words])
        elif 'as' in step_lower:
            # "Enter Username as ..." → "email" (registry has "email", not "Username")
            # "Enter Password as ..." → "password"
            parts = step_lower.split('as', 1)  # Split only on first 'as'
            if len(parts) > 0:
                element_part = parts[0].strip()
                # Remove "enter" prefix
                element_part = re.sub(r'^enter\s+', '', element_part).strip()
                # Map common names to registry names
                if 'username' in element_part or 'email' in element_part:
                    return 'email'  # Registry uses "email"
                elif 'password' in element_part:
                    return 'password'  # Registry uses "password"
                elif 'totp' in element_part or 'one-time' in element_part or 'authenticator' in element_part:
                    return 'input.one-time-code-input__input'  # Registry name
                else:
                    # Take the last word (the actual field name)
                    words = [w for w in element_part.split() if w and w not in ['the', 'enter']]
                    if words:
                        return words[-1].capitalize()  # Last word is usually the field name
                    return None
        else:
            # "Enter Username" → "email"
            element_part = step_lower.replace('enter', '').replace('the', '').strip()
            if 'username' in element_part or 'email' in element_part:
                return 'email'
            elif 'password' in element_part:
                return 'password'  # Registry uses "password"
            elif 'totp' in element_part or 'one-time' in element_part or 'authenticator' in element_part:
                return 'input.one-time-code-input__input'
            else:
                words = [w for w in element_part.split() if w and w not in ['the']]
                return ' '.join([w.capitalize() for w in words if w])
    
    elif action_type == 'click':
        # "Click on Login" → "Login"
        # "Click Create button" → "Create"
        # "Click on link Login" → "Login"
        # "Pick GC from Datacommons dropdown" → "Datacommons" (the dropdown)
        # "Pick NewTestSpn_laxmi from Study dropdown" → "Study" (the dropdown)
        step_clean = step_lower
        
        # Remove common prefixes
        step_clean = re.sub(r'^(click|press|tap|select|pick)\s+(on\s+)?(the\s+)?(button\s+)?(link\s+)?', '', step_clean)
        
        if 'from' in step_clean:
            # "Pick GC from Datacommons dropdown" → "Datacommons"
            # "Pick NewTestSpn_laxmi from Study dropdown" → "Study"
            parts = step_clean.split('from', 1)  # Split only on first 'from'
            if len(parts) > 1:
                dropdown_part = parts[-1].strip()
                # Remove common suffixes
                dropdown_part = re.sub(r'\s*(dropdown|the|form|pop|up|popup|form)\s*', ' ', dropdown_part, flags=re.IGNORECASE).strip()
                words = [w for w in dropdown_part.split() if w and len(w) > 1]  # Filter out single chars
                if words:
                    # Take first meaningful word (the dropdown name)
                    first_word = words[0].capitalize()
                    # Map common variations
                    if 'datacommons' in first_word.lower() or 'datacommons' in dropdown_part.lower():
                        return 'Datacommons'
                    elif 'study' in first_word.lower() or 'study' in dropdown_part.lower():
                        return 'Study'
                    return first_word
        elif 'with text' in step_clean:
            # "click on the button with text "Grant"" → "Grant"
            match = re.search(r'with text\s+"([^"]+)"', step_clean)
            if match:
                return match.group(1).strip()
        elif '"' in step_clean:
            # "click on "Data Submissions" link" → "Data Submissions"
            match = re.search(r'"([^"]+)"', step_clean)
            if match:
                return match.group(1).strip()
        elif 'login.gov' in step_clean:
            return 'Login.gov'
        elif 'login' in step_clean and 'link' in step_clean:
            return 'Login'
        elif 'continue' in step_clean:
            return 'Continue'
        elif 'submit' in step_clean:
            return 'Submit'
        elif 'create' in step_clean:
            if 'data submission' in step_clean:
                return 'Create a Data Submission'
            else:
                return 'Create'
        elif 'study' in step_clean and 'dropdown' in step_clean:
            return 'Study'
        elif 'datacommons' in step_clean or 'datacommons' in step_clean:
            return 'Datacommons'
        else:
            # "Click Login" → "Login"
            # "Click Create" → "Create"
            words = step_clean.split()
            # Remove common suffixes
            words = [w for w in words if w not in ['button', 'link', 'on', 'the', '.']]
            if words:
                result = ' '.join([w.capitalize() for w in words[:2]])
                # Map to registry names
                if 'data submissions' in result.lower():
                    return 'Data Submissions'
                return result
    
    return None


def generate_navigate_code(step_num: int, step_text: str, url: str, indent: int = 4) -> str:
    """Generate navigation code"""
    ind = ' ' * indent
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    code += f"{ind}    page.goto('{url}')\n"
    code += f"{ind}    page.wait_for_load_state('networkidle')\n"
    code += f"{ind}    print('📍 Step {step_num}: Navigated to {url}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_navigate.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: Navigation failed: {{e}}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_navigate_failed.png')\n"
    code += f"{ind}\n"
    return code


def generate_wait_code(step_num: int, step_text: str, indent: int = 12) -> str:
    """Generate wait code"""
    ind = ' ' * indent
    # Extract wait duration
    wait_match = re.search(r'wait (\d+) seconds?', step_text, re.IGNORECASE)
    duration_ms = int(wait_match.group(1)) * 1000 if wait_match else 1000
    
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}try:\n"
    code += f"{ind}    page.wait_for_timeout({duration_ms})\n"
    code += f"{ind}    print('⏱️  Step {step_num}: Waited {duration_ms}ms')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_wait.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: Wait failed: {{e}}')\n"
    code += f"{ind}\n"
    return code


def generate_click_code(step_num: int, step_text: str, element: Dict, indent: int = 12) -> str:
    """Generate click code using XPath directly from registry"""
    ind = ' ' * indent
    xpath = element['xpath']
    element_name = element['element_name']
    
    # Escape single quotes in XPath for Python string
    xpath_escaped = xpath.replace("'", "\\'")
    
    # Sanitize element name for screenshot filename
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30]
    
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}# Using XPath directly from registry: {element_name}\n"
    code += f"{ind}try:\n"
    code += f"{ind}    selector = 'xpath={xpath_escaped}'\n"
    code += f"{ind}    element = page.locator(selector).nth(0)\n"
    code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
    code += f"{ind}    element.click()\n"
    code += f"{ind}    page.wait_for_timeout(1000)  # Wait after click\n"
    code += f"{ind}    print(f'✅ Step {step_num}: Clicked {element_name}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_{safe_name}.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: Failed to click {element_name}: {{e}}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_{safe_name}_failed.png')\n"
    code += f"{ind}\n"
    return code


def generate_fill_code(step_num: int, step_text: str, element: Dict, text_value: str, indent: int = 12) -> str:
    """Generate fill code using XPath directly from registry"""
    ind = ' ' * indent
    xpath = element['xpath']
    element_name = element['element_name']
    
    # Extract text value from step if not provided
    if not text_value:
        # "Enter Username as Laxmi_AI_test@yahoo.com" → "Laxmi_AI_test@yahoo.com"
        if 'as' in step_text.lower():
            parts = step_text.split('as')
            if len(parts) > 1:
                text_value = parts[-1].strip()
        elif 'timestamp' in step_text.lower():
            text_value = "${TIMESTAMP}"  # Special variable
    
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30]
    
    # Escape single quotes in XPath for Python string
    xpath_escaped = xpath.replace("'", "\\'")
    # Escape single quotes in text_value
    text_value_escaped = text_value.replace("'", "\\'") if text_value else ""
    
    code = f"{ind}# Step {step_num}: {step_text}\n"
    code += f"{ind}page.wait_for_timeout(3000)  # Wait 3 seconds before step\n"
    code += f"{ind}# Using XPath directly from registry: {element_name}\n"
    code += f"{ind}try:\n"
    code += f"{ind}    selector = 'xpath={xpath_escaped}'\n"
    code += f"{ind}    element = page.locator(selector).nth(0)\n"
    code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
    code += f"{ind}    element.fill('{text_value_escaped}')\n"
    code += f"{ind}    page.wait_for_timeout(500)  # Wait after fill\n"
    code += f"{ind}    print(f'✅ Step {step_num}: Filled {element_name} with {text_value}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_{safe_name}.png')\n"
    code += f"{ind}except Exception as e:\n"
    code += f"{ind}    print(f'❌ Step {step_num}: Failed to fill {element_name}: {{e}}')\n"
    code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_{safe_name}_failed.png')\n"
    code += f"{ind}\n"
    return code


def generate_playwright_script(story: str, element_maps_dir: Path, output_file: Path) -> Dict:
    """
    Generate Playwright script from story using registry XPaths directly
    
    Args:
        story: Story text with steps
        element_maps_dir: Directory containing registry JSON files
        output_file: Path to output Playwright script
    
    Returns:
        Dict with success status and info
    """
    # Load all registries
    registries = load_registry_files(element_maps_dir)
    
    # Parse story into steps
    steps = parse_story(story)
    
    # Generate code
    test_body = ""
    missing_elements = []
    current_url = None
    
    for step in steps:
        step_num = step['step_number']
        step_text = step['step_text']
        
        # Detect action type
        action_type = detect_action_type(step_text)
        
        # Extract URL if present
        url = extract_url_from_step(step_text)
        if url:
            current_url = url
        
        # Generate code based on action type
        if action_type == 'navigate':
            if url:
                test_body += generate_navigate_code(step_num, step_text, url, indent=12)
                current_url = url
            else:
                test_body += f"            # Step {step_num}: {step_text} - URL not found\n\n"
        
        elif action_type == 'wait':
            test_body += generate_wait_code(step_num, step_text, indent=12)
        
        elif action_type == 'click':
            element_name = extract_element_name(step_text, action_type)
            if element_name:
                element = find_element_in_registries(element_name, registries, current_url)
                if element:
                    test_body += generate_click_code(step_num, step_text, element, indent=12)
                else:
                    test_body += f"            # Step {step_num}: {step_text} - Element '{element_name}' not found in registry\n"
                    test_body += f"            # TODO: Add '{element_name}' to registry or update step text\n\n"
                    missing_elements.append({'step': step_num, 'name': element_name, 'text': step_text})
            else:
                test_body += f"    # Step {step_num}: {step_text} - Could not extract element name\n\n"
        
        elif action_type == 'fill':
            element_name = extract_element_name(step_text, action_type)
            if element_name:
                element = find_element_in_registries(element_name, registries, current_url)
                if element:
                    # Extract text value
                    text_value = None
                    if 'as' in step_text.lower():
                        parts = step_text.split('as')
                        if len(parts) > 1:
                            text_value = parts[-1].strip()
                    elif 'timestamp' in step_text.lower():
                        text_value = "${TIMESTAMP}"
                    
                    test_body += generate_fill_code(step_num, step_text, element, text_value, indent=12)
                else:
                    test_body += f"            # Step {step_num}: {step_text} - Element '{element_name}' not found in registry\n"
                    test_body += f"            # TODO: Add '{element_name}' to registry or update step text\n\n"
                    missing_elements.append({'step': step_num, 'name': element_name, 'text': step_text})
            else:
                test_body += f"            # Step {step_num}: {step_text} - Could not extract element name\n\n"
        
        else:
            test_body += f"            # Step {step_num}: {step_text} - Action type '{action_type}' not yet supported\n\n"
    
    # test_body is already indented with 12 spaces (from generate_* functions)
    indented_body = test_body
    
    # Build full test script
    test_name = "test_simple_generated"
    test_script = f'''"""
Simple Generated Playwright Test
Generated from story using registry XPaths directly
"""
from playwright.sync_api import sync_playwright
import os
from datetime import datetime

def {test_name}():
    """Auto-generated test using registry XPaths"""
    critical_failures = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={{'width': 1920, 'height': 1080}})
        
        # Generate timestamp if needed
        TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
{indented_body}
            if critical_failures:
                print(f"\\n❌ Test completed with {{len(critical_failures)}} failure(s)")
                raise Exception("Test failed")
            else:
                print("✅ Test completed successfully")
        except Exception as e:
            print(f"❌ Test failed: {{e}}")
            raise
        finally:
            browser.close()

if __name__ == '__main__':
    {test_name}()
'''
    
    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(test_script)
    
    return {
        'success': len(missing_elements) == 0,
        'output_file': str(output_file),
        'steps_processed': len(steps),
        'missing_elements': missing_elements
    }

