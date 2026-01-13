"""
Prompt Builder - Build prompts for LLM
Extracted from bedrock_playwright_agent.py lines 3223-3282
"""
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Build prompts for LLM"""
    
    def __init__(self, story_parser):
        """
        Initialize prompt builder
        Args:
            story_parser: StoryParser instance
        """
        self.story_parser = story_parser
    
    def build_story_prompt(self, story: str, parsed_steps: Dict) -> str:
        """
        Build formatted story prompt with action hints
        Args:
            story: Original story text
            parsed_steps: Parsed steps metadata
        Returns: Formatted story with action hints
        """
        enhanced_story = []
        for line in story.strip().split('\n'):
            # Extract step identifier from line: "Step 1:" → "1", "Step 1 a:" → "1a"
            step_identifier = None
            if line.strip().startswith('Step'):
                step_match = re.match(r'Step\s+(\d+)\s*([a-z])?\s*[\.:)]?\s*', line, re.IGNORECASE)
                if step_match:
                    step_num = step_match.group(1)
                    sub_step = step_match.group(2)
                    step_identifier = f"{step_num}{sub_step.lower()}" if sub_step else step_num
            
            metadata = parsed_steps.get(step_identifier, {}) if step_identifier else {}
            action_hint = self._detect_action_type(line, metadata)
            enhanced_story.append(line + action_hint)
        
        formatted_story = '\n'.join(enhanced_story)
        logger.info(f"📝 Enhanced story with action hints:\n{formatted_story}")
        return formatted_story
    
    def _detect_action_type(self, line: str, metadata: Dict) -> str:
        """
        Detect action type for hint
        """
        if metadata.get('type') == 'checkbox':
            return " [ACTION: Click checkbox]"
        elif metadata.get('type') == 'accordion':
            return " [ACTION: Click to expand]"
        elif metadata.get('type') == 'tab':
            return " [ACTION: Click tab]"
        elif 'wait' in line.lower():
            return " [ACTION: Wait/No click]"
        elif 'verify' in line.lower():
            # Check if it's table verification or element verification
            if 'table' in line.lower() or 'column' in line.lower() or 'row' in line.lower():
                return " [ACTION: Use browser_verify_table]"
            else:
                return " [ACTION: Use browser_verify_element]"
        return ""
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for agent
        Returns: System prompt string
        """
        return """You are a QA automation agent. Use browser tools to execute tests.

CRITICAL: EXTRACT EXACT ELEMENT NAMES
Read each step carefully and extract the EXACT element name to click:

Examples:
- Step: "Select the Acute leukemia, NOS checkbox" → Click: text=Acute leukemia, NOS
- Step: "Click on DIAGNOSIS to expand" → Click: text=DIAGNOSIS  
- Step: "Click on Diagnosis tab" → Click: text=Diagnosis
- Step: "Click Continue button" → Click: text=Continue

DO NOT use words from previous steps or context. ONLY use the exact element name in the current step.

ACTION HINTS:
- [ACTION: Click checkbox] → Extract checkbox name, use browser_click("text=<exact name>")
- [ACTION: Click to expand] → Extract accordion name, use browser_click("text=<exact name>")
- [ACTION: Click tab] → Extract tab name, use browser_click("text=<exact name>")
- [ACTION: Wait/No click] → Use browser_evaluate to wait (e.g., await new Promise(r => setTimeout(r, 2000)))
- [ACTION: Use browser_verify_table] → Use browser_verify_table(column_name="<name>", expected_value="<value>")
- [ACTION: Use browser_verify_element] → Use browser_verify_element(element_description="<element name>", verification_type="present|visible|text|attribute", expected_value="<value if needed>")

ELEMENT SELECTION:
- For INPUT FIELDS (username, password, email, text inputs): Use CSS selectors like input[type="email"], input[type="password"], input[name="username"], etc.
- For BUTTONS/LINKS/TEXT: Use text= selectors with the EXACT element name from the step
- For DROPDOWNS: Use text= selector for the dropdown button, then select option
- System validates and finds the correct element automatically
- If element not found, system will use discovery methods

INPUT FIELD EXAMPLES:
- "enter username" → browser_fill("input[type='email']" or "input[name='username']", "value")
- "enter password" → browser_fill("input[type='password']", "value")
- "enter email" → browser_fill("input[type='email']", "value")

Take screenshots at key moments (after clicks, before verification)."""


