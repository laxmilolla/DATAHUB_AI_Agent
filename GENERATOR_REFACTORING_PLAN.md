# Playwright Generator Refactoring Plan

## Current State Analysis

**File:** `generator/playwright_generator.py`
- **Lines:** 2,016
- **Methods:** 34 methods
- **Class:** 1 monolithic class (`PlaywrightGenerator`)
- **Main Issues:**
  - Hard to navigate and debug
  - Difficult to test individual components
  - Repeated fixes across multiple methods
  - Tight coupling between loading, matching, and code generation

## Refactoring Goals

1. **Modularity:** Break into focused, single-responsibility modules
2. **Testability:** Each component can be tested independently
3. **Maintainability:** Easier to find and fix bugs
4. **Reusability:** Components can be reused across different generators
5. **Clarity:** Clear separation of concerns

## Proposed Module Structure

```
generator/
├── __init__.py
├── pw_core/
│   ├── __init__.py
│   └── generator.py              # Main orchestrator (100-150 lines)
├── pw_loaders/
│   ├── __init__.py
│   ├── execution_loader.py       # Load execution JSON (50-80 lines)
│   ├── discovery_loader.py       # Load discovery JSON (50-80 lines)
│   └── registry_loader.py         # Load registry files, multi-registry support (150-200 lines)
├── pw_matchers/
│   ├── __init__.py
│   ├── action_matcher.py         # Match story steps to actions (200-250 lines)
│   └── discovery_matcher.py       # Match discoveries to steps (200-250 lines)
├── pw_codegen/
│   ├── __init__.py
│   ├── step_generators.py         # Generate code for each step type (400-500 lines)
│   ├── test_template.py           # Test file template/structure (100-150 lines)
│   └── code_formatter.py          # Code formatting utilities (50-100 lines)
├── pw_utils/
│   ├── __init__.py
│   ├── selector_utils.py          # Selector cleaning/normalization (100-150 lines)
│   ├── story_parser.py            # Parse story into steps (100-150 lines)
│   └── registry_utils.py          # Registry lookup utilities (100-150 lines)
└── playwright_generator.py        # DEPRECATED - keep for backward compat, delegate to new structure
```

## Detailed Module Breakdown

### 1. `generator/pw_core/generator.py` (Main Orchestrator)
**Purpose:** Coordinate the generation process
**Methods:**
- `generate(execution_id, test_name)` - Main entry point
- `_save_generated_test(code, filename, metadata)` - Save test file
- `_generate_test_metadata()` - Generate metadata

**Dependencies:**
- `pw_loaders.*` - Load execution/discovery/registry data
- `pw_codegen.test_template` - Generate test structure
- `pw_codegen.step_generators` - Generate step code

**Lines:** ~100-150

---

### 2. `generator/pw_loaders/execution_loader.py`
**Purpose:** Load execution JSON data
**Methods:**
- `load_execution(execution_id)` - Load execution JSON
- `validate_execution(execution)` - Validate execution data

**Lines:** ~50-80

---

### 3. `generator/pw_loaders/discovery_loader.py`
**Purpose:** Load discovery JSON data
**Methods:**
- `load_discoveries(execution_id)` - Load discovery JSON
- `validate_discoveries(discoveries)` - Validate discovery data

**Lines:** ~50-80

---

### 4. `generator/pw_loaders/registry_loader.py`
**Purpose:** Load and merge registry files
**Methods:**
- `load_registry(url)` - Load single registry file
- `detect_registry_files(execution)` - Detect all registry files needed
- `merge_registries(registry_files)` - Merge multiple registries
- `get_registry_path(url)` - Get registry file path from URL
- `find_element_in_registry(element_name, registry)` - Find element by name

**Lines:** ~150-200

---

### 5. `generator/pw_matchers/action_matcher.py`
**Purpose:** Match story steps to actions taken
**Methods:**
- `find_action_by_iteration(step_num, actions_taken)` - Match by iteration number
- `find_action_by_content(step_text, step_num, actions_taken)` - Match by content/type
- `_match_username_action(step_text, actions_taken)` - Match username fill
- `_match_password_action(step_text, actions_taken)` - Match password fill
- `_match_totp_action(step_text, actions_taken)` - Match TOTP fill
- `_match_click_action(step_text, actions_taken)` - Match click actions
- `_match_wait_action(step_text, actions_taken)` - Match wait actions

**Lines:** ~200-250

---

### 6. `generator/pw_matchers/discovery_matcher.py`
**Purpose:** Match discoveries to story steps
**Methods:**
- `find_discovery_by_step(step_num, step_text, discoveries, action)` - Main matcher
- `find_verification_discovery(step_num, discoveries)` - Find verification discovery
- `_calculate_match_score(discovery, action, step_text)` - Score matching
- `_extract_clicked_selector(result)` - Extract selector from result

**Lines:** ~200-250

---

### 7. `generator/pw_codegen/step_generators.py`
**Purpose:** Generate code for each step type
**Methods:**
- `generate_navigate_step(step_num, step_text, action, indent)` - Navigation
- `generate_wait_step(step_num, step_text, action, indent)` - Wait
- `generate_click_step(step_num, step_text, action, discovery, registry, indent, next_step_discovery)` - Click
- `generate_fill_step(step_num, step_text, action, discovery, registry, indent)` - Fill
- `generate_verify_step(step_num, step_text, action, discovery, indent)` - Verify
- `_generate_optional_click_code(step_num, step_text, action, discovery, indent)` - Optional clicks
- `_generate_checkbox_code(element_id, step_num, indent)` - Checkbox-specific
- `_generate_accordion_code(element_id, step_num, indent)` - Accordion-specific
- `_generate_popup_dismissal_code(element_id, step_num, next_step_discovery, indent)` - Popup dismissal

**Lines:** ~400-500

---

### 8. `generator/pw_codegen/test_template.py`
**Purpose:** Generate test file structure and template
**Methods:**
- `generate_test_header(execution_id, test_name, story)` - Header with imports
- `generate_registry_loading_code(registry_files)` - Registry loading code
- `generate_test_function(test_name, code_body)` - Test function wrapper
- `generate_test_footer()` - Footer/cleanup code

**Lines:** ~100-150

---

### 9. `generator/pw_codegen/code_formatter.py`
**Purpose:** Code formatting and utilities
**Methods:**
- `format_code(code)` - Format generated code
- `sanitize_filename(name)` - Sanitize for filenames
- `escape_string(text)` - Escape Python strings

**Lines:** ~50-100

---

### 10. `generator/pw_utils/selector_utils.py`
**Purpose:** Selector manipulation utilities
**Methods:**
- `clean_selector(selector)` - Clean state-dependent attributes
- `normalize_selector(selector)` - Normalize for comparison
- `strip_dynamic_xpath(xpath)` - Strip dynamic content from XPath

**Lines:** ~100-150

---

### 11. `generator/pw_utils/story_parser.py`
**Purpose:** Parse story text into structured steps
**Methods:**
- `parse_story_steps(story)` - Parse story into steps
- `extract_step_number(line)` - Extract step number
- `extract_step_text(line)` - Extract step text
- `is_optional_step(step_text)` - Check if step is optional

**Lines:** ~100-150

---

### 12. `generator/pw_utils/registry_utils.py`
**Purpose:** Registry lookup and utilities
**Methods:**
- `get_element_id_from_registry(element_name, registry)` - Find element_id by name
- `get_element_id_by_xpath(xpath, registry)` - Find element_id by XPath
- `get_xpath_by_id(element_id, registry)` - Get XPath by element_id
- `backfill_element_id(discovery, registry)` - Backfill element_id into discovery

**Lines:** ~100-150

---

## Refactoring Execution Plan

### Phase 1: Foundation (Day 1 - 4 hours)
1. Create directory structure (`pw_core/`, `pw_loaders/`, `pw_matchers/`, `pw_codegen/`, `pw_utils/`)
2. Extract utilities first (lowest dependencies):
   - `pw_utils/selector_utils.py`
   - `pw_utils/story_parser.py`
   - `pw_utils/registry_utils.py`
3. Extract loaders:
   - `pw_loaders/execution_loader.py`
   - `pw_loaders/discovery_loader.py`
   - `pw_loaders/registry_loader.py`
4. Test each module independently

### Phase 2: Matchers (Day 1-2 - 4 hours)
1. Extract `pw_matchers/action_matcher.py`
2. Extract `pw_matchers/discovery_matcher.py`
3. Test matching logic
4. Ensure backward compatibility

### Phase 3: Code Generation (Day 2 - 6 hours)
1. Extract `pw_codegen/test_template.py`
2. Extract `pw_codegen/code_formatter.py`
3. Extract `pw_codegen/step_generators.py` (largest module)
4. Test code generation for each step type

### Phase 4: Core Orchestrator (Day 2-3 - 4 hours)
1. Create `pw_core/generator.py`
2. Wire up all modules
3. Update `playwright_generator.py` to delegate to new structure
4. Maintain backward compatibility

### Phase 5: Testing & Cleanup (Day 3 - 2 hours)
1. Test full generation flow
2. Fix any integration issues
3. Update imports in `api/routes.py` if needed
4. Document new structure

**Total Estimated Time:** 2-3 days (20 hours)

## Migration Strategy

### Backward Compatibility
- Keep `playwright_generator.py` as a thin wrapper
- Delegate to new `core/generator.py`
- Maintain same public API
- No changes needed in `api/routes.py` initially

### Gradual Migration
1. Extract modules one at a time
2. Test after each extraction
3. Keep old code until new code is proven
4. Switch over when all modules are extracted

## Benefits After Refactoring

1. **Easier Debugging:** Issues isolated to specific modules
2. **Faster Fixes:** Find and fix bugs in focused files
3. **Better Testing:** Test each component independently
4. **Clearer Code:** Each module has a single responsibility
5. **Reusability:** Components can be reused elsewhere
6. **Maintainability:** Much easier to understand and modify

## Critical Considerations

1. **XPath Preservation Logic:** Must be preserved in `pw_utils/registry_utils.py`
2. **Step Matching Logic:** Critical for accurate test generation - preserve in `pw_matchers/`
3. **Multi-registry Support:** Must work correctly in `pw_loaders/registry_loader.py`
4. **Optional Step Handling:** Must be preserved in `pw_codegen/step_generators.py`
5. **Dialog Dismissal Logic:** Must be preserved in `pw_codegen/step_generators.py`
6. **TOTP Generation:** Must be preserved in `pw_codegen/step_generators.py`

## Testing Strategy

1. **Unit Tests:** Test each module independently
2. **Integration Tests:** Test full generation flow
3. **Regression Tests:** Compare generated code before/after refactoring
4. **Edge Cases:** Test optional steps, missing discoveries, multi-registry

## Success Criteria

- ✅ All existing functionality preserved
- ✅ Generated tests are identical (or better) than before
- ✅ Code is easier to navigate and debug
- ✅ Each module is independently testable
- ✅ No breaking changes to API
- ✅ Faster to fix bugs (isolated to specific modules)

