"""
Code Formatter - Formatting utilities for generated code
Extracted from playwright_generator.py
"""
import re
from typing import Dict


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """
    Sanitize name for use in filename
    Args:
        name: Name to sanitize
        max_length: Maximum length
    Returns:
        Sanitized name
    """
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    return safe_name[:max_length]


def escape_string(text: str) -> str:
    """
    Escape string for Python string literals
    Args:
        text: Text to escape
    Returns:
        Escaped text
    """
    if not text:
        return ""
    return text.replace("'", "\\'").replace('"', '\\"')


def generate_test_name(story: str) -> str:
    """
    Generate test name from story
    Args:
        story: Story text
    Returns:
        Test function name
    """
    # Extract meaningful words
    words = re.findall(r'\b[a-z]{4,}\b', story.lower())
    # Take first 3-4 meaningful words
    name_words = [w for w in words if w not in ['click', 'verify', 'check', 'should', 'will', 'that', 'the', 'and', 'for']][:3]
    name = '_'.join(name_words) if name_words else 'test'
    return f"test_{name}"





