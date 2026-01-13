# Refactoring Completion Plan - Final Steps

## ✅ Completed (17 modules)

1. ✅ `agent/utils/story_parser.py`
2. ✅ `agent/utils/totp_handler.py`
3. ✅ `agent/utils/llm_helper.py`
4. ✅ `agent/browser/screenshot_manager.py`
5. ✅ `agent/browser/playwright_manager.py`
6. ✅ `agent/browser/element_locator.py`
7. ✅ `agent/browser/action_executor.py`
8. ✅ `agent/discovery/xpath_generator.py`
9. ✅ `agent/discovery/discovery_tracker.py`
10. ✅ `agent/discovery/registry_manager.py` (CRITICAL: XPath preservation)
11. ✅ `agent/llm/bedrock_client.py`
12. ✅ `agent/llm/prompt_builder.py`
13. ✅ `agent/llm/tool_definitions.py`
14. ✅ `agent/core/execution_context.py`
15. ✅ `agent/tools/browser_navigate.py`
16. ✅ `agent/tools/browser_evaluate.py`
17. ✅ `agent/tools/browser_verify.py`

## ⏳ Remaining Critical Modules (3 files)

### 1. `agent/tools/browser_click.py` (MOST COMPLEX - 1300+ lines)
**Critical Logic to Preserve:**
- Registry check FIRST (lines 1277-1288)
- Skip tree climbing if using registry XPath (lines 1362-1366)
- Tree climbing logic (lines 1402-1555)
- LLM disambiguation (lines 1558-1595)
- Click strategies (lines 1973-2044)
- Discovery tracking (lines 2295-2388)
- Skip discovery if using registry XPath (lines 2352-2373)
- TOTP submission handling (lines 2046-2147)
- Tab/accordion validation (lines 2390-2527)

**Approach:** Create simplified but complete version preserving all critical logic

### 2. `agent/tools/browser_fill.py` (COMPLEX - 400+ lines)
**Critical Logic to Preserve:**
- Registry check FIRST (lines 2646-2712)
- TOTP detection (lines 2642-2772)
- TOTP fallback selectors (lines 2773-2827)
- Skip TOTP fallback if using registry XPath (line 2775)
- Discovery tracking

**Approach:** Create simplified but complete version preserving all critical logic

### 3. `agent/core/agent.py` (ORCHESTRATOR - 300+ lines)
**Purpose:** Wire all components together
- Initialize all components
- Execute story with agentic loop
- Route tool execution to handlers
- Save discoveries to registry

**Approach:** Create complete orchestrator

## Integration Tasks

1. Update `api/routes.py` to import from new structure
2. Test basic import
3. Test story execution
4. Verify XPath preservation
5. Verify registry checks
6. Verify TOTP generation

## Status: ~85% Complete

**Next:** Create browser_click.py, browser_fill.py, and agent.py to complete refactoring.





