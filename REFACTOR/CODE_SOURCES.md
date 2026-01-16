# Code Sources - What to Pull From Where

**IMPORTANT**: All existing codebase is now in `BACKUP/` folder. Pull from BACKUP methodically.

## Excel Generator Core

### File: `REFACTOR/generator/excel_generator.py`
**Source**: `BACKUP/generator/excel_generator.py` → Already copied to REFACTOR
**Status**: ✅ Working
**Functions to Keep**:
- `escape_xpath()` - ✅ Keep as-is
- `escape_text()` - ✅ Keep as-is
- `generate_navigate_code()` - ✅ Keep as-is
- `generate_wait_code()` - ✅ Keep as-is
- `generate_click_code()` - ✅ Keep, enhance modal support
- `generate_fill_code()` - ✅ Keep, enhance TOTP and modal support
- `generate_verify_code()` - ✅ Keep as-is
- `generate_playwright_from_excel()` - ✅ Keep, enhance validation

**Enhancements Needed**:
- Add Excel validation
- Add metadata tracking
- Add error handling
- Add template generation support

---

## Test Runner Integration

### File: `validator/test_runner.py`
**Source**: `BACKUP/validator/test_runner.py` (existing production code)
**Status**: ✅ Working
**What to Pull**:
- Test execution logic
- Screenshot capture
- Result reporting
- Background thread execution

**Enhancements Needed**:
- Add Excel file reference to execution metadata
- Link Excel ID to test execution
- Store Excel metadata in results

**Integration Point**:
```python
# In validator/test_runner.py
def run(self, test_filename: str, execution_id: str = None, 
        excel_id: str = None) -> Dict:
    """
    Run test with optional Excel file reference
    """
    # Existing logic...
    # Add: if excel_id: metadata['excel_id'] = excel_id
```

---

## API Routes

### File: `api/routes.py`
**Source**: `BACKUP/api/routes.py` (existing production code)
**Status**: ✅ Working
**What to Pull**:
- Flask Blueprint pattern
- File upload handling (if exists)
- Background thread execution
- Result polling mechanism

**New Endpoints to Add**:
1. `POST /api/excel/upload` - Upload Excel file
2. `POST /api/excel/generate` - Generate test from Excel
3. `GET /api/excel/template` - Download template
4. `GET /api/excel/<id>/metadata` - Get Excel metadata

**Pattern to Follow**:
```python
# Similar to existing /api/executions/<exec_id>/generate-and-validate
@bp.route('/api/excel/generate', methods=['POST'])
def generate_from_excel():
    # Follow same pattern as generate_and_validate()
```

---

## UI Components

### File: `web/templates/results.html`
**Source**: `BACKUP/web/templates/results.html` (existing production code)
**Status**: ✅ Working
**What to Pull**:
- Results display structure
- Screenshot gallery
- Step-by-step view
- Status indicators

**Enhancements Needed**:
- Add Excel file reference display
- Show Excel metadata
- Link to Excel file download

### New File: `web/templates/excel_upload.html`
**Source**: New file
**Pattern to Follow**: Similar to existing upload pages
**Components**:
- File upload (drag & drop)
- Template download button
- Validation feedback
- Generate button

---

## Storage Structure

### Directory: `storage/`
**Source**: `BACKUP/storage/` (existing production structure - reference only)
**Status**: ✅ Working
**What to Pull**:
- `storage/executions/` - Execution JSON files
- `storage/screenshots/` - Screenshot files
- `storage/generated_tests/` - Generated test files

**New Directories to Add**:
- `storage/excel_files/` - Uploaded Excel files
- `storage/excel_files/metadata/` - Excel metadata JSON
- `storage/excel_tests/` - Excel-generated tests (or reuse generated_tests/)

---

## Environment and Configuration

### File: `.env`
**Source**: Existing production
**Status**: ✅ Working
**What to Pull**:
- TOTP_SECRET_KEY handling
- Environment variable loading
- Configuration patterns

**No Changes Needed**: ✅ Reuse as-is

---

## Pull Order (Methodical)

### Step 1: Excel Generator Core ✅
- [x] Copy `generator/excel_generator.py` to REFACTOR
- [ ] Enhance with validation
- [ ] Add metadata tracking
- [ ] Test standalone

### Step 2: Excel Validator
- [ ] Create `generator/excel_validator.py`
- [ ] Implement validation logic
- [ ] Test validation

### Step 3: Excel Template Generator
- [ ] Create `generator/excel_template.py`
- [ ] Generate template with examples
- [ ] Test template generation

### Step 4: API Integration
- [ ] Reference `api/routes.py` patterns
- [ ] Add Excel upload endpoint
- [ ] Add Excel generate endpoint
- [ ] Add template download endpoint
- [ ] Test API endpoints

### Step 5: Test Runner Integration
- [ ] Reference `validator/test_runner.py`
- [ ] Add Excel metadata support
- [ ] Test execution with Excel reference

### Step 6: UI Integration
- [ ] Reference `web/templates/results.html`
- [ ] Create Excel upload page
- [ ] Enhance results page
- [ ] Test UI flow

### Step 7: Full Integration
- [ ] Integrate all components
- [ ] End-to-end testing
- [ ] Production deployment

---

## Code References

### Files to Reference (Not Copy)
- `validator/test_runner.py` - Reference for test execution
- `validator/comparator.py` - Reference for result comparison
- `api/routes.py` - Reference for API patterns
- `web/templates/results.html` - Reference for UI patterns
- `agent/core/execution_context.py` - Reference for execution context

### Files to Copy and Enhance
- `generator/excel_generator.py` - Copy → Enhance
- `test_excel_generator.py` - Copy → Enhance

### Files to Create New
- `generator/excel_validator.py` - New
- `generator/excel_template.py` - New
- `generator/excel_metadata.py` - New
- `web/templates/excel_upload.html` - New
- `web/static/js/excel_upload.js` - New

