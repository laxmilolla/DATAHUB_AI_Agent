"""
Playwright Code Generator
Converts AI discoveries into executable Python Playwright test code
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


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
        
        # Detect all registry files needed (multi-registry support)
        registry_files = self._detect_registry_files(execution)
        
        # Load registries for backward compatibility (used in some places)
        # Extract URL from story if story_url not present
        story_url = execution.get('story_url', '')
        if not story_url:
            # Try to extract URL from story
            if match := re.search(r'https?://[^\s]+', execution.get('story', '')):
                story_url = match.group(0)
        
        registry = self._load_registry(story_url)
        
        # Generate test name
        if not test_name:
            test_name = self._generate_test_name(execution['story'])
        
        # Generate code with multi-registry support
        code = self._generate_test_code(execution, discoveries, test_name, registry, registry_files)
        
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
    
    def _get_registry_path(self, url: str) -> str:
        """Get relative path to registry file for use in generated test"""
        if not url:
            # Default to main registry
            return 'element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json'
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Extract page name from URL path (same logic as agent)
        url_path = url.split('/')[-1].split('#')[0]
        if url_path == 'explore':
            page = 'explore'
        elif not url_path or url_path == '':
            page = 'home'
        else:
            page = url_path
        
        # Always return the expected path based on URL structure
        # (even if file doesn't exist yet - user can create it)
        expected_path = f'element_maps/{domain}/{page}_page.json'
        
        # Check if file exists - if so, use it; otherwise check for common alternatives
        domain_dir = self.element_maps_dir / domain
        if domain_dir.exists():
            # Try specific page first
            registry_file = domain_dir / f'{page}_page.json'
            if registry_file.exists():
                return expected_path
            
            # Fallback to common page names if specific page doesn't exist
            for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
                registry_file = domain_dir / page_name
                if registry_file.exists():
                    return f'element_maps/{domain}/{page_name}'
        
        # Return expected path (even if it doesn't exist yet)
        # This allows the test to work once the registry is created
        return expected_path
    
    def _detect_registry_files(self, execution: Dict) -> List[str]:
        """
        Detect all registry files needed based on URLs visited during test execution.
        Scans actions_taken for browser_navigate actions and extracts registry paths.
        """
        registry_files = set()
        
        # Get initial URL from story
        story_url = execution.get('story_url', '')
        if not story_url:
            # Try to extract URL from story
            if match := re.search(r'https?://[^\s]+', execution.get('story', '')):
                story_url = match.group(0)
        
        if story_url:
            registry_path = self._get_registry_path(story_url)
            if registry_path:
                registry_files.add(registry_path)
        
        # Scan actions_taken for navigations
        for action in execution.get('actions_taken', []):
            tool = action.get('tool', '')
            if tool == 'browser_navigate':
                url = action.get('input', {}).get('url', '')
                if url:
                    registry_path = self._get_registry_path(url)
                    if registry_path:
                        registry_files.add(registry_path)
        
        # Also check discoveries for URL metadata (if available)
        # This catches elements discovered on pages that weren't explicitly navigated to
        # (e.g., if page changed due to form submission)
        discoveries = execution.get('discoveries', [])
        for disc in discoveries:
            metadata = disc.get('metadata', {})
            url = metadata.get('url', '')
            if url:
                registry_path = self._get_registry_path(url)
                if registry_path:
                    registry_files.add(registry_path)
        
        # Extract URLs from story text (catches URLs mentioned in steps like "goes to https://...")
        story = execution.get('story', '')
        if story:
            story_urls = re.findall(r'https?://[^\s\)]+', story)
            for url in story_urls:
                registry_path = self._get_registry_path(url)
                if registry_path:
                    registry_files.add(registry_path)
        
        return sorted(list(registry_files))
    
    def _generate_test_name(self, story: str) -> str:
        """Generate test name from story"""
        # Extract meaningful words
        words = re.findall(r'\b[a-z]{4,}\b', story.lower())
        # Take first 3-4 meaningful words
        name_words = [w for w in words if w not in ['click', 'verify', 'check', 'should', 'will', 'that', 'the', 'and', 'for']][:3]
        name = '_'.join(name_words) if name_words else 'test'
        return f"test_{name}"
    
    def _clean_selector(self, selector: str) -> str:
        """
        Clean selector by removing state-dependent attributes and dynamic content
        
        The AI discovers elements AFTER clicking them (in their final state),
        but Playwright tests need selectors that work BEFORE clicking and with
        dynamic content (like changing counts).
        
        Remove:
        - [aria-selected] - tabs are NOT selected before clicking
        - [aria-selected='true'] or [aria-selected='false']
        - [aria-expanded='true'] - accordions may not be expanded yet
        - [aria-expanded='false'] - accordions may already be expanded
        - Dynamic counts in text - e.g., 'Diagnosis(97)' → 'Diagnosis'
        
        Keep:
        - [aria-expanded] without value - just checks attribute exists
        - Other attributes like [role='tab'], [role='button'], etc.
        """
        # Remove [aria-selected] and [aria-selected='true'/'false']
        selector = re.sub(r'\[aria-selected(?:=["\'](?:true|false)["\'])?\]', '', selector)
        
        # Remove [aria-expanded='true'] or [aria-expanded='false'] but keep [aria-expanded]
        # This regex looks for aria-expanded with a specific value
        selector = re.sub(r'\[aria-expanded=["\'](?:true|false)["\']?\]', '[aria-expanded]', selector)
        
        # Remove dynamic counts from has-text() - e.g., 'Diagnosis(97)' → 'Diagnosis'
        # Match patterns like: has-text('Something(123)') or has-text('Something(1,234)')
        # This handles tabs/buttons that show counts which change dynamically
        selector = re.sub(r"(:has-text\(['\"])(.*?)\(\d+(?:,\d+)*\)(['\"])", r"\1\2\3", selector)
        
        return selector
    
    def _generate_test_code(self, execution: Dict, discoveries: Dict, test_name: str, registry: Dict = None, registry_files: List[str] = None) -> str:
        """Generate complete Python Playwright test code - 1:1 mirror of AI execution"""
        
        if registry is None:
            registry = {}
        
        if registry_files is None:
            # Fallback: detect registry files if not provided
            registry_files = self._detect_registry_files(execution)
            if not registry_files:
                # Fallback to story URL
                story_url = execution.get('story_url', '')
                if not story_url:
                    if match := re.search(r'https?://[^\s]+', execution.get('story', '')):
                        story_url = match.group(0)
                if story_url:
                    registry_files = [self._get_registry_path(story_url)]
        
        story = execution['story']
        actions_taken = execution.get('actions_taken', [])
        discoveries_list = discoveries.get('discoveries', [])
        
        # Use first registry as default (for backward compatibility)
        default_registry_path = registry_files[0] if registry_files else 'element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json'
        
        # Load and merge ALL registries for multi-registry support
        merged_registry = {'elements': {}, 'id_index': {}}
        for registry_path_str in registry_files:
            registry_file_path = self.element_maps_dir.parent / registry_path_str
            if registry_file_path.exists():
                try:
                    with open(registry_file_path, 'r') as f:
                        registry_data = json.load(f)
                        # Merge elements (later registries override earlier ones if same key)
                        merged_registry['elements'].update(registry_data.get('elements', {}))
                        # Merge id_index (later registries override earlier ones if same element_id)
                        merged_registry['id_index'].update(registry_data.get('id_index', {}))
                except Exception as e:
                    logger.warning(f"Failed to load registry {registry_path_str}: {e}")
        
        # Use merged registry instead of single registry
        registry = merged_registry
        
        # Header
        execution_id = execution['execution_id']
        
        # Extract test-specific values from discoveries (embed in test, not load from file)
        # Find verification discovery
        verify_discovery = None
        verify_column_name = ''
        verify_expected_value = ''
        for disc in discoveries_list:
            if disc.get('discovery_method') == 'table_verification':
                verify_discovery = disc
                metadata = disc.get('metadata', {})
                verify_column_name = metadata.get('column_name', '')
                verify_expected_value = metadata.get('expected_value', '')
                break
        
        # Find optional element selectors (elements without element_id)
        optional_selectors = {}  # element_name -> selector
        for disc in discoveries_list:
            if not disc.get('element_id'):
                element_name = disc.get('name', '')
                # Use original_query (what AI was instructed to use) for true mirroring
                selector = disc.get('original_query') or disc.get('final_selector', '')
                if selector and element_name:
                    optional_selectors[element_name] = selector
        
        # Escape for Python string literals
        verify_column_name_escaped = verify_column_name.replace("'", "\\'").replace('"', '\\"')
        verify_expected_value_escaped = verify_expected_value.replace("'", "\\'").replace('"', '\\"')
        
        # Build test-specific constants section
        test_constants = ""
        if verify_column_name and verify_expected_value:
            test_constants += f"# Verification values (test-specific, from story)\n"
            test_constants += f"VERIFY_COLUMN_NAME = '{verify_column_name_escaped}'\n"
            test_constants += f"VERIFY_EXPECTED_VALUE = '{verify_expected_value_escaped}'\n\n"
        
        if optional_selectors:
            test_constants += f"# Optional element selectors (test-specific, elements not in registry)\n"
            for name, selector in optional_selectors.items():
                selector_escaped = selector.replace("'", "\\'").replace('"', '\\"')
                # Create safe constant name (match what we'll use in code generation)
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
                constant_name = f"OPTIONAL_{safe_name.upper()}_SELECTOR"
                test_constants += f"{constant_name} = '{selector_escaped}'\n"
            test_constants += "\n"
        
        # Format registry paths list for Python code
        registry_paths_list_str = "[\n"
        for reg_path in registry_files:
            registry_paths_list_str += f"    '{reg_path}',\n"
        registry_paths_list_str += "]"
        
        code = f'''"""
Generated Playwright Test
Source Execution: {execution_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
Status: {execution['status']}

Story:
{story}
"""

from playwright.sync_api import sync_playwright, expect
import re
import json
from pathlib import Path

# ============================================================================
# TEST-SPECIFIC VALUES (from story - embedded in test, not in registry)
# ============================================================================
{test_constants}# ============================================================================
# MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
# ============================================================================
# Automatically detects and loads all registry files needed based on URLs visited
# Update paths below if registries are in different locations
REGISTRY_PATHS = {registry_paths_list_str}

# Load and merge all registries
REGISTRY = {{}}
REGISTRY_ID_INDEX = {{}}
loaded_count = 0
for registry_path_str in REGISTRY_PATHS:
    try:
        registry_path = Path(registry_path_str)
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
                # Merge elements (later registries override earlier ones if same key)
                REGISTRY.update(registry_data.get('elements', {{}}))
                # Merge id_index (later registries override earlier ones if same element_id)
                REGISTRY_ID_INDEX.update(registry_data.get('id_index', {{}}))
            loaded_count += 1
            print(f"✅ Loaded registry: {{len(registry_data.get('elements', {{}}))}} elements from {{registry_path.name}}")
        else:
            print(f"⚠️  Registry file not found: {{registry_path}}")
    except Exception as e:
        print(f"⚠️  Failed to load registry {{registry_path_str}}: {{e}}")

if loaded_count > 0:
    print(f"✅ Merged {{loaded_count}} registries: {{len(REGISTRY)}} total elements, {{len(REGISTRY_ID_INDEX)}} total IDs")
else:
    print(f"⚠️  No registries loaded. Please check REGISTRY_PATHS above.")

def get_xpath_by_id(element_id):
    """Get XPath from registry by unique ID - ONLY source of XPaths (strict, no fallbacks)"""
    if not element_id:
        raise Exception(f"❌ element_id is required")
    
    if element_id not in REGISTRY_ID_INDEX:
        raise Exception(f"❌ element_id '{{element_id}}' not found in registry id_index")
    
    registry_key = REGISTRY_ID_INDEX[element_id]
    
    if registry_key not in REGISTRY:
        raise Exception(f"❌ Registry key '{{registry_key}}' not found for element_id '{{element_id}}'")
    
    xpath = REGISTRY[registry_key].get('xpath')
    
    if not xpath:
        raise Exception(f"❌ XPath missing for element_id '{{element_id}}' (registry_key: '{{registry_key}}')")
    
    return xpath


def {test_name}():
    """Auto-generated test from AI discovery - 1:1 mirror of AI execution"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Match AI agent viewport to ensure tabs are visible (not hidden in "More" dropdown)
        page = browser.new_page(viewport={{'width': 1920, 'height': 1080}})
        
        try:
'''
        
        # NEW APPROACH: Process story steps sequentially, matching with actions_taken
        # This ensures perfect 1:1 mapping between AI execution and Playwright
        code += self._generate_sequential_code(story, actions_taken, discoveries_list, registry, indent=12)
        
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
    
    def _extract_infrastructure(self, story: str) -> Dict:
        """Extract infrastructure elements (navigation, waits, optionals) from story"""
        infrastructure = {
            'navigation': None,
            'waits': [],
            'optionals': []
        }
        
        # Extract navigation URL
        navigate_pattern = r'go to (https?://\S+)'
        if match := re.search(navigate_pattern, story, re.IGNORECASE):
            infrastructure['navigation'] = match.group(1)
        
        # Extract wait steps
        wait_pattern = r'wait (\d+) seconds'
        for match in re.finditer(wait_pattern, story, re.IGNORECASE):
            infrastructure['waits'].append({
                'duration': int(match.group(1)) * 1000,
                'position': match.start()  # Track position in story
            })
        
        # Extract optional/conditional steps
        conditional_pattern = r'if\s+there\s+is\s+(?:a\s+)?(?:popup|dialog|modal)\s+with\s+(?:a\s+)?(\w+)\s+button'
        for match in re.finditer(conditional_pattern, story, re.IGNORECASE):
            element = match.group(1).strip()
            infrastructure['optionals'].append({
                'element': element,
                'context': 'popup',
                'position': match.start()
            })
        
        return infrastructure
    
    def _generate_sequential_code(self, story: str, actions_taken: List[Dict], discoveries: List[Dict], registry: Dict, indent: int = 12) -> str:
        """
        Generate code by processing story steps sequentially - Perfect 1:1 mirror of AI execution
        
        Strategy:
        1. Parse story into numbered steps (Step 1, Step 2, etc.)
        2. For each step, find the corresponding action from actions_taken (by iteration number)
        3. Extract selector, timing, everything from actual AI execution
        4. Generate code in exact story order
        
        Result: Playwright = Carbon copy of AI, same steps, same selectors, same timing
        """
        ind = ' ' * indent
        code = ''
        
        # CRITICAL: Always generate navigation if iteration 1 is browser_navigate
        # This ensures navigation is never skipped, even if story parsing fails
        navigation_generated = False
        if actions_taken:
            first_action = actions_taken[0]
            if first_action.get('tool') == 'browser_navigate' and first_action.get('iteration') == 1:
                # Generate navigation step first, regardless of story parsing
                step_text = first_action.get('input', {}).get('url', '')
                if not step_text:
                    step_text = f"Navigate to {first_action.get('input', {}).get('url', 'unknown URL')}"
                code += self._generate_navigate_step(1, step_text, first_action, indent)
                navigation_generated = True
        
        # Parse story into steps
        story_lines = story.strip().split('\n')
        step_number = 1
        
        for line in story_lines:
            # Extract step number - handle variations: "Step 1:", "Steps 15:", "Step 1", "Steps 15", etc.
            # More flexible regex to catch malformed story text (handles plural "Steps" and optional colon)
            step_match = re.match(r'[Ss]teps?\s+(\d+)\s*:?\s*(.+)', line, re.IGNORECASE)
            if not step_match:
                continue
            
            step_num = int(step_match.group(1))
            step_text = step_match.group(2).strip()
            
            # Skip Step 1 if navigation was already generated
            if step_num == 1 and navigation_generated:
                continue
            
            # Find corresponding action from actions_taken
            # For wait steps, match by step text content, not iteration number
            if 'wait' in step_text.lower() and any(char.isdigit() for char in step_text):
                # This is a wait step - find browser_evaluate action with setTimeout
                action = None
                for act in actions_taken:
                    if act.get('tool') == 'browser_evaluate':
                        code_str = act.get('input', {}).get('code', '')
                        if 'setTimeout' in code_str or 'Promise' in code_str:
                            action = act
                            break
            else:
                # For other steps, use iteration matching
                action = self._find_action_by_iteration(step_num, actions_taken)
            
            # Generate code based on action type
            if not action:
                # No action found - add comment
                code += f"{ind}# Step {step_num}: {step_text[:80]}\n"
                code += f"{ind}# (No corresponding action found in execution)\n\n"
                continue
            
            tool = action.get('tool', '')
            input_params = action.get('input', {})
            result = action.get('result', '')
            
            # Generate code based on tool type
            if tool == 'browser_navigate':
                code += self._generate_navigate_step(step_num, step_text, action, indent)
            
            elif tool == 'browser_evaluate':
                # Likely a wait step
                code += self._generate_wait_step(step_num, step_text, action, indent)
            
            elif tool == 'browser_click':
                # Find corresponding discovery for this click
                discovery = self._find_discovery_by_step(step_num, step_text, discoveries, action)
                
                # If no discovery found, try to find element in registry by step text/action selector
                if not discovery:
                    selector = action.get('input', {}).get('selector', '')
                    # Try to extract element name from step text or selector
                    element_name_from_step = None
                    if 'checkbox' in step_text.lower():
                        # Extract checkbox name from step text (e.g., "Select the Acute leukemia, NOS checkbox")
                        checkbox_match = re.search(r'select\s+(?:the\s+)?(.+?)\s+checkbox', step_text, re.IGNORECASE)
                        if checkbox_match:
                            element_name_from_step = checkbox_match.group(1).strip()
                    
                    # Try to find in registry
                    if element_name_from_step and registry:
                        for key, elem_data in registry.items():
                            if element_name_from_step.lower() in key.lower() or key.lower() in element_name_from_step.lower():
                                # Create a discovery-like dict from registry entry
                                discovery = {
                                    'name': key,
                                    'element_id': elem_data.get('element_id'),
                                    'xpath': elem_data.get('xpath'),
                                    'original_query': selector,
                                    'final_selector': elem_data.get('selector', selector),
                                    'discovery_method': 'registry_lookup'
                                }
                                logger.info(f"  🔍 Found element in registry for Step {step_num}: {key} (ID: {discovery.get('element_id', 'N/A')})")
                                break
                
                # Find next step's discovery (for popup dismissal - wait for next element to be clickable)
                next_step_discovery = None
                if step_num < len(story_lines):  # Not the last step
                    # Look ahead to find next click step
                    current_line_idx = story_lines.index(line) if line in story_lines else -1
                    if current_line_idx >= 0:
                        for next_line in story_lines[current_line_idx + 1:]:
                            next_step_match = re.match(r'[Ss]?tep\s+(\d+):\s*(.+)', next_line, re.IGNORECASE)
                            if next_step_match:
                                next_step_num = int(next_step_match.group(1))
                                next_step_text = next_step_match.group(2).strip()
                                # Find next step's action
                                next_action = self._find_action_by_iteration(next_step_num, actions_taken)
                                if next_action and next_action.get('tool') == 'browser_click':
                                    # Find next step's discovery
                                    next_step_discovery = self._find_discovery_by_step(next_step_num, next_step_text, discoveries, next_action)
                                    break
                
                code += self._generate_click_step(step_num, step_text, action, discovery, registry, indent, next_step_discovery)
            
            elif tool == 'browser_fill':
                # Find corresponding discovery for this fill action
                discovery = self._find_discovery_by_step(step_num, step_text, discoveries, action)
                code += self._generate_fill_step(step_num, step_text, action, discovery, registry, indent)
            
            elif tool == 'browser_verify_table':
                # Find corresponding verification discovery (must be table_verification type)
                discovery = self._find_verification_discovery(step_num, discoveries)
                code += self._generate_verify_step(step_num, step_text, action, discovery, indent)
            
            else:
                # Unknown tool - add comment
                code += f"{ind}# Step {step_num}: {step_text[:80]}\n"
                code += f"{ind}# Tool: {tool} (not yet supported in generator)\n\n"
        
        return code
    
    def _find_action_by_iteration(self, step_num: int, actions_taken: List[Dict]) -> Dict:
        """Find action corresponding to a story step number"""
        for action in actions_taken:
            if action.get('iteration') == step_num:
                return action
        return None
    
    def _find_verification_discovery(self, step_num: int, discoveries: List[Dict]) -> Dict:
        """
        Find table_verification discovery for a verify step.
        Returns the first table_verification discovery found (there's usually only one).
        """
        for disc in discoveries:
            if disc.get('discovery_method') == 'table_verification':
                logger.info(f"  ✅ Found table verification discovery for step {step_num}")
                return disc
        
        logger.warning(f"  ⚠️ No table verification discovery found for step {step_num}")
        return None
    
    def _find_discovery_by_step(self, step_num: int, step_text: str, discoveries: List[Dict], action: Dict) -> Dict:
        """
        Find discovery metadata that matches this step.
        Match by comparing action's selector with discovery's original_query AND actual clicked selector.
        Also considers step context (e.g., "tab" in step text should match tab discoveries).
        This prevents wrong matches (e.g., checkbox being matched with table verification, tab vs accordion).
        """
        selector = action.get('input', {}).get('selector', '')
        result = action.get('result', '')
        
        if not selector:
            return None
        
        # Extract actual clicked selector from result (what AI actually clicked)
        actual_clicked_selector = None
        if result and 'Clicked' in result:
            clicked_match = re.search(r'(?:✅\s*)?Clicked\s+(.+?)(?:\s+-\s+|$)', result)
            if clicked_match:
                selector_raw = clicked_match.group(1).strip().rstrip('.,;').strip()
                if selector_raw and (selector_raw.startswith(('xpath=', 'text=', 'css=', '#')) or 
                                     '[' in selector_raw or selector_raw.startswith('.')):
                    actual_clicked_selector = selector_raw.lower()
        
        # Normalize selector for comparison
        selector_normalized = selector.lower().strip()
        if selector_normalized.startswith('text='):
            selector_normalized = selector_normalized[5:].strip()
        
        # Extract step context keywords (e.g., "tab", "accordion", "checkbox")
        step_lower = step_text.lower()
        is_tab_step = 'tab' in step_lower
        is_accordion_step = 'accordion' in step_lower or 'expand' in step_lower
        is_checkbox_step = 'checkbox' in step_lower or 'select' in step_lower
        
        # Find discovery with matching original_query AND context
        best_match = None
        best_score = 0
        
        for disc in discoveries:
            disc_query = disc.get('original_query', '').lower().strip()
            if disc_query.startswith('text='):
                disc_query = disc_query[5:].strip()
            
            # Skip verification discoveries (they don't have element selectors)
            if disc.get('discovery_method') == 'table_verification':
                continue
            
            # Check if discovery matches the actual clicked selector (highest priority)
            disc_final_selector = disc.get('final_selector', '').lower()
            disc_xpath = disc.get('xpath', '').lower()
            matches_clicked_selector = False
            
            if actual_clicked_selector:
                # Check if actual clicked selector matches discovery's final_selector or xpath
                if (actual_clicked_selector in disc_final_selector or 
                    disc_final_selector in actual_clicked_selector or
                    actual_clicked_selector in disc_xpath or
                    disc_xpath in actual_clicked_selector):
                    matches_clicked_selector = True
            
            # Check discovery type from final_selector or metadata
            disc_is_tab = 'tab' in disc_final_selector or 'role=\'tab\'' in disc_final_selector or '[role="tab"]' in disc_final_selector
            disc_is_accordion = 'accordion' in disc.get('name', '').lower() or 'button' in disc_final_selector and 'aria-expanded' in disc_final_selector
            disc_is_checkbox = 'checkbox' in disc_final_selector or 'input[type=\'checkbox\']' in disc_final_selector
            
            # Calculate match score
            score = 0
            
            # PRIORITY 1: Exact match on original_query
            if selector_normalized == disc_query:
                score += 100
            
            # PRIORITY 2: Match on actual clicked selector (very high priority)
            if matches_clicked_selector:
                score += 90
            
            # PRIORITY 3: Context match (tab step should match tab discovery, etc.)
            if is_tab_step and disc_is_tab:
                score += 50
            elif is_accordion_step and disc_is_accordion:
                score += 50
            elif is_checkbox_step and disc_is_checkbox:
                score += 50
            
            # PRIORITY 4: Very close match (selector is substring of discovery or vice versa)
            if len(selector_normalized) > 3 and len(disc_query) > 3:
                if selector_normalized in disc_query or disc_query in selector_normalized:
                    overlap = min(len(selector_normalized), len(disc_query))
                    total = max(len(selector_normalized), len(disc_query))
                    score += (overlap / total) * 30
            
            # Penalty for context mismatch
            if is_tab_step and disc_is_accordion:
                score -= 30  # Tab step shouldn't match accordion discovery
            elif is_accordion_step and disc_is_tab:
                score -= 30  # Accordion step shouldn't match tab discovery
            
            if score > best_score:
                best_score = score
                best_match = disc
        
        # Return best match if score is high enough
        # Lower threshold if we have a clicked selector match (more reliable)
        threshold = 50 if actual_clicked_selector else 70
        if best_match and best_score >= threshold:
            logger.info(f"  ✅ Matched Step {step_num} to discovery: {best_match.get('name')} (score={best_score:.1f})")
            return best_match
        
        return None
    
    def _generate_navigate_step(self, step_num: int, step_text: str, action: Dict, indent: int) -> str:
        """Generate navigation code"""
        ind = ' ' * indent
        url = action.get('input', {}).get('url', '')
        
        code = f"{ind}# Step {step_num}: {step_text}\n"
        code += f"{ind}page.goto('{url}')\n"
        code += f"{ind}print('📍 Step {step_num}: Navigated to {url}')\n\n"
        
        return code
    
    def _generate_wait_step(self, step_num: int, step_text: str, action: Dict, indent: int) -> str:
        """Generate wait code"""
        ind = ' ' * indent
        
        # Extract wait duration from step text
        wait_match = re.search(r'wait (\d+) seconds?', step_text, re.IGNORECASE)
        if wait_match:
            duration_sec = int(wait_match.group(1))
            duration_ms = duration_sec * 1000
        else:
            # Default to 1 second if not specified
            duration_ms = 1000
        
        code = f"{ind}# Step {step_num}: {step_text}\n"
        code += f"{ind}page.wait_for_timeout({duration_ms})\n"
        code += f"{ind}print('⏱️  Step {step_num}: Waited {duration_ms}ms')\n\n"
        
        return code
    
    def _generate_click_step(self, step_num: int, step_text: str, action: Dict, discovery: Dict, registry: Dict, indent: int, next_step_discovery: Dict = None) -> str:
        """
        Generate click code using PURE REGISTRY system - element_id only, no fallbacks
        All XPaths come from JSON registry ONLY
        """
        ind = ' ' * indent
        
        # Determine if this is an optional click (e.g., popup dismissal)
        is_optional = 'optional' in step_text.lower() or 'if there is' in step_text.lower()
        
        # Extract element name for display
        element_name = discovery.get('name', 'element') if discovery else 'element'
        
        # Get element_id from discovery (REQUIRED for pure registry system)
        element_id = discovery.get('element_id') if discovery else None
        
        # If element_id is missing, try to look it up from merged registry by name or XPath
        if not element_id and discovery:
            discovery_xpath = discovery.get('xpath', '')
            discovery_name = discovery.get('name', '')
            
            # Try to find element_id in merged registry by name first
            if discovery_name and registry:
                elements = registry.get('elements', {})
                if discovery_name in elements:
                    element_id = elements[discovery_name].get('element_id')
                    if element_id:
                        logger.info(f"  🔍 Found element_id in merged registry by name: {discovery_name} -> {element_id}")
            
            # If still not found, try by XPath (search across all merged registries)
            if not element_id and discovery_xpath and registry:
                for key, elem_data in registry.get('elements', {}).items():
                    if elem_data.get('xpath') == discovery_xpath:
                        element_id = elem_data.get('element_id')
                        if element_id:
                            logger.info(f"  🔍 Found element_id in merged registry by XPath: {key} -> {element_id}")
                            break
            
            # If still not found, try reverse lookup via id_index (in case element_id exists but discovery doesn't have it)
            if not element_id and discovery_xpath and registry:
                id_index = registry.get('id_index', {})
                # Search for element_id that points to an element with matching XPath
                for elem_id, elem_key in id_index.items():
                    elem_data = registry.get('elements', {}).get(elem_key)
                    if elem_data and elem_data.get('xpath') == discovery_xpath:
                        element_id = elem_id
                        logger.info(f"  🔍 Found element_id in merged registry via id_index reverse lookup: {elem_key} -> {element_id}")
                        break
            
            # If found, update discovery in-place (for future use)
            if element_id and discovery:
                discovery['element_id'] = element_id
                logger.info(f"  ✅ Backfilled element_id into discovery: {discovery_name} -> {element_id}")
        
        # Get selector from AI action (what AI actually used)
        action_selector = action.get('input', {}).get('selector', '') if action else ''
        
        if not element_id:
            # If no element_id, check if we can use AI's selector directly
            if is_optional and action_selector:
                # For optional elements, use selector from test-specific constants (embedded in test)
                # Extract selector from discovery to determine constant name
                discovery_selector = discovery.get('original_query', '') if discovery else ''
                if not discovery_selector:
                    discovery_selector = discovery.get('final_selector', '') if discovery else ''
                selector_to_use = discovery_selector if discovery_selector else action_selector
                
                # Escape for Python string
                selector_escaped = selector_to_use.replace("'", "\\'").replace('"', '\\"')
                
                # Find matching optional selector constant (embedded in test)
                # Use discovery name if available, otherwise use element_name
                disc_name = discovery.get('name', '') if discovery else ''
                name_for_constant = disc_name if disc_name else element_name
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name_for_constant)
                constant_name = f"OPTIONAL_{safe_name.upper()}_SELECTOR"
                
                code = f"{ind}# Step {step_num}: {step_text}\n"
                code += f"{ind}# ⚠️  No element_id found - using test-specific selector (embedded in test, not hardcoded)\n"
                code += f"{ind}# Use selector from test-specific constants (matches AI behavior)\n"
                code += f"{ind}try:\n"
                code += f"{ind}    selector = {constant_name}\n"
                code += f"{ind}except NameError:\n"
                code += f"{ind}    # Fallback if constant not defined\n"
                code += f"{ind}    selector = '{selector_escaped}'\n"
                code += f"{ind}\n"
                code += f"{ind}try:\n"
                code += f"{ind}    element = page.locator(selector).nth(0)\n"
                code += f"{ind}    if element.is_visible(timeout=10000):\n"
                code += f"{ind}        element.click()\n"
                code += f"{ind}        page.wait_for_timeout(1000)  # Wait after click (matches AI behavior)\n"
                code += f"{ind}        # Wait for dialog to disappear (if popup was dismissed)\n"
                code += f"{ind}        try:\n"
                code += f"{ind}            # Wait for dialog to be detached (completely removed from DOM) - most reliable\n"
                code += f"{ind}            page.locator('[data-testid=\"system-use-warning-dialog\"]').wait_for(state='detached', timeout=3000)\n"
                code += f"{ind}        except:\n"
                code += f"{ind}            # Fallback: dialog might stay in DOM but hidden\n"
                code += f"{ind}            try:\n"
                code += f"{ind}                page.locator('[data-testid=\"system-use-warning-dialog\"]').wait_for(state='hidden', timeout=2000)\n"
                code += f"{ind}            except:\n"
                code += f"{ind}                pass  # Dialog may not exist or already dismissed\n"
                code += f"{ind}        \n"
                code += f"{ind}        # Wait for next step's element to be clickable (if available)\n"
                if next_step_discovery and next_step_discovery.get('element_id'):
                    next_element_id = next_step_discovery.get('element_id')
                    code += f"{ind}        try:\n"
                    code += f"{ind}            next_element_id = '{next_element_id}'\n"
                    code += f"{ind}            next_xpath = get_xpath_by_id(next_element_id)\n"
                    code += f"{ind}            next_element = page.locator(f'xpath={{next_xpath}}').nth(0)\n"
                    code += f"{ind}            next_element.wait_for(state='visible', timeout=5000)\n"
                    code += f"{ind}            # Wait for dialog to not be blocking\n"
                    code += f"{ind}            for attempt in range(15):\n"
                    code += f"{ind}                dialog_blocking = page.locator('[data-testid=\"system-use-warning-dialog\"]').count() > 0\n"
                    code += f"{ind}                if not dialog_blocking:\n"
                    code += f"{ind}                    break\n"
                    code += f"{ind}                try:\n"
                    code += f"{ind}                    dialog_visible = page.locator('[data-testid=\"system-use-warning-dialog\"]').first.is_visible(timeout=100)\n"
                    code += f"{ind}                    if not dialog_visible:\n"
                    code += f"{ind}                        break\n"
                    code += f"{ind}                except:\n"
                    code += f"{ind}                    break\n"
                    code += f"{ind}                page.wait_for_timeout(200)\n"
                    code += f"{ind}        except:\n"
                    code += f"{ind}            pass\n"
                else:
                    code += f"{ind}        page.wait_for_timeout(500)  # Wait for animations\n"
                code += f"{ind}        print(f'✅ Step {step_num}: Clicked (using selector from discovery: {{selector}})')\n"
                code += f"{ind}        page.screenshot(path='storage/screenshots/pw_step{step_num}_{re.sub(r'[^a-zA-Z0-9_-]', '_', element_name)[:50]}.png')\n"
                code += f"{ind}    else:\n"
                code += f"{ind}        print(f'ℹ️  Step {step_num}: {element_name} not found (optional)')\n"
                code += f"{ind}except Exception as e:\n"
                code += f"{ind}    print(f'ℹ️  Step {step_num}: {element_name} not found (optional): {{e}}')\n\n"
                return code
            elif is_optional:
                # Optional but no selector - skip
                code = f"{ind}# Step {step_num}: {step_text}\n"
                code += f"{ind}# ⚠️  No element_id and no selector found - skipping optional element\n"
                code += f"{ind}print('ℹ️  Step {step_num}: {element_name} not found in registry (optional)')\n\n"
                return code
            else:
                raise Exception(f"❌ Step {step_num}: Discovery missing element_id for '{element_name}' - cannot generate Playwright step. Registry must be complete.")
        
        # Sanitize for screenshot filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', element_name)[:50]
        screenshot_path = f"storage/screenshots/pw_step{step_num}_{safe_name}.png"
        
        # Detect element type from step text
        is_checkbox = 'checkbox' in step_text.lower()
        is_accordion = 'accordion' in step_text.lower() or 'expand' in step_text.lower()
        is_nested_accordion = discovery and discovery.get('metadata', {}).get('nested', False) if discovery else False
        
        # Escape element_id for Python string
        element_id_escaped = element_id.replace("'", "\\'")
        
        # Generate pure registry code
        code = f"{ind}# Step {step_num}: {step_text}\n"
        code += f"{ind}# Using element_id: {element_id} (PURE REGISTRY - XPath from JSON ONLY)\n"
        code += f"{ind}element_id = '{element_id_escaped}'\n"
        code += f"{ind}xpath = get_xpath_by_id(element_id)  # Lookup from JSON registry ONLY\n"
        code += f"{ind}selector = f'xpath={{xpath}}'\n"
        code += f"{ind}\n"
        code += f"{ind}try:\n"
        code += f"{ind}    element = page.locator(selector).nth(0)\n"
        
        if is_checkbox:
            code += f"{ind}    # Checkbox: Wait for attached, then scroll into view\n"
            code += f"{ind}    element.wait_for(state='attached', timeout=10000)\n"
            code += f"{ind}    element.scroll_into_view_if_needed()\n"
            code += f"{ind}    page.wait_for_timeout(500)\n"
            code += f"{ind}    # Check if checkbox is already checked\n"
            code += f"{ind}    is_checked = element.is_checked()\n"
            code += f"{ind}    if is_checked:\n"
            code += f"{ind}        print(f'ℹ️  Checkbox already checked, skipping')\n"
            code += f"{ind}    else:\n"
            code += f"{ind}        element.click(force=True)\n"
            code += f"{ind}        page.wait_for_timeout(1000)\n"
            code += f"{ind}        if element.is_checked():\n"
            code += f"{ind}            print(f'✅ Step {step_num}: Checkbox checked (element_id: {{element_id}})')\n"
            code += f"{ind}        else:\n"
            code += f"{ind}            raise Exception(f'Checkbox click did not change state')\n"
            code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
        elif is_accordion:
            code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
            if is_nested_accordion:
                code += f"{ind}    # Nested accordion: always click\n"
                code += f"{ind}    element.click()\n"
                code += f"{ind}    page.wait_for_timeout(1000)\n"
                code += f"{ind}    print(f'✅ Step {step_num}: Clicked nested accordion (element_id: {{element_id}})')\n"
            else:
                code += f"{ind}    # Top-level accordion: check state\n"
                code += f"{ind}    initial_aria_expanded = element.get_attribute('aria-expanded')\n"
                code += f"{ind}    if initial_aria_expanded == 'true':\n"
                code += f"{ind}        print(f'ℹ️  Accordion already expanded, skipping click')\n"
                code += f"{ind}        page.wait_for_timeout(1000)\n"
                code += f"{ind}    else:\n"
                code += f"{ind}        element.click()\n"
                code += f"{ind}        page.wait_for_timeout(500)\n"
                code += f"{ind}        current_aria_expanded = element.get_attribute('aria-expanded')\n"
                code += f"{ind}        if current_aria_expanded == 'true':\n"
                code += f"{ind}            print(f'✅ Step {step_num}: Accordion expanded: {{initial_aria_expanded}} → {{current_aria_expanded}}')\n"
                code += f"{ind}        page.wait_for_timeout(1000)\n"
            code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
        else:
            # Detect if this is a popup dismissal button (Continue, OK, Accept, etc.)
            is_popup_dismissal = any(keyword in step_text.lower() or keyword in element_name.lower() 
                                    for keyword in ['continue', 'ok', 'accept', 'dismiss', 'close', 'got it'])
            
            code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
            code += f"{ind}    element.click()\n"
            code += f"{ind}    page.wait_for_timeout(1000)  # Wait after click (matches AI behavior)\n"
            
            # If popup dismissal button, wait for dialog to disappear and next element to be clickable
            if is_popup_dismissal:
                code += f"{ind}    # Wait for dialog to disappear after popup dismissal\n"
                code += f"{ind}    try:\n"
                code += f"{ind}        # Wait for dialog to be detached (completely removed from DOM) - most reliable\n"
                code += f"{ind}        page.locator('[data-testid=\"system-use-warning-dialog\"]').wait_for(state='detached', timeout=3000)\n"
                code += f"{ind}    except:\n"
                code += f"{ind}        # Fallback: dialog might stay in DOM but hidden\n"
                code += f"{ind}        try:\n"
                code += f"{ind}            page.locator('[data-testid=\"system-use-warning-dialog\"]').wait_for(state='hidden', timeout=2000)\n"
                code += f"{ind}        except:\n"
                code += f"{ind}            pass  # Dialog may not exist or already dismissed\n"
                code += f"{ind}    \n"
                code += f"{ind}    # Wait for next step's element to be clickable (not blocked by overlay)\n"
                code += f"{ind}    # This ensures the page is ready for the next action\n"
                if next_step_discovery and next_step_discovery.get('element_id'):
                    next_element_id = next_step_discovery.get('element_id')
                    code += f"{ind}    try:\n"
                    code += f"{ind}        # Wait for next element to be visible and not blocked\n"
                    code += f"{ind}        next_element_id = '{next_element_id}'\n"
                    code += f"{ind}        next_xpath = get_xpath_by_id(next_element_id)\n"
                    code += f"{ind}        next_element = page.locator(f'xpath={{next_xpath}}').nth(0)\n"
                    code += f"{ind}        # Wait for element to be visible\n"
                    code += f"{ind}        next_element.wait_for(state='visible', timeout=5000)\n"
                    code += f"{ind}        # Wait for dialog to not be blocking (check if dialog is gone or not intercepting)\n"
                    code += f"{ind}        for attempt in range(15):  # Try for up to 3 seconds\n"
                    code += f"{ind}            dialog_blocking = page.locator('[data-testid=\"system-use-warning-dialog\"]').count() > 0\n"
                    code += f"{ind}            if not dialog_blocking:\n"
                    code += f"{ind}                break  # Dialog is gone\n"
                    code += f"{ind}            # Check if dialog is still visible/blocking\n"
                    code += f"{ind}            try:\n"
                    code += f"{ind}                dialog_visible = page.locator('[data-testid=\"system-use-warning-dialog\"]').first.is_visible(timeout=100)\n"
                    code += f"{ind}                if not dialog_visible:\n"
                    code += f"{ind}                    break  # Dialog exists but not visible\n"
                    code += f"{ind}            except:\n"
                    code += f"{ind}                break  # Dialog check failed, assume it's gone\n"
                    code += f"{ind}            page.wait_for_timeout(200)  # Wait 200ms before retry\n"
                    code += f"{ind}    except:\n"
                    code += f"{ind}        # Next element not found or not ready - wait for animations\n"
                    code += f"{ind}        page.wait_for_timeout(500)\n"
                else:
                    code += f"{ind}    # No next step element available - wait for animations to complete\n"
                    code += f"{ind}    page.wait_for_timeout(500)  # Extra wait for dialog dismissal animations\n"
            
            code += f"{ind}    print(f'✅ Step {step_num}: Clicked {element_name} (element_id: {{element_id}})')\n"
            code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
        
        code += f"{ind}except Exception as e:\n"
        if is_optional:
            code += f"{ind}    print(f'ℹ️  Step {step_num}: {element_name} not found (optional): {{e}}')\n"
        else:
            code += f"{ind}    print(f'❌ Step {step_num}: Failed to click {element_name} (element_id: {{element_id}}): {{e}}')\n"
            code += f"{ind}    raise\n"
        code += f"{ind}\n"
        
        return code
    
    def _generate_fill_step(self, step_num: int, step_text: str, action: Dict, discovery: Dict, registry: Dict, indent: int) -> str:
        """
        Generate fill code for input fields (username, password, TOTP, etc.)
        """
        ind = ' ' * indent
        
        # Get input parameters from action
        input_params = action.get('input', {}) if action else {}
        selector = input_params.get('selector', '')
        text = input_params.get('text', '')
        
        # Extract field name from step text (e.g., "Enter Username" -> "Username")
        field_name = 'field'
        if 'username' in step_text.lower() or 'email' in step_text.lower():
            field_name = 'Username'
        elif 'password' in step_text.lower():
            field_name = 'Password'
        elif 'totp' in step_text.lower() or 'one-time' in step_text.lower() or 'authenticator' in step_text.lower():
            field_name = 'TOTP'
        else:
            # Try to extract from step text
            match = re.search(r'enter\s+(?:the\s+)?(.+?)\s+as', step_text, re.IGNORECASE)
            if match:
                field_name = match.group(1).strip()
        
        # Escape text for Python string
        text_escaped = text.replace("'", "\\'").replace('"', '\\"')
        
        # Check if this is a TOTP step
        is_totp_step = any(keyword in step_text.lower() for keyword in ['totp', 'one-time', 'one time', '2fa', 'two-factor', 'authenticator code', 'security code'])
        
        # Generate code
        code = f"{ind}# Step {step_num}: {step_text}\n"
        
        if is_totp_step:
            code += f"{ind}# TOTP step - generate code dynamically\n"
            code += f"{ind}import sys\n"
            code += f"{ind}from pathlib import Path\n"
            code += f"{ind}# Add project root to path for utils import\n"
            code += f"{ind}project_root = Path(__file__).parent.parent.parent\n"
            code += f"{ind}if str(project_root) not in sys.path:\n"
            code += f"{ind}    sys.path.insert(0, str(project_root))\n"
            code += f"{ind}from utils.otp_helper import generate_otp\n"
            code += f"{ind}import os\n"
            code += f"{ind}try:\n"
            code += f"{ind}    totp_code = generate_otp()  # Uses TOTP_SECRET_KEY from environment\n"
            code += f"{ind}    print(f'🔐 Step {step_num}: Generated TOTP code: {{totp_code[:2]}}****')\n"
            code += f"{ind}except Exception as e:\n"
            code += f"{ind}    raise Exception(f'Failed to generate TOTP code: {{e}}')\n"
            code += f"{ind}fill_text = totp_code\n"
        else:
            code += f"{ind}fill_text = '{text_escaped}'\n"
        
        # Use selector from action (what AI actually used)
        selector_escaped = selector.replace("'", "\\'").replace('"', '\\"')
        
        code += f"{ind}selector = '{selector_escaped}'\n"
        code += f"{ind}\n"
        code += f"{ind}try:\n"
        code += f"{ind}    element = page.locator(selector).nth(0)\n"
        code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
        
        # For TOTP fields, try multiple selectors if the first one fails
        if is_totp_step:
            code += f"{ind}    # TOTP field - try multiple selectors if needed\n"
            code += f"{ind}    if selector == \"input[name='code']\" or 'input[name=\"code\"]' in selector:\n"
            code += f"{ind}        totp_selectors = [\n"
            code += f"{ind}            \"input.one-time-code-input__input\",\n"
            code += f"{ind}            \"input[autocomplete='one-time-code']\",\n"
            code += f"{ind}            \"input[type='text'][name='code']\",\n"
            code += f"{ind}            \"input[name='code']:not([type='hidden'])\",\n"
            code += f"{ind}            \"lg-one-time-code-input input[type='text']\",\n"
            code += f"{ind}        ]\n"
            code += f"{ind}        selector_found = False\n"
            code += f"{ind}        for totp_sel in totp_selectors:\n"
            code += f"{ind}            try:\n"
            code += f"{ind}                test_elem = page.locator(totp_sel).first\n"
            code += f"{ind}                if test_elem.is_visible(timeout=1000):\n"
            code += f"{ind}                    selector = totp_sel\n"
            code += f"{ind}                    element = test_elem\n"
            code += f"{ind}                    selector_found = True\n"
            code += f"{ind}                    break\n"
            code += f"{ind}            except:\n"
            code += f"{ind}                continue\n"
            code += f"{ind}        if not selector_found:\n"
            code += f"{ind}            element = page.locator(selector).nth(0)\n"
        
        code += f"{ind}    \n"
        code += f"{ind}    # Check if field is readonly/disabled\n"
        code += f"{ind}    is_readonly = element.evaluate('el => el.readOnly || el.disabled')\n"
        code += f"{ind}    if is_readonly:\n"
        code += f"{ind}        raise Exception(f'Field {{selector}} is readonly or disabled')\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Fill the field\n"
        code += f"{ind}    element.fill(fill_text)\n"
        code += f"{ind}    page.wait_for_timeout(500)  # Wait after fill (matches AI behavior)\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Verify the value was filled correctly\n"
        code += f"{ind}    actual_value = element.input_value()\n"
        code += f"{ind}    if actual_value == fill_text:\n"
        code += f"{ind}        print(f'✅ Step {step_num}: Filled {field_name} (verified)')\n"
        code += f"{ind}    else:\n"
        code += f"{ind}        print(f'⚠️  Step {step_num}: Fill mismatch - expected {{fill_text[:20]}}..., got {{actual_value[:20]}}...')\n"
        
        # Sanitize field name for screenshot filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', field_name)[:50]
        screenshot_path = f"storage/screenshots/pw_step{step_num}_{safe_name}.png"
        code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    print(f'❌ Step {step_num}: Failed to fill {field_name}: {{e}}')\n"
        code += f"{ind}    raise\n"
        code += f"{ind}\n"
        
        return code
    
    def _generate_verify_step(self, step_num: int, step_text: str, action: Dict, discovery: Dict, indent: int) -> str:
        """Generate verification code"""
        ind = ' ' * indent
        
        if not discovery or discovery.get('discovery_method') != 'table_verification':
            # Generic verification
            code = f"{ind}# Step {step_num}: {step_text}\n"
            code += f"{ind}print('⚠️  Step {step_num}: Verification performed by AI - add specific assertions if needed')\n\n"
            return code
        
        # Table column verification
        metadata = discovery.get('metadata', {})
        column_name = metadata.get('column_name', 'unknown')
        expected_value = metadata.get('expected_value', '')
        
        # Escape for Python string literals
        column_name_escaped = column_name.replace("'", "\\'").replace('"', '\\"')
        expected_value_escaped = expected_value.replace("'", "\\'").replace('"', '\\"')
        
        code = f"{ind}# Step {step_num}: {step_text}\n"
        code += f"{ind}# Verify: All rows in column contain expected value (values from test-specific constants - NO HARDCODING)\n"
        code += f"{ind}# Use verification values embedded in test (test-specific, not in registry)\n"
        code += f"{ind}column_name = VERIFY_COLUMN_NAME\n"
        code += f"{ind}expected_value = VERIFY_EXPECTED_VALUE\n"
        code += f"{ind}if not column_name or not expected_value:\n"
        code += f"{ind}    raise Exception('❌ Verification values missing: VERIFY_COLUMN_NAME or VERIFY_EXPECTED_VALUE not defined')\n"
        code += f"{ind}\n"
        code += f"{ind}try:\n"
        code += f"{ind}    print(f'🔍 Step {step_num}: Verifying table column \"{{column_name}}\" contains \"{{expected_value}}\"...')\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Find table\n"
        code += f"{ind}    table = page.locator('table').nth(0)\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Find column index by header text\n"
        code += f"{ind}    headers = table.locator('thead th, thead td').all_text_contents()\n"
        code += f"{ind}    column_index = -1\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Try exact match (case-insensitive)\n"
        code += f"{ind}    for i, header in enumerate(headers):\n"
        code += f"{ind}        if column_name.lower() == header.lower().strip():\n"
        code += f"{ind}            column_index = i\n"
        code += f"{ind}            break\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Fallback: partial match\n"
        code += f"{ind}    if column_index == -1:\n"
        code += f"{ind}        for i, header in enumerate(headers):\n"
        code += f"{ind}            if column_name.lower() in header.lower():\n"
        code += f"{ind}                column_index = i\n"
        code += f"{ind}                break\n"
        code += f"{ind}    \n"
        code += f"{ind}    if column_index == -1:\n"
        code += f"{ind}        raise Exception(f\"Column '{{column_name}}' not found. Available: {{headers}}\")\n"
        code += f"{ind}    \n"
        code += f"{ind}    print(f'📋 Step {step_num}: Found column \"{{column_name}}\" at index {{column_index}}')\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Verify all rows\n"
        code += f"{ind}    rows = table.locator('tbody tr').all()\n"
        code += f"{ind}    total_rows = len(rows)\n"
        code += f"{ind}    matching_rows = 0\n"
        code += f"{ind}    \n"
        code += f"{ind}    print(f'🔍 Step {step_num}: Checking {{total_rows}} rows...')\n"
        code += f"{ind}    \n"
        code += f"{ind}    for row_idx, row in enumerate(rows):\n"
        code += f"{ind}        cells = row.locator('td').all()\n"
        code += f"{ind}        if column_index < len(cells):\n"
        code += f"{ind}            cell_text = cells[column_index].inner_text().strip()\n"
        code += f"{ind}            if expected_value.lower() in cell_text.lower():\n"
        code += f"{ind}                matching_rows += 1\n"
        code += f"{ind}            else:\n"
        code += f"{ind}                print(f'⚠️  Row {{row_idx + 1}}: Expected \"{{expected_value}}\", got \"{{cell_text}}\"')\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Assert all rows match\n"
        code += f"{ind}    assert matching_rows == total_rows, f\"Only {{matching_rows}}/{{total_rows}} rows match\"\n"
        code += f"{ind}    \n"
        code += f"{ind}    print(f'✅ Step {step_num}: VERIFICATION PASSED: All {{total_rows}} rows contain \"{{expected_value}}\"')\n"
        code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_verify.png')\n"
        code += f"{ind}    print('📸 Screenshot: storage/screenshots/pw_step{step_num}_verify.png')\n"
        code += f"{ind}    \n"
        code += f"{ind}except Exception as e:\n"
        code += f"{ind}    print(f'❌ Step {step_num}: VERIFICATION FAILED: {{e}}')\n"
        code += f"{ind}    page.screenshot(path='storage/screenshots/pw_step{step_num}_verify_failed.png')\n"
        code += f"{ind}    raise\n\n"
        
        return code
    
    def _generate_hybrid_code(self, infrastructure: Dict, discoveries: List[Dict], registry: Dict, indent: int = 12) -> str:
        """
        DEPRECATED: Old hybrid approach that processed discoveries and waits separately
        Kept for backward compatibility only - use _generate_sequential_code instead
        """
        ind = ' ' * indent
        code = ''
        
        # 1. Navigation (always first)
        if infrastructure['navigation']:
            code += f"{ind}# Navigate to page\n"
            code += f"{ind}page.goto('{infrastructure['navigation']}')\n"
            code += f"{ind}print('📍 Navigated to {infrastructure['navigation']}')\n\n"
        
        # 2. Initial waits (before first discovery)
        first_discovery_time = discoveries[0].get('timestamp', '') if discoveries else None
        for wait in infrastructure['waits']:
            # Add waits that appear early in story (before discoveries)
            if not first_discovery_time or wait.get('position', 0) < 1000:  # Rough heuristic
                code += f"{ind}# Wait for page load\n"
                code += f"{ind}page.wait_for_timeout({wait['duration']})\n\n"
                break  # Only add first wait here
        
        # 3. Optional steps (conditional popups, etc.)
        for optional in infrastructure['optionals']:
            code += self._generate_optional_click_code(optional, discoveries, registry, indent)
        
        # 4. Discoveries (actual interactions) in timestamp order
        for i, discovery in enumerate(discoveries):
            method = discovery.get('discovery_method', 'unknown')
            
            if method == 'table_verification':
                # Generate verification code
                code += self._generate_verify_from_discovery(discovery, indent)
            else:
                # Generate click/interaction code
                code += self._generate_click_from_discovery(discovery, registry, indent)
            
            # Add waits between discoveries if specified in story
            # (Look for waits that appear after this discovery but before next)
            # For now, simplified: add any remaining waits after last discovery
            if i == len(discoveries) - 1:
                for wait in infrastructure['waits'][1:]:  # Skip first wait already added
                    code += f"{ind}# Wait\n"
                    code += f"{ind}page.wait_for_timeout({wait['duration']})\n\n"
        
        return code
    
    def _generate_optional_click_code(self, optional: Dict, discoveries: List[Dict], registry: Dict, indent: int) -> str:
        """Generate optional click code (for popups, etc.)"""
        ind = ' ' * indent
        element = optional['element']
        context = optional.get('context', 'element')
        
        # Try to find in discoveries first
        discovery = self._find_discovery(element, discoveries)
        if discovery:
            # Use XPath if available
            xpath = discovery.get('xpath')
            if xpath:
                selector = f"xpath={xpath}"
            else:
                selector = discovery.get('final_selector', f"text={element}")
                selector = self._clean_selector(selector)  # Clean state-dependent attributes
        else:
            selector = f"text={element}"
        
        selector_escaped = selector.replace("'", "\\'")
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', element)[:50]
        
        code = f"{ind}# Optional: {element} ({context} - may not be present)\n"
        code += f"{ind}try:\n"
        code += f"{ind}    element = page.locator('{selector_escaped}').nth(0)\n"
        code += f"{ind}    if element.is_visible(timeout=2000):\n"
        code += f"{ind}        element.click()\n"
        code += f"{ind}        page.wait_for_timeout(500)\n"
        code += f"{ind}        print('✅ Clicked: {element} ({context})')\n"
        code += f"{ind}        page.screenshot(path='storage/screenshots/pw_{safe_name}.png')\n"
        code += f"{ind}    else:\n"
        code += f"{ind}        print('ℹ️  {element} not visible (optional)')\n"
        code += f"{ind}except Exception:\n"
        code += f"{ind}    print('ℹ️  {element} not found (optional)')\n\n"
        
        return code
    
    def _generate_click_from_discovery(self, discovery: Dict, registry: Dict, indent: int) -> str:
        """Generate click code directly from discovery metadata - Use what AI actually used"""
        ind = ' ' * indent
        
        name = discovery.get('name', 'unknown')
        
        # PRIORITY 1: Use what AI actually used (original_query)
        # This is the EXACT selector the AI agent successfully used
        original_query = discovery.get('original_query', '').strip()
        if original_query and not original_query.startswith('verify'):
            selector = original_query
            logger.info(f"✅ Using AI's selector for {name}: {selector}")
            uniqueness_method = 'ai_original'
        # PRIORITY 2: Use final_selector (cleaned selector AI used)
        elif discovery.get('final_selector'):
            selector = discovery.get('final_selector')
            selector = self._clean_selector(selector)  # Clean state-dependent attributes
            logger.info(f"✅ Using AI's final selector for {name}: {selector}")
            uniqueness_method = 'ai_final'
        # PRIORITY 3: Last resort - XPath (strip dynamic content like counts)
        elif discovery.get('xpath'):
            xpath = discovery.get('xpath')
            selector = f"xpath={self._strip_dynamic_xpath(xpath)}"
            logger.info(f"⚠️ Using XPath (dynamic content stripped) for {name}: {selector}")
            uniqueness_method = 'xpath_fallback'
        else:
            # Ultimate fallback
            selector = f"text={name}"
            logger.info(f"⚠️ No selector found, using text fallback for {name}: {selector}")
            uniqueness_method = None
        
        method = discovery.get('discovery_method', 'unknown')
        metadata = discovery.get('metadata', {})
        
        # Check registry for additional metadata
        registry_entry = registry.get(discovery.get('original_query', ''), {})
        element_type = registry_entry.get('type', 'element')
        
        selector_escaped = selector.replace("'", "\\'")
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:50]
        screenshot_path = f"storage/screenshots/pw_{safe_name}.png"
        
        code = f"{ind}# Click: {name}\n"
        
        # Add source note
        if uniqueness_method == 'ai_original':
            code += f"{ind}# Selector: AI's original query (exact match to AI execution)\n"
        elif uniqueness_method == 'ai_final':
            code += f"{ind}# Selector: AI's final selector (cleaned)\n"
        elif uniqueness_method == 'xpath_fallback':
            code += f"{ind}# Selector: XPath with dynamic content stripped\n"
        elif registry_entry:
            code += f"{ind}# Selector from registry (optimized)\n"
        elif method == 'tree_climbing':
            code += f"{ind}# AI Note: Found via tree climbing\n"
        
        # For tree_climbing elements, use force click (may be hidden but clickable)
        if method == 'tree_climbing':
            code += f"{ind}try:\n"
            code += f"{ind}    # Strategy 1: Try direct click (force=True for tree-climbed elements)\n"
            code += f"{ind}    element = page.locator('{selector_escaped}').nth(0)\n"
            code += f"{ind}    element.scroll_into_view_if_needed()\n"
            code += f"{ind}    element.click(force=True)  # Force click as AI discovered via tree climbing\n"
            code += f"{ind}    page.wait_for_timeout(1000)  # Wait for UI update\n"
            code += f"{ind}    print('✅ Clicked: {name}')\n"
            code += f"{ind}    # Capture screenshot after click\n"
            code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
            code += f"{ind}    print('📸 Screenshot: {screenshot_path}')\n"
            code += f"{ind}except Exception as e:\n"
            
            if metadata.get('relationship') == 'parent':
                code += f"{ind}    # Fallback: Try clicking parent element\n"
                code += f"{ind}    try:\n"
                code += f"{ind}        print(f'⚠️  Direct click failed, trying parent element...')\n"
                code += f"{ind}        parent = page.locator('{selector_escaped}').nth(0).locator('xpath=..')\n"
                code += f"{ind}        parent.scroll_into_view_if_needed()\n"
                code += f"{ind}        parent.click(force=True)\n"
                code += f"{ind}        page.wait_for_timeout(1000)\n"
                code += f"{ind}        print('✅ Clicked parent element: {name}')\n"
                code += f"{ind}        page.screenshot(path='{screenshot_path}')\n"
                code += f"{ind}    except Exception as e2:\n"
                code += f"{ind}        print(f'❌ Both strategies failed for {name}')\n"
                code += f"{ind}        raise e2\n"
            else:
                code += f"{ind}    print(f'❌ Failed to click {name}: {{e}}')\n"
                code += f"{ind}    raise\n"
        else:
            # For non-tree-climbing elements, use standard wait for visible
            code += f"{ind}try:\n"
            code += f"{ind}    # Strategy 1: Try direct click on element\n"
            code += f"{ind}    element = page.locator('{selector_escaped}').nth(0)\n"
            code += f"{ind}    element.wait_for(state='visible', timeout=10000)\n"
            code += f"{ind}    element.click()\n"
            code += f"{ind}    page.wait_for_timeout(1000)  # Wait for UI update\n"
            code += f"{ind}    print('✅ Clicked: {name}')\n"
            code += f"{ind}    # Capture screenshot after click\n"
            code += f"{ind}    page.screenshot(path='{screenshot_path}')\n"
            code += f"{ind}    print('📸 Screenshot: {screenshot_path}')\n"
            code += f"{ind}except Exception as e:\n"
            code += f"{ind}    print(f'❌ Failed to click {name}: {{e}}')\n"
            code += f"{ind}    raise\n"
        
        code += f"\n"
        return code
    
    def _generate_verify_from_discovery(self, discovery: Dict, indent: int) -> str:
        """Generate verification code from discovery metadata"""
        ind = ' ' * indent
        metadata = discovery.get('metadata', {})
        
        if metadata.get('verification_type') == 'table_column':
            column_name = metadata.get('column_name', 'unknown')
            expected_value = metadata.get('expected_value', '')
            
            code = f"{ind}# Verify: All rows in '{column_name}' column contain '{expected_value}'\n"
            code += f"{ind}try:\n"
            code += f"{ind}    print('🔍 Verifying table column...')\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Find table\n"
            code += f"{ind}    table = page.locator('table').nth(0)\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Find column index by header text (exact match first, then partial)\n"
            code += f"{ind}    headers = table.locator('thead th, thead td').all_text_contents()\n"
            code += f"{ind}    column_index = -1\n"
            code += f"{ind}    \n"
            code += f"{ind}    # First try exact match (case-insensitive)\n"
            code += f"{ind}    for i, header in enumerate(headers):\n"
            code += f"{ind}        if '{column_name}'.lower() == header.lower().strip():\n"
            code += f"{ind}            column_index = i\n"
            code += f"{ind}            break\n"
            code += f"{ind}    \n"
            code += f"{ind}    # If no exact match, try partial match\n"
            code += f"{ind}    if column_index == -1:\n"
            code += f"{ind}        for i, header in enumerate(headers):\n"
            code += f"{ind}            if '{column_name}'.lower() in header.lower():\n"
            code += f"{ind}                column_index = i\n"
            code += f"{ind}                break\n"
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
        
        # Generic verification fallback
        code = f"{ind}# Verify: {discovery.get('name', 'unknown')}\n"
        code += f"{ind}print('⚠️  Verification performed by AI - add specific assertions if needed')\n\n"
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
                # Use XPath if available
                xpath = discovery.get('xpath')
                if xpath:
                    selector = f"xpath={xpath}"
                    uniqueness_method = discovery.get('uniqueness_method', 'unknown')
                    code += f"{ind}# XPath: Unique via {uniqueness_method}\n"
                else:
                    selector = discovery.get('final_selector', f"text={element}")
                    selector = self._clean_selector(selector)  # Clean state-dependent attributes
                
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
            table_selector = self._clean_selector(table_selector)  # Clean state-dependent attributes
            # Convert 'visible_table' to 'table' for Playwright
            if table_selector == 'visible_table':
                table_selector = 'table'
            
            code = f"{ind}# Verify: All rows in '{column_name}' column contain '{expected_value}'\n"
            code += f"{ind}try:\n"
            code += f"{ind}    print('🔍 Verifying table column...')\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Find table\n"
            code += f"{ind}    table = page.locator('{table_selector}').nth(0)\n"
            code += f"{ind}    \n"
            code += f"{ind}    # Find column index by header text (exact match first, then partial)\n"
            code += f"{ind}    headers = table.locator('thead th, thead td').all_text_contents()\n"
            code += f"{ind}    column_index = -1\n"
            code += f"{ind}    \n"
            code += f"{ind}    # First try exact match (case-insensitive)\n"
            code += f"{ind}    for i, header in enumerate(headers):\n"
            code += f"{ind}        if '{column_name}'.lower() == header.lower().strip():\n"
            code += f"{ind}            column_index = i\n"
            code += f"{ind}            break\n"
            code += f"{ind}    \n"
            code += f"{ind}    # If no exact match, try partial match\n"
            code += f"{ind}    if column_index == -1:\n"
            code += f"{ind}        for i, header in enumerate(headers):\n"
            code += f"{ind}            if '{column_name}'.lower() in header.lower():\n"
            code += f"{ind}                column_index = i\n"
            code += f"{ind}                break\n"
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
        """Get optimized selector from registry (legacy method - returns selector only)"""
        selector, _ = self._get_selector_and_key_from_registry(element_name, registry)
        return selector
    
    def _get_selector_and_key_from_registry(self, element_name: str, registry: Dict) -> tuple:
        """Get optimized selector AND registry key from registry"""
        if not registry:
            return (None, None)
        
        element_lower = element_name.lower().strip()
        
        # Try exact match first
        for key, value in registry.items():
            key_lower = key.lower()
            # Strip common prefixes like "text=" for better matching
            key_clean = key_lower.replace('text=', '').replace('selector=', '').strip()
            
            # Check if element matches registry key (bidirectional)
            if (element_lower in key_clean or key_clean in element_lower or
                # Also try matching with normalized whitespace
                element_lower.replace(' ', '') == key_clean.replace(' ', '')):
                # Return the optimized selector AND the exact registry key
                selector = None
                if isinstance(value, dict):
                    # Prefer XPath if available
                    if 'xpath' in value:
                        selector = f"xpath={value['xpath']}"
                    elif 'selector' in value:
                        selector = value['selector']
                    elif 'query' in value:
                        selector = value['query']
                
                if selector:
                    return (selector, key)  # Return both selector and exact registry key
        
        return (None, None)
    
    def _find_discovery(self, element_name: str, discoveries: List[Dict]) -> Dict:
        """Find discovery metadata for an element"""
        element_lower = element_name.lower().strip()
        
        for disc in discoveries:
            disc_name = disc.get('name', '').lower()
            orig_query = disc.get('original_query', '').lower().replace('text=', '').replace('selector=', '').strip()
            
            # Check if discovery name/query is IN the element name (not the other way around)
            if (disc_name in element_lower or orig_query in element_lower or
                # Also try normalized whitespace matching
                disc_name.replace(' ', '') == element_lower.replace(' ', '')):
                return disc
        
        return None
    
    def _strip_dynamic_xpath(self, xpath: str) -> str:
        """
        Strip dynamic content from XPath that changes between runs
        Examples:
          - 'Diagnosis(97)' -> 'Diagnosis'
          - 'normalize-space(.)="Count: 123"' -> remove exact match, use contains
        """
        if not xpath:
            return xpath
        
        # Strip counts in parentheses: Diagnosis(97) -> Diagnosis
        # Pattern: text followed by (number) or (number,number)
        xpath = re.sub(r'\([\d,]+\)', '', xpath)
        
        # Convert exact text matches to contains (more flexible)
        # From: normalize-space(.)='Diagnosis(97)'
        # To:   contains(normalize-space(.), 'Diagnosis')
        if "normalize-space(.)" in xpath and "=" in xpath:
            # Extract the text being matched
            if match := re.search(r"normalize-space\(\.\)\s*=\s*['\"]([^'\"]+)['\"]", xpath):
                text = match.group(1)
                # Remove counts from text
                text_clean = re.sub(r'\s*\([\d,]+\)\s*', '', text).strip()
                # Replace with contains
                xpath = re.sub(
                    r"normalize-space\(\.\)\s*=\s*['\"][^'\"]+['\"]",
                    f"contains(normalize-space(.), '{text_clean}')",
                    xpath
                )
        
        return xpath


# Example usage
if __name__ == '__main__':
    generator = PlaywrightGenerator()
    result = generator.generate('exec_172351d5')
    print(f"Generated: {result['filename']}")
    print(f"Path: {result['filepath']}")

