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
        
        # Load registry for the domain
        # Extract URL from story if story_url not present
        story_url = execution.get('story_url', '')
        if not story_url:
            # Try to extract URL from story
            import re
            if match := re.search(r'https?://[^\s]+', execution.get('story', '')):
                story_url = match.group(0)
        
        registry = self._load_registry(story_url)
        
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
    
    def _get_registry_path(self, url: str) -> str:
        """Get relative path to registry file for use in generated test"""
        if not url:
            # Default to main registry
            return 'element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json'
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Look for registry file (try home_page.json or explore_page.json)
        domain_dir = self.element_maps_dir / domain
        if not domain_dir.exists():
            # Fallback to default
            return 'element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json'
        
        # Try common page names
        for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
            registry_file = domain_dir / page_name
            if registry_file.exists():
                # Return relative path from project root
                return f'element_maps/{domain}/{page_name}'
        
        # Fallback to default
        return 'element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json'
    
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
    
    def _generate_test_code(self, execution: Dict, discoveries: Dict, test_name: str, registry: Dict = None) -> str:
        """Generate complete Python Playwright test code - 1:1 mirror of AI execution"""
        
        if registry is None:
            registry = {}
        
        story = execution['story']
        actions_taken = execution.get('actions_taken', [])
        discoveries_list = discoveries.get('discoveries', [])
        
        # Determine registry file path from story URL (for default/placeholder)
        story_url = execution.get('story_url', '')
        if not story_url:
            # Try to extract URL from story
            import re
            if match := re.search(r'https?://[^\s]+', story):
                story_url = match.group(0)
        
        default_registry_path = self._get_registry_path(story_url)
        
        # Header
        code = f'''"""
Generated Playwright Test
Source Execution: {execution['execution_id']}
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
# CONFIGURATION: Set the path to your shared element registry JSON file
# ============================================================================
# This allows all tests to use the same registry file (single source of truth)
# Update this path to point to your registry JSON file location
REGISTRY_JSON_PATH = "{default_registry_path}"  # <-- USER: Update this path

# Load shared element registry
REGISTRY = {{}}
try:
    registry_path = Path(REGISTRY_JSON_PATH)
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry_data = json.load(f)
            REGISTRY = registry_data.get('elements', {{}})
        print(f"✅ Loaded registry: {{len(REGISTRY)}} elements from {{registry_path.name}}")
    else:
        print(f"⚠️  Registry file not found: {{registry_path}}")
        print(f"   Please update REGISTRY_JSON_PATH to point to your registry JSON file")
except Exception as e:
    print(f"⚠️  Failed to load registry: {{e}}")
    print(f"   Please check REGISTRY_JSON_PATH: {{REGISTRY_JSON_PATH}}")

def get_xpath(registry_key):
    """Get XPath from registry by exact registry key"""
    if registry_key and registry_key in REGISTRY:
        xpath = REGISTRY[registry_key].get('xpath')
        if xpath:
            return xpath
    return None


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
            # Extract step number - handle variations: "Step 1:", "tep 1:", "step 1:", etc.
            # More flexible regex to catch malformed story text
            step_match = re.match(r'[Ss]?tep\s+(\d+):\s*(.+)', line, re.IGNORECASE)
            if not step_match:
                continue
            
            step_num = int(step_match.group(1))
            step_text = step_match.group(2).strip()
            
            # Skip Step 1 if navigation was already generated
            if step_num == 1 and navigation_generated:
                continue
            
            # Find corresponding action from actions_taken
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
                code += self._generate_click_step(step_num, step_text, action, discovery, registry, indent)
            
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
        Match by comparing action's selector with discovery's original_query.
        This prevents wrong matches (e.g., checkbox being matched with table verification).
        """
        selector = action.get('input', {}).get('selector', '')
        
        if not selector:
            return None
        
        # Normalize selector for comparison
        selector_normalized = selector.lower().strip()
        if selector_normalized.startswith('text='):
            selector_normalized = selector_normalized[5:].strip()
        
        # Find discovery with matching original_query
        # Use EXACT or VERY CLOSE match, not fuzzy substring match
        best_match = None
        best_score = 0
        
        for disc in discoveries:
            disc_query = disc.get('original_query', '').lower().strip()
            if disc_query.startswith('text='):
                disc_query = disc_query[5:].strip()
            
            # Skip verification discoveries (they don't have element selectors)
            if disc.get('discovery_method') == 'table_verification':
                continue
            
            # Exact match (best)
            if selector_normalized == disc_query:
                return disc
            
            # Very close match (selector is substring of discovery or vice versa)
            # But both must be substantial (>3 chars) to avoid false positives
            if len(selector_normalized) > 3 and len(disc_query) > 3:
                if selector_normalized in disc_query or disc_query in selector_normalized:
                    # Calculate match quality (prefer longer matches)
                    overlap = min(len(selector_normalized), len(disc_query))
                    total = max(len(selector_normalized), len(disc_query))
                    score = overlap / total
                    
                    if score > best_score:
                        best_score = score
                        best_match = disc
        
        # Only return match if score is high enough (>70% overlap)
        if best_match and best_score > 0.7:
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
    
    def _generate_click_step(self, step_num: int, step_text: str, action: Dict, discovery: Dict, registry: Dict, indent: int) -> str:
        """Generate click code from actual AI execution"""
        ind = ' ' * indent
        input_params = action.get('input', {})
        selector = input_params.get('selector', '')
        result = action.get('result', '')
        
        # Determine if this is an optional click (e.g., popup dismissal)
        is_optional = 'optional' in step_text.lower() or 'if there is' in step_text.lower()
        
        # Extract element name for display
        if selector.startswith('text='):
            element_name = selector.replace('text=', '').strip()
        elif selector.startswith('xpath='):
            xpath_match = re.search(r"text\(\)\s*=\s*['\"]([^'\"]+)['\"]", selector)
            element_name = xpath_match.group(1) if xpath_match else 'element'
        else:
            element_name = 'element'
        
        # Track registry key for this element (exact key from discovery or registry lookup)
        registry_key = None
        selector_source = "AI action"
        selector = ""  # Initialize selector
        
        # PRIORITY 1: Extract ACTUAL selector from AI result (what AI actually clicked)
        # AI result contains the actual XPath/selector that was clicked, not just input selector
        # Examples:
        #   "✅ Clicked xpath=//div[@id='Diagnosis' and @role='button'...] - Verified"
        #   "✅ Clicked text=DIAGNOSIS - Verified"
        #   "✅ Clicked input[type='checkbox'][id='...'] - Verified"
        #   "✅ Clicked [role='tab']:has-text('Diagnosis') - Verified"
        actual_clicked_selector = None
        if result and 'Clicked' in result:
            # Extract selector from result string
            # Pattern matches: "✅ Clicked <selector> - <rest>" or "Clicked <selector> - <rest>"
            # Captures full selector including spaces within quotes (for XPaths)
            clicked_match = re.search(r'(?:✅\s*)?Clicked\s+(.+?)(?:\s+-\s+|$)', result)
            if clicked_match:
                selector_raw = clicked_match.group(1).strip()
                # Clean up trailing punctuation/whitespace
                selector_raw = selector_raw.rstrip('.,;').strip()
                
                # Validate it looks like a selector (contains = or [ or starts with common patterns)
                if selector_raw and (selector_raw.startswith(('xpath=', 'text=', 'css=', '#')) or 
                                     '[' in selector_raw or selector_raw.startswith('.')):
                    actual_clicked_selector = selector_raw
                    logger.info(f"  🎯 Extracted actual clicked selector from AI result: {actual_clicked_selector[:100]}")
                else:
                    logger.debug(f"  ⚠️ Extracted text doesn't look like a selector: {selector_raw[:50]}")
        
        # PRIORITY 1: Use the EXACT selector from actions_taken (what AI actually clicked)
        # This ensures Playwright uses the same selector that worked for AI
        action_selector = input_params.get('selector', '')
        original_selector = action_selector  # Keep original for fallback
        
        # Prepare fallback selectors (discovery XPath, registry XPath)
        fallback_selectors = []
        
        logger.info(f"🔍 Step {step_num}: element_name='{element_name}', action_selector='{action_selector}', actual_clicked='{actual_clicked_selector}', discovery={'YES' if discovery else 'NO'}, registry={'YES' if registry else 'NO'}")
        
        # PRIORITY 1: Use ACTUAL clicked selector from AI result FIRST (for true mirroring)
        # This ensures Playwright uses the EXACT same selector that AI actually clicked
        # This is critical for 1:1 mirroring - both must click the same element
        if actual_clicked_selector and actual_clicked_selector.strip():
            selector = actual_clicked_selector
            selector_source = "AI result (actual clicked selector - PRIMARY for mirroring)"
            logger.info(f"  ✅ Using actual clicked selector from AI result (PRIMARY): {actual_clicked_selector[:100]}")
            logger.info(f"  🎯 This ensures true mirroring - Playwright uses exact same selector AI clicked")
        elif action_selector and action_selector.strip():
            selector = action_selector
            selector_source = "AI action (exact selector from actions_taken - PRIMARY for mirroring)"
            logger.info(f"  ✅ Using AI action selector (PRIMARY): {action_selector[:100]}")
            logger.info(f"  🎯 This ensures true mirroring - Playwright uses same selector as AI")
            
            # Track registry key from discovery if available (for fallback XPath lookup)
            if discovery:
                registry_key = discovery.get('name')
                logger.info(f"  📝 Discovery found: registry_key='{registry_key}' (for fallback XPath)")
                
                # Prepare fallback: discovery XPath
                if discovery.get('xpath'):
                    fallback_selectors.append(f"xpath={discovery['xpath']}")
                    logger.info(f"  📋 Fallback 1: Discovery XPath available")
                # Prepare fallback: registry XPath via discovery key
                elif registry_key and registry and registry_key in registry:
                    registry_entry = registry[registry_key]
                    if registry_entry.get('xpath'):
                        fallback_selectors.append(f"xpath={registry_entry['xpath']}")
                        logger.info(f"  📋 Fallback 1: Registry XPath via discovery key available")
            
            # Also try registry lookup for fallback XPath (even when using AI selector)
            if registry:
                logger.info(f"  🔍 Checking registry for fallback XPath: '{element_name}'")
                registry_selector, matched_registry_key = self._get_selector_and_key_from_registry(element_name, registry)
                if registry_selector and not registry_key:
                    registry_key = matched_registry_key
                    logger.info(f"  📋 Fallback 2: Registry XPath available: {matched_registry_key}")
        
        # PRIORITY 2: Use discovery if no action selector
        elif discovery:
            # Discovery has exact registry key in 'name' field
            registry_key = discovery.get('name')  # This IS the exact registry key!
            logger.info(f"  📝 Discovery found: registry_key='{registry_key}', has_xpath={bool(discovery.get('xpath'))}")
            
            # PRIORITY: Use original_query (what AI actually used) if available
            if discovery.get('original_query'):
                selector = discovery.get('original_query')
                selector_source = "AI discovery (original_query)"
                logger.info(f"  ✅ Using discovery original_query: {selector[:100]}")
            # Fallback: Use discovery XPath if available
            elif discovery.get('xpath'):
                selector = f"xpath={discovery['xpath']}"
                selector_source = "AI discovery XPath"
                logger.info(f"  ✅ Using discovery XPath: {discovery['xpath'][:100]}")
            else:
                # Fallback: check if registry key exists in registry and get XPath from there
                if registry_key and registry and registry_key in registry:
                    registry_entry = registry[registry_key]
                    if registry_entry.get('xpath'):
                        selector = f"xpath={registry_entry['xpath']}"
                        selector_source = "registry (via discovery key)"
                        logger.info(f"  ✅ Using registry XPath via discovery key: {registry_entry['xpath'][:100]}")
                    else:
                        selector_source = "AI action (no XPath in registry)"
                        logger.info(f"  ⚠️ Discovery exists but no XPath in registry, using action selector")
                else:
                    selector_source = "AI action (discovery key not in registry)"
                    logger.info(f"  ⚠️ Discovery key '{registry_key}' not found in registry, using action selector")
        
        # PRIORITY 3: Use registry lookup if no action selector and no discovery
        elif registry:
            # No action selector and no discovery - try registry lookup
            logger.info(f"  ⚠️ No action selector or discovery for step {step_num}, checking registry for '{element_name}'")
            logger.info(f"  📊 Registry has {len(registry)} elements")
            registry_selector, matched_key = self._get_selector_and_key_from_registry(element_name, registry)
            if registry_selector:
                selector = registry_selector
                registry_key = matched_key  # Track the exact registry key that was matched
                selector_source = "registry (no action selector or discovery)"
                logger.info(f"  ✅ Found in registry: key='{matched_key}', selector={selector[:100]}")
            else:
                logger.warning(f"  ⚠️ Element '{element_name}' not found in registry either")
                logger.warning(f"  Tried to match '{element_name.lower()}' against {len(registry)} registry keys")
        
        # Ensure selector is set (fallback to action_selector if nothing else worked)
        if not selector or not selector.strip():
            selector = action_selector if action_selector else ""
            if selector:
                selector_source = "AI action (final fallback)"
                logger.info(f"  ⚠️ Using action selector as final fallback: {selector[:100]}")
            else:
                logger.warning(f"  ⚠️ No selector found from any source for step {step_num}")
        
        # Track registry key from discovery if available (for XPath lookup fallback)
        if discovery and not registry_key:
            registry_key = discovery.get('name')
            logger.info(f"  📝 Discovery found: registry_key='{registry_key}' (for XPath lookup)")
            
            # Prepare fallback: discovery XPath
            if discovery.get('xpath'):
                fallback_selectors.append(f"xpath={discovery['xpath']}")
                logger.info(f"  📋 Fallback 1: Discovery XPath available")
            # Prepare fallback: registry XPath via discovery key
            elif registry_key and registry and registry_key in registry:
                registry_entry = registry[registry_key]
                if registry_entry.get('xpath'):
                    fallback_selectors.append(f"xpath={registry_entry['xpath']}")
                    logger.info(f"  📋 Fallback 1: Registry XPath via discovery key available")
        
        # Normalize text selectors for case-insensitivity (Playwright text= is case-sensitive)
        # Convert text=DIAGNOSIS to xpath with normalize-space() for case-insensitive matching
        normalized_selector = selector
        if selector.startswith('text='):
            text_value = selector.replace('text=', '').strip()
            # Escape quotes in text_value for XPath
            text_value_escaped = text_value.replace("'", "\\'")
            # Convert to XPath with normalize-space() and translate() for case-insensitive matching
            # This matches any element whose normalized lowercase text equals the search term
            normalized_selector = f"xpath=//*[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='{text_value.lower()}']"
            logger.info(f"  🔄 Normalized text selector '{text_value}' to case-insensitive XPath")
        
        # Clean selector (remove state-dependent attributes) - but preserve exact action selector
        # If we have the exact action selector, don't clean it (use what AI used)
        if selector_source != "AI action (exact selector from actions_taken)":
            selector = self._clean_selector(selector)
            normalized_selector = self._clean_selector(normalized_selector)
        
        # Sanitize for screenshot filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', element_name)[:50]
        screenshot_path = f"storage/screenshots/pw_step{step_num}_{safe_name}.png"
        
        # Escape selectors for Python string (for fallback)
        selector_escaped = selector.replace("'", "\\'")
        normalized_selector_escaped = normalized_selector.replace("'", "\\'")
        fallback_selectors_escaped = [s.replace("'", "\\'") for s in fallback_selectors]
        
        # Escape registry key for Python string (if using registry)
        registry_key_escaped = registry_key.replace("'", "\\'") if registry_key else None
        
        code = f"{ind}# Step {step_num}: {step_text}\n"
        
        # Add source note
        if registry_key:
            code += f"{ind}# Using registry key: '{registry_key_escaped}' (from {selector_source})\n"
        else:
            code += f"{ind}# Selector from {selector_source}: {selector[:100]}\n"
        
        # Detect element type from step text or selector
        is_checkbox = 'checkbox' in step_text.lower() or 'input[type=\'checkbox\']' in selector.lower()
        
        # Detect accordion clicks (for expansion verification)
        is_accordion = (
            'accordion' in step_text.lower() or 
            'expand' in step_text.lower() or
            '[role="button"][aria-expanded]' in selector or
            'ancestor::*[@id=' in selector  # Nested accordion indicator
        )
        
        # Detect nested accordion (XPath contains ancestor::*[@id='...'])
        # Check both the primary selector and step metadata from discovery
        step_metadata = discovery.get('metadata', {}) if discovery else {}
        is_nested_accordion = 'ancestor::*[@id=' in selector or (is_accordion and step_metadata.get('nested', False))
        
        # Generate locator code with fallback logic
        # CRITICAL: Order matters for mirroring - AI selector MUST be first
        # Order: AI selector (PRIMARY) -> Normalized -> Registry XPath (fallbacks)
        code += f"{ind}# Build selector list for true mirroring (AI selector FIRST, then fallbacks)\n"
        code += f"{ind}selectors_to_try = [\n"
        
        # PRIORITY 1: Add AI selector FIRST (for true mirroring)
        # This ensures Playwright tries the exact same selector AI used
        code += f"{ind}    '{selector_escaped}',  # AI selector (PRIMARY - same as AI used)\n"
        
        # PRIORITY 2: Add normalized selector as fallback (for case-insensitivity)
        if normalized_selector != selector and selector.startswith('text='):
            code += f"{ind}    '{normalized_selector_escaped}',  # Normalized (case-insensitive fallback)\n"
        
        # PRIORITY 3: Add discovery/registry XPaths as fallbacks
        if fallback_selectors_escaped:
            for fallback in fallback_selectors_escaped:
                code += f"{ind}    '{fallback}',  # Fallback XPath\n"
        elif registry_key:
            # Add registry XPath lookup as fallback
            code += f"{ind}    None,  # Will be set via registry lookup\n"
        
        code += f"{ind}]\n"
        
        # If we have registry key, add registry lookup logic
        if registry_key:
            code += f"{ind}# Try registry XPath lookup (fallback only)\n"
            code += f"{ind}xpath = get_xpath('{registry_key_escaped}')\n"
            code += f"{ind}if xpath:\n"
            code += f"{ind}    registry_xpath = f'xpath={{xpath}}'\n"
            code += f"{ind}    # Add registry XPath as fallback (after AI selector and normalized)\n"
            code += f"{ind}    if len(selectors_to_try) > 1 and selectors_to_try[-1] is None:\n"
            code += f"{ind}        selectors_to_try[-1] = registry_xpath\n"
            code += f"{ind}    else:\n"
            code += f"{ind}        selectors_to_try.append(registry_xpath)  # Add as last fallback\n"
        
        # Filter out None values
        code += f"{ind}# Remove None values\n"
        code += f"{ind}selectors_to_try = [s for s in selectors_to_try if s is not None]\n"
        
        if is_optional:
            # Optional click - try all selectors, don't fail if not found
            code += f"{ind}clicked = False\n"
            code += f"{ind}for sel in selectors_to_try:\n"
            code += f"{ind}    try:\n"
            code += f"{ind}        element = page.locator(sel).nth(0)\n"
            code += f"{ind}        if element.is_visible(timeout=2000):\n"
            code += f"{ind}            element.click()\n"
            code += f"{ind}            page.wait_for_timeout(500)\n"
            code += f"{ind}            print(f'✅ Step {step_num}: Clicked: {element_name} (using: {{sel[:80]}}...)')\n"
            code += f"{ind}            page.screenshot(path='{screenshot_path}')\n"
            code += f"{ind}            clicked = True\n"
            code += f"{ind}            break\n"
            code += f"{ind}    except Exception:\n"
            code += f"{ind}        continue\n"
            code += f"{ind}if not clicked:\n"
            code += f"{ind}    print('ℹ️  Step {step_num}: {element_name} not found (optional)')\n\n"
        else:
            # Required click - try multiple selectors if first fails
            # Take screenshot BEFORE attempting click to capture current state
            pre_attempt_path = screenshot_path.replace('.png', '_pre_attempt.png')
            code += f"{ind}# Take screenshot before attempting click (captures state even if click fails)\n"
            code += f"{ind}try:\n"
            code += f"{ind}    page.screenshot(path='{pre_attempt_path}')\n"
            code += f"{ind}    print('📸 Pre-attempt screenshot: {pre_attempt_path}')\n"
            code += f"{ind}except Exception:\n"
            code += f"{ind}    pass  # Ignore screenshot errors\n"
            code += f"{ind}clicked = False\n"
            code += f"{ind}last_error = None\n"
            # Determine if this is a nested accordion BEFORE the loop (based on step metadata or primary selector)
            code += f"{ind}# Check if this is a nested accordion (determine once before loop)\n"
            code += f"{ind}is_nested_accordion_step = {is_nested_accordion}  # From step metadata or primary selector\n"
            code += f"{ind}for sel in selectors_to_try:\n"
            code += f"{ind}    try:\n"
            
            # CRITICAL: For XPaths with ancestor::* pattern, DON'T use .nth(1) - the XPath already targets the nested element
            # Only use .nth(1) for non-XPath selectors (like text=) that might match multiple elements
            code += f"{ind}        # Check if this selector targets a nested accordion\n"
            code += f"{ind}        # If selector has ancestor::* pattern, XPath already targets nested element - use .nth(0)\n"
            code += f"{ind}        # If selector is text= or other non-XPath, might need .nth(1) to skip parent\n"
            code += f"{ind}        has_ancestor_pattern = 'ancestor::*[@id=' in sel\n"
            code += f"{ind}        # Determine if this is a nested selector (for accordion logic later)\n"
            code += f"{ind}        is_nested_selector = has_ancestor_pattern or (is_nested_accordion_step and not sel.startswith('xpath='))\n"
            code += f"{ind}        if has_ancestor_pattern:\n"
            code += f"{ind}            # XPath with ancestor::* already targets nested element - use .nth(0) or .first()\n"
            code += f"{ind}            nth_index = 0\n"
            code += f"{ind}        elif is_nested_accordion_step and not sel.startswith('xpath='):\n"
            code += f"{ind}            # Non-XPath selector for nested accordion - might need .nth(1) to skip parent\n"
            code += f"{ind}            nth_index = 1\n"
            code += f"{ind}        else:\n"
            code += f"{ind}            # Regular selector - use .nth(0)\n"
            code += f"{ind}            nth_index = 0\n"
            code += f"{ind}        element = page.locator(sel).nth(nth_index)\n"
            
            # CRITICAL: For checkboxes, skip visibility check due to virtual scrolling
            # Virtual scrolling can mark elements as "hidden" even though they're clickable
            if is_checkbox:
                code += f"{ind}        # Checkbox: Wait for attached, then scroll into view (skip visibility check for virtual scrolling)\n"
                code += f"{ind}        element.wait_for(state='attached', timeout=10000)\n"
                code += f"{ind}        element.scroll_into_view_if_needed()\n"
                code += f"{ind}        page.wait_for_timeout(500)  # Allow scroll to complete\n"
                code += f"{ind}        # Check if checkbox is already checked\n"
                code += f"{ind}        is_checked = element.is_checked()\n"
                code += f"{ind}        if is_checked:\n"
                code += f"{ind}            print(f'ℹ️  Checkbox already checked, skipping')\n"
                code += f"{ind}        else:\n"
                code += f"{ind}            # Mirror AI behavior: Use .click() FIRST (like AI does), not .check()\n"
                code += f"{ind}            # AI agent uses click(), so Playwright should too for true mirroring\n"
                code += f"{ind}            try:\n"
                code += f"{ind}                # Use click() first (matches AI behavior)\n"
                code += f"{ind}                element.click(force=True)\n"
                code += f"{ind}                page.wait_for_timeout(1000)  # Wait for Material-UI to update\n"
                code += f"{ind}                if element.is_checked():\n"
                code += f"{ind}                    print(f'✅ Checkbox checked successfully (via click - mirrors AI)')\n"
                code += f"{ind}                else:\n"
                code += f"{ind}                    # Click didn't work, try .check() as fallback\n"
                code += f"{ind}                    print(f'⚠️  click() did not change state, trying .check() fallback')\n"
                code += f"{ind}                    element.check(force=True)\n"
                code += f"{ind}                    page.wait_for_timeout(1000)\n"
                code += f"{ind}                    if element.is_checked():\n"
                code += f"{ind}                        print(f'✅ Checkbox checked via .check() fallback')\n"
                code += f"{ind}                    else:\n"
                code += f"{ind}                        # Last resort: JavaScript to set state and trigger handlers\n"
                code += f"{ind}                        print(f'⚠️  Both click() and .check() failed, using JavaScript fallback')\n"
                code += f"{ind}                        element.evaluate('el => el.checked = true')\n"
                code += f"{ind}                        element.evaluate('el => el.dispatchEvent(new Event(\"change\", {{ bubbles: true }}))')\n"
                code += f"{ind}                        element.evaluate('el => el.click()')  # Trigger click handler\n"
                code += f"{ind}                        page.wait_for_timeout(500)\n"
                code += f"{ind}                        if element.is_checked():\n"
                code += f"{ind}                            print(f'✅ Checkbox checked via JavaScript fallback')\n"
                code += f"{ind}                        else:\n"
                code += f"{ind}                            print(f'⚠️  Checkbox state still not updated')\n"
                code += f"{ind}            except Exception as click_error:\n"
                code += f"{ind}                # click() failed, try .check() as fallback\n"
                code += f"{ind}                print(f'⚠️  click() failed, trying .check() fallback: {{click_error}}')\n"
                code += f"{ind}                try:\n"
                code += f"{ind}                    element.check(force=True)\n"
                code += f"{ind}                    page.wait_for_timeout(1000)\n"
                code += f"{ind}                    if element.is_checked():\n"
                code += f"{ind}                        print(f'✅ Checkbox checked via .check() fallback')\n"
                code += f"{ind}                    else:\n"
                code += f"{ind}                        # Last resort: JavaScript\n"
                code += f"{ind}                        element.evaluate('el => el.checked = true')\n"
                code += f"{ind}                        element.evaluate('el => el.dispatchEvent(new Event(\"change\", {{ bubbles: true }}))')\n"
                code += f"{ind}                        element.evaluate('el => el.click()')\n"
                code += f"{ind}                        page.wait_for_timeout(500)\n"
                code += f"{ind}                        if element.is_checked():\n"
                code += f"{ind}                            print(f'✅ Checkbox checked via JavaScript fallback')\n"
                code += f"{ind}                        else:\n"
                code += f"{ind}                            print(f'⚠️  Checkbox may not have updated: {{click_error}}')\n"
                code += f"{ind}                except Exception as check_error:\n"
                code += f"{ind}                    # Both click() and .check() failed, use JavaScript\n"
                code += f"{ind}                    print(f'⚠️  .check() also failed, using JavaScript fallback: {{check_error}}')\n"
                code += f"{ind}                    element.evaluate('el => el.checked = true')\n"
                code += f"{ind}                    element.evaluate('el => el.dispatchEvent(new Event(\"change\", {{ bubbles: true }}))')\n"
                code += f"{ind}                    element.evaluate('el => el.click()')\n"
                code += f"{ind}                    page.wait_for_timeout(500)\n"
                code += f"{ind}                    if element.is_checked():\n"
                code += f"{ind}                        print(f'✅ Checkbox checked via JavaScript fallback')\n"
                code += f"{ind}                    else:\n"
                code += f"{ind}                        print(f'⚠️  Checkbox may not have updated: {{check_error}}')\n"
            else:
                code += f"{ind}        element.wait_for(state='visible', timeout=10000)\n"
                
                # For accordions, check if already expanded before clicking
                if is_accordion:
                    code += f"{ind}        # Accordion detected: check if already expanded\n"
                    code += f"{ind}        # For nested accordions, always click (don't skip) to ensure content is visible\n"
                    code += f"{ind}        if is_nested_selector:\n"
                    code += f"{ind}            # Nested accordion: always click to ensure it's expanded\n"
                    code += f"{ind}            element.click()\n"
                    code += f"{ind}            page.wait_for_timeout(1000)  # Wait for content to render\n"
                    code += f"{ind}            print(f'✅ Clicked nested accordion')\n"
                    code += f"{ind}        else:\n"
                    code += f"{ind}            # Top-level accordion: check state before clicking\n"
                    code += f"{ind}            initial_aria_expanded = element.get_attribute('aria-expanded')\n"
                    code += f"{ind}            if initial_aria_expanded == 'true':\n"
                    code += f"{ind}                print(f'ℹ️  Accordion already expanded (aria-expanded={{initial_aria_expanded}}), skipping click')\n"
                    code += f"{ind}                # Wait for accordion content to be visible\n"
                    code += f"{ind}                page.wait_for_timeout(1000)  # Wait for content to render\n"
                    code += f"{ind}            else:\n"
                    code += f"{ind}                # Accordion is closed, click to expand\n"
                    code += f"{ind}                element.click()\n"
                    code += f"{ind}                # Verify accordion expanded (aria-expanded: false→true)\n"
                    code += f"{ind}                page.wait_for_timeout(500)  # Wait for state change\n"
                    code += f"{ind}                current_aria_expanded = element.get_attribute('aria-expanded')\n"
                    code += f"{ind}                if current_aria_expanded == 'true':\n"
                    code += f"{ind}                    print(f'✅ Accordion expanded: {{initial_aria_expanded}} → {{current_aria_expanded}}')\n"
                    code += f"{ind}                else:\n"
                    code += f"{ind}                    print(f'⚠️  Accordion state unchanged: {{initial_aria_expanded}} → {{current_aria_expanded}}')\n"
                    code += f"{ind}                # Wait for accordion content to appear\n"
                    code += f"{ind}                page.wait_for_timeout(1000)  # Wait for content to render\n"
                else:
                    code += f"{ind}        element.click()\n"
                    code += f"{ind}        page.wait_for_timeout(1000)  # Wait for UI update\n"
            
            code += f"{ind}        print(f'✅ Step {step_num}: Clicked: {element_name} (using: {{sel[:80]}}...)')\n"
            code += f"{ind}        page.screenshot(path='{screenshot_path}')\n"
            code += f"{ind}        print('📸 Screenshot: {screenshot_path}')\n"
            code += f"{ind}        clicked = True\n"
            code += f"{ind}        break\n"
            code += f"{ind}    except Exception as e:\n"
            code += f"{ind}        last_error = e\n"
            code += f"{ind}        print(f'⚠️  Selector failed: {{sel[:80]}}... - {{str(e)[:100]}}')\n"
            code += f"{ind}        continue\n"
            code += f"{ind}if not clicked:\n"
            code += f"{ind}    # Take screenshot even on failure to show what was visible\n"
            failed_path = screenshot_path.replace('.png', '_failed.png')
            code += f"{ind}    try:\n"
            code += f"{ind}        page.screenshot(path='{failed_path}')\n"
            code += f"{ind}        print('📸 Screenshot: {failed_path}')\n"
            code += f"{ind}    except Exception:\n"
            code += f"{ind}        pass  # Ignore screenshot errors\n"
            code += f"{ind}    print(f'❌ Step {step_num}: Failed to click {element_name} with all selectors')\n"
            code += f"{ind}    print(f'Last error: {{last_error}}')\n"
            code += f"{ind}    raise last_error\n\n"
        
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
        
        code = f"{ind}# Step {step_num}: {step_text}\n"
        code += f"{ind}# Verify: All rows in '{column_name}' column contain '{expected_value}'\n"
        code += f"{ind}try:\n"
        code += f"{ind}    print('🔍 Step {step_num}: Verifying table column...')\n"
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
        code += f"{ind}        if '{column_name}'.lower() == header.lower().strip():\n"
        code += f"{ind}            column_index = i\n"
        code += f"{ind}            break\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Fallback: partial match\n"
        code += f"{ind}    if column_index == -1:\n"
        code += f"{ind}        for i, header in enumerate(headers):\n"
        code += f"{ind}            if '{column_name}'.lower() in header.lower():\n"
        code += f"{ind}                column_index = i\n"
        code += f"{ind}                break\n"
        code += f"{ind}    \n"
        code += f"{ind}    if column_index == -1:\n"
        code += f"{ind}        raise Exception(f\"Column '{column_name}' not found. Available: {{headers}}\")\n"
        code += f"{ind}    \n"
        code += f"{ind}    print(f'📋 Step {step_num}: Found column \"{column_name}\" at index {{column_index}}')\n"
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
        code += f"{ind}            if '{expected_value}'.lower() in cell_text.lower():\n"
        code += f"{ind}                matching_rows += 1\n"
        code += f"{ind}            else:\n"
        code += f"{ind}                print(f'⚠️  Row {{row_idx + 1}}: Expected \"{expected_value}\", got \"{{cell_text}}\"')\n"
        code += f"{ind}    \n"
        code += f"{ind}    # Assert all rows match\n"
        code += f"{ind}    assert matching_rows == total_rows, f\"Only {{matching_rows}}/{{total_rows}} rows match\"\n"
        code += f"{ind}    \n"
        code += f"{ind}    print(f'✅ Step {step_num}: VERIFICATION PASSED: All {{total_rows}} rows contain \"{expected_value}\"')\n"
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

