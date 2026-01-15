"""
Excel File Validator
Validates Excel file format and data for Playwright test generation.
All validation is generic - no application-specific hard-coding.
"""
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse


def validate_excel_format(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate Excel file format and structure.
    
    Args:
        df: Pandas DataFrame from Excel file
        
    Returns:
        Dict with 'valid' (bool) and 'errors' (list of error messages)
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    # Check if DataFrame is empty
    if df.empty:
        errors.append("Excel file is empty")
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Normalize column names (case-insensitive, handle spaces)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Required columns
    required_columns = ['step', 'url', 'xpath', 'action']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Check for empty required columns
    for col in required_columns:
        if col in df.columns:
            empty_count = df[col].isna().sum() + (df[col] == '').sum()
            if empty_count > 0:
                warnings.append(f"Column '{col}' has {empty_count} empty values")
    
    # Validate data types
    if 'step' in df.columns:
        # Step should be numeric or string
        invalid_steps = df[df['step'].notna() & ~df['step'].astype(str).str.match(r'^[\d\w]+$')]
        if not invalid_steps.empty:
            warnings.append(f"Some step values may be invalid (non-alphanumeric)")
    
    # Validate each row
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row number (accounting for header)
        row_errors = _validate_row(row, row_num)
        if row_errors:
            errors.extend(row_errors)
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'row_count': len(df)
    }


def _validate_row(row: pd.Series, row_num: int) -> List[str]:
    """
    Validate a single row of Excel data.
    
    Args:
        row: Pandas Series representing one row
        row_num: Row number in Excel (for error messages)
        
    Returns:
        List of error messages for this row
    """
    errors: List[str] = []
    
    # Validate URL (if present and not N/A)
    if 'url' in row.index and pd.notna(row.get('url')):
        url = str(row['url']).strip()
        if url and url.upper() != 'N/A':
            if not validate_url(url):
                errors.append(f"Row {row_num}: Invalid URL format: '{url}'")
    
    # Validate XPath (if present and not N/A)
    if 'xpath' in row.index and pd.notna(row.get('xpath')):
        xpath = str(row['xpath']).strip()
        if xpath and xpath.upper() != 'N/A':
            if not validate_xpath(xpath):
                errors.append(f"Row {row_num}: Invalid XPath syntax: '{xpath}'")
    
    # Validate Action (if present)
    if 'action' in row.index and pd.notna(row.get('action')):
        action = str(row['action']).strip().lower()
        valid_actions = ['navigate', 'click', 'fill', 'verify', 'wait']
        if action and action not in valid_actions:
            errors.append(f"Row {row_num}: Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
    
    # Validate Object Type (if present)
    if 'object_type' in row.index and pd.notna(row.get('object_type')):
        obj_type = str(row['object_type']).strip().lower()
        valid_types = ['button', 'input', 'link', 'dropdown', 'checkbox', 'radio', 'text', 'div', 'span', 'a']
        if obj_type and obj_type not in valid_types:
            warnings = []  # Object type is optional, so warnings only
            # Note: We don't add to errors, just note it
    
    # Validate Wait Time (if present and action is 'wait')
    if 'wait_time' in row.index and pd.notna(row.get('wait_time')):
        wait_time = row['wait_time']
        if 'action' in row.index and str(row.get('action', '')).strip().lower() == 'wait':
            try:
                wait_val = int(float(wait_time))
                if wait_val < 0:
                    errors.append(f"Row {row_num}: Wait time must be non-negative, got: {wait_time}")
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: Wait time must be numeric, got: {wait_time}")
    
    # Validate Optional flag (if present)
    if 'optional' in row.index and pd.notna(row.get('optional')):
        optional_val = str(row['optional']).strip().lower()
        if optional_val not in ['true', 'false', 'yes', 'no', '1', '0', '']:
            warnings = []  # Optional flag is optional, so warnings only
    
    return errors


def validate_xpath(xpath: str) -> bool:
    """
    Validate XPath syntax (basic validation).
    Generic validation only - no application-specific checks.
    
    Args:
        xpath: XPath string to validate
        
    Returns:
        True if XPath appears valid, False otherwise
    """
    if not xpath or not isinstance(xpath, str):
        return False
    
    xpath = xpath.strip()
    
    # Allow N/A
    if xpath.upper() == 'N/A':
        return True
    
    # Basic XPath patterns
    # Must start with / or // or ( or . or contain @ or [
    if not (xpath.startswith('/') or 
            xpath.startswith('//') or 
            xpath.startswith('(') or 
            xpath.startswith('.') or
            '@' in xpath or
            '[' in xpath):
        # Allow simple selectors like "button" or "input[type='text']"
        # But require at least some XPath-like structure
        if not re.match(r'^[\w\[\]()@=\'\"\s\.\/]+$', xpath):
            return False
    
    # Check for balanced brackets (accounting for escaped quotes)
    # Count brackets outside of quoted strings
    bracket_count = 0
    paren_count = 0
    in_single_quote = False
    in_double_quote = False
    escape_next = False
    
    for i, char in enumerate(xpath):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        
        if not in_single_quote and not in_double_quote:
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
            elif char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
    
    if bracket_count != 0:
        return False
    
    if paren_count != 0:
        return False
    
    # Check for balanced quotes (simple check)
    # Count unescaped quotes
    single_quotes = 0
    double_quotes = 0
    escape_next = False
    
    for char in xpath:
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == "'":
            single_quotes += 1
        elif char == '"':
            double_quotes += 1
    
    if single_quotes % 2 != 0 or double_quotes % 2 != 0:
        return False
    
    return True


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    Generic validation only - no application-specific checks.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL appears valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    # Allow N/A
    if url.upper() == 'N/A':
        return True
    
    # Basic URL validation using urllib.parse
    try:
        result = urlparse(url)
        # Must have scheme (http/https)
        if not result.scheme:
            return False
        
        # Scheme must be http or https
        if result.scheme not in ['http', 'https']:
            return False
        
        # Must have netloc (domain)
        if not result.netloc:
            return False
        
        return True
    except Exception:
        return False


def validate_excel_file(excel_path: Path) -> Dict[str, Any]:
    """
    Validate Excel file (file existence and format).
    
    Args:
        excel_path: Path to Excel file
        
    Returns:
        Dict with validation results
    """
    errors: List[str] = []
    
    # Check file exists
    if not excel_path.exists():
        errors.append(f"Excel file not found: {excel_path}")
        return {'valid': False, 'errors': errors}
    
    # Check file extension
    if excel_path.suffix.lower() not in ['.xlsx', '.xls']:
        errors.append(f"Invalid file extension. Expected .xlsx or .xls, got: {excel_path.suffix}")
        return {'valid': False, 'errors': errors}
    
    # Try to read Excel file
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        errors.append(f"Failed to read Excel file: {str(e)}")
        return {'valid': False, 'errors': errors}
    
    # Validate format
    format_result = validate_excel_format(df)
    
    return {
        'valid': format_result['valid'],
        'errors': errors + format_result['errors'],
        'warnings': format_result.get('warnings', []),
        'row_count': format_result.get('row_count', 0)
    }


def get_validation_summary(validation_result: Dict[str, Any]) -> str:
    """
    Get human-readable validation summary.
    
    Args:
        validation_result: Result from validate_excel_file() or validate_excel_format()
        
    Returns:
        Formatted summary string
    """
    lines = []
    
    if validation_result['valid']:
        lines.append("✅ Excel file validation passed")
    else:
        lines.append("❌ Excel file validation failed")
    
    if validation_result.get('row_count'):
        lines.append(f"📊 Rows: {validation_result['row_count']}")
    
    if validation_result.get('errors'):
        lines.append(f"\n❌ Errors ({len(validation_result['errors'])}):")
        for error in validation_result['errors']:
            lines.append(f"  • {error}")
    
    if validation_result.get('warnings'):
        lines.append(f"\n⚠️  Warnings ({len(validation_result['warnings'])}):")
        for warning in validation_result['warnings']:
            lines.append(f"  • {warning}")
    
    return "\n".join(lines)

