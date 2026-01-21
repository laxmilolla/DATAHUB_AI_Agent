# Dead Code Analysis Report

## Summary
- **Total Python files**: 76
- **Potentially unused files**: 52
- **Files with unused routes**: 3
- **Main issue**: Migration from Python Agent execution to TypeScript Playwright tests left behind unused code

---

## 🔴 CONFIRMED DEAD CODE (Safe to Remove)

### 1. Experimented/ Folder (Moved Features)
**Status**: ✅ **SAFE TO DELETE** - Features moved to BACKUP or no longer used

- `Experimented/api/excel_execution_routes.py` - Excel execution routes (moved)
- `Experimented/api/instructions_routes.py` - Instructions routes (moved to BACKUP)
- `Experimented/api/html_helper.py` - HTML helper (unused)

**Routes in Experimented that are NOT used**:
- `/api/instructions/execute` ❌
- `/api/instructions/start-browser` ❌
- `/api/instructions/<execution_id>/status` ❌
- `/api/instructions/<execution_id>/excel` ❌

### 2. Utils/ Folder (Many Unused Utilities)
**Status**: ⚠️ **REVIEW BEFORE DELETING** - Some may be used indirectly

**Potentially unused**:
- `utils/capture_filters_graphql.py` - GraphQL capture (not imported anywhere)
- `utils/capture_graphql.py` - GraphQL capture (not imported anywhere)
- `utils/check_api_calls.py` - API call checker (not imported)
- `utils/compare_maps.py` - Map comparison (not imported)
- `utils/create_element_map.py` - Element map creation (not imported)
- `utils/fetch_and_parse_html.py` - HTML fetcher (not imported)
- `utils/html_parser.py` - HTML parser (not imported in main code)
- `utils/playwright_tree_parser.py` - Tree parser (not imported)
- `utils/test_element_matching.py` - Test matching (not imported)
- `utils/xpath_builder.py` - XPath builder (not imported)

**Still used**:
- `utils/element_registry.py` ✅ (used by agent)
- `utils/otp_helper.py` ✅ (used for TOTP)
- `utils/table_verification.py` ✅ (used by browser_verify)

### 3. Root Level Scripts (Test/Debug Scripts)
**Status**: ✅ **SAFE TO MOVE TO BACKUP** - Not part of main application

- `experiment_extended_test.py` - Test script
- `extract_all_elements.py` - Extraction script
- `extract_datasubmissions_elements.py` - Extraction script
- `extract_input_fields.py` - Extraction script
- `test_add_steps.py` - Test script
- `test_cdp_connection.py` - Test script
- `analyze_dead_code.py` - This analysis script

### 4. Unused Routes in api/routes.py
**Status**: ⚠️ **REVIEW** - Some may be used by old UI features

**Routes NOT found in frontend JS**:
- `/api/fetch-html` ❌ (not in app.js, excel_upload.js, or experiment.js)
- `/api/parse-html` ❌
- `/api/manual-register` ❌
- `/api/save-element-map` ❌
- `/api/element-maps/list` ❌
- `/api/element-maps/<domain>/<page>` ❌
- `/api/executions/<exec_id>/download-env` ❌
- `/api/executions/<exec_id>/download-test` ❌
- `/api/executions/<exec_id>/download-test-zip` ❌
- `/api/executions/<exec_id>/download-test-ts-zip` ❌
- `/api/executions/<exec_id>/generate-and-validate` ❌
- `/api/executions/<exec_id>/generated-test` ❌
- `/api/executions/<exec_id>/run-test` ❌
- `/api/executions/<exec_id>/mark-passed` ❌
- `/api/executions/<execution_id>/approve-discoveries` ❌
- `/api/registry/<domain>/<page>` ❌ (GET/PUT/DELETE)
- `/api/registry/<domain>/<page>/download` ❌
- `/api/registry/<domain>/<page>/element` ❌ (PUT/DELETE)
- `/api/parser/registry` ❌ (only used by tree_viewer.js which may be unused)

**Routes STILL USED**:
- `/api/execute` ✅ (used by app.js)
- `/api/executions/<execution_id>/status` ✅ (used by app.js)
- `/api/executions` ✅ (used by app.js)
- `/api/health` ✅ (health check)
- `/api/screenshots/<filename>` ✅ (used by results page)
- `/api/excel/*` ✅ (all Excel routes used by excel_upload.js)

---

## ✅ ACTIVE CODE (Keep)

### Core Agent Code
- `agent/core/agent.py` ✅
- `agent/core/execution_context.py` ✅
- `agent/browser/*` ✅ (all browser tools)
- `agent/discovery/*` ✅ (all discovery tools)
- `agent/llm/*` ✅ (all LLM tools)
- `agent/tools/*` ✅ (all tool handlers)
- `agent/utils/*` ✅ (all utilities)

### Excel System (Current Main Feature)
- `REFACTOR/api/excel_routes.py` ✅
- `REFACTOR/generator/excel_generator.py` ✅
- `REFACTOR/generator/excel_generator_ts.py` ✅
- `REFACTOR/generator/excel_validator.py` ✅
- `REFACTOR/generator/excel_template.py` ✅
- `REFACTOR/generator/excel_registry_helper.py` ✅

### Validator
- `validator/typescript_test_runner.py` ✅ (runs TypeScript tests)

### API Entry Points
- `api/app.py` ✅
- `api/routes.py` ✅ (but has many unused routes)

---

## 📋 RECOMMENDATIONS

### Phase 1: Safe Deletions (No Risk)
1. **Delete `Experimented/` folder** - Features moved to BACKUP
2. **Move test scripts to `BACKUP/scripts/`**:
   - `experiment_extended_test.py`
   - `extract_*.py`
   - `test_*.py`
3. **Delete unused HTML parser routes** if HTML parser UI is removed

### Phase 2: Review Before Deleting
1. **Review `utils/` folder** - Check if any utilities are used by Excel generator
2. **Review unused routes in `api/routes.py`** - Check if they're used by old UI features
3. **Check `tree_viewer.js`** - If unused, can remove `/api/parser/registry` routes

### Phase 3: Clean Up Routes
1. **Remove unused routes from `api/routes.py`**:
   - Story-based execution routes (if only Excel is used)
   - Manual registry routes (if not used)
   - HTML parser routes (if parser UI removed)

---

## 🔍 HOW TO VERIFY DEAD CODE

### Method 1: Check Imports
```bash
# Find files that are never imported
grep -r "from utils.html_parser" . --include="*.py"
grep -r "import html_parser" . --include="*.py"
```

### Method 2: Check Route Usage
```bash
# Find routes used in frontend
grep -r "/api/fetch-html" web/
grep -r "/api/parse-html" web/
```

### Method 3: Check File References
```bash
# Find if a file is imported anywhere
grep -r "from utils.capture_graphql" . --include="*.py"
grep -r "import capture_graphql" . --include="*.py"
```

---

## ⚠️ IMPORTANT NOTES

1. **Don't delete `agent/` folder** - Still used by Excel system for registry lookups
2. **Don't delete `REFACTOR/` folder** - Contains active Excel functionality
3. **Check `BACKUP/` folder** - May contain code that's still referenced
4. **Test after deletions** - Run Excel upload/generation to ensure nothing breaks

---

## 📊 Statistics

- **Active Python files**: ~24 (agent, REFACTOR, api, validator)
- **Dead Python files**: ~52 (utils, Experimented, test scripts)
- **Dead code percentage**: ~68% of Python files
- **Main cause**: Migration from Python Agent → TypeScript Playwright

