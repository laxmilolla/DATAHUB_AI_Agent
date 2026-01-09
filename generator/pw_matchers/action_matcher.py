"""
Action Matcher - Match story steps to actions taken
Extracted from playwright_generator.py
"""
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def find_action_by_iteration(step_num: int, actions_taken: List[Dict]) -> Optional[Dict]:
    """
    Find action corresponding to a story step number by iteration
    Args:
        step_num: Story step number
        actions_taken: List of actions taken during execution
    Returns:
        Action dictionary or None
    """
    for action in actions_taken:
        if action.get('iteration') == step_num:
            return action
    return None


def find_action_by_content(step_text: str, step_num: int, actions_taken: List[Dict]) -> Optional[Dict]:
    """
    Find action by matching step content/type instead of iteration number.
    This is more reliable when story steps don't align with action iterations.
    
    Args:
        step_text: Story step text
        step_num: Story step number
        actions_taken: List of actions taken during execution
    Returns:
        Action dictionary or None
    """
    step_lower = step_text.lower()
    
    # Match by step content patterns
    if 'enter username' in step_lower or 'enter email' in step_lower or ('username' in step_lower and 'enter' in step_lower):
        # Find browser_fill with email selector
        for action in actions_taken:
            if action.get('tool') == 'browser_fill':
                selector = action.get('input', {}).get('selector', '')
                if 'email' in selector.lower() or 'username' in selector.lower():
                    return action
    
    elif 'enter password' in step_lower or ('password' in step_lower and 'enter' in step_lower):
        # Find browser_fill with password selector
        for action in actions_taken:
            if action.get('tool') == 'browser_fill':
                selector = action.get('input', {}).get('selector', '')
                if 'password' in selector.lower():
                    return action
    
    elif 'totp' in step_lower or 'one-time' in step_lower or 'authenticator' in step_lower:
        # Find browser_fill with TOTP/code selector
        for action in actions_taken:
            if action.get('tool') == 'browser_fill':
                selector = action.get('input', {}).get('selector', '')
                text = action.get('input', {}).get('text', '')
                if 'code' in selector.lower() or 'totp' in text.lower() or 'SYSTEM_GENERATED' in text:
                    return action
    
    elif 'click' in step_lower and 'submit' in step_lower:
        # Find browser_click with Submit selector
        for action in actions_taken:
            if action.get('tool') == 'browser_click':
                selector = action.get('input', {}).get('selector', '')
                if 'submit' in selector.lower() or 'button' in selector.lower():
                    # Check if it's actually a submit button
                    result = action.get('result', '')
                    if 'submit' in result.lower():
                        return action
                    # Also check by selector pattern
                    if 'submit' in selector.lower():
                        return action
    
    elif 'click' in step_lower and 'continue' in step_lower:
        # Find browser_click with Continue selector
        for action in actions_taken:
            if action.get('tool') == 'browser_click':
                selector = action.get('input', {}).get('selector', '')
                if 'continue' in selector.lower():
                    return action
    
    elif 'click' in step_lower and 'login' in step_lower:
        # Find browser_click with Login selector - prioritize exact matches
        # Extract element name from step (e.g., "Click On Login.gov button" -> "Login.gov")
        element_match = re.search(r'click\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+button|\s+link|\s+tab|$)', step_lower)
        element_name = element_match.group(1).strip() if element_match else ''
        
        # First pass: exact match
        for action in actions_taken:
            if action.get('tool') == 'browser_click':
                selector = action.get('input', {}).get('selector', '').lower()
                result = action.get('result', '').lower()
                # Exact match (e.g., "login.gov" matches "login.gov")
                if element_name and element_name.lower() in selector and selector.count(element_name.lower()) == 1:
                    return action
                if element_name and element_name.lower() in result:
                    return action
        
        # Second pass: substring match (fallback)
        for action in actions_taken:
            if action.get('tool') == 'browser_click':
                selector = action.get('input', {}).get('selector', '').lower()
                result = action.get('result', '').lower()
                if 'login' in selector or 'login' in result:
                    return action
    
    elif 'click' in step_lower and 'grant' in step_lower:
        # Find browser_click with Grant selector
        for action in actions_taken:
            if action.get('tool') == 'browser_click':
                selector = action.get('input', {}).get('selector', '')
                if 'grant' in selector.lower():
                    return action
    
    elif 'click' in step_lower:
        # Generic click - try to match by element name in step text
        # Extract element name from step (e.g., "Click on Login button" -> "Login")
        element_match = re.search(r'click\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+button|\s+link|\s+tab|$)', step_lower)
        if element_match:
            element_name = element_match.group(1).strip()
            element_name_lower = element_name.lower()
            
            # First pass: exact match (element name exactly matches selector text)
            for action in actions_taken:
                if action.get('tool') == 'browser_click':
                    selector = action.get('input', {}).get('selector', '').lower()
                    result = action.get('result', '').lower()
                    # Check for exact match (normalize text= prefix)
                    selector_text = selector.replace('text=', '').strip()
                    if selector_text == element_name_lower or element_name_lower == selector_text:
                        return action
                    # Also check result for exact match
                    if element_name_lower in result and result.count(element_name_lower) == 1:
                        return action
            
            # Second pass: substring match (fallback)
            for action in actions_taken:
                if action.get('tool') == 'browser_click':
                    selector = action.get('input', {}).get('selector', '').lower()
                    result = action.get('result', '').lower()
                    if element_name_lower in selector or element_name_lower in result:
                        return action
    
    # Fallback: Try iteration matching if content matching failed
    return find_action_by_iteration(step_num, actions_taken)


def find_wait_action(step_text: str, actions_taken: List[Dict]) -> Optional[Dict]:
    """
    Find wait action (browser_evaluate with setTimeout/Promise)
    Args:
        step_text: Story step text
        actions_taken: List of actions taken
    Returns:
        Wait action dictionary or None
    """
    wait_match = re.search(r'wait (\d+) seconds?', step_text, re.IGNORECASE)
    wait_duration = int(wait_match.group(1)) * 1000 if wait_match else None
    
    for act in actions_taken:
        if act.get('tool') == 'browser_evaluate':
            code_str = act.get('input', {}).get('code', '')
            if 'setTimeout' in code_str or 'Promise' in code_str:
                # Try to match duration if available
                if wait_duration:
                    code_duration_match = re.search(r'setTimeout.*?(\d+)', code_str)
                    if code_duration_match:
                        code_duration = int(code_duration_match.group(1))
                        if abs(code_duration - wait_duration) < 100:  # Allow small variance
                            return act
                # If no duration match or no duration specified, use first match
                return act
    
    return None


