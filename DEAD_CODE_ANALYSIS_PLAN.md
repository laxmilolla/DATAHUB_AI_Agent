# Dead Code Identification Plan

## Overview
This plan provides a systematic approach to identify unused/dead code in the codebase without making any changes.

---

## Phase 1: Identify Obvious Dead Code

### 1.1 Backup/Temporary Files
**Files to Check:**
- `agent/bedrock_playwright_agent.py.backup_20260101_162039` ⚠️ **BACKUP FILE**
- `agent/bedrock_playwright_agent.py.bak2` ⚠️ **BACKUP FILE**
- `element_maps/caninecommons.cancer.gov/explore_page.json.backup_20260102_135710` ⚠️ **BACKUP FILE**

**Action:** These are clearly backup files and can be safely identified as dead code.

---

### 1.2 Temporary/Unused Files
**Files to Check:**
- `agent/temp_method.py` - Contains `_get_domain_and_page()` method
  - **Check:** Is this method used anywhere in `bedrock_playwright_agent.py`?
  - **Status:** ⚠️ **LIKELY DEAD** - File name suggests temporary

---

### 1.3 Broken Imports
**Files to Check:**
- `agent/__init__.py` - Imports `BedrockAgentQA` from `bedrock_agent`
  - **Check:** Does `agent/bedrock_agent.py` exist?
  - **Check:** Is `BedrockAgentQA` used anywhere?
  - **Status:** ⚠️ **LIKELY BROKEN** - References non-existent module

---

## Phase 2: Unused Python Modules

### 2.1 Utility Files Usage Analysis

**Check each file in `utils/`:**

| File | Imported By | Status |
|------|-------------|--------|
| `utils/capture_filters_graphql.py` | ❓ Check | ⚠️ **LIKELY DEAD** - Temporary debug script |
| `utils/capture_graphql.py` | ❓ Check | ⚠️ **LIKELY DEAD** - Temporary debug script |
| `utils/check_api_calls.py` | ❓ Check | ⚠️ **LIKELY DEAD** - Temporary debug script |
| `utils/compare_maps.py` | `utils/create_element_map.py` | ✅ Check if `create_element_map.py` is used |
| `utils/create_element_map.py` | ❓ Check | ⚠️ **LIKELY DEAD** - Old parser? |
| `utils/fetch_and_parse_html.py` | `utils/html_parser.py` | ✅ Check if `html_parser.py` is used |
| `utils/html_parser.py` | `api/routes.py` | ✅ **USED** - Imported in routes |
| `utils/element_registry.py` | `api/routes.py`, `agent/bedrock_playwright_agent.py` | ✅ **USED** |
| `utils/playwright_parser.py` | ❓ Check | ⚠️ **LIKELY DEAD** - Old parser? |
| `utils/playwright_tree_parser.py` | `run_parser.py` | ✅ **USED** - Via run_parser.py |
| `utils/table_verification.py` | ❓ Check | ⚠️ Check if used |
| `utils/test_element_matching.py` | ❓ Check | ✅ **USED** - Developer utility |
| `utils/xpath_builder.py` | `agent/bedrock_playwright_agent.py` | ✅ **USED** |

**Action:** Run import analysis to confirm.

---

### 2.2 Root-Level Scripts

| File | Status |
|------|--------|
| `run_parser.py` | ✅ **USED** - Parser runner script |
| `test_enhanced_matching.py` | ✅ **USED** - Developer utility (renamed to `utils/test_element_matching.py`?) |

**Action:** Check if `test_enhanced_matching.py` duplicates `utils/test_element_matching.py`.

---

## Phase 3: Unused Functions/Classes

### 3.1 API Routes Analysis

**Check each route in `api/routes.py`:**

| Route | Method | Called From Frontend? | Status |
|-------|--------|----------------------|--------|
| `/execute` | POST | ✅ Yes - Main execution | ✅ **USED** |
| `/executions/<id>/status` | GET | ✅ Yes - Status polling | ✅ **USED** |
| `/executions/<id>/results` | GET | ✅ Yes - Results page | ✅ **USED** |
| `/executions` | GET | ✅ Yes - Execution list | ✅ **USED** |
| `/screenshots/<filename>` | GET | ✅ Yes - Screenshot display | ✅ **USED** |
| `/health` | GET | ❓ Check | ⚠️ **CHECK** |
| `/fetch-html` | POST | ❓ Check | ⚠️ **CHECK** |
| `/parse-html` | POST | ✅ Yes - Parser page | ✅ **USED** |
| `/save-element-map` | POST | ✅ Yes - Parser page | ✅ **USED** |
| `/element-maps/list` | GET | ❓ Check | ⚠️ **CHECK** |
| `/element-maps/<domain>/<page>` | GET | ❓ Check | ⚠️ **CHECK** |
| `/executions/<id>/approve-discoveries` | POST | ❓ Check | ⚠️ **CHECK** |
| `/executions/<id>/generate-and-validate` | POST | ✅ Yes - Results page | ✅ **USED** |
| `/executions/<id>/generated-test` | GET | ✅ Yes - View code button | ✅ **USED** |
| `/executions/<id>/download-test` | GET | ✅ Yes - Download button | ✅ **USED** |
| `/registry` | GET | ✅ Yes - Registry list | ✅ **USED** |
| `/registry/<domain>/<page>` | GET | ✅ Yes - Tree viewer | ✅ **USED** |
| `/registry/<domain>/<page>/element` | PUT | ✅ Yes - Tree viewer | ✅ **USED** |
| `/registry/<domain>/<page>` | DELETE | ✅ Yes - Delete registry | ✅ **USED** |
| `/registry/<domain>/<page>/element` | DELETE | ✅ Yes - Delete element | ✅ **USED** |
| `/parser/registry` | GET | ✅ Yes - Tree viewer | ✅ **USED** |
| `/parser/registry` | PUT | ✅ Yes - Tree viewer | ✅ **USED** |

**Action:** Search frontend JavaScript/HTML for route usage.

---

### 3.2 Agent Methods

**Check `agent/bedrock_playwright_agent.py`:**
- List all `def` methods
- Check which are called internally
- Check which are called from routes

**Action:** Use static analysis tool or manual grep.

---

### 3.3 Generator Methods

**Check `generator/playwright_generator.py`:**
- List all methods
- Check which are called from routes

---

## Phase 4: Unused JavaScript Functions

### 4.1 Frontend JavaScript Analysis

**Check `web/static/js/` files:**

| File | Functions | Status |
|------|-----------|--------|
| `app.js` | `displayExecutions()`, `updateShowAllButton()`, `toggleShowAll()`, `getStatusIcon()`, `truncateStory()`, `formatDate()` | ✅ Check if called from HTML |
| `parser.js` | `switchTab()`, `handleFile()`, `displayResults()`, `displayRegistryElements()` | ✅ Check if called from HTML |
| `tree_viewer.js` | All functions | ✅ Check if called from HTML |

**Action:** Search HTML templates for function calls.

---

## Phase 5: Unused HTML Templates/Sections

### 5.1 Template Files

| File | Status |
|------|--------|
| `web/templates/index.html` | ✅ **USED** - Home page |
| `web/templates/parser.html` | ✅ **USED** - Parser page |
| `web/templates/element_maps.html` | ❓ Check if route exists |
| `web/templates/results.html` | ✅ **USED** - Results page |

**Action:** Check if `element_maps.html` is rendered by any route.

---

### 5.2 Unused HTML Sections

**Check for:**
- Commented-out HTML blocks
- Hidden/display:none sections that are never shown
- Unused modals/dialogs
- Unused form fields

---

## Phase 6: Unused Imports

### 6.1 Python Imports

**For each Python file:**
1. List all imports
2. Check if imported modules/functions are used
3. Flag unused imports

**Tools:** Use `vulture` or `pylint` for automatic detection.

---

### 6.2 JavaScript Imports

**Check:**
- Unused jQuery functions
- Unused library functions
- Unused CSS classes

---

## Phase 7: Analysis Tools & Commands

### 7.1 Python Dead Code Detection

```bash
# Install vulture (dead code detector)
pip install vulture

# Run on specific directories
vulture agent/ --min-confidence 80
vulture utils/ --min-confidence 80
vulture api/ --min-confidence 80

# Run on entire project (excluding venv)
vulture . --exclude venv --min-confidence 80
```

### 7.2 Import Analysis

```bash
# Find all imports
grep -r "^import\|^from" --include="*.py" . | grep -v venv

# Find unused imports (requires pylint)
pylint --disable=all --enable=unused-import api/routes.py
```

### 7.3 Route Usage Analysis

```bash
# Find all route definitions
grep -r "@bp.route\|@app.route" api/

# Find route usage in frontend
grep -r "/api/" web/static/js/ web/templates/
```

### 7.4 Function Usage Analysis

```bash
# Find function definitions
grep -r "^def \|^class " --include="*.py" .

# Find function calls
grep -r "function_name(" --include="*.py" --include="*.js" .
```

---

## Phase 8: Manual Verification Checklist

### 8.1 Files to Manually Verify

- [ ] `agent/temp_method.py` - Check if `_get_domain_and_page()` is used
- [ ] `agent/__init__.py` - Check if `BedrockAgentQA` exists and is used
- [ ] `utils/capture_*.py` - Check if these debug scripts are needed
- [ ] `utils/check_api_calls.py` - Check if this debug script is needed
- [ ] `utils/compare_maps.py` - Check if used by `create_element_map.py`
- [ ] `utils/create_element_map.py` - Check if this old parser is used
- [ ] `utils/playwright_parser.py` - Check if this old parser is used
- [ ] `utils/table_verification.py` - Check if used anywhere
- [ ] `test_enhanced_matching.py` - Check if duplicates `utils/test_element_matching.py`
- [ ] `web/templates/element_maps.html` - Check if route renders this

### 8.2 Routes to Verify

- [ ] `/health` - Is this used for monitoring?
- [ ] `/fetch-html` - Is this used?
- [ ] `/element-maps/list` - Is this used?
- [ ] `/element-maps/<domain>/<page>` - Is this used?
- [ ] `/executions/<id>/approve-discoveries` - Is this used?

---

## Phase 9: Reporting Template

### 9.1 Dead Code Report Structure

```markdown
# Dead Code Report

## Confirmed Dead Code (Safe to Delete)
1. Backup files: [list]
2. Temporary files: [list]
3. Unused modules: [list]
4. Unused functions: [list]
5. Unused routes: [list]

## Likely Dead Code (Needs Verification)
1. [list with reasoning]

## False Positives (Actually Used)
1. [list with explanation]
```

---

## Phase 10: Execution Order

1. **Phase 1** - Quick wins (backup files, obvious dead code)
2. **Phase 2** - Module analysis (import tracking)
3. **Phase 3** - Function/class analysis (usage tracking)
4. **Phase 4** - JavaScript analysis (frontend usage)
5. **Phase 5** - HTML analysis (template usage)
6. **Phase 6** - Import cleanup (unused imports)
7. **Phase 7** - Run automated tools (vulture, pylint)
8. **Phase 8** - Manual verification (edge cases)
9. **Phase 9** - Generate report
10. **Phase 10** - Review and prioritize deletions

---

## Tools Needed

1. **vulture** - Python dead code detector
2. **pylint** - Python linter (unused imports)
3. **grep/ripgrep** - Text search
4. **Manual code review** - For edge cases

---

## Notes

- **DO NOT DELETE** anything until verification is complete
- Create a backup branch before deletions
- Test after each deletion phase
- Some "dead" code might be:
  - Planned for future use
  - Used in tests
  - Used conditionally
  - Part of a public API

---

## Next Steps

1. Run Phase 1 analysis (backup files)
2. Run Phase 7 automated tools (vulture)
3. Create initial dead code report
4. Review with team
5. Execute deletions in phases






