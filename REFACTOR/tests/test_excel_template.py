"""
Test Excel Template Generator
Tests the Excel template generation functionality.
"""
import pandas as pd
from pathlib import Path
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from REFACTOR.generator.excel_template import (
    generate_excel_template,
    get_template_path,
    _get_example_rows
)


def test_generate_template():
    """Test template generation"""
    print("Testing template generation...")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        # Generate template
        result_path = generate_excel_template(tmp_path, include_examples=True)
        
        # Verify file exists
        assert result_path.exists(), "Template file should exist"
        assert result_path == tmp_path, "Returned path should match input"
        
        # Verify file is valid Excel
        df = pd.read_excel(result_path, sheet_name="Test Steps")
        
        # Check required columns
        required_columns = ['Step', 'URL', 'XPath', 'Object Type', 'Action', 
                          'Functions', 'Text Value', 'Wait Time', 'Optional']
        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"
        
        # Check example rows exist
        assert len(df) > 0, "Template should have example rows"
        
        # Check instructions sheet exists
        xl_file = pd.ExcelFile(result_path)
        assert "Instructions" in xl_file.sheet_names, "Should have Instructions sheet"
        
        print("✅ Template generation test passed")
        
    finally:
        # Cleanup
        if tmp_path.exists():
            tmp_path.unlink()


def test_template_without_examples():
    """Test template generation without examples"""
    print("Testing template without examples...")
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        # Generate template without examples
        result_path = generate_excel_template(tmp_path, include_examples=False)
        
        # Verify file exists
        assert result_path.exists(), "Template file should exist"
        
        # Verify file is valid Excel
        df = pd.read_excel(result_path, sheet_name="Test Steps")
        
        # Should only have header row
        assert len(df) == 0, "Template without examples should have no data rows"
        
        print("✅ Template without examples test passed")
        
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_example_rows():
    """Test example rows are generic"""
    print("Testing example rows are generic...")
    
    example_rows = _get_example_rows()
    
    # Check all examples are generic (no application-specific URLs)
    for row in example_rows:
        url = row[1]  # URL is second column
        if url and url.upper() != 'N/A':
            # Should be generic example.com or similar
            assert 'example.com' in url.lower() or url.startswith('https://'), \
                f"Example URL should be generic, got: {url}"
    
    # Check XPaths are generic
    for row in example_rows:
        xpath = row[2]  # XPath is third column
        if xpath and xpath.upper() != 'N/A':
            # Should not contain application-specific selectors
            assert 'data-testid' not in xpath.lower() or 'example' in xpath.lower(), \
                f"Example XPath should be generic, got: {xpath}"
    
    print("✅ Example rows generic test passed")


def test_get_template_path():
    """Test template path generation"""
    print("Testing template path generation...")
    
    path = get_template_path("test_template.xlsx")
    
    # Should be in storage/excel_files/templates/
    assert "storage" in str(path), "Path should include storage directory"
    assert "excel_files" in str(path), "Path should include excel_files directory"
    assert "templates" in str(path), "Path should include templates directory"
    assert path.name == "test_template.xlsx", "Filename should match"
    
    print("✅ Template path generation test passed")


def test_template_structure():
    """Test template structure"""
    print("Testing template structure...")
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        # Generate template
        generate_excel_template(tmp_path, include_examples=True)
        
        # Read Excel file
        xl_file = pd.ExcelFile(tmp_path)
        
        # Should have two sheets
        assert len(xl_file.sheet_names) == 2, "Should have 2 sheets"
        assert "Test Steps" in xl_file.sheet_names, "Should have Test Steps sheet"
        assert "Instructions" in xl_file.sheet_names, "Should have Instructions sheet"
        
        # Read instructions sheet
        df_instructions = pd.read_excel(tmp_path, sheet_name="Instructions")
        assert len(df_instructions) > 0, "Instructions sheet should have content"
        
        print("✅ Template structure test passed")
        
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Excel Template Generator")
    print("=" * 50)
    
    try:
        test_generate_template()
        test_template_without_examples()
        test_example_rows()
        test_get_template_path()
        test_template_structure()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

