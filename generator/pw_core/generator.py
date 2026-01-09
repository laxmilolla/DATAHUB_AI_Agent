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
    get_registry_path
)
from generator.pw_matchers.action_matcher import (
    find_action_by_step_number,
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

# Import validator (optional - only if validation is enabled)
try:
    from validator.selector_validator import SelectorValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    logger.warning("SelectorValidator not available - validation will be skipped")


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
        registry_files: List[str],
        validate_selectors: bool = True
    ) -> str:
        """
        Generate complete Python Playwright test code
        
        Args:
            execution: Execution dictionary
            discoveries: Discoveries dictionary
            test_name: Test function name
            registry_files: List of registry file paths
            validate_selectors: Whether to validate selectors before generation (default: True)
        Returns:
            Complete test code as string
        Raises:
            Exception: If selector validation fails
        """
        story = execution['story']
        actions_taken = execution.get('actions_taken', [])
        discoveries_list = discoveries.get('discoveries', [])
        
        # PRE-VALIDATION: Validate selectors before generating code
        if validate_selectors and VALIDATOR_AVAILABLE:
            logger.info("🔍 Pre-validating selectors before code generation...")
            validator = SelectorValidator(self.project_root)
            validation_result = validator.validate_all_selectors(
                execution, discoveries_list, actions_taken
            )
            
            if not validation_result['all_valid']:
                # Build detailed error message
                error_msg = "❌ Selector Validation Failed\n\n"
                error_msg += "The following selectors failed validation:\n\n"
                
                for error in validation_result['errors']:
                    error_msg += f"  • {error}\n"
                
                if validation_result['warnings']:
                    error_msg += "\n⚠️  Warnings:\n"
                    for warning in validation_result['warnings']:
                        error_msg += f"  • {warning}\n"
                
                error_msg += "\n💡 Suggestions:\n"
                error_msg += "  1. Check the registry files mentioned above for correct XPaths\n"
                error_msg += "  2. Verify elements exist on the page\n"
                error_msg += "  3. Update the registry file with correct selectors\n"
                error_msg += "  4. Re-run AI execution to capture correct elements\n"
                
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"✅ All {len(validation_result['validated_steps'])} selectors validated successfully")
        
        # NO MERGE: Use page-specific registries only (loaded at runtime in generated script)
        # Registry files are passed to template, but not merged here to avoid conflicts
        
        # Extract test-specific constants
        test_constants = extract_test_constants(discoveries_list)
        
        # Generate test body (sequential code generation)
        # No registry parameter needed - all lookups use element_id via page-specific registries at runtime
        test_body = self._generate_sequential_code(
            story, actions_taken, discoveries_list, indent=12
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
            
            # PRIORITY 1: Direct lookup by step_number (like element_id for XPaths)
            # This uses the AI's decision directly - most reliable
            action = find_action_by_step_number(step_num, actions_taken)
            
            # PRIORITY 2: For wait steps, match by step text content
            if not action and 'wait' in step_text.lower() and any(char.isdigit() for char in step_text):
                action = find_wait_action(step_text, actions_taken)
            
            # PRIORITY 3: Fallback to content-based matching (for backward compatibility)
            if not action:
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
                
                # NO NAME-BASED FALLBACK: Rely only on discovery's element_id
                # Name-based lookup causes conflicts when same element name exists in multiple registries
                # element_id is unique and page-specific, so it's the only reliable lookup method
                
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
                
                code += generate_click_step(step_num, step_text, action, discovery, None, indent, next_step_discovery)
            
            elif tool == 'browser_fill':
                # Find corresponding discovery for this fill action
                discovery = find_discovery_by_step(step_num, step_text, discoveries, action)
                code += generate_fill_step(step_num, step_text, action, discovery, None, indent)
            
            elif tool == 'browser_verify_table':
                # Find corresponding verification discovery (must be table_verification type)
                discovery = find_verification_discovery(step_num, discoveries)
                code += generate_verify_step(step_num, step_text, action, discovery, indent)
            
            else:
                # Unknown tool - add comment
                code += f"{ind}# Step {step_num}: {step_text[:80]}\n"
                code += f"{ind}# Tool: {tool} (not yet supported in generator)\n\n"
        
        return code

