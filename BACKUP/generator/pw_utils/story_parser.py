"""
Story Parser - Parse story text into structured steps
Extracted from playwright_generator.py
"""
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def parse_story_steps(story: str) -> List[Dict]:
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


def extract_step_number(line: str) -> int:
    """Extract step number from story line"""
    step_match = re.match(r'[Ss]teps?\s+(\d+)', line, re.IGNORECASE)
    if step_match:
        return int(step_match.group(1))
    return None


def extract_step_text(line: str) -> str:
    """Extract step text from story line"""
    step_match = re.match(r'[Ss]teps?\s+\d+\s*:?\s*(.+)', line, re.IGNORECASE)
    if step_match:
        return step_match.group(1).strip()
    return ""


def is_optional_step(step_text: str) -> bool:
    """Check if step is optional (e.g., 'if there is', 'optional')"""
    step_lower = step_text.lower()
    return 'optional' in step_lower or 'if there is' in step_lower





