# Refactored Code Structure - Detailed Breakdown

## Overview: Before vs After

### Before (Current)
```
agent/bedrock_playwright_agent.py
├── 3,580 lines
├── 29 methods
├── 1 class (BedrockPlaywrightAgent)
└── All responsibilities mixed together
```

### After (Refactored)
```
agent/
├── core/ (2 modules, ~450 lines, 8 functions)
├── llm/ (3 modules, ~600 lines, 12 functions)
├── browser/ (4 modules, ~1,200 lines, 25 functions)
├── discovery/ (4 modules, ~1,050 lines, 20 functions)
├── tools/ (5 modules, ~1,300 lines, 15 functions)
└── utils/ (3 modules, ~400 lines, 10 functions)

Total: 21 modules, ~5,000 lines, 90 functions
```

**Note**: Slight increase in total lines due to:
- Module docstrings
- Type hints
- Interface definitions
- Better error handling

---

## Module-by-Module Breakdown

### 1. `agent/utils/story_parser.py` (150 lines, 3 functions)

**Reused from**: Lines 64-136

```python
class StoryParser:
    """Parse story into steps with metadata"""
    
    def parse(self, story: str) -> Dict[int, Dict]:
        """
        Parse story and extract metadata for each step
        Returns: {step_number: {metadata}}
        """
        # Lines 64-136 extracted exactly
        # ~70 lines
        
    def _extract_step_metadata(self, step_text: str) -> Dict:
        """
        Extract metadata from step text
        Returns: {type, location, parent_hint, etc.}
        """
        # Lines 87-132 extracted
        # ~45 lines
        
    def _detect_element_type(self, step_text: str) -> str:
        """
        Detect element type (tab, accordion, checkbox)
        """
        # Lines 90-96 extracted
        # ~35 lines
```

**Functions**: 3
**Lines**: 150
**Reused**: 100% (exact copy from original)
**New**: 50 lines (docstrings, type hints, minor cleanup)

---

### 2. `agent/utils/totp_handler.py` (150 lines, 4 functions)

**Reused from**: Lines 2720-2772, 2080-2120

```python
class TOTPHandler:
    """Handle TOTP code generation"""
    
    def generate_code(self, secret_key: str = None) -> str:
        """
        Generate TOTP code
        Returns: 6-digit code
        """
        # Lines 2755-2771 extracted
        # ~40 lines
        
    def _extract_secret_from_story(self, story: str) -> Optional[str]:
        """
        Extract secret key from story text
        """
        # Lines 2730-2754 extracted
        # ~50 lines
        
    def _get_secret_from_env(self) -> Optional[str]:
        """
        Get secret key from environment variable
        """
        # New helper function
        # ~20 lines
        
    def is_totp_step(self, step_text: str, text: str) -> bool:
        """
        Detect if step is TOTP-related
        """
        # Lines 2714-2718 extracted
        # ~40 lines
```

**Functions**: 4
**Lines**: 150
**Reused**: 80% (TOTP generation logic)
**New**: 20% (helper functions, better organization)

---

### 3. `agent/browser/screenshot_manager.py` (150 lines, 5 functions)

**Reused from**: Lines 47-49, 584-686

```python
class ScreenshotManager:
    """Manage screenshot capture and storage"""
    
    def __init__(self, screenshots_dir: Path):
        """
        Initialize screenshot manager
        """
        # Lines 47-49 extracted
        # ~20 lines
        
    async def capture(self, page: Page, name: str) -> Dict[str, str]:
        """
        Capture screenshot
        Returns: {path, url}
        """
        # Lines 584-686 extracted
        # ~50 lines
        
    def _get_screenshot_path(self, name: str) -> Path:
        """
        Generate screenshot file path
        """
        # Extracted from capture logic
        # ~30 lines
        
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename for filesystem
        """
        # Lines 452-466 extracted
        # ~30 lines
        
    async def capture_post_click(self, page: Page, element_name: str) -> Dict:
        """
        Capture screenshot after click
        """
        # Lines 584-686 extracted
        # ~20 lines
```

**Functions**: 5
**Lines**: 150
**Reused**: 90% (screenshot logic)
**New**: 10% (better organization, helper methods)

---

### 4. `agent/browser/playwright_manager.py` (200 lines, 6 functions)

**Reused from**: Lines 34-42, 137-157

```python
class PlaywrightManager:
    """Manage Playwright browser lifecycle"""
    
    def __init__(self):
        """
        Initialize Playwright manager
        """
        # Lines 34-42 extracted
        # ~30 lines
        
    async def start(self, headless: bool = True) -> None:
        """
        Start browser
        """
        # Lines 137-149 extracted
        # ~40 lines
        
    async def close(self) -> None:
        """
        Close browser
        """
        # Lines 151-156 extracted
        # ~20 lines
        
    def get_page(self) -> Page:
        """
        Get current page
        """
        # New helper
        # ~10 lines
        
    def get_current_url(self) -> str:
        """
        Get current page URL
        """
        # Lines 158-197 extracted (partially)
        # ~50 lines
        
    def _get_domain_and_page(self) -> tuple:
        """
        Extract domain and page from URL
        """
        # Lines 158-196 extracted
        # ~50 lines
```

**Functions**: 6
**Lines**: 200
**Reused**: 85% (browser management)
**New**: 15% (helper methods, better API)

---

### 5. `agent/browser/element_locator.py` (400 lines, 8 functions)

**Reused from**: Lines 197-400, 476-492

```python
class ElementLocator:
    """Find elements using multiple strategies"""
    
    def __init__(self, page: Page, registry: ElementRegistry):
        """
        Initialize element locator
        """
        # ~30 lines
        
    async def find_element(self, selector: str, element_description: str) -> Locator:
        """
        Find element using registry-first strategy
        """
        # Lines 197-400 extracted (main logic)
        # ~100 lines
        
    def check_registry(self, element_description: str) -> Optional[str]:
        """
        Check element registry first
        Returns: selector if found, None otherwise
        """
        # Lines 197-347 extracted
        # ~150 lines
        
    def normalize_selector(self, selector: str) -> tuple:
        """
        Normalize selector for dynamic content
        """
        # Lines 401-451 extracted
        # ~50 lines
        
    async def find_parent_or_sibling(self, selector: str) -> Optional[Locator]:
        """
        Try tree climbing to find interactive parent
        """
        # Lines 476-492 extracted
        # ~40 lines
        
    async def try_tree_climbing(self, selector: str) -> Optional[Locator]:
        """
        Tree climbing strategy
        """
        # Extracted from click logic
        # ~30 lines
```

**Functions**: 8
**Lines**: 400
**Reused**: 90% (registry checking, tree climbing)
**New**: 10% (better organization, clearer API)

---

### 6. `agent/browser/action_executor.py` (500 lines, 10 functions)

**Reused from**: Lines 493-583, 687-776, 1973-2044

```python
class ActionExecutor:
    """Execute browser actions with validation"""
    
    def __init__(self, page: Page, screenshot_manager: ScreenshotManager):
        """
        Initialize action executor
        """
        # ~20 lines
        
    async def click(self, locator: Locator, element_description: str) -> Dict:
        """
        Execute click with validation
        """
        # Lines 1973-2044 extracted
        # ~150 lines
        
    async def fill(self, locator: Locator, text: str) -> Dict:
        """
        Execute fill with validation
        """
        # Extracted from fill logic
        # ~100 lines
        
    async def validate_visibility(self, selector: str, element_description: str) -> Dict:
        """
        Validate element visibility
        """
        # Lines 493-583 extracted
        # ~90 lines
        
    async def validate_filter_applied(self, filter_name: str, initial_state: Dict) -> Dict:
        """
        Validate filter was applied
        """
        # Lines 687-776 extracted
        # ~90 lines
        
    async def handle_dialogs(self) -> None:
        """
        Handle blocking dialogs
        """
        # Extracted from click logic
        # ~50 lines
```

**Functions**: 10
**Lines**: 500
**Reused**: 85% (validation, execution logic)
**New**: 15% (better organization, error handling)

---

### 7. `agent/discovery/xpath_generator.py` (300 lines, 6 functions)

**Reused from**: Lines 941-1077

```python
class XPathGenerator:
    """Generate unique XPaths for elements"""
    
    def __init__(self, page: Page):
        """
        Initialize XPath generator
        """
        # Uses utils.xpath_builder.XPathBuilder
        # ~20 lines
        
    async def generate_xpath(self, element_attrs: Dict, element_name: str) -> Dict:
        """
        Generate unique XPath
        Returns: {xpath, uniqueness_method}
        """
        # Lines 941-1007 extracted
        # ~100 lines
        
    async def extract_element_attributes(self, locator: Locator) -> Dict:
        """
        Extract element attributes
        """
        # Lines 1008-1062 extracted
        # ~80 lines
        
    def extract_xpath_from_result(self, result_string: str) -> str:
        """
        Extract XPath from string result
        """
        # Lines 1063-1077 extracted
        # ~50 lines
        
    def _build_xpath_from_attributes(self, attrs: Dict) -> str:
        """
        Build XPath from attributes
        """
        # Helper method
        # ~50 lines
```

**Functions**: 6
**Lines**: 300
**Reused**: 90% (XPath generation logic)
**New**: 10% (better organization, helper methods)

---

### 8. `agent/discovery/discovery_tracker.py` (300 lines, 5 functions)

**Reused from**: Lines 1078-1193

```python
class DiscoveryTracker:
    """Track element discoveries"""
    
    def __init__(self, xpath_generator: XPathGenerator):
        """
        Initialize discovery tracker
        """
        # ~20 lines
        
    async def track(self, element_name: str, original_query: str, 
                   final_selector: str, discovery_method: str, 
                   metadata: dict) -> Dict:
        """
        Track element discovery
        Returns: Discovery metadata
        """
        # Lines 1078-1193 extracted
        # ~120 lines
        
    async def _extract_element_attributes(self, element: Locator) -> Dict:
        """
        Extract attributes from element
        """
        # Lines 1008-1062 extracted (shared with XPathGenerator)
        # ~80 lines
        
    def _build_discovery_metadata(self, element_name: str, selector: str, 
                                 method: str, xpath: str) -> Dict:
        """
        Build discovery metadata dict
        """
        # Helper method
        # ~50 lines
        
    def _handle_tree_climbing_discovery(self, metadata: dict, element_name: str) -> Dict:
        """
        Handle discovery when tree climbing found parent
        """
        # Extracted from _track_discovery
        # ~30 lines
```

**Functions**: 5
**Lines**: 300
**Reused**: 85% (discovery tracking logic)
**New**: 15% (better organization, helper methods)

---

### 9. `agent/discovery/registry_manager.py` (250 lines, 4 functions)

**Reused from**: Lines 3342-3500+ (approximate)

```python
class RegistryManager:
    """Manage element registry operations"""
    
    def __init__(self, registry: ElementRegistry):
        """
        Initialize registry manager
        """
        # ~20 lines
        
    async def save_discoveries(self, discoveries: List[Dict], 
                              preserve_manual: bool = True) -> None:
        """
        Save discoveries to registry
        CRITICAL: Preserves manual XPaths
        """
        # Lines 3342-3500+ extracted
        # ~150 lines
        
    def _preserve_manual_xpath(self, existing: Dict, new: Dict) -> Dict:
        """
        Preserve manual XPath if exists
        CRITICAL: Never overwrite manual XPaths
        """
        # Lines 3342-3360 extracted (exact copy)
        # ~40 lines
        
    def _backfill_element_id(self, discovery: Dict) -> Dict:
        """
        Backfill element_id into discovery
        """
        # Extracted from save logic
        # ~40 lines
```

**Functions**: 4
**Lines**: 250
**Reused**: 95% (CRITICAL: XPath preservation logic exact copy)
**New**: 5% (better organization)

---

### 10. `agent/llm/bedrock_client.py` (200 lines, 5 functions)

**Reused from**: Lines 34-36, 3290-3310, 867-887

```python
class BedrockClient:
    """Bedrock LLM API client"""
    
    def __init__(self, region: str, model_id: str):
        """
        Initialize Bedrock client
        """
        # Lines 34-36 extracted
        # ~20 lines
        
    async def converse(self, messages: List[Dict], tools: List[Dict], 
                      system_prompt: str) -> Dict:
        """
        Make LLM conversation call
        Returns: {stop_reason, tool_uses, response_text}
        """
        # Lines 3290-3310 extracted
        # ~80 lines
        
    def _extract_tool_uses(self, response: Dict) -> List[Dict]:
        """
        Extract tool uses from response
        """
        # Lines 3302-3306 extracted
        # ~30 lines
        
    async def _call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        """
        Simple LLM call for disambiguation
        """
        # Lines 867-887 extracted
        # ~50 lines
        
    def _format_response(self, response: Dict) -> Dict:
        """
        Format Bedrock response
        """
        # Helper method
        # ~20 lines
```

**Functions**: 5
**Lines**: 200
**Reused**: 85% (Bedrock API calls)
**New**: 15% (better error handling, response formatting)

---

### 11. `agent/llm/prompt_builder.py` (250 lines, 4 functions)

**Reused from**: Lines 3223-3282

```python
class PromptBuilder:
    """Build prompts for LLM"""
    
    def __init__(self, story_parser: StoryParser):
        """
        Initialize prompt builder
        """
        # ~20 lines
        
    def build_story_prompt(self, story: str) -> str:
        """
        Build formatted story prompt with action hints
        """
        # Lines 3223-3240 extracted
        # ~80 lines
        
    def add_action_hints(self, story: str, parsed_steps: Dict) -> str:
        """
        Add [ACTION] hints to story steps
        """
        # Lines 3224-3238 extracted
        # ~60 lines
        
    def get_system_prompt(self) -> str:
        """
        Get system prompt for agent
        """
        # Lines 3257-3282 extracted
        # ~70 lines
        
    def _detect_action_type(self, step_text: str, metadata: Dict) -> str:
        """
        Detect action type for hint
        """
        # Helper method
        # ~20 lines
```

**Functions**: 4
**Lines**: 250
**Reused**: 90% (prompt building logic)
**New**: 10% (better organization)

---

### 12. `agent/llm/tool_definitions.py` (150 lines, 1 function)

**Reused from**: Lines 3114-3210

```python
class ToolDefinitions:
    """Tool schema definitions for LLM"""
    
    def get_tools(self) -> List[Dict]:
        """
        Get tool definitions for Bedrock
        Returns: List of tool schemas
        """
        # Lines 3114-3210 extracted (exact copy)
        # ~100 lines
        
    # Constants for tool names
    BROWSER_NAVIGATE = "browser_navigate"
    BROWSER_CLICK = "browser_click"
    BROWSER_FILL = "browser_fill"
    BROWSER_EVALUATE = "browser_evaluate"
    BROWSER_VERIFY = "browser_verify"
    # ~50 lines
```

**Functions**: 1
**Lines**: 150
**Reused**: 100% (exact copy of tool schemas)
**New**: 0% (just constants added)

---

### 13. `agent/tools/browser_navigate.py` (100 lines, 2 functions)

**Reused from**: Lines 1202-1215

```python
class BrowserNavigateTool:
    """Handle browser_navigate tool"""
    
    def __init__(self, playwright_manager: PlaywrightManager, 
                 context: ExecutionContext):
        """
        Initialize navigate tool
        """
        # ~20 lines
        
    async def execute(self, url: str) -> str:
        """
        Execute navigation
        Returns: Result message
        """
        # Lines 1202-1215 extracted
        # ~60 lines
        
    def _validate_url(self, url: str) -> bool:
        """
        Validate URL format
        """
        # Helper method
        # ~20 lines
```

**Functions**: 2
**Lines**: 100
**Reused**: 80% (navigation logic)
**New**: 20% (validation, better error handling)

---

### 14. `agent/tools/browser_click.py` (500 lines, 8 functions) ⚠️ MOST COMPLEX

**Reused from**: Lines 1216-1972

```python
class BrowserClickTool:
    """Handle browser_click tool"""
    
    def __init__(self, element_locator: ElementLocator, 
                 action_executor: ActionExecutor,
                 discovery_tracker: DiscoveryTracker,
                 registry_manager: RegistryManager):
        """
        Initialize click tool
        """
        # ~30 lines
        
    async def execute(self, selector: str, element_description: str, 
                     step_metadata: Dict) -> str:
        """
        Execute click operation
        CRITICAL: Checks registry first, preserves XPaths
        """
        # Lines 1216-1972 extracted (main logic)
        # ~200 lines
        
    async def _handle_registry_xpath(self, selector: str, 
                                    element_description: str) -> Optional[str]:
        """
        Check registry first, skip tree climbing if found
        CRITICAL: If registry XPath found, skip discovery
        """
        # Lines 197-400 extracted (registry check)
        # ~80 lines
        
    async def _handle_tree_climbing(self, selector: str) -> Optional[Locator]:
        """
        Try tree climbing if registry check failed
        """
        # Lines 476-492, tree climbing logic extracted
        # ~60 lines
        
    async def _handle_discovery(self, element_name: str, selector: str, 
                               final_selector: str, method: str) -> None:
        """
        Track discovery (skip if using registry XPath)
        """
        # Lines 1078-1193 extracted (discovery tracking)
        # ~50 lines
        
    async def _validate_click(self, locator: Locator) -> Dict:
        """
        Validate click succeeded
        """
        # Lines 493-583 extracted
        # ~40 lines
        
    async def _handle_dialogs(self) -> None:
        """
        Handle blocking dialogs
        """
        # Extracted from click logic
        # ~40 lines
```

**Functions**: 8
**Lines**: 500
**Reused**: 90% (click logic, registry checks, discovery)
**New**: 10% (better organization, clearer flow)

---

### 15. `agent/tools/browser_fill.py` (400 lines, 6 functions) ⚠️ COMPLEX

**Reused from**: Lines 2636-2900+

```python
class BrowserFillTool:
    """Handle browser_fill tool"""
    
    def __init__(self, element_locator: ElementLocator,
                 action_executor: ActionExecutor,
                 totp_handler: TOTPHandler,
                 discovery_tracker: DiscoveryTracker):
        """
        Initialize fill tool
        """
        # ~30 lines
        
    async def execute(self, selector: str, text: str, 
                    step_metadata: Dict) -> str:
        """
        Execute fill operation
        CRITICAL: Checks registry first, handles TOTP
        """
        # Lines 2636-2900+ extracted (main logic)
        # ~150 lines
        
    async def _check_registry(self, element_name: str, 
                             selector: str) -> Optional[str]:
        """
        Check registry for element
        CRITICAL: Registry XPath = source of truth
        """
        # Lines 2646-2712 extracted (registry check)
        # ~80 lines
        
    async def _handle_totp(self, selector: str, step_text: str, 
                          text: str) -> str:
        """
        Handle TOTP code generation
        """
        # Uses TOTPHandler
        # ~50 lines
        
    async def _try_totp_fallbacks(self, selector: str) -> str:
        """
        Try TOTP fallback selectors
        CRITICAL: Only if not using registry XPath
        """
        # Lines 2774-2826 extracted (exact copy)
        # ~60 lines
        
    def _extract_element_name(self, step_text: str) -> Optional[str]:
        """
        Extract element name from step text for registry lookup
        """
        # Lines 2649-2676 extracted
        # ~30 lines
```

**Functions**: 6
**Lines**: 400
**Reused**: 90% (fill logic, TOTP fallbacks, registry checks)
**New**: 10% (better organization)

---

### 16. `agent/tools/browser_evaluate.py` (100 lines, 2 functions)

**Reused from**: Lines 2901-3000+ (approximate)

```python
class BrowserEvaluateTool:
    """Handle browser_evaluate tool"""
    
    def __init__(self, playwright_manager: PlaywrightManager):
        """
        Initialize evaluate tool
        """
        # ~20 lines
        
    async def execute(self, code: str) -> str:
        """
        Execute JavaScript code
        Returns: Result as string
        """
        # Extracted from evaluate logic
        # ~60 lines
        
    def _parse_result(self, result: Any) -> str:
        """
        Parse JavaScript result to string
        """
        # Helper method
        # ~20 lines
```

**Functions**: 2
**Lines**: 100
**Reused**: 80% (evaluation logic)
**New**: 20% (better error handling)

---

### 17. `agent/tools/browser_verify.py` (200 lines, 3 functions)

**Reused from**: Lines 3001-3113 (approximate)

```python
class BrowserVerifyTool:
    """Handle browser_verify_table tool"""
    
    def __init__(self, playwright_manager: PlaywrightManager):
        """
        Initialize verify tool
        """
        # ~20 lines
        
    async def execute(self, column_name: str, expected_value: str) -> str:
        """
        Verify table column values
        """
        # Uses utils.table_verification (already exists)
        # ~100 lines
        
    def _find_column_index(self, table: Locator, column_name: str) -> int:
        """
        Find column index by name
        """
        # Helper method
        # ~50 lines
        
    def _verify_rows(self, table: Locator, column_index: int, 
                    expected_value: str) -> bool:
        """
        Verify all rows match expected value
        """
        # Helper method
        # ~30 lines
```

**Functions**: 3
**Lines**: 200
**Reused**: 70% (verification logic)
**New**: 30% (better organization, helper methods)

---

### 18. `agent/core/execution_context.py` (150 lines, 8 functions)

**Reused from**: Lines 44-63, 3248-3255, 3318-3330

```python
class ExecutionContext:
    """Manage execution state"""
    
    def __init__(self, execution_id: str):
        """
        Initialize execution context
        """
        # Lines 44-63 extracted
        # ~30 lines
        
    def increment_step(self) -> None:
        """
        Increment current step number
        """
        # Lines 1199 extracted
        # ~10 lines
        
    def get_current_step_metadata(self) -> Dict:
        """
        Get metadata for current step
        """
        # Lines 207-208 extracted
        # ~20 lines
        
    def add_action(self, action: Dict) -> None:
        """
        Add action to results
        """
        # Lines 3318-3330 extracted
        # ~20 lines
        
    def add_screenshot(self, screenshot: Dict) -> None:
        """
        Add screenshot to results
        """
        # Extracted from screenshot logic
        # ~20 lines
        
    def get_results(self) -> Dict:
        """
        Get final results dict
        """
        # Lines 3248-3255 extracted
        # ~30 lines
        
    def set_story(self, story: str) -> None:
        """
        Set story for context
        """
        # Helper method
        # ~10 lines
        
    def set_parsed_steps(self, parsed_steps: Dict) -> None:
        """
        Set parsed steps
        """
        # Helper method
        # ~10 lines
```

**Functions**: 8
**Lines**: 150
**Reused**: 80% (state management)
**New**: 20% (better API, helper methods)

---

### 19. `agent/core/agent.py` (300 lines, 5 functions)

**Reused from**: Lines 3211-3580

```python
class Agent:
    """Main agent orchestrator"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize agent with all components
        """
        # Wire all components together
        # ~80 lines
        
    async def execute_story(self, story: str, max_iterations: int = 50) -> Dict:
        """
        Execute story using agentic loop
        """
        # Lines 3211-3255 extracted (initialization)
        # Lines 3284-3380 extracted (agentic loop)
        # ~100 lines
        
    async def _agentic_loop(self, story: str, max_iterations: int) -> Dict:
        """
        Main agentic loop
        """
        # Lines 3286-3380 extracted
        # ~80 lines
        
    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """
        Route tool execution to appropriate handler
        """
        # Routes to tool handlers
        # ~40 lines
```

**Functions**: 5
**Lines**: 300
**Reused**: 70% (orchestration logic)
**New**: 30% (component wiring, better structure)

---

## Summary Statistics

### Code Reuse Breakdown

| Category | Reused | New | Total |
|----------|--------|-----|-------|
| **Pure Logic** | 95% | 5% | Core algorithms unchanged |
| **Organization** | 0% | 100% | New structure |
| **Interfaces** | 0% | 100% | New APIs |
| **Error Handling** | 60% | 40% | Enhanced |
| **Documentation** | 0% | 100% | New docstrings |

### Overall Statistics

```
Total Modules: 21
Total Functions: 90
Total Lines: ~5,000

Average per Module:
- Functions: 4.3
- Lines: 238

Largest Module: browser_click.py (500 lines, 8 functions)
Smallest Module: browser_navigate.py (100 lines, 2 functions)

Code Reuse: ~85% (logic preserved)
New Code: ~15% (organization, interfaces, docs)
```

### Function Distribution

```
core/         13 functions
llm/          10 functions
browser/      19 functions
discovery/    15 functions
tools/        18 functions
utils/        15 functions
```

### Line Distribution

```
core/         450 lines
llm/          600 lines
browser/      1,200 lines
discovery/    1,050 lines
tools/        1,300 lines
utils/        400 lines
```

---

## What Gets Reused vs New

### ✅ Reused (85% of logic)

1. **XPath Preservation Logic** - Exact copy (CRITICAL)
   - Location: `discovery/registry_manager.py`
   - Lines: 3342-3360 → Exact copy

2. **Registry Check Logic** - Exact copy
   - Location: `browser/element_locator.py`
   - Lines: 197-400 → Exact copy

3. **TOTP Fallback Selectors** - Exact copy
   - Location: `tools/browser_fill.py`
   - Lines: 2774-2826 → Exact copy

4. **Tree Climbing Logic** - Exact copy
   - Location: `browser/element_locator.py`
   - Lines: 476-492 → Exact copy

5. **Discovery Tracking** - Exact copy
   - Location: `discovery/discovery_tracker.py`
   - Lines: 1078-1193 → Exact copy

6. **Tool Schemas** - Exact copy
   - Location: `llm/tool_definitions.py`
   - Lines: 3114-3210 → Exact copy

7. **Story Parsing** - Exact copy
   - Location: `utils/story_parser.py`
   - Lines: 64-136 → Exact copy

### 🆕 New (15% - organization & interfaces)

1. **Module Structure** - New
   - 21 focused modules vs 1 monolithic file

2. **Dependency Injection** - New
   - Components passed as dependencies

3. **Type Hints** - New
   - Better IDE support, type checking

4. **Interface Definitions** - New
   - Clear contracts between modules

5. **Better Error Handling** - Enhanced
   - More specific exceptions

6. **Documentation** - New
   - Module docstrings, function docs

---

## Example: How Code Looks After Refactoring

### Before (Current)
```python
# agent/bedrock_playwright_agent.py (3,580 lines)

class BedrockPlaywrightAgent:
    def __init__(self):
        # 60 lines of initialization
        self.bedrock = ...
        self.page = ...
        self.current_step_number = 0
        # ... 50 more lines
        
    def parse_story_metadata(self, story: str):
        # 70 lines
        
    async def execute_tool(self, tool_name: str, tool_input: Dict):
        # 1,800 lines (all tools mixed together)
        if tool_name == "browser_click":
            # 500 lines of click logic
        elif tool_name == "browser_fill":
            # 400 lines of fill logic
        # ... etc
        
    async def execute_story(self, story: str):
        # 200 lines
```

### After (Refactored)
```python
# agent/core/agent.py (300 lines)

from agent.browser.playwright_manager import PlaywrightManager
from agent.llm.bedrock_client import BedrockClient
from agent.tools.browser_click import BrowserClickTool
from agent.tools.browser_fill import BrowserFillTool
# ... other imports

class Agent:
    def __init__(self, region: str = 'us-east-1'):
        # Wire components (dependency injection)
        self.playwright_manager = PlaywrightManager()
        self.llm_client = BedrockClient(region)
        self.context = ExecutionContext()
        
        # Initialize tools
        self.click_tool = BrowserClickTool(
            element_locator=self.element_locator,
            action_executor=self.action_executor,
            discovery_tracker=self.discovery_tracker
        )
        # ... other tools
        
    async def execute_story(self, story: str, max_iterations: int = 50):
        # Parse story
        parsed_steps = self.story_parser.parse(story)
        self.context.set_parsed_steps(parsed_steps)
        
        # Start browser
        await self.playwright_manager.start()
        
        # Agentic loop
        return await self._agentic_loop(story, max_iterations)
        
    async def _execute_tool(self, tool_name: str, tool_input: Dict):
        # Route to appropriate tool handler
        if tool_name == "browser_click":
            return await self.click_tool.execute(**tool_input)
        elif tool_name == "browser_fill":
            return await self.fill_tool.execute(**tool_input)
        # ... etc
```

```python
# agent/tools/browser_click.py (500 lines)

class BrowserClickTool:
    def __init__(self, element_locator, action_executor, discovery_tracker):
        self.locator = element_locator
        self.executor = action_executor
        self.tracker = discovery_tracker
        
    async def execute(self, selector: str, element_description: str, step_metadata: Dict):
        # Check registry first
        registry_selector = await self.locator.check_registry(element_description)
        using_registry_xpath = False
        
        if registry_selector:
            selector = registry_selector
            if selector.startswith("xpath="):
                using_registry_xpath = True
                # Skip tree climbing & discovery
        
        # Try tree climbing if needed
        if not using_registry_xpath:
            locator = await self.locator.try_tree_climbing(selector)
        
        # Execute click
        result = await self.executor.click(locator, element_description)
        
        # Track discovery (skip if using registry XPath)
        if not using_registry_xpath:
            await self.tracker.track(element_description, selector, final_selector, method)
        
        return result
```

---

## Benefits Summary

### ✅ Maintainability
- **Before**: Find bug in 3,580 lines
- **After**: Find bug in specific 200-500 line module

### ✅ Testability
- **Before**: Mock entire agent class
- **After**: Mock single dependency

### ✅ Readability
- **Before**: Scroll through 3,580 lines
- **After**: Read focused 200-500 line module

### ✅ Extensibility
- **Before**: Modify 3,580 line file
- **After**: Add new tool handler module

### ✅ Performance
- **Before**: Import entire 3,580 line file
- **After**: Import only needed modules

---

## Conclusion

**Refactored Code Will Have**:
- ✅ 21 focused modules (vs 1 monolithic file)
- ✅ 90 functions (vs 29 methods)
- ✅ ~5,000 lines total (vs 3,580)
- ✅ 85% code reuse (logic preserved)
- ✅ 15% new code (organization, interfaces)
- ✅ Clear separation of concerns
- ✅ Easy to test, maintain, extend

**Critical Logic Preserved**:
- ✅ XPath preservation (exact copy)
- ✅ Registry check order (exact copy)
- ✅ TOTP fallback selectors (exact copy)
- ✅ Discovery tracking (exact copy)

**Ready to build?** I can start extracting modules now!


