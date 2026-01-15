# No Hard-Coding Rules - Critical

## ⚠️ CRITICAL RULE: NO HARD-CODING

**NEVER hard-code application-specific selectors, IDs, or values in production code.**

## Rules for Excel Generator Components

### ✅ ALLOWED
- Generic patterns: `[role="dialog"]`, `.MuiDialog-root`
- ARIA attributes: `[role="button"]`, `[aria-label="..."]`
- Dynamic attribute extraction: `await dialog.get_attribute('data-testid')`
- Environment variables: `os.getenv('TOTP_SECRET_KEY')`
- Configuration values from `.env` or config files
- Generic CSS patterns: `input[type='password']`, `button[type='submit']`

### ❌ NOT ALLOWED
- Application-specific selectors: `[data-testid="create-submission-dialog"]` ❌
- Hard-coded IDs: `#mui-component-select-studyID` ❌
- Application-specific strings: `'create-submission-dialog'` ❌
- Hard-coded URLs (unless from config): `'https://hub-stage.datacommons.cancer.gov'` ❌
- Hard-coded element names: `'datacommons'`, `'study'` ❌

## Excel Validator Rules

### ✅ ALLOWED
```python
# Generic validation
def validate_xpath(xpath: str) -> bool:
    """Validate XPath syntax - generic only"""
    if not xpath or xpath == 'N/A':
        return True
    # Check for basic XPath patterns (generic)
    return xpath.startswith('//') or xpath.startswith('/')
```

### ❌ NOT ALLOWED
```python
# Hard-coded application-specific validation
def validate_xpath(xpath: str) -> bool:
    if 'create-submission-dialog' in xpath:  # ❌ HARD-CODED
        return True
    if 'study' in xpath.lower():  # ❌ HARD-CODED
        return True
```

## Excel Template Generator Rules

### ✅ ALLOWED
```python
# Generic example data
example_data = {
    'Step': [1, 2, 3],
    'Action': ['navigate', 'click', 'fill'],
    'Object Type': ['button', 'input', 'link'],
}
```

### ❌ NOT ALLOWED
```python
# Hard-coded application-specific examples
example_data = {
    'XPath': ['//*[@data-testid="create-submission-dialog"]'],  # ❌ HARD-CODED
    'URL': ['https://hub-stage.datacommons.cancer.gov'],  # ❌ HARD-CODED
}
```

## API Endpoints Rules

### ✅ ALLOWED
```python
# Generic file upload pattern
@bp.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    file = request.files.get('file')
    # Generic validation
    if not file or not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'Invalid file'}), 400
```

### ❌ NOT ALLOWED
```python
# Hard-coded application-specific logic
@bp.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    if 'datacommons' not in file.filename:  # ❌ HARD-CODED
        return jsonify({'error': 'Must be datacommons file'}), 400
```

## UI Components Rules

### ✅ ALLOWED
```javascript
// Generic file upload
const fileInput = document.querySelector('input[type="file"]');
const formData = new FormData();
formData.append('file', fileInput.files[0]);
```

### ❌ NOT ALLOWED
```javascript
// Hard-coded application-specific selectors
const dialog = document.querySelector('[data-testid="create-submission-dialog"]');  // ❌ HARD-CODED
const studyDropdown = document.getElementById('mui-component-select-studyID');  // ❌ HARD-CODED
```

## Storage Structure Rules

### ✅ ALLOWED
```python
# Generic storage paths
storage_dir = Path('storage') / 'excel_files'
metadata_dir = storage_dir / 'metadata'
```

### ❌ NOT ALLOWED
```python
# Hard-coded application-specific paths
storage_dir = Path('storage') / 'datacommons_excel_files'  # ❌ HARD-CODED
```

## Test Files Exception

### ✅ ALLOWED IN TEST FILES ONLY
Hard-coding is **ONLY allowed** in test/debug scripts (e.g., `test_*.py`):

```python
# test_excel_generator.py - OK to hard-code for testing
test_data = {
    'XPath': ['//*[@data-testid="create-submission-dialog"]'],  # ✅ OK in test
    'URL': ['https://hub-stage.datacommons.cancer.gov'],  # ✅ OK in test
}
```

## Checklist for Each Component

Before creating any component, verify:

- [ ] No application-specific selectors hard-coded
- [ ] No application-specific IDs hard-coded
- [ ] No application-specific URLs hard-coded (unless from config)
- [ ] No application-specific element names hard-coded
- [ ] All values come from:
  - User input (Excel file)
  - Environment variables
  - Configuration files
  - Generic patterns/detection
- [ ] Test files can have hard-coded values (for testing only)

## Examples of Good vs Bad

### Excel Validator

**✅ GOOD:**
```python
def validate_excel_format(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate Excel file format - generic"""
    required_columns = ['Step', 'URL', 'XPath', 'Action']
    missing = [col for col in required_columns if col not in df.columns]
    # Generic validation only
```

**❌ BAD:**
```python
def validate_excel_format(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate Excel file format"""
    # Hard-coded application-specific validation
    if 'datacommons' not in df['URL'].values:  # ❌ HARD-CODED
        errors.append('Must include datacommons URLs')
```

### Excel Template Generator

**✅ GOOD:**
```python
def generate_excel_template(output_path: Path) -> Path:
    """Generate generic Excel template"""
    example_data = {
        'Step': [1, 2, 3],
        'URL': ['https://example.com', 'https://example.com/page', 'N/A'],
        'XPath': ['//button[@type="submit"]', '//input[@type="text"]', 'N/A'],
        'Action': ['navigate', 'click', 'fill'],
    }
```

**❌ BAD:**
```python
def generate_excel_template(output_path: Path) -> Path:
    """Generate Excel template"""
    example_data = {
        'URL': ['https://hub-stage.datacommons.cancer.gov'],  # ❌ HARD-CODED
        'XPath': ['//*[@data-testid="create-submission-dialog"]'],  # ❌ HARD-CODED
    }
```

---

## Summary

**Rule**: Everything must be generic and configurable. No application-specific hard-coding in production code.

**Exception**: Test files (`test_*.py`) can have hard-coded values for testing purposes only.

