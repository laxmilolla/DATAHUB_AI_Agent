# REFACTOR Excel Input Workflow

## Overview
The Excel workflow is **completely deterministic** - it does NOT use Bedrock, Claude, or any AI. It's a direct code generator that converts Excel rows to Playwright Python code.

---

## 🔄 Complete Workflow

```
Excel File Upload
    ↓
Excel Validation (Structure Check)
    ↓
Pandas Reads Excel Rows
    ↓
Template-Based Code Generation (No AI)
    ↓
Python Playwright File Generated
    ↓
TestRunner Executes Python File (Direct Playwright)
    ↓
Results Captured & Saved
```

---

## 📋 Step-by-Step Breakdown

### **Step 1: Excel Upload**
- **File**: `REFACTOR/api/excel_routes.py` → `upload_excel()`
- **What happens**:
  - User uploads `.xlsx` or `.xls` file
  - File saved to `storage/excel_files/`
  - Metadata saved to `storage/excel_files/metadata/`
- **No AI involved**: Just file handling

---

### **Step 2: Excel Validation**
- **File**: `REFACTOR/generator/excel_validator.py`
- **What happens**:
  - Reads Excel with pandas
  - Checks required columns: `Step`, `URL`, `XPath`, `Action`
  - Validates data types and formats
  - Checks for empty values
  - Validates URLs, XPaths, actions
- **No AI involved**: Pure validation logic

**Validation checks**:
- Required columns exist
- Step numbers are valid
- URLs are valid format
- XPaths are valid format
- Actions are valid (`navigate`, `click`, `fill`, `wait`, `verify`)

---

### **Step 3: Code Generation (Template-Based)**
- **File**: `REFACTOR/generator/excel_generator.py`
- **What happens**:
  - Reads Excel rows with pandas
  - For each row, calls template function based on `Action`:
    - `navigate` → `generate_navigate_code()`
    - `click` → `generate_click_code()`
    - `fill` → `generate_fill_code()`
    - `wait` → `generate_wait_code()`
    - `verify` → `generate_verify_code()`
  - Each function generates Python code as a string
  - All code strings concatenated into complete Python file
- **No AI involved**: Pure string template generation

**Example Code Generation**:

```python
# Excel Row:
Step: 1
Action: navigate
URL: https://example.com
XPath: N/A

# Generated Code:
# Step 1: Navigate to https://example.com
page.wait_for_timeout(3000)
try:
    page.goto('https://example.com')
    page.wait_for_load_state('networkidle')
    print('📍 Step 1: Navigated to https://example.com')
    page.screenshot(path='storage/screenshots/pw_step1_navigate.png')
except Exception as e:
    print(f'❌ Step 1: Navigation failed: {e}')
```

**Template Functions**:
- `generate_navigate_code()` - Creates `page.goto()` code
- `generate_click_code()` - Creates `element.click()` code
- `generate_fill_code()` - Creates `element.fill()` code (handles TOTP)
- `generate_wait_code()` - Creates `page.wait_for_timeout()` code
- `generate_verify_code()` - Creates element verification code

---

### **Step 4: Test Execution**
- **File**: `REFACTOR/api/excel_routes.py` → `generate_from_excel()` → Background thread
- **What happens**:
  - Python file saved to `storage/excel_tests/`
  - File copied to `tests/generated/` (where TestRunner expects it)
  - `TestRunner.run()` executes Python file as subprocess
  - Playwright runs directly (no AI interpretation)
- **No AI involved**: Direct Playwright execution

**TestRunner Flow**:
```python
# REFACTOR/api/excel_routes.py (line 230-262)
def run_excel_test_background():
    # Import TestRunner
    from validator.test_runner import TestRunner
    
    # Copy test file to tests/generated/
    shutil.copy2(output_file, test_dest)
    
    # Run test as subprocess
    runner = TestRunner(project_root)
    test_result = runner.run(test_filename_to_run, execution_id=execution_id)
    
    # Save results
    execution_data['status'] = test_result.get('status')
    execution_data['screenshots'] = test_result.get('screenshots')
```

**TestRunner** (`BACKUP/validator/test_runner.py`):
- Runs Python file as subprocess: `subprocess.run([python_executable, test_path])`
- Captures stdout/stderr
- Counts assertions (✅/❌ in output)
- Collects screenshots
- Returns results dict

---

### **Step 5: Results Storage**
- **What happens**:
  - Test results saved to `storage/executions/<execution_id>.json`
  - Excel metadata updated with execution results
  - Screenshots saved to `storage/screenshots/`
- **No AI involved**: Just file I/O

---

## 🔑 Key Points

### **No AI/Bedrock Used**
- ✅ Excel validation: Pure logic
- ✅ Code generation: String templates
- ✅ Test execution: Direct Playwright subprocess
- ✅ Results: File I/O

### **Deterministic Process**
- Same Excel input → Same Python code → Same execution
- No LLM interpretation
- No element discovery
- No adaptive behavior

### **Template-Based Generation**
- Each Excel row maps to a code template
- Templates are hardcoded functions
- No learning or adaptation

---

## 📊 Example: Complete Flow

**Input Excel**:
| Step | Action | URL | XPath | Object Type | Text Value |
|------|--------|-----|-------|-------------|------------|
| 1 | navigate | https://example.com | N/A | page | |
| 2 | click | | //button[@id='login'] | button | |
| 3 | fill | | //input[@name='email'] | input | test@example.com |

**Generated Python**:
```python
from playwright.sync_api import sync_playwright

def test_excel_20240115_120000():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Step 1: Navigate to https://example.com
        page.wait_for_timeout(3000)
        try:
            page.goto('https://example.com')
            page.wait_for_load_state('networkidle')
            print('📍 Step 1: Navigated to https://example.com')
            page.screenshot(path='storage/screenshots/pw_step1_navigate.png')
        except Exception as e:
            print(f'❌ Step 1: Navigation failed: {e}')
        
        # Step 2: Click button
        page.wait_for_timeout(3000)
        try:
            selector = 'xpath=//button[@id=\'login\']'
            element = page.locator(selector).nth(0)
            element.wait_for(state='visible', timeout=10000)
            element.click()
            print('✅ Step 2: Clicked button')
            page.screenshot(path='storage/screenshots/pw_step2_button.png')
        except Exception as e:
            print(f'❌ Step 2: Failed to click button: {e}')
        
        # Step 3: Fill input
        page.wait_for_timeout(3000)
        try:
            selector = 'xpath=//input[@name=\'email\']'
            element = page.locator(selector).nth(0)
            element.wait_for(state='visible', timeout=10000)
            element.fill('test@example.com')
            print('✅ Step 3: Filled input')
            page.screenshot(path='storage/screenshots/pw_step3_input.png')
        except Exception as e:
            print(f'❌ Step 3: Failed to fill input: {e}')
        
        browser.close()
```

**Execution**:
- TestRunner runs Python file
- Playwright executes code line by line
- Screenshots captured
- Results saved

---

## 🆚 Comparison: Excel vs Instructions Workflow

| Feature | Excel Workflow | Instructions Workflow |
|---------|---------------|---------------------|
| **AI/Bedrock** | ❌ No | ✅ Yes (Claude) |
| **Code Generation** | Template-based | AI-generated |
| **Element Discovery** | ❌ No (XPath provided) | ✅ Yes (Agent finds elements) |
| **Adaptive Behavior** | ❌ No | ✅ Yes |
| **Deterministic** | ✅ Yes | ❌ No (can vary) |
| **Input Format** | Excel rows | Natural language |
| **Login Handling** | Manual (in Excel) | Automatic (from test_case.xlsx) |

---

## 📁 Key Files

### **Excel Routes**
- `REFACTOR/api/excel_routes.py`
  - `upload_excel()` - File upload
  - `generate_from_excel()` - Code generation + execution

### **Code Generation**
- `REFACTOR/generator/excel_generator.py`
  - `generate_playwright_from_excel()` - Main generator
  - Template functions: `generate_navigate_code()`, `generate_click_code()`, etc.

### **Validation**
- `REFACTOR/generator/excel_validator.py`
  - `validate_excel_file()` - Structure validation
  - `_validate_row()` - Row validation

### **Test Execution**
- `BACKUP/validator/test_runner.py`
  - `TestRunner.run()` - Executes Python file as subprocess

---

## 💡 Summary

**The Excel workflow is:**
- ✅ **Deterministic**: Same input → Same output
- ✅ **Template-based**: Code generated from string templates
- ✅ **No AI**: Pure code generation and execution
- ✅ **Fast**: No LLM calls, no interpretation
- ✅ **Predictable**: Excel rows map directly to Playwright code

**It does NOT:**
- ❌ Use Bedrock/Claude
- ❌ Discover elements dynamically
- ❌ Adapt to page changes
- ❌ Interpret natural language
- ❌ Make decisions

**It's a simple, deterministic code generator that converts Excel test cases to executable Playwright scripts.**

