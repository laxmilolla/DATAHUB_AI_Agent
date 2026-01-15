# Exact Pull List - What to Pull from BACKUP

**Rule**: Pull ONLY what's needed. Nothing more, nothing less.

---

## ✅ Already Done

- [x] `generator/excel_generator.py` → Already in `REFACTOR/generator/`
- [x] `test_excel_generator.py` → Already in `REFACTOR/tests/`

---

## 📋 Files to Pull (In Order)

### Phase 1: Core Generator Support (Do First)

#### 1. Excel Validator - CREATE NEW
**Source**: Reference patterns from `BACKUP/generator/pw_codegen/step_generators.py` (if exists)
**Destination**: `REFACTOR/generator/excel_validator.py`
**Action**: CREATE NEW FILE (reference validation patterns, don't copy)
**Functions Needed**:
- `validate_excel_format(df)` - Check required columns, data types
- `validate_xpath(xpath)` - Basic XPath syntax check
- `validate_url(url)` - URL format check

#### 2. Excel Template Generator - CREATE NEW
**Source**: Reference `REFACTOR/tests/test_excel_generator.py` Excel creation pattern
**Destination**: `REFACTOR/generator/excel_template.py`
**Action**: CREATE NEW FILE (use pattern from test script)
**Functions Needed**:
- `generate_excel_template(output_path)` - Create template with examples

---

### Phase 2: API Integration (Pull Patterns Only)

#### 3. API Routes - REFERENCE PATTERNS
**Source**: `BACKUP/api/routes.py`
**Destination**: Create new endpoints in `REFACTOR/api/excel_routes.py` OR add to existing `api/routes.py`
**Action**: **STUDY ONLY** - Don't copy entire file
**What to Study**:
- File upload pattern (lines ~518-582 for `generate_and_validate`)
- Background thread execution pattern
- Error handling pattern (`try/except`, response format)
- Flask Blueprint structure (`@bp.route`)

**New Endpoints to Create** (using studied patterns):
- `POST /api/excel/upload` - Upload Excel file
- `POST /api/excel/generate` - Generate test from Excel
- `GET /api/excel/template` - Download template
- `GET /api/excel/<id>/metadata` - Get Excel metadata

**Pull Only**:
- Flask import pattern
- Blueprint pattern
- Error handling pattern
- Response format pattern

---

### Phase 3: Test Runner Integration (Reference Only)

#### 4. Test Runner - REFERENCE PATTERNS
**Source**: `BACKUP/validator/test_runner.py`
**Destination**: Enhance existing `validator/test_runner.py` (when pulled back)
**Action**: **STUDY ONLY** - Don't copy entire file
**What to Study**:
- `TestRunner.run()` method structure
- Screenshot capture logic
- Result reporting format
- Execution metadata structure

**Enhancement Needed** (add to existing code):
```python
def run(self, test_filename: str, execution_id: str = None, 
        excel_id: str = None) -> Dict:
    # Add: if excel_id: metadata['excel_id'] = excel_id
```

**Pull Only**:
- Method signature pattern
- Metadata structure pattern
- Screenshot capture pattern

---

### Phase 4: UI Integration (Reference Patterns Only)

#### 5. Results Page - REFERENCE PATTERNS
**Source**: `BACKUP/web/templates/results.html`
**Destination**: Enhance existing `web/templates/results.html` (when pulled back)
**Action**: **STUDY ONLY** - Don't copy entire file
**What to Study**:
- Results display structure
- Screenshot gallery implementation
- Step-by-step view structure
- Status indicator patterns
- JavaScript API call patterns

**Enhancement Needed** (add to existing code):
- Add Excel file reference display
- Add Excel metadata display
- Add Excel file download link

#### 6. Excel Upload Page - CREATE NEW
**Source**: Reference `BACKUP/web/templates/index.html` structure
**Destination**: `REFACTOR/web/templates/excel_upload.html`
**Action**: CREATE NEW FILE (reference HTML structure, don't copy)
**What to Reference**:
- HTML structure pattern
- CSS class names
- Layout pattern

#### 7. Excel Upload JavaScript - CREATE NEW
**Source**: Reference `BACKUP/web/static/js/app.js` patterns
**Destination**: `REFACTOR/web/static/js/excel_upload.js`
**Action**: CREATE NEW FILE (reference patterns, don't copy)
**What to Reference**:
- API call pattern (`fetch()` usage)
- Error handling pattern
- Status update pattern
- File upload handling (if exists)

---

### Phase 5: Storage Structure (Reference Only)

#### 8. Storage Structure - REFERENCE ONLY
**Source**: `BACKUP/storage/` directory structure
**Destination**: Create new directories in `storage/`
**Action**: **REFERENCE ONLY** - Don't copy files
**What to Reference**:
- Directory naming pattern (`executions/`, `screenshots/`)
- File naming pattern (timestamp-based IDs)
- Metadata JSON structure

**Create New**:
- `storage/excel_files/` - Uploaded Excel files
- `storage/excel_files/metadata/` - Excel metadata JSON
- `storage/excel_tests/` - Excel-generated tests (or reuse `generated_tests/`)

---

### Phase 6: Environment (Already Exists)

#### 9. Environment Variables - NO ACTION NEEDED
**Source**: `.env` (already in root)
**Status**: ✅ Already exists
**Action**: **NO ACTION** - Reuse as-is

---

## 📊 Pull Summary

### Files to CREATE NEW (Reference Patterns)
1. `REFACTOR/generator/excel_validator.py` - Reference validation patterns
2. `REFACTOR/generator/excel_template.py` - Reference Excel creation pattern
3. `REFACTOR/web/templates/excel_upload.html` - Reference HTML structure
4. `REFACTOR/web/static/js/excel_upload.js` - Reference JS patterns

### Files to STUDY ONLY (Don't Copy)
1. `BACKUP/api/routes.py` - Study API patterns
2. `BACKUP/validator/test_runner.py` - Study test execution patterns
3. `BACKUP/web/templates/results.html` - Study UI patterns
4. `BACKUP/web/static/js/app.js` - Study JavaScript patterns
5. `BACKUP/storage/` - Study storage structure

### Directories to CREATE NEW
1. `storage/excel_files/`
2. `storage/excel_files/metadata/`
3. `storage/excel_tests/` (or reuse existing)

---

## 🎯 Pull Order (One at a Time)

1. **Excel Validator** (CREATE NEW)
   - Reference: `BACKUP/generator/pw_codegen/` (if exists)
   - Create: `REFACTOR/generator/excel_validator.py`

2. **Excel Template** (CREATE NEW)
   - Reference: `REFACTOR/tests/test_excel_generator.py` Excel creation
   - Create: `REFACTOR/generator/excel_template.py`

3. **API Patterns** (STUDY ONLY)
   - Study: `BACKUP/api/routes.py`
   - Create: `REFACTOR/api/excel_routes.py` (new endpoints)

4. **Test Runner Patterns** (STUDY ONLY)
   - Study: `BACKUP/validator/test_runner.py`
   - Enhance: When `validator/test_runner.py` is pulled back

5. **UI Patterns** (STUDY ONLY)
   - Study: `BACKUP/web/templates/results.html`
   - Study: `BACKUP/web/static/js/app.js`
   - Create: `REFACTOR/web/templates/excel_upload.html`
   - Create: `REFACTOR/web/static/js/excel_upload.js`

6. **Storage Structure** (REFERENCE ONLY)
   - Reference: `BACKUP/storage/` structure
   - Create: New directories in `storage/`

---

## ⚠️ Important Rules

1. **Don't copy entire files** - Only study patterns
2. **Create new files** - Don't modify BACKUP files
3. **One at a time** - Pull/study one component, test, then next
4. **Reference, don't copy** - Use patterns, not entire code blocks
5. **Test after each** - Verify each component works before next

---

## ✅ Checklist

### Phase 1: Core Generator Support
- [ ] Create `excel_validator.py` (reference patterns)
- [ ] Create `excel_template.py` (reference patterns)
- [ ] Test both standalone

### Phase 2: API Integration
- [ ] Study `BACKUP/api/routes.py` patterns
- [ ] Create `REFACTOR/api/excel_routes.py` with new endpoints
- [ ] Test API endpoints

### Phase 3: Test Runner Integration
- [ ] Study `BACKUP/validator/test_runner.py` patterns
- [ ] Plan enhancement (don't implement yet)

### Phase 4: UI Integration
- [ ] Study `BACKUP/web/templates/results.html` patterns
- [ ] Study `BACKUP/web/static/js/app.js` patterns
- [ ] Create `REFACTOR/web/templates/excel_upload.html`
- [ ] Create `REFACTOR/web/static/js/excel_upload.js`
- [ ] Test UI

### Phase 5: Storage Structure
- [ ] Reference `BACKUP/storage/` structure
- [ ] Create new storage directories
- [ ] Test storage operations

---

## 📝 Notes

- **Excel generator is already done** ✅
- **Only pull patterns, not entire files**
- **Create new files based on patterns**
- **Test each component before moving to next**

