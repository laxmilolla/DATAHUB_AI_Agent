# Refactoring Execution Plan - Step by Step

## Goal
Refactor `agent/bedrock_playwright_agent.py` (3,580 lines) into 21 modular files (~5,000 lines total) with 85% code reuse.

## Success Criteria
- ✅ All modules extracted
- ✅ All tests pass
- ✅ XPath preservation works
- ✅ Registry checks work
- ✅ TOTP generation works
- ✅ Code is testable

---

## Execution Steps

### Phase 1: Setup Structure (5 min)
- [x] Create directory structure
- [x] Create __init__.py files

### Phase 2: Extract Utilities (1 hour)
- [ ] Extract `utils/story_parser.py` (150 lines, 3 functions)
- [ ] Extract `utils/totp_handler.py` (150 lines, 4 functions)
- [ ] Extract `browser/screenshot_manager.py` (150 lines, 5 functions)
- [ ] Test: Import and verify functions work

### Phase 3: Extract Browser Components (1 hour)
- [ ] Extract `browser/playwright_manager.py` (200 lines, 6 functions)
- [ ] Extract `browser/element_locator.py` (400 lines, 8 functions)
- [ ] Test: Start browser, find element

### Phase 4: Extract Discovery Components (1 hour)
- [ ] Extract `discovery/xpath_generator.py` (300 lines, 6 functions)
- [ ] Extract `discovery/discovery_tracker.py` (300 lines, 5 functions)
- [ ] Extract `discovery/registry_manager.py` (250 lines, 4 functions)
- [ ] Test: Track discovery, verify XPath preserved

### Phase 5: Extract LLM Components (1 hour)
- [ ] Extract `llm/bedrock_client.py` (200 lines, 5 functions)
- [ ] Extract `llm/prompt_builder.py` (250 lines, 4 functions)
- [ ] Extract `llm/tool_definitions.py` (150 lines, 1 function)
- [ ] Test: Make LLM call, verify response

### Phase 6: Extract Core Components (1 hour)
- [ ] Extract `core/execution_context.py` (150 lines, 8 functions)
- [ ] Extract `core/agent.py` (skeleton, 300 lines, 5 functions)
- [ ] Test: Track execution state

### Phase 7: Extract Tool Handlers (3 hours)
- [ ] Extract `tools/browser_navigate.py` (100 lines, 2 functions)
- [ ] Extract `tools/browser_click.py` (500 lines, 8 functions) ⚠️
- [ ] Extract `tools/browser_fill.py` (400 lines, 6 functions) ⚠️
- [ ] Extract `tools/browser_evaluate.py` (100 lines, 2 functions)
- [ ] Extract `tools/browser_verify.py` (200 lines, 3 functions)
- [ ] Test: Execute each tool, verify behavior

### Phase 8: Extract Action Executor (1 hour)
- [ ] Extract `browser/action_executor.py` (500 lines, 10 functions)
- [ ] Test: Execute actions, verify validation

### Phase 9: Complete Integration (1 hour)
- [ ] Complete `core/agent.py` - wire all components
- [ ] Update imports in `api/routes.py`
- [ ] Test: Execute full story

### Phase 10: Testing & Cleanup (1 hour)
- [ ] Run existing tests
- [ ] Fix integration issues
- [ ] Verify XPath preservation
- [ ] Verify registry checks
- [ ] Verify TOTP generation
- [ ] Rename old file to `.old`

---

## Critical Checkpoints

### Checkpoint 1: After Phase 2 (Utilities)
- ✅ Can import story_parser
- ✅ Can import totp_handler
- ✅ Can import screenshot_manager
- ✅ Functions work independently

### Checkpoint 2: After Phase 4 (Discovery)
- ✅ XPath preservation logic exact copy
- ✅ Registry manager preserves manual XPaths
- ✅ Discovery tracker saves metadata

### Checkpoint 3: After Phase 7 (Tools)
- ✅ Browser_click checks registry first
- ✅ Browser_fill handles TOTP correctly
- ✅ All tools execute successfully

### Checkpoint 4: After Phase 9 (Integration)
- ✅ Full story execution works
- ✅ All components wired correctly
- ✅ No circular dependencies

### Checkpoint 5: After Phase 10 (Testing)
- ✅ All tests pass
- ✅ XPath preservation verified
- ✅ Registry checks verified
- ✅ TOTP generation verified
- ✅ Code is testable

---

## Execution Log

Starting execution...





