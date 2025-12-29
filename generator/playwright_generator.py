"""
Playwright Code Generator
Converts AI discoveries into executable Python Playwright test code
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from urllib.parse import urlparse


class PlaywrightGenerator:
    """Generate Python Playwright test code from AI discovery metadata"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.discoveries_dir = self.project_root / 'storage' / 'discoveries'
        self.executions_dir = self.project_root / 'storage' / 'executions'
        self.generated_tests_dir = self.project_root / 'tests' / 'generated'
        self.generated_tests_metadata_dir = self.project_root / 'storage' / 'generated_tests'
        self.element_maps_dir = self.project_root / 'element_maps'
        self.generated_tests_dir.mkdir(parents=True, exist_ok=True)
        self.generated_tests_metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, execution_id: str, test_name: str = None) -> Dict[str, Any]:
        """
        Generate Playwright test from successful AI execution
        
        Args:
            execution_id: The execution ID (e.g., 'exec_172351d5')
            test_name: Optional custom test name
            
        Returns:
            Dict with 'code', 'filename', 'metadata'
        """
        # Load execution data
        execution = self._load_execution(execution_id)
        discoveries = self._load_discoveries(execution_id)
        
        # Load registry for the domain
        registry = self._load_registry(execution.get('story_url', ''))
        
        # Generate test name
        if not test_name:
            test_name = self._generate_test_name(execution['story'])
        
        # Generate code
        code = self._generate_test_code(execution, discoveries, test_name, registry)
        
        # Save to file
        filename = f"{test_name}.py"
        filepath = self.generated_tests_dir / filename
        with open(filepath, 'w') as f:
            f.write(code)
        
        # Save metadata
        metadata = {
            'execution_id': execution_id,
            'test_name': test_name,
            'filename': str(filepath),
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'story': execution['story'],
            'discoveries_count': len(discoveries.get('discoveries', []))
        }
        
        metadata_file = self.generated_tests_metadata_dir / f'{execution_id}_test.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'code': code,
            'filename': filename,
            'filepath': str(filepath),
            'metadata': metadata
        }
    
    def _load_execution(self, execution_id: str) -> Dict:
        """Load execution results"""
        file_path = self.executions_dir / f'{execution_id}.json'
        if not file_path.exists():
            raise FileNotFoundError(f"Execution {execution_id} not found")
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _load_discoveries(self, execution_id: str) -> Dict:
        """Load discovery metadata"""
        file_path = self.discoveries_dir / f'{execution_id}_discoveries.json'
        if not file_path.exists():
            return {'discoveries': []}
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _load_registry(self, url: str) -> Dict:
        """Load element registry for the domain"""
        if not url:
            return {}
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Look for registry file (try home_page.json or explore_page.json)
        domain_dir = self.element_maps_dir / domain
        if not domain_dir.exists():
            return {}
        
        # Try common page names
        for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
            registry_file = domain_dir / page_name
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    data = json.load(f)
                    return data.get('elements', {})
        
        return {}
    
    def _generate_test_name(self, story: str) -> str:
        """Generate test name from story"""
        # Extract meaningful words
        words = re.findall(r'\b[a-z]{4,}\b', story.lower())
        # Take first 3-4 meaningful words
        name_words = [w for w in words if w not in ['click', 'verify', 'check', 'should', 'will', 'that', 'the', 'and', 'for']][:3]
        name = '_'.join(name_words) if name_words else 'test'
        return f"test_{name}"
    
    def _generate_test_code(self, execution: Dict, discoveries: Dict, test_name: str, registry: Dict = None) -> str:
        """Generate complete Python Playwright test code"""
        
        if registry is None:
            registry = {}
        
        # Header
        code = f'''"""
Generated Playwright Test
Source Execution: {execution['execution_id']}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
Status: {execution['status']}

Story:
{execution['story']}
"""

from playwright.sync_api import sync_playwright, expect
import re


def {test_name}():
    """Auto-generated test from AI discovery"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
'''
        
        # Parse story into steps
        steps = self._parse_story_steps(execution['story'])
        discoveries_list = discoveries.get('discoveries', [])
        
        # Generate code for each step
        for i, step in enumerate(steps):
            code += self._generate_step_code(step, discoveries_list, registry, indent=12)
        
        # Footer
        code += f'''            
            print("✅ Test completed successfully")
            
        except Exception as e:
            print(f"❌ Test failed: {{e}}")
            raise
        finally:
            browser.close()


if __name__ == '__main__':
    {test_name}()
'''
        
        return code
    
    def _parse_story_steps(self, story: str) -> List[Dict]:
        """Parse story into actionable steps"""
        steps = []
        
        # Common patterns
        navigate_pattern = r'go to (https?://\S+)'
        
        # Navigate
        if match := re.search(navigate_pattern, story, re.IGNORECASE):
            steps.append({'action': 'navigate', 'url': match.group(1)})
        
        # Wait for page load
        if 'wait' in story.lower() and 'seconds' in story.lower():
            if match := re.search(r'wait (\d+) seconds', story, re.IGNORECASE):
                steps.append({'action': 'wait', 'duration': int(match.group(1)) * 1000})
        
        # Find CONDITIONAL click actions (e.g., "If there is a popup... click it")
        # These are optional and should not fail the test if element not found
        # Pattern: "If there is [context] with [element] button, click it"
        conditional_pattern = r'if\s+there\s+is\s+(?:a\s+)?(\w+)\s+with\s+(?:a\s+)?(\w+)\s+button,?\s+click'
        for match in re.finditer(conditional_pattern, story, re.IGNORECASE):
            context = match.group(1).strip()  # e.g., "popup"
            element = match.group(2).strip()   # e.g., "Continue"
            if element and len(element) > 2:
                steps.append({'action': 'click', 'element': element, 'optional': True, 'context': context})
        
        # Find all regular click actions (improved regex to handle run-on sentences)
        # Look for "click on/the X" patterns
        click_pattern = r'click (?:on )?(?:the )?([^,\.\n]+?)(?:\s+(?:to|and|in|inside|now|then|verify|check)|$)'
        for match in re.finditer(click_pattern, story, re.IGNORECASE):
            element = match.group(1).strip()
            # Skip if this was already captured as a conditional click
            if any(s.get('element', '').lower() == element.lower() and s.get('optional') for s in steps):
                continue
            # Clean up common trailing words
            element = re.sub(r'\s+(to|and|expand|dismiss|checkbox|tab|button)$', '', element, flags=re.IGNORECASE).strip()
            if element and len(element) > 2:  # Avoid single-character matches
                steps.append({'action': 'click', 'element': element})
        
        # Find verification steps
        # Match "Verify that X" or "Verify X" - capture everything until newline or end of string
        verify_pattern = r'verify\s+(?:that\s+)?(.+?)(?:\n|$)'
        for match in re.finditer(verify_pattern, story, re.IGNORECASE | re.MULTILINE):
            description = match.group(1).strip()
            steps.append({'action': 'verify', 'description': description})
        
        return steps
    
    def _generate_step_code(self, step: Dict, discoveries: List[Dict], registry: Dict, indent: int = 12) -> str:
        """Generate code for a single step"""
        ind = ' ' * indent
        code = ''
        
        if step['action'] == 'navigate':
            code += f"{ind}# Navigate to page\n"
            code += f"{ind}page.goto('{step['url']}')\n"
            code += f"{ind}print('📍 Navigated to {step['url']}')\n\n"
        
        elif step['action'] == 'wait':
            code += f"{ind}# Wait for page load\n"
            code += f"{ind}page.wait_for_timeout({step['duration']})\n\n"
        
        elif step['action'] == 'click':
            code += self._generate_click_code(step, discoveries, registry, indent)
        
        elif step['action'] == 'verify':
            code += self._generate_verify_code(step, discoveries, indent)
        
        return code
    
    def _generate_click_code(self, step: Dict, discoveries: List[Dict], registry: Dict, indent: int) -> str:
        """Generate click action code with discovery metadata"""
        ind = ' ' * indent
        element = step['element']
        is_optional = step.get('optional', False)
        context = step.get('context', '')
        
        if is_optional:
            code = f"{ind}# Optional: {element} ({context} - may not be present)\n"
        else:
            code = f"{ind}# Click: {element}\n"
        
        # Try to find selector in registry first (priority)
        selector = self._get_selector_from_registry(element, registry)
        source = "registry"
        discovery = None
        method = ''
        metadata = {}
        
        if not selector:
            # Fallback to discovery metadata
            discovery = self._find_discovery(element, discoveries)
            if discovery:
                selector = discovery.get('final_selector', f"text={element}")
                method = discovery.get('discovery_method', 'unknown')
                metadata = discovery.get('metadata', {})
                
                if method == 'tree_climbing':
                    code += f"{ind}# AI Note: Found via tree climbing (with parent fallback)\n"
                elif method == 'ai_disambiguation':
                    code += f"{ind}# AI Note: Found via AI disambiguation\n"
                source = "discovery"
            else:
                # No discovery metadata, use simple text selector
                selector = f"text={element}"
                source = "default"
        else:
            code += f"{ind}# Selector from registry (optimized)\n"
        
        # Sanitize element name for screenshot filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', element)[:50]
        screenshot_path = f"storage/screenshots/pw_{safe_name}.png"
        
        # Escape quotes in selector for Python string
        selector_escaped = selector.replace("'", "\\'")
        
        if is_optional:
            # Optional click - don't fail if not found
            code += f"{ind}try:\n"
            code += f"{ind}    element = page.locator('{selector_escaped}').nth(0)\n"
            code += f"{ind}    if element.is_visible(timeout=2000):\n"
            code += f"{ind}        element.click()\n"
            code += f"{ind}        page.wait_for_timeout(500)\n"
            code += f"{ind}        print('✅ Clicked: {element} ({context})')\n"
            code += f"{ind}        page.screenshot(path='{screenshot_path}')\n"
            code += f"{ind}        print('📸 Screenshot: {screenshot_path}')\n"
            code += f"{ind}    else:\n"
            code += f"{ind}        print('ℹ️  {element} not visible (this is fine, {context} not present)')\n"
            code += f"{ind}except Exception:\n"
            code += f"{ind}    print('ℹ️  {element} not found (this is fine, {context} not present)')\n\n"
        else:
            # Required click with tree climbing fallback
            code += f"{ind}try:\n"
            code += f"{ind}    # Strategy 1: Try direct click on element\n"
            code += f"{ind}    element = page.locator('{selector_escaped}').nth(0)\n"
            code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
            code += f"{ind}    element.click()\n"
            code += f"{ind}    page.wait_for_timeout(1000)  # Wait for UI update\n"
            code += f"{ind}    print('✅ Clicked: {element}')\n"
            code += f"{ind}    # Capture screenshot after click\n"
            code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
            code += f"{ind}    print('📸 Screenshot: {screenshot_path}')\n"
            code += f"{ind}except Exception as e:\n"
            
            # Add tree climbing fallback if metadata indicates it was used
            if method == 'tree_climbing' and metadata.get('relationship') == 'parent':
                code += f"{ind}    # Fallback: AI used tree climbing, try clicking parent element\n"
                code += f"{ind}    try:\n"
                code += f"{ind}        print(f'⚠️  Direct click failed, trying parent element (AI tree climbing strategy)...')\n"
                code += f"{ind}        parent = page.locator('{selector_escaped}').nth(0).locator('xpath=..')\n"
                code += f"{ind}        parent.wait_for(state='visible', timeout=5000)\n"
                code += f"{ind}        parent.click()\n"
                code += f"{ind}        page.wait_for_timeout(1000)\n"
                code += f"{ind}        print('✅ Clicked parent element: {element}')\n"
                code += f"{ind}        page.screenshot(path='{screenshot_path}')\n"
                code += f"{ind}        print('📸 Screenshot: {screenshot_path}')\n"
                code += f"{ind}    except Exception as e2:\n"
                code += f"{ind}        print(f'❌ Both strategies failed for {element}')\n"
                code += f"{ind}        print(f'   Direct: {{e}}')\n"
                code += f"{ind}        print(f'   Parent: {{e2}}')\n"
                code += f"{ind}        raise e2\n"
            else:
                # No tree climbing metadata, just fail
                code += f"{ind}    print(f'❌ Failed to click {element}: {{e}}')\n"
                code += f"{ind}    raise\n"
            
            code += f"\n"
        
        return code
    
    def _generate_verify_code(self, step: Dict, discoveries: List[Dict], indent: int) -> str:
        """Generate verification code based on AI verification metadata"""
        ind = ' ' * indent
        description = step['description']
        
        # Try to find verification discovery metadata
        verify_discovery = None
        for disc in discoveries:
            if disc.get('discovery_method') == 'table_verification':
                verify_discovery = disc
                break
        
        if verify_discovery and verify_discovery.get('metadata', {}).get('verification_type') == 'table_column':
            # Generate table column verification code
            metadata = verify_discovery['metadata']
            column_name = metadata.get('column_name', 'unknown')
            expected_value = metadata.get('expected_value', '')
            table_selector = verify_discovery.get('final_selector', 'table')
            
            code = f"{ind}# Verify: All rows in '{column_name}' column contain '{expected_value}'\n"
            code += f"{ind}try:\n"
            code += f"{ind}    print('🔍 Verifying table column...')\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Find table\n"
            code += f"{ind}    table = page.locator('{table_selector}').first\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Find column index by header text\n"
            code += f"{ind}    headers = table.locator('thead th, thead td').all_text_contents()\n"
            code += f"{ind}    column_index = -1\n"
            code += f"{ind}    for i, header in enumerate(headers):\n"
            code += f"{ind}        if '{column_name}'.lower() in header.lower():\n"
            code += f"{ind}            column_index = i\n"
            code += f"{ind}            break\n"
            code += f"{ind}    \n"
            code += f"{ind}    if column_index == -1:\n"
            code += f"{ind}        raise Exception(f\"Column '{column_name}' not found. Available: {{headers}}\")\n"
            code += f"{ind}    \n"
            code += f"{ind}    print(f'📋 Found column \"{column_name}\" at index {{column_index}}')\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Get all rows and verify\n"
            code += f"{ind}    rows = table.locator('tbody tr').all()\n"
            code += f"{ind}    total_rows = len(rows)\n"
            code += f"{ind}    matching_rows = 0\n"
            code += f"{ind}    \n"
            code += f"{ind}    print(f'🔍 Checking {{total_rows}} rows...')\n"
            code += f"{ind}    \n"
            code += f"{ind}    for row_idx, row in enumerate(rows):\n"
            code += f"{ind}        cells = row.locator('td').all()\n"
            code += f"{ind}        if column_index < len(cells):\n"
            code += f"{ind}            cell_text = cells[column_index].inner_text().strip()\n"
            code += f"{ind}            if '{expected_value}'.lower() in cell_text.lower():\n"
            code += f"{ind}                matching_rows += 1\n"
            code += f"{ind}            else:\n"
            code += f"{ind}                print(f'⚠️  Row {{row_idx + 1}}: Expected \"{expected_value}\", got \"{{cell_text}}\"')\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Assert all rows match\n"
            code += f"{ind}    assert matching_rows == total_rows, f\"Only {{matching_rows}}/{{total_rows}} rows match\"\n"
            code += f"{ind}    \n"
            code += f"{ind}    print(f'✅ VERIFICATION PASSED: All {{total_rows}} rows in \"{column_name}\" contain \"{expected_value}\"')\n"
            code += f"{ind}    page.screenshot(path='storage/screenshots/pw_verify_table.png')\n"
            code += f"{ind}    print('📸 Screenshot: storage/screenshots/pw_verify_table.png')\n"
            code += f"{ind}    \n"
            code += f"{ind}except Exception as e:\n"
            code += f"{ind}    print(f'❌ VERIFICATION FAILED: {{e}}')\n"
            code += f"{ind}    page.screenshot(path='storage/screenshots/pw_verify_table_failed.png')\n"
            code += f"{ind}    raise\n\n"
            
            return code
        
        # Fallback: Generic verification
        code = f"{ind}# Verify: {description}\n"
        
        # URL verification
        if 'url' in description.lower() or 'parameter' in description.lower():
            if match := re.search(r'(\w+)=(\w+)', description):
                param = match.group(1)
                value = match.group(2)
                code += f"{ind}try:\n"
                code += f"{ind}    expect(page).to_have_url(re.compile('{param}={value}'))\n"
                code += f"{ind}    print('✅ URL verification passed')\n"
                code += f"{ind}except Exception as e:\n"
                code += f"{ind}    print(f'❌ URL verification failed: {{e}}')\n\n"
        
        # Generic verification
        else:
            code += f"{ind}# AI Agent performed verification, see execution results\n"
            code += f"{ind}print('⚠️  Verification performed by AI - add specific Playwright assertions if needed')\n\n"
        
        return code
    
    def _get_selector_from_registry(self, element_name: str, registry: Dict) -> str:
        """Get optimized selector from registry"""
        if not registry:
            return None
        
        element_lower = element_name.lower().strip()
        
        # Try exact match first
        for key, value in registry.items():
            key_lower = key.lower()
            if element_lower in key_lower or key_lower in element_lower:
                # Return the optimized selector from registry
                if isinstance(value, dict) and 'selector' in value:
                    return value['selector']
                elif isinstance(value, dict) and 'query' in value:
                    # Fallback to query if no selector
                    return value['query']
        
        return None
    
    def _find_discovery(self, element_name: str, discoveries: List[Dict]) -> Dict:
        """Find discovery metadata for an element"""
        element_lower = element_name.lower().strip()
        
        for disc in discoveries:
            disc_name = disc.get('name', '').lower()
            orig_query = disc.get('original_query', '').lower().replace('text=', '')
            
            if element_lower in disc_name or element_lower in orig_query:
                return disc
        
        return None


# Example usage
if __name__ == '__main__':
    generator = PlaywrightGenerator()
    result = generator.generate('exec_172351d5')
    print(f"Generated: {result['filename']}")
    print(f"Path: {result['filepath']}")

