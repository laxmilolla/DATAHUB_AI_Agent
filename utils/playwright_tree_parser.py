"""
Playwright Tree Parser - Parse HTML elements from a Playwright page
Extracts interactive elements (inputs, buttons, links, selects) with their XPaths
"""
from typing import Dict, List, Any
from datetime import datetime


async def parse_with_tree(page) -> Dict[str, Any]:
    """
    Parse page using Playwright and extract interactive elements
    
    Args:
        page: Playwright Page object
        
    Returns:
        {
            'page': page_name,
            'url': current_url,
            'version': '1.0',
            'timestamp': ISO timestamp,
            'elements': {
                'element_name': {
                    'xpath': '//input[@data-testid="..."]',
                    'selector': '//input[@data-testid="..."]',
                    'tag': 'input',
                    'type': 'text',
                    'attributes': {...},
                    ...
                }
            },
            'statistics': {
                'total_elements': count,
                'parsed_elements': count
            }
        }
    """
    try:
        # Get current URL
        url = page.url
        
        # Extract page name from URL
        page_name = url.split('/')[-1] or 'home'
        if '?' in page_name:
            page_name = page_name.split('?')[0]
        if not page_name or page_name == '':
            page_name = 'home'
        
        elements = {}
        
        # Find all interactive elements
        # Inputs
        inputs = await page.locator('input, textarea, select').all()
        for idx, input_elem in enumerate(inputs):
            try:
                # Get attributes
                tag_name = await input_elem.evaluate('el => el.tagName.toLowerCase()')
                input_type = await input_elem.get_attribute('type') or 'text'
                data_testid = await input_elem.get_attribute('data-testid')
                element_id = await input_elem.get_attribute('id')
                name = await input_elem.get_attribute('name')
                placeholder = await input_elem.get_attribute('placeholder')
                aria_label = await input_elem.get_attribute('aria-label')
                
                # Generate XPath
                xpath = await generate_xpath(input_elem, page)
                
                # Generate element name
                element_name = generate_element_name(
                    tag_name, data_testid, name, element_id, placeholder, idx
                )
                
                # Get all attributes
                attributes = await input_elem.evaluate('''el => {
                    const attrs = {};
                    for (let attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }''')
                
                elements[element_name] = {
                    'xpath': xpath,
                    'selector': xpath,
                    'tag': tag_name,
                    'type': input_type if tag_name == 'input' else tag_name,
                    'attributes': attributes,
                    'url': url,
                    'element_id': f"ID_{hash(xpath) % 100000000:08x}",
                    'usage_count': 0,
                    'last_used': None,
                    'source': 'parser',
                    'object_type': tag_name,
                    'action': 'fill' if tag_name in ['input', 'textarea'] else 'select',
                    'discovered_at': datetime.utcnow().isoformat() + 'Z',
                    'last_updated': datetime.utcnow().isoformat() + 'Z'
                }
            except Exception as e:
                print(f"Error parsing input element {idx}: {e}")
                continue
        
        # Buttons
        buttons = await page.locator('button, [role="button"], a[href]').all()
        for idx, button_elem in enumerate(buttons):
            try:
                tag_name = await button_elem.evaluate('el => el.tagName.toLowerCase()')
                data_testid = await button_elem.get_attribute('data-testid')
                element_id = await button_elem.get_attribute('id')
                text_content = await button_elem.inner_text()
                aria_label = await button_elem.get_attribute('aria-label')
                
                # Skip if already processed as link
                if tag_name == 'a' and element_id in [e.get('attributes', {}).get('id') for e in elements.values()]:
                    continue
                
                xpath = await generate_xpath(button_elem, page)
                element_name = generate_element_name(
                    tag_name, data_testid, None, element_id, text_content[:50] if text_content else None, idx, 'button'
                )
                
                attributes = await button_elem.evaluate('''el => {
                    const attrs = {};
                    for (let attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }''')
                
                elements[element_name] = {
                    'xpath': xpath,
                    'selector': xpath,
                    'tag': tag_name,
                    'type': 'button',
                    'attributes': attributes,
                    'text': text_content[:100] if text_content else '',
                    'url': url,
                    'element_id': f"ID_{hash(xpath) % 100000000:08x}",
                    'usage_count': 0,
                    'last_used': None,
                    'source': 'parser',
                    'object_type': 'button' if tag_name == 'button' else 'link',
                    'action': 'click',
                    'discovered_at': datetime.utcnow().isoformat() + 'Z',
                    'last_updated': datetime.utcnow().isoformat() + 'Z'
                }
            except Exception as e:
                print(f"Error parsing button element {idx}: {e}")
                continue
        
        return {
            'page': page_name,
            'url': url,
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'elements': elements,
            'statistics': {
                'total_elements': len(elements),
                'parsed_elements': len(elements)
            }
        }
        
    except Exception as e:
        print(f"Error in parse_with_tree: {e}")
        import traceback
        traceback.print_exc()
        return {
            'page': 'error',
            'url': '',
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'elements': {},
            'statistics': {
                'total_elements': 0,
                'parsed_elements': 0
            },
            'error': str(e)
        }


async def generate_xpath(element, page) -> str:
    """Generate XPath for an element"""
    try:
        # Try to use data-testid first (most reliable)
        data_testid = await element.get_attribute('data-testid')
        if data_testid:
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            return f"//{tag_name}[@data-testid='{data_testid}']"
        
        # Try id
        element_id = await element.get_attribute('id')
        if element_id and not element_id.startswith(('mui-', 'Mui', 'css-')):
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            return f"//{tag_name}[@id='{element_id}']"
        
        # Try name
        name = await element.get_attribute('name')
        if name:
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            return f"//{tag_name}[@name='{name}']"
        
        # Fallback: use Playwright's built-in XPath generation
        # This is a simplified version - in production you might want more sophisticated XPath generation
        tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
        text_content = await element.inner_text()
        
        if text_content and len(text_content.strip()) < 50:
            # Use text content if available and reasonable
            text_clean = text_content.strip().replace("'", "\\'")
            return f"//{tag_name}[normalize-space(.)='{text_clean}']"
        
        # Last resort: use position-based XPath (less reliable)
        # Get parent and index
        parent_tag = await element.evaluate('el => el.parentElement ? el.parentElement.tagName.toLowerCase() : "body"')
        siblings = await element.evaluate('''el => {
            const parent = el.parentElement;
            if (!parent) return 0;
            const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            return siblings.indexOf(el) + 1;
        }''')
        
        return f"//{parent_tag}//{tag_name}[{siblings}]"
        
    except Exception as e:
        print(f"Error generating XPath: {e}")
        return "//*[@data-testid='unknown']"


def generate_element_name(tag: str, data_testid: str = None, name: str = None, 
                          element_id: str = None, text: str = None, idx: int = 0, 
                          default_type: str = 'element') -> str:
    """Generate a readable element name"""
    # Priority: data-testid > name > id > text > default
    if data_testid:
        # "submission-name-input" -> "submission_name_input"
        name_parts = data_testid.replace('-', '_').split('_')
        # Remove common suffixes
        if name_parts[-1] in ['input', 'field', 'button', 'dropdown', 'select']:
            name_parts = name_parts[:-1]
        return '_'.join(name_parts) if name_parts else f"{default_type}_{idx}"
    
    if name:
        # Convert camelCase to snake_case
        import re
        name_clean = re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()
        return name_clean
    
    if element_id and not element_id.startswith(('mui-', 'Mui', 'css-')):
        return element_id.replace('-', '_').replace('.', '_')
    
    if text and len(text.strip()) < 30:
        # Use text content, cleaned up
        text_clean = text.strip().lower().replace(' ', '_').replace('-', '_')
        # Remove special chars
        text_clean = ''.join(c if c.isalnum() or c == '_' else '' for c in text_clean)
        if text_clean:
            return text_clean[:30]
    
    return f"{default_type}_{idx}"

