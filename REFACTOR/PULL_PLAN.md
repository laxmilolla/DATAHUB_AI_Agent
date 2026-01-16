# Methodical Pull Plan - Excel Generator Production

This document outlines exactly what code to pull from the existing codebase, in what order, and how to integrate it.

## Pull Strategy

**Principle**: Pull one component at a time, test it, then move to the next.

---

## Phase 1: Core Excel Generator (Week 1, Days 1-2)

### Step 1.1: Copy Excel Generator ✅ DONE
**Source**: `generator/excel_generator.py`
**Destination**: `REFACTOR/generator/excel_generator.py`
**Status**: ✅ Copied

**What We Have**:
- ✅ All code generation functions
- ✅ XPath escaping
- ✅ TOTP handling
- ✅ Modal scoping
- ✅ TIMESTAMP replacement

**What to Enhance**:
- [ ] Add Excel validation
- [ ] Add error handling
- [ ] Add metadata tracking

### Step 1.2: Create Excel Validator
**Source**: New file (reference validation patterns from existing code)
**Destination**: `REFACTOR/generator/excel_validator.py`

**Code to Reference**:
- Look at `generator/pw_codegen/step_generators.py` for validation patterns
- Look at `agent/tools/browser_click.py` for selector validation

**Functions to Create**:
```python
def validate_excel_format(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate Excel file format"""
    errors = []
    
    # Check required columns
    required = ['Step', 'URL', 'XPath', 'Action']
    missing = [col for col in required if col not in df.columns]
    if missing:
        errors.append(f"Missing columns: {missing}")
    
    # Validate data types
    # Validate XPath syntax
    # Validate URLs
    # Check for duplicates
    
    return {'valid': len(errors) == 0, 'errors': errors}

def validate_xpath(xpath: str) -> bool:
    """Validate XPath syntax"""
    # Basic XPath validation
    if not xpath or xpath == 'N/A':
        return True
    # Check for basic XPath patterns
    return True  # For now, accept all

def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url or url == 'N/A':
        return True
    return url.startswith('http://') or url.startswith('https://')
```

### Step 1.3: Create Excel Template Generator
**Source**: New file
**Destination**: `REFACTOR/generator/excel_template.py`

**Code Pattern**: Similar to `test_excel_generator.py` Excel creation

**Functions to Create**:
```python
def generate_excel_template(output_path: Path) -> Path:
    """Generate Excel template with example data and instructions"""
    # Create example data
    # Add instructions sheet
    # Save to output_path
    return output_path
```

---

## Phase 2: API Integration (Week 1, Days 3-5)

### Step 2.1: Study Existing API Patterns
**Source**: `api/routes.py`
**What to Study**:
- File upload handling (if exists)
- Background thread execution
- Error handling patterns
- Response formats

**Key Patterns to Reuse**:
```python
# From api/routes.py line 518-582
@bp.route('/executions/<exec_id>/generate-and-validate', methods=['POST'])
def generate_and_validate(exec_id):
    # Pattern: Load data → Generate → Save → Return
    # Pattern: Background thread for test execution
    # Pattern: Error handling with try/except
```

### Step 2.2: Create Excel Upload Endpoint
**Destination**: Add to `api/routes.py` (or create `api/excel_routes.py`)

**Code to Pull**:
- File upload pattern (if exists in codebase)
- Error handling pattern from existing endpoints
- Response format from existing endpoints

**Implementation**:
```python
@bp.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    """Upload and validate Excel file"""
    # Pull pattern from existing file upload endpoints
    # Use validation from REFACTOR/generator/excel_validator.py
    # Save file to storage/excel_files/
    # Return excel_id
```

### Step 2.3: Create Excel Generate Endpoint
**Destination**: Add to `api/routes.py`

**Code to Pull**:
- Pattern from `/api/executions/<exec_id>/generate-and-validate`
- Background thread execution pattern
- Result format pattern

**Implementation**:
```python
@bp.route('/api/excel/generate', methods=['POST'])
def generate_from_excel():
    """Generate Playwright test from Excel"""
    # Pull pattern from generate_and_validate()
    # Use REFACTOR/generator/excel_generator.py
    # Save test to storage/excel_tests/
    # Optionally run test in background
```

### Step 2.4: Create Template Download Endpoint
**Destination**: Add to `api/routes.py`

**Code to Pull**:
- File download pattern from existing endpoints
- Use `send_file` from Flask

**Implementation**:
```python
@bp.route('/api/excel/template', methods=['GET'])
def download_excel_template():
    """Download Excel template"""
    # Use REFACTOR/generator/excel_template.py
    # Return file download
```

---

## Phase 3: Test Runner Integration (Week 2, Days 1-2)

### Step 3.1: Study Test Runner
**Source**: `validator/test_runner.py`
**What to Study**:
- Test execution logic
- Screenshot capture
- Result reporting
- Execution metadata structure

**Key Code to Reference**:
```python
# From validator/test_runner.py
class TestRunner:
    def run(self, test_filename: str, execution_id: str = None) -> Dict:
        # Study: How tests are executed
        # Study: How screenshots are captured
        # Study: How results are saved
```

### Step 3.2: Enhance Test Runner
**Destination**: Modify `validator/test_runner.py`

**Enhancement**:
```python
def run(self, test_filename: str, execution_id: str = None, 
        excel_id: str = None) -> Dict:
    """
    Run test with optional Excel file reference
    """
    # Existing execution logic...
    
    # Add Excel metadata if provided
    if excel_id:
        result['excel_id'] = excel_id
        result['excel_metadata'] = load_excel_metadata(excel_id)
    
    return result
```

---

## Phase 4: UI Integration (Week 2, Days 3-5)

### Step 4.1: Study Existing UI Patterns
**Source**: `web/templates/results.html`, `web/templates/index.html`
**What to Study**:
- File upload UI (if exists)
- Results display structure
- JavaScript patterns
- API call patterns

**Key Patterns to Reuse**:
```javascript
// From web/templates/results.html
async function generateAndValidate() {
    const response = await fetch(`/api/executions/${executionId}/generate-and-validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ... })
    });
    // Study: Error handling
    // Study: Result display
    // Study: Status updates
}
```

### Step 4.2: Create Excel Upload Page
**Destination**: `web/templates/excel_upload.html`

**Code to Pull**:
- HTML structure from `web/templates/index.html`
- CSS classes from existing templates
- JavaScript patterns from `web/static/js/app.js`

**Implementation**:
```html
<!-- Pull structure from index.html -->
<!-- Add file upload component -->
<!-- Add template download button -->
<!-- Add generate button -->
```

### Step 4.3: Create Excel Upload JavaScript
**Destination**: `web/static/js/excel_upload.js`

**Code to Pull**:
- API call patterns from `web/static/js/app.js`
- Error handling patterns
- Status update patterns

**Implementation**:
```javascript
// Pull patterns from app.js
// Adapt for Excel upload flow
// Add file upload handling
// Add validation feedback
// Add generate button handler
```

### Step 4.4: Enhance Results Page
**Destination**: Modify `web/templates/results.html`

**Enhancement**:
- Add Excel file reference display
- Show Excel metadata
- Link to Excel file download

**Code to Pull**:
- Results display structure (existing)
- Metadata display patterns (existing)

---

## Phase 5: Storage Structure (Week 2, Day 5)

### Step 5.1: Create Storage Directories
**Source**: Reference `storage/` structure
**Destination**: Create new directories

**Directories to Create**:
```bash
storage/excel_files/          # Uploaded Excel files
storage/excel_files/metadata/ # Excel metadata JSON
storage/excel_tests/          # Excel-generated tests (or reuse generated_tests/)
```

**Pattern to Follow**:
- Use same naming convention as `storage/executions/`
- Use timestamp-based IDs
- Store metadata in JSON format

### Step 5.2: Create Metadata Manager
**Destination**: `REFACTOR/generator/excel_metadata.py`

**Code to Pull**:
- Metadata structure from `storage/executions/` JSON files
- File naming patterns

**Functions to Create**:
```python
def save_excel_metadata(excel_id: str, excel_path: Path, 
                        test_file: str = None) -> Dict:
    """Save Excel file metadata"""
    # Follow pattern from execution metadata
    # Save to storage/excel_files/metadata/{excel_id}.json

def load_excel_metadata(excel_id: str) -> Dict:
    """Load Excel file metadata"""
    # Load from storage/excel_files/metadata/{excel_id}.json

def update_excel_metadata(excel_id: str, **updates) -> Dict:
    """Update Excel file metadata"""
    # Update metadata file
```

---

## Pull Checklist

### ✅ Phase 1: Core Generator
- [x] Copy Excel generator to REFACTOR
- [ ] Create Excel validator
- [ ] Create Excel template generator
- [ ] Test core generator standalone

### ⏳ Phase 2: API Integration
- [ ] Study existing API patterns
- [ ] Create Excel upload endpoint
- [ ] Create Excel generate endpoint
- [ ] Create template download endpoint
- [ ] Test API endpoints

### ⏳ Phase 3: Test Runner Integration
- [ ] Study test runner code
- [ ] Enhance test runner for Excel
- [ ] Test test execution

### ⏳ Phase 4: UI Integration
- [ ] Study existing UI patterns
- [ ] Create Excel upload page
- [ ] Create Excel upload JavaScript
- [ ] Enhance results page
- [ ] Test UI flow

### ⏳ Phase 5: Storage Structure
- [ ] Create storage directories
- [ ] Create metadata manager
- [ ] Test storage operations

### ⏳ Phase 6: Integration Testing
- [ ] End-to-end test: Upload → Generate → Run
- [ ] Test error handling
- [ ] Test edge cases
- [ ] Performance testing

---

## Code Reference Map

### Files to Reference (Study, Don't Copy)
| File | What to Study | Use For |
|------|--------------|---------|
| `api/routes.py` | API patterns, error handling | Excel API endpoints |
| `validator/test_runner.py` | Test execution, screenshots | Excel test execution |
| `web/templates/results.html` | Results display | Excel results display |
| `web/static/js/app.js` | JavaScript patterns | Excel upload JS |
| `agent/core/execution_context.py` | Execution metadata | Excel execution context |

### Files to Copy and Enhance
| File | Source | Destination | Enhancements |
|------|--------|-------------|--------------|
| `excel_generator.py` | `generator/excel_generator.py` | `REFACTOR/generator/` | Add validation, metadata |
| `test_excel_generator.py` | `test_excel_generator.py` | `REFACTOR/tests/` | Add production tests |

### Files to Create New
| File | Purpose | Reference |
|------|---------|-----------|
| `excel_validator.py` | Excel validation | Validation patterns |
| `excel_template.py` | Template generation | Excel creation patterns |
| `excel_metadata.py` | Metadata management | Execution metadata patterns |
| `excel_upload.html` | Upload UI | Existing upload pages |
| `excel_upload.js` | Upload JavaScript | `app.js` patterns |

---

## Integration Order

1. **Excel Generator** (Standalone) ✅
   - Copy → Enhance → Test

2. **Excel Validator** (Standalone)
   - Create → Test

3. **Excel Template** (Standalone)
   - Create → Test

4. **API Endpoints** (Integration)
   - Create → Test with Excel generator

5. **Test Runner** (Integration)
   - Enhance → Test with Excel tests

6. **UI Components** (Integration)
   - Create → Test with API

7. **Full System** (End-to-End)
   - Integrate all → Test complete flow

---

## Testing Strategy

### Unit Tests (Before Integration)
- [ ] Test Excel generator standalone
- [ ] Test Excel validator standalone
- [ ] Test Excel template generator standalone

### Integration Tests (During Integration)
- [ ] Test API + Excel generator
- [ ] Test API + Test runner
- [ ] Test UI + API

### End-to-End Tests (After Integration)
- [ ] Test full flow: Upload → Generate → Run → Results
- [ ] Test error scenarios
- [ ] Test edge cases

---

## Next Steps

1. ✅ Create REFACTOR folder structure
2. ✅ Copy Excel generator
3. ⏳ Create Excel validator
4. ⏳ Create Excel template generator
5. ⏳ Study API patterns
6. ⏳ Create API endpoints
7. ⏳ Integrate test runner
8. ⏳ Create UI components
9. ⏳ Full integration testing

