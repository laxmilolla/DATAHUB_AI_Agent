# Detailed Refactoring Plan - Aggressive Timeline

## Why Faster? Because I Can Work in Parallel

**Human Developer**: Reads code → Understands → Extracts → Tests → Moves on (Sequential)
**AI Assistant**: Sees entire codebase → Extracts multiple modules simultaneously → Tests all at once (Parallel)

**Estimated Time**: 2-3 days (vs 15-20 days for human)

---

## Day 1: Foundation & Utilities (4-6 hours)

### Hour 1: Setup Structure & Extract Utilities

#### 1.1 Create Directory Structure (5 min)
```bash
mkdir -p agent/core agent/llm agent/browser agent/discovery agent/tools agent/utils
touch agent/core/__init__.py agent/llm/__init__.py agent/browser/__init__.py agent/discovery/__init__.py agent/tools/__init__.py agent/utils/__init__.py
```

#### 1.2 Extract `utils/story_parser.py` (15 min)
**Source**: Lines 64-136
**What to Extract**:
- `parse_story_metadata()` method
- Step parsing logic
- Metadata extraction (type, location, parent_hint)
- ~150 lines → New file

**Dependencies**: None (pure function)
**Test**: Copy existing story, verify same output

#### 1.3 Extract `utils/totp_handler.py` (20 min)
**Source**: Lines 2720-2772, 2080-2120
**What to Extract**:
- TOTP code generation logic
- Secret key extraction from story
- Environment variable reading
- ~150 lines → New file

**Dependencies**: `utils.otp_helper` (already exists)
**Test**: Generate TOTP code, verify format

#### 1.4 Extract `browser/screenshot_manager.py` (15 min)
**Source**: Lines 584-686, 47-49
**What to Extract**:
- Screenshot capture logic
- Screenshot directory management
- Screenshot counter
- ~150 lines → New file

**Dependencies**: `pathlib.Path`
**Test**: Capture screenshot, verify file exists

**Total Hour 1**: 55 minutes → 3 new modules

---

### Hour 2: Browser Components

#### 2.1 Extract `browser/playwright_manager.py` (20 min)
**Source**: Lines 34-42, 137-157
**What to Extract**:
- Browser initialization
- `start_browser()` → `start()`
- `close_browser()` → `close()`
- Page management
- ~200 lines → New file

**Dependencies**: `playwright.async_api`
**Test**: Start browser, verify page accessible

#### 2.2 Extract `browser/element_locator.py` (40 min)
**Source**: Lines 197-400, 476-492
**What to Extract**:
- `_check_element_registry()` → `check_registry()`
- `_normalize_selector_for_dynamic_content()` → `normalize_selector()`
- `_click_parent_or_sibling()` → `find_parent_or_sibling()`
- Registry lookup logic
- Tree climbing logic
- ~400 lines → New file

**Dependencies**: `utils.element_registry`, `playwright.async_api`
**Test**: Find element by registry, verify selector returned

**Total Hour 2**: 60 minutes → 2 new modules

---

### Hour 3: Discovery Components

#### 3.1 Extract `discovery/xpath_generator.py` (20 min)
**Source**: Lines 941-1007, 1008-1062, 1063-1077
**What to Extract**:
- `_generate_final_selector()` → `generate_selector()`
- `_extract_element_attributes()` → `extract_attributes()`
- `_extract_xpath_from_result()` → `extract_xpath()`
- XPath building logic
- ~300 lines → New file

**Dependencies**: `utils.xpath_builder.XPathBuilder` (already exists)
**Test**: Generate XPath for element, verify uniqueness

#### 3.2 Extract `discovery/discovery_tracker.py` (30 min)
**Source**: Lines 1078-1193
**What to Extract**:
- `_track_discovery()` → `track()`
- Discovery metadata collection
- Element attribute extraction
- Relationship tracking (parent/child)
- ~300 lines → New file

**Dependencies**: `discovery.xpath_generator`, `browser.element_locator`
**Test**: Track discovery, verify metadata saved

#### 3.3 Extract `discovery/registry_manager.py` (10 min)
**Source**: Lines 3342-3500+ (approximate, need to find exact location)
**What to Extract**:
- `_save_discoveries_to_registry()` → `save_discoveries()`
- XPath preservation logic (CRITICAL)
- Element ID backfilling
- Registry update logic
- ~250 lines → New file

**Dependencies**: `utils.element_registry`
**Test**: Save discovery, verify XPath preserved if manual

**Total Hour 3**: 60 minutes → 3 new modules

---

### Hour 4: LLM Components

#### 4.1 Extract `llm/bedrock_client.py` (25 min)
**Source**: Lines 34-36, 3290-3310, 867-887
**What to Extract**:
- Bedrock client initialization
- `converse()` method
- Response parsing
- Tool use extraction
- ~200 lines → New file

**Dependencies**: `boto3`
**Test**: Make LLM call, verify response format

#### 4.2 Extract `llm/prompt_builder.py` (25 min)
**Source**: Lines 3223-3282
**What to Extract**:
- `parse_story_metadata()` integration (uses `utils.story_parser`)
- Story enhancement with action hints
- System prompt generation
- Prompt formatting
- ~250 lines → New file

**Dependencies**: `utils.story_parser`
**Test**: Build prompt, verify action hints added

#### 4.3 Extract `llm/tool_definitions.py` (10 min)
**Source**: Lines 3114-3210
**What to Extract**:
- `get_tools()` → Tool schema definitions
- Tool descriptions
- Tool input schemas
- ~150 lines → New file

**Dependencies**: None (pure data)
**Test**: Verify tool schemas valid

**Total Hour 4**: 60 minutes → 3 new modules

---

### Hour 5-6: Core Components

#### 5.1 Extract `core/execution_context.py` (30 min)
**Source**: Lines 44-63, 3248-3255, 3318-3330
**What to Extract**:
- Execution state management
- Step tracking
- Action logging
- Screenshot tracking
- Results collection
- ~150 lines → New file

**Dependencies**: None (pure state)
**Test**: Track actions, verify state updated

#### 5.2 Extract `core/agent.py` - Part 1 (30 min)
**Source**: Lines 3211-3255 (initialization)
**What to Extract**:
- Agent initialization
- Component wiring
- High-level structure
- ~200 lines → New file (skeleton)

**Dependencies**: All other modules
**Test**: Initialize agent, verify components connected

**Total Hours 5-6**: 60 minutes → 2 new modules

---

## Day 2: Tool Handlers & Integration (4-6 hours)

### Hour 7-8: Extract Tool Handlers

#### 7.1 Extract `tools/browser_navigate.py` (20 min)
**Source**: Lines 1202-1215
**What to Extract**:
- Navigation tool handler
- URL validation
- Page tracking
- ~100 lines → New file

**Dependencies**: `browser.playwright_manager`, `core.execution_context`
**Test**: Navigate to URL, verify page loaded

#### 7.2 Extract `tools/browser_click.py` (90 min) ⚠️ MOST COMPLEX
**Source**: Lines 1216-1972
**What to Extract**:
- Click tool handler
- Registry check integration
- Tree climbing integration
- Discovery tracking integration
- Validation logic
- Dialog handling
- ~500 lines → New file

**Dependencies**: `browser.element_locator`, `browser.action_executor`, `discovery.discovery_tracker`
**Test**: Click element, verify discovery tracked, XPath preserved

#### 7.3 Extract `tools/browser_fill.py` (60 min) ⚠️ COMPLEX
**Source**: Lines 2636-2900+
**What to Extract**:
- Fill tool handler
- Registry check integration
- TOTP detection & handling
- TOTP fallback selectors
- ~400 lines → New file

**Dependencies**: `browser.element_locator`, `utils.totp_handler`, `discovery.discovery_tracker`
**Test**: Fill field, verify TOTP generated if needed

#### 7.4 Extract `tools/browser_evaluate.py` (15 min)
**Source**: Lines 2901-3000+ (approximate)
**What to Extract**:
- JavaScript evaluation handler
- Code execution
- Result parsing
- ~100 lines → New file

**Dependencies**: `browser.playwright_manager`
**Test**: Execute JS, verify result

#### 7.5 Extract `tools/browser_verify.py` (30 min)
**Source**: Lines 3001-3113 (approximate)
**What to Extract**:
- Verification handler
- Table verification logic
- Column matching
- ~200 lines → New file

**Dependencies**: `utils.table_verification` (already exists)
**Test**: Verify table, verify results

**Total Hours 7-8**: 215 minutes → 5 new modules

---

### Hour 9: Browser Action Executor

#### 9.1 Extract `browser/action_executor.py` (60 min)
**Source**: Lines 493-583, 687-776, 1973-2044
**What to Extract**:
- `_validate_element_visibility()` → `validate_visibility()`
- `_capture_post_click_screenshot()` → `capture_screenshot()`
- `_validate_filter_applied()` → `validate_filter()`
- Click execution helpers
- Force click logic
- ~500 lines → New file

**Dependencies**: `browser.screenshot_manager`, `browser.playwright_manager`
**Test**: Execute click, verify validation, verify screenshot

**Total Hour 9**: 60 minutes → 1 new module

---

### Hour 10: Integration & Wiring

#### 10.1 Complete `core/agent.py` (60 min)
**Source**: Lines 3211-3580 (remaining parts)
**What to Extract**:
- `execute_story()` method
- Agentic loop logic
- Tool execution routing
- Error handling
- Results compilation
- ~300 lines → Complete file

**Dependencies**: All modules
**Test**: Execute full story, verify all components work together

**Total Hour 10**: 60 minutes → Complete integration

---

## Day 3: Testing & Cleanup (2-4 hours)

### Hour 11-12: Testing

#### 11.1 Unit Tests (60 min)
- Test each module independently
- Mock dependencies
- Verify interfaces
- ~20 test files

#### 11.2 Integration Tests (60 min)
- Test full execution flow
- Test XPath preservation
- Test registry checks
- Test TOTP generation
- Test Playwright generation

**Total Hours 11-12**: 120 minutes → Full test coverage

---

### Hour 13: Cleanup & Documentation

#### 13.1 Update Imports (30 min)
- Update `api/routes.py`
- Update `generator/playwright_generator.py` (if needed)
- Update any other files importing agent

#### 13.2 Remove Old Code (10 min)
- Rename `bedrock_playwright_agent.py` → `bedrock_playwright_agent.py.old`
- Keep as backup for 1 week

#### 13.3 Documentation (20 min)
- Update README
- Add module docstrings
- Document interfaces

**Total Hour 13**: 60 minutes → Cleanup complete

---

## Why This Timeline Works

### Parallel Extraction Strategy

**Instead of**: Extract → Test → Fix → Next (Sequential)
**We do**: Extract 3-5 modules → Test all → Fix all → Next batch (Parallel)

### I Can:
1. **See entire codebase** - No need to search for dependencies
2. **Extract multiple modules simultaneously** - Work on 3-5 at once
3. **Fix integration issues immediately** - See conflicts before they happen
4. **Test comprehensively** - Run all tests in parallel

### Time Breakdown:
- **Day 1**: 6 hours → 11 modules extracted
- **Day 2**: 6 hours → 6 modules + integration
- **Day 3**: 4 hours → Testing + cleanup
- **Total**: 16 hours (2 days) vs 15-20 days for human

---

## Critical Success Factors

### 1. XPath Preservation (MUST WORK)
**Location**: `discovery/registry_manager.py`
**Test**: Manual XPath in registry → Agent discovers element → XPath preserved
**Verification**: Check registry file, verify manual XPath unchanged

### 2. Registry Check Order (MUST WORK)
**Location**: `browser/element_locator.py`
**Test**: Element in registry → Registry check first → Skip tree climbing
**Verification**: Check logs, verify "Using XPath from registry" message

### 3. TOTP Fallback (MUST WORK)
**Location**: `tools/browser_fill.py` + `utils/totp_handler.py`
**Test**: TOTP step → Generate code → Try fallback selectors → Fill field
**Verification**: Check logs, verify TOTP code generated and filled

### 4. Discovery Tracking (MUST WORK)
**Location**: `discovery/discovery_tracker.py`
**Test**: Click element → Track discovery → Save to registry
**Verification**: Check discoveries JSON, verify metadata saved

### 5. Playwright Generation (MUST WORK)
**Location**: `generator/playwright_generator.py` (already modular)
**Test**: Execute story → Generate Playwright → Verify XPaths match
**Verification**: Run generated test, verify it passes

---

## Execution Plan

### Step-by-Step Execution Order

1. **Create structure** (5 min)
   ```bash
   mkdir -p agent/{core,llm,browser,discovery,tools,utils}
   ```

2. **Extract utilities first** (1 hour)
   - `utils/story_parser.py`
   - `utils/totp_handler.py`
   - `browser/screenshot_manager.py`
   - Test: Import and verify functions work

3. **Extract browser components** (1 hour)
   - `browser/playwright_manager.py`
   - `browser/element_locator.py`
   - Test: Start browser, find element

4. **Extract discovery components** (1 hour)
   - `discovery/xpath_generator.py`
   - `discovery/discovery_tracker.py`
   - `discovery/registry_manager.py`
   - Test: Track discovery, verify XPath preserved

5. **Extract LLM components** (1 hour)
   - `llm/bedrock_client.py`
   - `llm/prompt_builder.py`
   - `llm/tool_definitions.py`
   - Test: Make LLM call, verify response

6. **Extract core components** (1 hour)
   - `core/execution_context.py`
   - `core/agent.py` (skeleton)
   - Test: Track execution state

7. **Extract tool handlers** (3 hours)
   - `tools/browser_navigate.py`
   - `tools/browser_click.py` ⚠️
   - `tools/browser_fill.py` ⚠️
   - `tools/browser_evaluate.py`
   - `tools/browser_verify.py`
   - Test: Execute each tool, verify behavior

8. **Extract action executor** (1 hour)
   - `browser/action_executor.py`
   - Test: Execute actions, verify validation

9. **Complete integration** (1 hour)
   - Finish `core/agent.py`
   - Wire all components
   - Test: Execute full story

10. **Testing & cleanup** (2 hours)
    - Unit tests
    - Integration tests
    - Update imports
    - Remove old code
    - Documentation

---

## Risk Mitigation

### Risk 1: XPath Preservation Broken
**Mitigation**: 
- Copy exact logic line-by-line
- Test immediately after extraction
- Compare registry files before/after

### Risk 2: Integration Issues
**Mitigation**:
- Extract modules in dependency order
- Test after each extraction
- Keep old code until new works

### Risk 3: Performance Regression
**Mitigation**:
- Profile before/after
- Verify no new imports slow startup
- Check memory usage

### Risk 4: Missing Functionality
**Mitigation**:
- Create checklist of all methods
- Verify each method extracted
- Test each method independently

---

## Success Criteria

### Code Quality
- ✅ All files < 500 lines
- ✅ All methods < 50 lines
- ✅ Cyclomatic complexity < 10
- ✅ No circular dependencies

### Functionality
- ✅ All existing tests pass
- ✅ XPath preservation works
- ✅ Registry checks work
- ✅ TOTP generation works
- ✅ Playwright generation works
- ✅ Full story execution works

### Performance
- ✅ No regression in execution time
- ✅ Import time < 1 second
- ✅ Memory usage similar

---

## Ready to Start?

**I can begin immediately and work through this plan systematically.**

**Estimated Completion**: 2-3 days (16-20 hours of work)

**Would you like me to:**
1. Start with Hour 1 (utilities extraction)?
2. Show you a sample extraction first?
3. Adjust the plan based on your priorities?

Let me know and I'll begin!





