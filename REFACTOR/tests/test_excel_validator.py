"""
Test Excel Validator
Tests the Excel file validation functionality.
"""
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from REFACTOR.generator.excel_validator import (
    validate_excel_format,
    validate_xpath,
    validate_url,
    validate_excel_file,
    get_validation_summary
)


def test_validate_xpath():
    """Test XPath validation"""
    print("Testing XPath validation...")
    
    # Valid XPaths
    assert validate_xpath("//button[@type='submit']") == True
    assert validate_xpath("//input[@type='text']") == True
    assert validate_xpath("/html/body/div") == True
    assert validate_xpath("N/A") == True
    assert validate_xpath("(//div)[1]") == True
    
    # Invalid XPaths
    assert validate_xpath("") == False
    assert validate_xpath("//button['unclosed") == False  # Unclosed quote
    # Note: //button[unclosed] is actually valid XPath syntax (attribute check without quotes)
    # So we test with truly invalid: unclosed bracket
    assert validate_xpath("//button[unclosed") == False  # Unclosed bracket
    
    print("✅ XPath validation tests passed")


def test_validate_url():
    """Test URL validation"""
    print("Testing URL validation...")
    
    # Valid URLs
    assert validate_url("https://example.com") == True
    assert validate_url("http://example.com/page") == True
    assert validate_url("https://example.com/path?query=value") == True
    assert validate_url("N/A") == True
    
    # Invalid URLs
    assert validate_url("") == False
    assert validate_url("not-a-url") == False
    assert validate_url("ftp://example.com") == False  # Only http/https allowed
    
    print("✅ URL validation tests passed")


def test_validate_excel_format():
    """Test Excel format validation"""
    print("Testing Excel format validation...")
    
    # Create valid DataFrame
    valid_data = {
        'Step': [1, 2, 3],
        'URL': ['https://example.com', 'https://example.com/page', 'N/A'],
        'XPath': ['//button[@type="submit"]', '//input[@type="text"]', 'N/A'],
        'Action': ['navigate', 'click', 'fill']
    }
    df_valid = pd.DataFrame(valid_data)
    
    result = validate_excel_format(df_valid)
    assert result['valid'] == True, f"Expected valid, got errors: {result['errors']}"
    print("✅ Valid Excel format test passed")
    
    # Create invalid DataFrame (missing required column)
    invalid_data = {
        'Step': [1, 2],
        'URL': ['https://example.com', 'https://example.com']
        # Missing XPath and Action
    }
    df_invalid = pd.DataFrame(invalid_data)
    
    result = validate_excel_format(df_invalid)
    assert result['valid'] == False, "Expected invalid format"
    assert len(result['errors']) > 0, "Should have errors"
    print("✅ Invalid Excel format test passed")
    
    # Test with invalid URL
    invalid_url_data = {
        'Step': [1],
        'URL': ['not-a-valid-url'],
        'XPath': ['//button'],
        'Action': ['click']
    }
    df_invalid_url = pd.DataFrame(invalid_url_data)
    
    result = validate_excel_format(df_invalid_url)
    assert result['valid'] == False, "Expected invalid due to bad URL"
    print("✅ Invalid URL detection test passed")


def test_validate_excel_file():
    """Test Excel file validation"""
    print("Testing Excel file validation...")
    
    # Test non-existent file
    result = validate_excel_file(Path("nonexistent.xlsx"))
    assert result['valid'] == False
    assert len(result['errors']) > 0
    print("✅ Non-existent file test passed")
    
    # Test invalid extension
    result = validate_excel_file(Path(__file__))  # This is a .py file
    assert result['valid'] == False
    assert any('extension' in error.lower() for error in result['errors'])
    print("✅ Invalid extension test passed")


def test_validation_summary():
    """Test validation summary generation"""
    print("Testing validation summary...")
    
    result = {
        'valid': True,
        'errors': [],
        'warnings': ['Some warning'],
        'row_count': 10
    }
    
    summary = get_validation_summary(result)
    assert '✅' in summary
    assert '10' in summary
    assert 'warning' in summary.lower()
    print("✅ Validation summary test passed")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Excel Validator")
    print("=" * 50)
    
    try:
        test_validate_xpath()
        test_validate_url()
        test_validate_excel_format()
        test_validate_excel_file()
        test_validation_summary()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

