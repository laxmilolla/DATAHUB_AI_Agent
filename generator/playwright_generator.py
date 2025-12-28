"""
Playwright Code Generator
Converts AI discoveries into executable Python Playwright test code
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class PlaywrightGenerator:
    """Generate Python Playwright test code from AI discovery metadata"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.discoveries_dir = self.project_root / 'storage' / 'discoveries'
        self.executions_dir = self.project_root / 'storage' / 'executions'
        self.generated_tests_dir = self.project_root / 'tests' / 'generated'
        self.generated_tests_metadata_dir = self.project_root / 'storage' / 'generated_tests'
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
        
        # Generate test name
        if not test_name:
            test_name = self._generate_test_name(execution['story'])
        
        # Generate code
        code = self._generate_test_code(execution, discoveries, test_name)
        
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
    
    def _generate_test_name(self, story: str) -> str:
        """Generate test name from story"""
        # Extract meaningful words
        words = re.findall(r'\b[a-z]{4,}\b', story.lower())
        # Take first 3-4 meaningful words
        name_words = [w for w in words if w not in ['click', 'verify', 'check', 'should', 'will', 'that', 'the', 'and', 'for']][:3]
        name = '_'.join(name_words) if name_words else 'test'
        return f"test_{name}"
    
    def _generate_test_code(self, execution: Dict, discoveries: Dict, test_name: str) -> str:
        """Generate complete Python Playwright test code"""
        
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
            code += self._generate_step_code(step, discoveries_list, indent=12)
        
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
        
        # Find all click actions (improved regex to handle run-on sentences)
        # Look for "click on/the X" patterns
        click_pattern = r'click (?:on )?(?:the )?([^,\.\n]+?)(?:\s+(?:to|and|in|inside|now|then|verify|check)|$)'
        for match in re.finditer(click_pattern, story, re.IGNORECASE):
            element = match.group(1).strip()
            # Clean up common trailing words
            element = re.sub(r'\s+(to|and|expand|dismiss|checkbox|tab|button)$', '', element, flags=re.IGNORECASE).strip()
            if element and len(element) > 2:  # Avoid single-character matches
                steps.append({'action': 'click', 'element': element})
        
        # Find verification steps
        verify_pattern = r'verify that (.+?)(?:\s+(?:click|$))'
        for match in re.finditer(verify_pattern, story, re.IGNORECASE):
            description = match.group(1).strip()
            steps.append({'action': 'verify', 'description': description})
        
        return steps
    
    def _generate_step_code(self, step: Dict, discoveries: List[Dict], indent: int = 12) -> str:
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
            code += self._generate_click_code(step, discoveries, indent)
        
        elif step['action'] == 'verify':
            code += self._generate_verify_code(step, indent)
        
        return code
    
    def _generate_click_code(self, step: Dict, discoveries: List[Dict], indent: int) -> str:
        """Generate click action code with discovery metadata"""
        ind = ' ' * indent
        element = step['element']
        
        # Find matching discovery
        discovery = self._find_discovery(element, discoveries)
        
        code = f"{ind}# Click: {element}\n"
        
        if discovery:
            # Add AI discovery comment
            method = discovery.get('discovery_method', 'unknown')
            metadata = discovery.get('metadata', {})
            
            if method == 'tree_climbing':
                depth = metadata.get('tree_depth', 'unknown')
                code += f"{ind}# AI Note: Found via tree climbing (depth {depth})\n"
            elif method == 'ai_disambiguation':
                code += f"{ind}# AI Note: Found via AI disambiguation\n"
            
            # Use the final selector from discovery
            selector = discovery.get('final_selector', f"text={element}")
        else:
            # No discovery metadata, use simple text selector
            selector = f"text={element}"
        
        # Sanitize element name for screenshot filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', element)[:50]
        screenshot_path = f"storage/screenshots/pw_{safe_name}.png"
        
        code += f"{ind}try:\n"
        code += f"{ind}    element = page.locator('{selector}')\n"
        code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
        code += f"{ind}    element.click()\n"
        code += f"{ind}    page.wait_for_timeout(1000)  # Wait for UI update\n"
        code += f"{ind}    print('✅ Clicked: {element}')\n"
        code += f"{ind}    # Capture screenshot after click\n"
        code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
        code += f"{ind}    print('📸 Screenshot: {screenshot_path}')\n"
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    print(f'❌ Failed to click {element}: {{e}}')\n"
        code += f"{ind}    raise\n\n"
        
        return code
    
    def _generate_verify_code(self, step: Dict, indent: int) -> str:
        """Generate verification code"""
        ind = ' ' * indent
        description = step['description']
        
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
        
        # Table data verification
        elif 'table' in description.lower() and 'show' in description.lower():
            code += f"{ind}# TODO: Add table data verification\n"
            code += f"{ind}print('⚠️  Table verification not yet implemented')\n\n"
        
        # Generic verification
        else:
            code += f"{ind}# TODO: Add specific verification for: {description}\n"
            code += f"{ind}print('⚠️  Manual verification needed')\n\n"
        
        return code
    
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

