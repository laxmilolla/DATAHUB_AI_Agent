"""
Selector Utilities - Clean and normalize selectors
Extracted from playwright_generator.py
"""
import re
import logging

logger = logging.getLogger(__name__)


def clean_selector(selector: str) -> str:
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
    - Dynamic counts in text - e.g., 'Diagnosis(97)' -> 'Diagnosis'
    
    Keep:
    - [aria-expanded] without value - just checks attribute exists
    - Other attributes like [role='tab'], [role='button'], etc.
    """
    if not selector:
        return selector
    
    # Remove [aria-selected] and [aria-selected='true'/'false']
    selector = re.sub(r'\[aria-selected(?:=["\'](?:true|false)["\'])?\]', '', selector)
    
    # Remove [aria-expanded='true'] or [aria-expanded='false'] but keep [aria-expanded]
    # This regex looks for aria-expanded with a specific value
    selector = re.sub(r'\[aria-expanded=["\'](?:true|false)["\']?\]', '[aria-expanded]', selector)
    
    # Remove dynamic counts from has-text() - e.g., 'Diagnosis(97)' -> 'Diagnosis'
    # Match patterns like: has-text('Something(123)') or has-text('Something(1,234)')
    # This handles tabs/buttons that show counts which change dynamically
    selector = re.sub(r"(:has-text\(['\"])(.*?)\(\d+(?:,\d+)*\)(['\"])", r"\1\2\3", selector)
    
    return selector


def strip_dynamic_xpath(xpath: str) -> str:
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


def normalize_selector(selector: str) -> str:
    """
    Normalize selector for comparison (remove text= prefix, lowercase, strip)
    """
    if not selector:
        return ""
    
    normalized = selector.lower().strip()
    if normalized.startswith('text='):
        normalized = normalized[5:].strip()
    
    return normalized


def escape_string(text: str) -> str:
    """
    Escape string for Python string literals
    """
    if not text:
        return ""
    
    return text.replace("'", "\\'").replace('"', '\\"')


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a filename.
    Removes special characters and limits length.
    """
    if not name:
        return "element"
    
    # Replace special characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    # Limit length to 50 characters
    sanitized = sanitized[:50]
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized if sanitized else "element"

