"""
Selector Validator
Validates selectors/XPaths before Playwright code generation
"""
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class SelectorValidator:
    """Validate selectors before Playwright code generation"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.element_maps_dir = project_root / 'element_maps'
        self.executions_dir = project_root / 'storage' / 'executions'
        self.screenshots_dir = project_root / 'storage' / 'screenshots'
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_all_selectors(
        self, 
        execution: Dict, 
        discoveries: List[Dict],
        actions_taken: List[Dict]
    ) -> Dict[str, Any]:
        """
        Validate all selectors from discoveries against registry
        
        Args:
            execution: Execution dictionary
            discoveries: List of discovery dictionaries
            actions_taken: List of actions taken during execution
            
        Returns:
            {
                'all_valid': bool,
                'validated_steps': List[Dict],  # Step-by-step results
                'errors': List[str],  # Error messages
                'warnings': List[str]  # Warning messages
            }
        """
        validated_steps = []
        errors = []
        warnings = []
        
        # Run async validation
        validation_result = asyncio.run(
            self._validate_selectors_async(execution, discoveries, actions_taken)
        )
        
        validated_steps = validation_result['validated_steps']
        errors = validation_result['errors']
        warnings = validation_result['warnings']
        
        all_valid = len(errors) == 0
        
        return {
            'all_valid': all_valid,
            'validated_steps': validated_steps,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _validate_selectors_async(
        self,
        execution: Dict,
        discoveries: List[Dict],
        actions_taken: List[Dict]
    ) -> Dict[str, Any]:
        """Async validation of selectors"""
        validated_steps = []
        errors = []
        warnings = []
        
        # Create a mapping of step_number to action for quick lookup
        step_to_action = {}
        for action in actions_taken:
            step_num = action.get('step_number')
            if step_num:
                step_to_action[step_num] = action
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
            
            try:
                # Group discoveries by step_number and validate each
                discoveries_by_step = {}
                for disc in discoveries:
                    step_num = disc.get('step_number')
                    if step_num:
                        if step_num not in discoveries_by_step:
                            discoveries_by_step[step_num] = []
                        discoveries_by_step[step_num].append(disc)
                
                # Validate each step
                for step_num in sorted(discoveries_by_step.keys()):
                    step_discoveries = discoveries_by_step[step_num]
                    action = step_to_action.get(step_num)
                    
                    for discovery in step_discoveries:
                        validation = await self._validate_single_selector(
                            page, discovery, action, step_num
                        )
                        validated_steps.append(validation)
                        
                        if not validation['valid']:
                            errors.append(validation['error'])
                        elif validation.get('warning'):
                            warnings.append(validation['warning'])
                
            finally:
                await browser.close()
        
        return {
            'validated_steps': validated_steps,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _validate_single_selector(
        self,
        page,
        discovery: Dict,
        action: Optional[Dict],
        step_num: int
    ) -> Dict[str, Any]:
        """
        Validate a single selector/XPath
        
        Returns:
            {
                'step_number': int,
                'element_name': str,
                'valid': bool,
                'error': str (if invalid),
                'warning': str (if warning),
                'xpath': str,
                'found': bool,
                'visible': bool,
                'clickable': bool
            }
        """
        element_name = discovery.get('name', 'unknown')
        element_id = discovery.get('element_id')
        xpath = discovery.get('xpath')
        discovery_url = discovery.get('discovery_url', '')
        
        result = {
            'step_number': step_num,
            'element_name': element_name,
            'valid': False,
            'xpath': xpath,
            'found': False,
            'visible': False,
            'clickable': False
        }
        
        # Get registry path early for error messages
        registry_info = self._load_registry_for_url(discovery_url)
        registry_path = registry_info.get('path') if registry_info else None
        
        # Check 1: element_id exists
        if not element_id:
            registry_info_str = f" (Registry: {registry_path})" if registry_path else ""
            result['error'] = f"Step {step_num}: '{element_name}' missing element_id - cannot validate{registry_info_str}"
            return result
        
        # Check 2: XPath exists
        if not xpath:
            registry_info_str = f" (Registry: {registry_path})" if registry_path else ""
            result['error'] = f"Step {step_num}: '{element_name}' missing XPath in discovery{registry_info_str}"
            return result
        
        # Check 3: Load registry and verify XPath exists
        registry_info = self._load_registry_for_url(discovery_url)
        registry = registry_info.get('data') if registry_info else None
        registry_path = registry_info.get('path') if registry_info else None
        
        if not registry:
            registry_path_str = f" (Registry: {registry_path})" if registry_path else ""
            result['warning'] = f"Step {step_num}: '{element_name}' - Registry not found for URL {discovery_url}{registry_path_str}"
            # Continue validation anyway (XPath might still work)
        
        # Store registry path for error messages
        result['registry_path'] = registry_path
        
        # Check 4: Navigate to page and find element
        try:
            # Get URL from discovery or action
            url = discovery_url
            if not url and action:
                url = action.get('input', {}).get('url', '')
            
            if not url:
                registry_info_str = f" (Registry: {registry_path})" if registry_path else ""
                result['error'] = f"Step {step_num}: '{element_name}' - No URL found for validation{registry_info_str}"
                return result
            
            # Navigate to page
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)  # Wait for dynamic content
            
            # Dismiss popups if any
            try:
                continue_btn = page.locator("text='Continue'").first
                if await continue_btn.is_visible(timeout=2000):
                    await continue_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # Try to find element using XPath (with fallback to alternative selectors)
            try:
                locator = page.locator(f"xpath={xpath}")
                count = await locator.count()
                
                # If primary XPath fails, try alternative selectors
                if count == 0:
                    # Try alternative selectors from action and discovery
                    alternative_selectors = self._get_alternative_selectors(discovery, action)
                    found_alternative = False
                    working_selector = None
                    
                    for alt_selector in alternative_selectors:
                        try:
                            alt_locator = page.locator(alt_selector)
                            alt_count = await alt_locator.count()
                            if alt_count > 0:
                                # Check if it's visible
                                try:
                                    if await alt_locator.first.is_visible(timeout=2000):
                                        found_alternative = True
                                        working_selector = alt_selector
                                        locator = alt_locator
                                        count = alt_count
                                        logger.info(f"  ✅ Found element using alternative selector: {alt_selector}")
                                        break
                                except:
                                    continue
                        except:
                            continue
                    
                    if not found_alternative:
                        # Build error message with suggestions
                        registry_info = f" (Registry: {registry_path})" if registry_path else ""
                        error_msg = f"Step {step_num}: '{element_name}' - Element not found using XPath: {xpath}{registry_info}"
                        
                        if alternative_selectors:
                            error_msg += f"\n   Tried alternative selectors: {', '.join(alternative_selectors[:3])}"
                            error_msg += f"\n   💡 Suggestion: Update registry XPath or check if element exists on page"
                        
                        result['error'] = error_msg
                        result['tried_alternatives'] = alternative_selectors
                        return result
                    else:
                        # Found using alternative - add warning
                        result['warning'] = f"Step {step_num}: '{element_name}' - Primary XPath failed, but found using alternative selector: {working_selector}"
                        result['working_selector'] = working_selector
                        result['primary_xpath_failed'] = True
                
                result['found'] = True
                
                # Check visibility
                try:
                    is_visible = await locator.first.is_visible(timeout=5000)
                    result['visible'] = is_visible
                    
                    if not is_visible:
                        result['warning'] = f"Step {step_num}: '{element_name}' - Element found but not visible"
                except:
                    result['visible'] = False
                    result['warning'] = f"Step {step_num}: '{element_name}' - Could not verify visibility"
                
                # Check clickability (for click steps)
                tool = action.get('tool', '') if action else ''
                if tool == 'browser_click':
                    try:
                        is_enabled = await locator.first.is_enabled(timeout=2000)
                        result['clickable'] = is_enabled
                        
                        if not is_enabled:
                            result['warning'] = f"Step {step_num}: '{element_name}' - Element found but not clickable/enabled"
                    except:
                        result['clickable'] = False
                
                # Take screenshot for comparison
                screenshot_path = self.screenshots_dir / f"validation_step{step_num}_{element_name.replace(' ', '_')}.png"
                await page.screenshot(path=str(screenshot_path))
                result['screenshot'] = str(screenshot_path.relative_to(self.project_root))
                
                # Validation passed
                result['valid'] = True
                
            except PlaywrightTimeoutError:
                registry_info = f" (Registry: {registry_path})" if registry_path else ""
                result['error'] = f"Step {step_num}: '{element_name}' - Timeout finding element with XPath: {xpath}{registry_info}"
                return result
            except Exception as e:
                registry_info = f" (Registry: {registry_path})" if registry_path else ""
                result['error'] = f"Step {step_num}: '{element_name}' - Error finding element: {str(e)}{registry_info}"
                return result
                
        except Exception as e:
            registry_info_str = f" (Registry: {registry_path})" if registry_path else ""
            result['error'] = f"Step {step_num}: '{element_name}' - Error navigating to page: {str(e)}{registry_info_str}"
            return result
        
        return result
    
    def _load_registry_for_url(self, url: str) -> Optional[Dict]:
        """
        Load registry for a given URL
        Returns dict with 'data' (registry dict) and 'path' (relative path string)
        """
        if not url:
            return None
        
        parsed = urlparse(url)
        domain = parsed.netloc.split(':')[0]
        
        # Extract page name
        path_segments = [s for s in parsed.path.split('/') if s]
        if not path_segments:
            page = 'home'
        else:
            last_segment = path_segments[-1]
            page = last_segment.split('?')[0].split('#')[0]
        
        # Sanitize page name
        import re
        page = re.sub(r'[^\w\-_\.]', '', page)
        if not page:
            page = 'default_page'
        
        # Try to load registry file
        domain_dir = self.element_maps_dir / domain
        if not domain_dir.exists():
            # Return path even if file doesn't exist (for error messages)
            expected_path = f'element_maps/{domain}/{page}_page.json'
            return {'data': None, 'path': expected_path}
        
        # Try different naming patterns
        registry_file = domain_dir / f'{page}_page.json'
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                    relative_path = f'element_maps/{domain}/{page}_page.json'
                    return {'data': registry_data, 'path': relative_path}
            except:
                pass
        
        # Try without extension
        if '.' in page:
            page_no_ext = page.rsplit('.', 1)[0]
            registry_file = domain_dir / f'{page_no_ext}_page.json'
            if registry_file.exists():
                try:
                    with open(registry_file, 'r') as f:
                        registry_data = json.load(f)
                        relative_path = f'element_maps/{domain}/{page_no_ext}_page.json'
                        return {'data': registry_data, 'path': relative_path}
                except:
                    pass
        
        # Fallback to common names
        for page_name in ['home_page.json', 'explore_page.json', 'index.json']:
            registry_file = domain_dir / page_name
            if registry_file.exists():
                try:
                    with open(registry_file, 'r') as f:
                        registry_data = json.load(f)
                        relative_path = f'element_maps/{domain}/{page_name}'
                        return {'data': registry_data, 'path': relative_path}
                except:
                    pass
        
        # Return expected path even if file doesn't exist (for error messages)
        expected_path = f'element_maps/{domain}/{page}_page.json'
        return {'data': None, 'path': expected_path}
    
    def _get_alternative_selectors(self, discovery: Dict, action: Optional[Dict]) -> List[str]:
        """
        Get alternative selectors to try when primary XPath fails
        Returns list of selector strings (Playwright locator format)
        """
        alternatives = []
        
        # 1. Try final_selector from discovery (the selector that actually worked)
        if discovery:
            final_selector = discovery.get('final_selector', '')
            if final_selector and final_selector != discovery.get('xpath', ''):
                alternatives.append(final_selector)
            
            # 2. Try original_query from discovery
            original_query = discovery.get('original_query', '')
            if original_query and original_query not in alternatives:
                alternatives.append(original_query)
        
        # 3. Try selector from action input (what AI actually used)
        if action:
            action_selector = action.get('input', {}).get('selector', '')
            if action_selector and action_selector not in alternatives:
                alternatives.append(action_selector)
        
        # 4. Try text-based selector from element name
        element_name = discovery.get('name', '') if discovery else ''
        if element_name:
            # Try text= selector
            text_selector = f"text={element_name}"
            if text_selector not in alternatives:
                alternatives.append(text_selector)
            
            # Try button with text
            button_text_selector = f"button:has-text('{element_name}')"
            if button_text_selector not in alternatives:
                alternatives.append(button_text_selector)
            
            # Try link with text
            link_text_selector = f"a:has-text('{element_name}')"
            if link_text_selector not in alternatives:
                alternatives.append(link_text_selector)
        
        return alternatives


# Example usage
if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    validator = SelectorValidator(project_root)
    
    # Load execution
    exec_id = sys.argv[1] if len(sys.argv) > 1 else 'exec_172351d5'
    exec_file = project_root / 'storage' / 'executions' / f'{exec_id}.json'
    
    if not exec_file.exists():
        print(f"❌ Execution file not found: {exec_file}")
        sys.exit(1)
    
    with open(exec_file, 'r') as f:
        execution = json.load(f)
    
    discoveries = execution.get('discoveries', [])
    actions_taken = execution.get('actions_taken', [])
    
    print(f"🔍 Validating {len(discoveries)} discoveries...")
    
    result = validator.validate_all_selectors(execution, discoveries, actions_taken)
    
    print(f"\n📊 Validation Results:")
    print(f"   All Valid: {result['all_valid']}")
    print(f"   Errors: {len(result['errors'])}")
    print(f"   Warnings: {len(result['warnings'])}")
    
    if result['errors']:
        print(f"\n❌ Errors:")
        for error in result['errors']:
            print(f"   - {error}")
    
    if result['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in result['warnings']:
            print(f"   - {warning}")
    
    if result['all_valid']:
        print(f"\n✅ All selectors validated successfully!")

