# Excel Test Generation System - Flow Documentation

## Overview
This document explains how the Excel-based test generation system works, including the interaction between Excel files, JSON element registries, and test generation.

---

## System Architecture

```
Excel File (.xlsx)
    ↓
Excel Upload & Validation
    ↓
Excel → JSON Registry (Auto-population)
    ↓
Test Generation (TypeScript Playwright)
    ↓
Test Execution
    ↓
Results & Screenshots
```

---

## 1. Excel File Structure

### Excel Columns
- **Step**: Step number/identifier (e.g., 1, 2, 13, 14)
- **URL**: Page URL where the step should execute
- **XPath**: Element XPath selector
- **Object Type**: Type of element (button, input, dropdown, option, etc.)
- **Action**: Action to perform (click, fill, navigate, wait, verify)
- **Text Value**: Value to fill (for fill actions) or option text (for dropdowns)
- **Functions**: Special functions (e.g., TOTP for two-factor authentication)
- **Wait Time**: Wait time in milliseconds (for wait actions)
- **Optional**: true/false (whether step failure should stop the test)

### Example Excel Row
```
Step: 13
URL: https://hub-stage.datacommons.cancer.gov/data-submissions
XPath: //div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]
Object Type: dropdown
Action: click
Text Value: (empty)
Functions: (empty)
Wait Time: 3000
Optional: false
```

---

## 2. JSON Element Registry System

### Registry File Structure
**Location**: `element_maps/{domain}/{page}_page.json`

**Example**: `element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json`

### Registry JSON Format
```json
{
  "page": "data-submissions",
  "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
  "version": "1.0",
  "timestamp": "2026-01-21T18:00:00Z",
  "elements": {
    "dropdown_16": {
      "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
      "selector": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
      "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
      "element_id": "ID_70bc9e6a",
      "usage_count": 0,
      "object_type": "dropdown",
      "action": "click",
      "source": "excel",
      "discovered_at": "2026-01-21T18:00:00Z"
    }
  },
  "id_index": {
    "ID_70bc9e6a": "dropdown_16"
  }
}
```

### Key Registry Fields
- **element_id**: Unique identifier (e.g., `ID_70bc9e6a`)
- **xpath**: XPath selector for the element
- **selector**: Alternative selector (usually same as XPath)
- **url**: URL where element was discovered/used
- **object_type**: Type of element
- **action**: Action performed on element
- **source**: Source of element (`excel`, `ai_discovery`, `manual`)

---

## 3. Flow: Excel → JSON Registry → Test Generation

### Step 1: Excel Upload
**File**: `REFACTOR/api/excel_routes.py` → `upload_excel()`

1. User uploads Excel file via UI
2. System validates Excel format
3. System generates unique `excel_id` (e.g., `excel_20260121_180912_4139f0c1`)
4. Excel file saved to `storage/excel_files/{excel_id}.xlsx`
5. Metadata saved to `storage/excel_files/metadata/{excel_id}.json`

### Step 2: Excel → JSON Registry (Auto-population)
**File**: `REFACTOR/generator/excel_registry_helper.py` → `populate_registry_from_excel()`

**Process**:
1. Read Excel file row by row
2. Extract elements (XPath, URL, Object Type, Action)
3. For each element:
   - Extract domain from URL (e.g., `hub-stage.datacommons.cancer.gov`)
   - Extract page name from URL (e.g., `data-submissions`)
   - Generate element name (e.g., `dropdown_16` for Step 13 dropdown)
   - Generate unique `element_id` (e.g., `ID_70bc9e6a`)
   - Save to registry: `element_maps/{domain}/{page}_page.json`

**Example**:
```
Excel Step 13:
  URL: https://hub-stage.datacommons.cancer.gov/data-submissions
  XPath: //div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]
  Object Type: dropdown
  Action: click

↓ Auto-populated to JSON:

element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json:
  {
    "dropdown_16": {
      "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
      "element_id": "ID_70bc9e6a",
      "object_type": "dropdown",
      "action": "click",
      "source": "excel"
    }
  }
```

### Step 3: Test Generation
**File**: `REFACTOR/generator/excel_generator_ts.py` → `generate_playwright_ts_from_excel()`

**Process**:
1. Read Excel file row by row
2. For each step:
   - Lookup `element_id` from registry using XPath and URL
   - Generate TypeScript Playwright code using registry XPath
   - Include registry lookup function in generated test

**Generated Test Code Structure**:
```typescript
// Registry lookup function
function getXpathById(elementId: string, url: string): string {
  // Lookup XPath from registry JSON files
  // Return XPath for element_id
}

test('test_excel_generated', async ({ page }) => {
  // Step 13: Click dropdown
  const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
  const xpath = getXpathById('ID_70bc9e6a', lookupUrl);  // ← Registry lookup
  const selector = `xpath=${xpath}`;
  const element = page.locator(selector).nth(0);
  await element.click();
});
```

### Step 4: Test Execution
**File**: `validator/typescript_test_runner.py` → `run()`

**Process**:
1. Execute generated TypeScript test using Playwright
2. Test uses registry lookup to get XPath for each element
3. Test executes steps using registry XPaths
4. Capture screenshots on failures
5. Save results to `storage/executions/{execution_id}.json`

---

## 4. Registry Lookup Flow

### How Element ID is Determined

**During Test Generation** (`excel_generator_ts.py`):
```python
# For each Excel row:
xpath = row.get('xpath')
url = row.get('url')
element_id = lookup_element_id_by_xpath(xpath, url, registry_files, element_maps_dir)
```

**Lookup Process** (`excel_registry_helper.py`):
1. Extract domain from URL: `hub-stage.datacommons.cancer.gov`
2. Extract page from URL: `data-submissions`
3. Load registry: `element_maps/{domain}/{page}_page.json`
4. Search for matching XPath in registry
5. Return `element_id` if found

**During Test Execution** (TypeScript):
```typescript
// Registry is loaded into memory as JavaScript object
const REGISTRY = {
  "hub-stage.datacommons.cancer.gov/data-submissions": {
    "ID_70bc9e6a": {
      "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]"
    }
  }
};

function getXpathById(elementId: string, url: string): string {
  const domain = extractDomain(url);
  const page = extractPage(url);
  const registryKey = `${domain}/${page}`;
  return REGISTRY[registryKey][elementId].xpath;
}
```

---

## 5. XPath Scoping for Modals

### Problem
Elements can exist in multiple contexts:
- **Main page**: Filter dropdowns, buttons
- **Modal dialogs**: Form fields, dropdowns inside modals

### Solution: XPath Scoping

**Main Page Element**:
```
XPath: //div[@id="mui-component-select-dataCommons"]
```

**Modal Element** (same ID, different context):
```
XPath: //div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]
```

**Why This Works**:
- Modal container has unique `data-testid`: `create-data-submission-dialog-data-commons-input`
- Scoping XPath to modal container ensures correct element is found
- Main page element doesn't have this parent, so it won't match

### Registry Storage
Modal elements are stored in the same registry file as main page elements, but with scoped XPaths:

```json
{
  "elements": {
    "dropdown_main": {
      "xpath": "//div[@id=\"mui-component-select-dataCommons\"]",
      "context": "main-page"
    },
    "dropdown_16": {
      "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
      "context": "modal"
    }
  }
}
```

---

## 6. File Paths and Locations

### Excel Files
- **Upload Location**: `storage/excel_files/{excel_id}.xlsx`
- **Metadata**: `storage/excel_files/metadata/{excel_id}.json`

### JSON Registries
- **Location**: `element_maps/{domain}/{page}_page.json`
- **Example**: `element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json`

### Generated Tests
- **Location**: `storage/excel_tests/{test_name}.spec.ts`
- **Example**: `storage/excel_tests/test_excel_excel_20260121_180912_4139f0c1.spec.ts`

### Execution Results
- **Location**: `storage/executions/{execution_id}.json`
- **Screenshots**: `storage/excel_tests/storage/screenshots/pw_step{number}_{element_name}.png`

---

## 7. Key Code Files

### Excel API Routes
- **File**: `REFACTOR/api/excel_routes.py`
- **Functions**:
  - `upload_excel()`: Upload and validate Excel
  - `generate_ts_from_excel()`: Generate TypeScript test
  - `download_ts_test_zip()`: Download test package

### Excel Generator
- **File**: `REFACTOR/generator/excel_generator_ts.py`
- **Functions**:
  - `generate_playwright_ts_from_excel()`: Main generation function
  - `generate_click_code_ts()`: Generate click code
  - `generate_fill_code_ts()`: Generate fill code

### Registry Helper
- **File**: `REFACTOR/generator/excel_registry_helper.py`
- **Functions**:
  - `populate_registry_from_excel()`: Auto-populate registry from Excel
  - `lookup_element_id_by_xpath()`: Find element_id for XPath
  - `extract_elements_from_excel()`: Extract elements from Excel rows

### Test Runner
- **File**: `validator/typescript_test_runner.py`
- **Functions**:
  - `run()`: Execute TypeScript test
  - `_collect_screenshots()`: Collect screenshots after execution

---

## 8. Data Flow Diagram

```
┌─────────────┐
│  Excel File │
│  (test_case │
│   .xlsx)    │
└──────┬──────┘
       │
       │ Upload & Validate
       ▼
┌─────────────────────┐
│  Excel Metadata    │
│  (excel_id.json)   │
└──────┬─────────────┘
       │
       │ Auto-populate Registry
       ▼
┌─────────────────────────────────────┐
│  JSON Registry                      │
│  element_maps/{domain}/{page}.json  │
│  - Stores XPaths                    │
│  - Maps element_id → XPath          │
└──────┬──────────────────────────────┘
       │
       │ Generate Test (lookup element_id)
       ▼
┌─────────────────────┐
│  TypeScript Test    │
│  (.spec.ts)         │
│  - Uses registry    │
│  - References       │
│    element_id       │
└──────┬──────────────┘
       │
       │ Execute Test
       ▼
┌─────────────────────┐
│  Execution Results  │
│  (execution_id.json)│
│  - Status           │
│  - Screenshots      │
│  - Logs             │
└─────────────────────┘
```

---

## 9. Important Notes

### XPath Updates
- **When Excel XPath changes**: Registry is auto-updated during test generation
- **When JSON XPath changes**: Test must be regenerated to use new XPath
- **Best Practice**: Update Excel XPath, then regenerate test

### Element ID Uniqueness
- Each element gets unique `element_id` (e.g., `ID_70bc9e6a`)
- `element_id` is stable across test regenerations
- XPath can change, but `element_id` remains the same

### Registry as Source of Truth
- **JSON Registry** is the source of truth for XPaths
- Test generation uses registry XPaths, not Excel XPaths directly
- Excel XPaths are used to populate/update registry

### Modal Elements
- Modal elements use scoped XPaths (include modal container)
- Example: `//div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]`
- This ensures correct element is found even if ID exists on main page

---

## 10. Troubleshooting

### Issue: Test fails with "Registry lookup failed"
**Cause**: Element not found in registry or XPath mismatch
**Solution**: 
1. Check if element exists in registry JSON
2. Verify XPath in Excel matches registry XPath
3. Regenerate test from Excel

### Issue: Invalid XPath syntax error
**Cause**: XPath contains invalid characters or syntax
**Solution**:
1. Check XPath in Excel file
2. Verify XPath in JSON registry
3. Remove problematic parts (e.g., `and @role="button"` if causing issues)

### Issue: Element found on wrong page
**Cause**: XPath not scoped to modal/main page correctly
**Solution**:
1. Add modal container to XPath: `//div[@data-testid="modal-container"]//element`
2. Update Excel XPath
3. Regenerate test

---

## 11. Example: Complete Flow

### Step-by-Step Example

**1. Excel File** (`test_case.xlsx`):
```
Step: 13
URL: https://hub-stage.datacommons.cancer.gov/data-submissions
XPath: //div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]
Action: click
Object Type: dropdown
```

**2. Auto-populate Registry**:
```json
// element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json
{
  "dropdown_16": {
    "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
    "element_id": "ID_70bc9e6a",
    "source": "excel"
  }
}
```

**3. Generate Test**:
```typescript
// storage/excel_tests/test_excel.spec.ts
const xpath = getXpathById('ID_70bc9e6a', 'https://hub-stage.datacommons.cancer.gov/data-submissions');
// Returns: //div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]
await page.locator(`xpath=${xpath}`).click();
```

**4. Execute Test**:
- Test runs, uses registry XPath
- Element found correctly in modal
- Step passes ✅

---

## Summary

The Excel test generation system uses a **two-stage approach**:

1. **Excel → JSON Registry**: Excel XPaths are automatically saved to JSON registries
2. **JSON Registry → Test**: Generated tests use registry XPaths via `element_id` lookup

**Key Benefits**:
- Centralized element management (JSON registries)
- Stable element IDs across test regenerations
- Automatic registry updates from Excel
- Support for modal/main page element scoping

**Key Files**:
- Excel: `test_case.xlsx`
- Registry: `element_maps/{domain}/{page}_page.json`
- Generated Test: `storage/excel_tests/{test_name}.spec.ts`
- Results: `storage/executions/{execution_id}.json`

