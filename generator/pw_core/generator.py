"""
Core Generator - Main orchestrator for Playwright test generation
Extracted from playwright_generator.py
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

from generator.pw_loaders.execution_loader import load_execution, validate_execution
from generator.pw_loaders.discovery_loader import load_discoveries, validate_discoveries
from generator.pw_loaders.registry_loader import (
    detect_registry_files,
    merge_registries,
    get_registry_path
)
from generator.pw_matchers.action_matcher import (
    find_action_by_content,
    find_action_by_iteration,
    find_wait_action
)
from generator.pw_matchers.discovery_matcher import (
    find_discovery_by_step,
    find_verification_discovery
)
from generator.pw_codegen.test_template import (
    build_test_template,
    extract_test_constants
)
from generator.pw_codegen.step_generators import (
    generate_navigate_step,
    generate_wait_step,
    generate_click_step,
    generate_fill_step,
    generate_verify_step
)
from generator.pw_codegen.code_formatter import generate_test_name

logger = logging.getLogger(__name__)


class PlaywrightGeneratorCore:
    """Core orchestrator for Playwright test generation"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.element_maps_dir = project_root / 'element_maps'
        self.executions_dir = project_root / 'storage' / 'executions'
        self.discoveries_dir = project_root / 'storage' / 'discoveries'
    
    def generate_test_code(
        self,
        execution: Dict,
        discoveries: Dict,
        test_name: str,
        registry_files: List[str]
    ) -> str:
        """
        Generate complete Python Playwright test code
        
        Args:
            execution: Execution dictionary
            discoveries: Discoveries dictionary
            test_name: Test function name
            registry_files: List of registry file paths
        Returns:
            Complete test code as string
        """
        story = execution['story']
        actions_taken = execution.get('actions_taken', [])
        discoveries_list = discoveries.get('discoveries', [])
        
        # Merge all registries
        merged_registry = merge_registries(registry_files, self.element_maps_dir)
        
        # Extract test-specific constants
        test_constants = extract_test_constants(discoveries_list)
        
        # Generate test body (sequential code generation)
        test_body = self._generate_sequential_code(
            story, actions_taken, discoveries_list, merged_registry, indent=12
        )
        
        # Build complete test template
        code = build_test_template(
            execution_id=execution['execution_id'],
            story=story,
            test_name=test_name,
            status=execution['status'],
            registry_files=registry_files,
            test_constants=test_constants,
            test_body=test_body
        )
        
        return code
    
    def _generate_sequential_code(
        self,
        story: str,
        actions_taken: List[Dict],
        discoveries: List[Dict],
        registry: Dict,
        indent: int = 12
    ) -> str:
        """
        Generate code by processing story steps sequentially - Perfect 1:1 mirror of AI execution
        
        Strategy:
        1. Parse story into numbered steps (Step 1, Step 2, etc.)
        2. For each step, find the corresponding action from actions_taken
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
                code += generate_navigate_step(1, step_text, first_action, indent)
                navigation_generated = True
        
        # Parse story into steps
        story_lines = story.strip().split('\n')
        
        for line in story_lines:
            # Extract step number - handle variations: "Step 1:", "Steps 15:", "Step 1", "Steps 15", etc.
            step_match = re.match(r'[Ss]teps?\s+(\d+)\s*:?\s*(.+)', line, re.IGNORECASE)
            if not step_match:
                continue
            
            step_num = int(step_match.group(1))
            step_text = step_match.group(2).strip()
            
            # Skip Step 1 if navigation was already generated
            if step_num == 1 and navigation_generated:
                continue
            
            # Find corresponding action from actions_taken
            action = None
            
            # For wait steps, match by step text content
            if 'wait' in step_text.lower() and any(char.isdigit() for char in step_text):
                action = find_wait_action(step_text, actions_taken)
            else:
                # For other steps, use content-based matching
                action = find_action_by_content(step_text, step_num, actions_taken)
            
            # Generate code based on action type
            if not action:
                # No action found - add comment
                code += f"{ind}# Step {step_num}: {step_text[:80]}\n"
                code += f"{ind}# (No corresponding action found in execution)\n\n"
                continue
            
            tool = action.get('tool', '')
            
            # Generate code based on tool type
            if tool == 'browser_navigate':
                code += generate_navigate_step(step_num, step_text, action, indent)
            
            elif tool == 'browser_evaluate':
                # Likely a wait step
                code += generate_wait_step(step_num, step_text, action, indent)
            
            elif tool == 'browser_click':
                # Find corresponding discovery for this click
                discovery = find_discovery_by_step(step_num, step_text, discoveries, action)
                
                # If no discovery found, try to find element in registry by step text/action selector
                if not discovery:
                    selector = action.get('input', {}).get('selector', '')
                    element_name_from_step = None
                    if 'checkbox' in step_text.lower():
                        checkbox_match = re.search(r'select\s+(?:the\s+)?(.+?)\s+checkbox', step_text, re.IGNORECASE)
                        if checkbox_match:
                            element_name_from_step = checkbox_match.group(1).strip()
                    
                    # Try to find in registry
                    if element_name_from_step and registry:
                        elements = registry.get('elements', {})
                        for key, elem_data in elements.items():
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
                if step_num < len(story_lines):
                    current_line_idx = story_lines.index(line) if line in story_lines else -1
                    if current_line_idx >= 0:
                        for next_line in story_lines[current_line_idx + 1:]:
                            next_step_match = re.match(r'[Ss]?tep\s+(\d+):\s*(.+)', next_line, re.IGNORECASE)
                            if next_step_match:
                                next_step_num = int(next_step_match.group(1))
                                next_step_text = next_step_match.group(2).strip()
                                # Find next step's action
                                next_action = find_action_by_iteration(next_step_num, actions_taken)
                                if next_action and next_action.get('tool') == 'browser_click':
                                    # Find next step's discovery
                                    next_step_discovery = find_discovery_by_step(next_step_num, next_step_text, discoveries, next_action)
                                    break
                
                code += generate_click_step(step_num, step_text, action, discovery, registry, indent, next_step_discovery)
            
            elif tool == 'browser_fill':
                # Find corresponding discovery for this fill action
                discovery = find_discovery_by_step(step_num, step_text, discoveries, action)
                code += generate_fill_step(step_num, step_text, action, discovery, registry, indent)
            
            elif tool == 'browser_verify_table':
                # Find corresponding verification discovery (must be table_verification type)
                discovery = find_verification_discovery(step_num, discoveries)
                code += generate_verify_step(step_num, step_text, action, discovery, indent)
            
            else:
                # Unknown tool - add comment
                code += f"{ind}# Step {step_num}: {step_text[:80]}\n"
                code += f"{ind}# Tool: {tool} (not yet supported in generator)\n\n"
        
        return code

