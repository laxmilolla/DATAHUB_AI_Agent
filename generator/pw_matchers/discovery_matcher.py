"""
Discovery Matcher - Match discoveries to story steps
Extracted from playwright_generator.py
"""
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def find_verification_discovery(step_num: int, discoveries: List[Dict]) -> Optional[Dict]:
    """
    Find table_verification discovery for a verify step.
    Returns the first table_verification discovery found (there's usually only one).
    
    Args:
        step_num: Story step number
        discoveries: List of discovery dictionaries
    Returns:
        Verification discovery dictionary or None
    """
    for disc in discoveries:
        if disc.get('discovery_method') == 'table_verification':
            logger.info(f"  ✅ Found table verification discovery for step {step_num}")
            return disc
    
    logger.warning(f"  ⚠️ No table verification discovery found for step {step_num}")
    return None


def find_discovery_by_step(step_num: int, step_text: str, discoveries: List[Dict], action: Dict) -> Optional[Dict]:
    """
    Find discovery metadata that matches this step.
    Match by comparing action's selector with discovery's original_query AND actual clicked selector.
    Also considers step context (e.g., "tab" in step text should match tab discoveries).
    This prevents wrong matches (e.g., checkbox being matched with table verification, tab vs accordion).
    
    Args:
        step_num: Story step number
        step_text: Story step text
        discoveries: List of discovery dictionaries
        action: Action dictionary from actions_taken
    Returns:
        Matching discovery dictionary or None
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
    
    # NOTE: We DON'T match by discovery's step_number directly because:
    # - Discovery's step_number is the AI's action step_number (iteration-based)
    # - Story step_number is the user's story step number
    # - These don't always align (e.g., "Step 1 a" increments action step_number but not story step)
    # Instead, we match by action selector/content, which is more reliable
    
    # If no step_number match, continue with normal matching
    for disc in discoveries:
        disc_query = disc.get('original_query', '').lower().strip()
        if disc_query.startswith('text='):
            disc_query = disc_query[5:].strip()
        
        # Skip verification discoveries (they don't have element selectors)
        if disc.get('discovery_method') == 'table_verification':
            continue
        
        # Check if discovery matches the actual clicked selector (highest priority)
        disc_final_selector = (disc.get('final_selector') or '').lower()
        disc_xpath = (disc.get('xpath') or '').lower()
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
        disc_is_accordion = 'accordion' in disc.get('name', '').lower() or ('button' in disc_final_selector and 'aria-expanded' in disc_final_selector)
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


def find_discovery_by_name(element_name: str, discoveries: List[Dict]) -> Optional[Dict]:
    """
    Find discovery by element name (simple lookup)
    Args:
        element_name: Name of the element
        discoveries: List of discovery dictionaries
    Returns:
        Matching discovery dictionary or None
    """
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


