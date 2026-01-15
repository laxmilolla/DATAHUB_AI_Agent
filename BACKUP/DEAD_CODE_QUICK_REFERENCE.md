# Dead Code Quick Reference

## 🚨 Definitely Dead (Safe to Delete)

### Backup Files
1. `agent/bedrock_playwright_agent.py.backup_20260101_162039`
2. `agent/bedrock_playwright_agent.py.bak2`
3. `element_maps/caninecommons.cancer.gov/explore_page.json.backup_20260102_135710`

### Broken Imports
1. `agent/__init__.py` - Imports `BedrockAgentQA` from non-existent `bedrock_agent.py`

---

## ⚠️ Likely Dead (Needs Verification)

### Temporary/Debug Scripts
1. `utils/capture_filters_graphql.py` - Temporary GraphQL capture script
2. `utils/capture_graphql.py` - Temporary GraphQL capture script
3. `utils/check_api_calls.py` - Temporary API call checker

### Old Parsers (Check if replaced)
1. `utils/create_element_map.py` - Old element map creator?
2. `utils/playwright_parser.py` - Old parser? (vs `playwright_tree_parser.py`)
3. `utils/compare_maps.py` - Only used by `create_element_map.py`?

### Temporary Files
1. `agent/temp_method.py` - Contains `_get_domain_and_page()` method
   - Check: Is this method used in `bedrock_playwright_agent.py`?

### Duplicate Files
1. `test_enhanced_matching.py` (root) vs `utils/test_element_matching.py`
   - Check: Are these duplicates?

### Unused Routes (Check Frontend)
1. `/health` - Health check endpoint
2. `/fetch-html` - HTML fetcher
3. `/element-maps/list` - Element maps list
4. `/element-maps/<domain>/<page>` - Element map getter
5. `/executions/<id>/approve-discoveries` - Discovery approval

### Unused Template
1. `web/templates/element_maps.html` - Check if route renders this

---

## ✅ Confirmed Used (Keep)

### Core Files
- `agent/bedrock_playwright_agent.py` - Main agent
- `api/routes.py` - API routes
- `api/app.py` - Flask app
- `generator/playwright_generator.py` - Test generator
- `validator/test_runner.py` - Test runner
- `validator/comparator.py` - Result comparator

### Utils (Used)
- `utils/element_registry.py` - Used by agent & routes
- `utils/html_parser.py` - Used by routes
- `utils/playwright_tree_parser.py` - Used by `run_parser.py`
- `utils/xpath_builder.py` - Used by agent
- `utils/test_element_matching.py` - Developer utility
- `utils/table_verification.py` - Check if used by agent

### Scripts
- `run_parser.py` - Parser runner

---

## 🔍 Quick Verification Commands

```bash
# Check if temp_method.py is used
grep -r "temp_method\|_get_domain_and_page" --include="*.py" .

# Check if BedrockAgentQA exists
find . -name "bedrock_agent.py" -o -name "*bedrock_agent*"

# Check if capture scripts are imported
grep -r "capture_filters_graphql\|capture_graphql\|check_api_calls" --include="*.py" .

# Check if old parsers are used
grep -r "create_element_map\|playwright_parser\|compare_maps" --include="*.py" .

# Check route usage in frontend
grep -r "/health\|/fetch-html\|/element-maps\|/approve-discoveries" web/

# Check if element_maps.html is rendered
grep -r "element_maps.html\|element_maps_page" --include="*.py" .
```

---

## 📊 Estimated Dead Code

- **Backup files:** ~3 files (safe to delete)
- **Broken imports:** ~1 file (`agent/__init__.py`)
- **Temporary scripts:** ~3 files (`utils/capture_*.py`, `check_api_calls.py`)
- **Old parsers:** ~3 files (`create_element_map.py`, `playwright_parser.py`, `compare_maps.py`)
- **Unused routes:** ~5 routes (need frontend verification)
- **Total estimated:** ~15 files/routes potentially dead

---

## 🎯 Priority Order

1. **High Priority (Safe):** Backup files, broken imports
2. **Medium Priority:** Temporary scripts, old parsers
3. **Low Priority:** Unused routes (verify first)






