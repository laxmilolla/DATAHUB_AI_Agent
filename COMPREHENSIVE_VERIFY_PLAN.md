# Comprehensive Verify Function - Implementation Plan

## ✅ IMPLEMENTATION COMPLETE

**Status**: Implemented and ready for testing
**Date**: 2026-01-22
**Files Modified**: 
- `REFACTOR/generator/excel_generator_ts.py` - Updated `generate_verify_code_ts()` function

## Implementation Summary

The comprehensive verify function has been successfully implemented with support for:
1. **Visibility Verification** (default) - Verifies element is visible
2. **Text Verification** - Verifies element text content matches expected value
3. **Table Verification** - Verifies all rows in a table column contain expected value

No new Excel columns were added - the implementation reuses existing `Functions` and `Text Value` columns.

## Overview
Enhance the `verify` action to support multiple verification types:
1. **Text Verification** - Verify element text content
2. **Table Verification** - Verify filtered table column values (all rows contain expected value)

## Current State

### Existing Verify Action
- **Location**: `REFACTOR/generator/excel_generator_ts.py` - `generate_verify_code_ts()`
- **Current Functionality**: Only verifies element visibility
- **Generated Code**: Checks if element exists and is visible using registry lookup

### Existing Table Verification
- **Location**: `agent/tools/browser_verify.py` - `execute()` method
- **Functionality**: Verifies table columns (all rows contain expected value)
- **Availability**: Only for AI agent, not in Excel-generated tests

## Requirements

### 1. Text Verification
- Verify that an element's text content matches expected value
- Support partial matches (contains) and exact matches
- Use registry lookup to find element

### 2. Table Verification
- Verify that ALL rows in a filtered table column contain the expected value
- Support table selector (XPath or CSS selector)
- Parse column name and expected value from Text Value column
- Handle filtered results (after applying filters)

## Excel Format Design

### Column Usage
- **Action**: `verify` (unchanged)
- **XPath**: 
  - For text verification: Element XPath (e.g., `//button[@id="submit"]`)
  - For table verification: Table selector (e.g., `visible_table`, `table`, `#data-table`)
- **Functions**: Verification type indicator
  - `text` - Text verification
  - `table` - Table verification
  - (empty/default) - Visibility verification (current behavior)
- **Text Value**: Expected value
  - For text: Expected text content (e.g., `"Submit"`, `"Welcome User"`)
  - For table: `ColumnName=ExpectedValue` (e.g., `Diagnosis=Acute leukemia`, `Treatment Type=Chemotherapy`)

### Excel Examples

#### Example 1: Text Verification
```
Step | Action  | XPath                    | Functions | Text Value
-----|---------|--------------------------|-----------|------------
10   | verify  | //button[@id="submit"]  | text      | "Submit"
11   | verify  | //h1[@class="title"]     | text      | "Welcome"
```

#### Example 2: Table Verification (After Filter)
```
Step | Action  | XPath            | Functions | Text Value
-----|---------|------------------|-----------|------------------
20   | verify  | visible_table    | table     | Diagnosis=Acute leukemia
21   | verify  | #data-table      | table     | Treatment Type=Chemotherapy
22   | verify  | table             | table     | Organization=NCI
```

#### Example 3: Visibility Verification (Default)
```
Step | Action  | XPath                    | Functions | Text Value
-----|---------|--------------------------|-----------|------------
5    | verify  | //button[@id="login"]    |           | (empty)
```

## Implementation Plan

### Phase 1: Update `generate_verify_code_ts()` Function

**File**: `REFACTOR/generator/excel_generator_ts.py`

**Changes**:
1. Add `functions` parameter to function signature
2. Add `text_value` parameter to function signature
3. Detect verification type from `functions`:
   - `functions == "text"` → Text verification
   - `functions == "table"` → Table verification
   - `functions == "" or None` → Visibility verification (current behavior)

**New Function Signature**:
```python
def generate_verify_code_ts(
    step: str, 
    xpath: str, 
    url: str, 
    element_name: str, 
    indent: int = 12, 
    element_id: Optional[str] = None,
    functions: Optional[str] = None,  # NEW
    text_value: Optional[str] = None   # NEW
) -> str:
```

### Phase 2: Text Verification Implementation

**Logic**:
1. Use registry lookup to find element (same as current)
2. Get element text content: `await element.textContent()`
3. Compare with expected value:
   - Support partial match (contains)
   - Support exact match (optional)
4. Generate assertion:
   ```typescript
   const elementText = await element.textContent();
   const expectedText = "Submit";
   if (!elementText.includes(expectedText)) {
       throw new Error(`Text verification failed: expected "${expectedText}", got "${elementText}"`);
   }
   ```

**Generated Code Structure**:
```typescript
// Step X: Verify text
await page.waitForTimeout(3000);
try {
    // Registry lookup (same as current)
    let element;
    try {
        const xpath = getXpathById('ID_xxx', lookupUrl);
        element = page.locator(`xpath=${xpath}`).first();
        await element.waitFor({ state: 'visible', timeout: 10000 });
    } catch (registry_error) {
        throw new Error(`Registry lookup failed: ${registry_error}`);
    }
    
    // Text verification
    const elementText = await element.textContent();
    const expectedText = "Submit";
    if (!elementText || !elementText.includes(expectedText)) {
        throw new Error(`Text verification failed: expected "${expectedText}", got "${elementText || 'empty'}"`);
    }
    
    console.log(`✅ Step X: Text verification passed: "${elementText}"`);
    await page.screenshot({ path: 'storage/screenshots/pw_stepX_text.png' });
} catch (e) {
    console.log(`❌ Step X: Text verification failed: ${e}`);
    await page.screenshot({ path: 'storage/screenshots/pw_stepX_text_failed.png' });
    criticalFailures.push(`Step X: Text verification failed`);
}
```

### Phase 3: Table Verification Implementation

**Logic**:
1. Parse `text_value` as `ColumnName=ExpectedValue`
2. Find table using XPath/selector
3. Find column index by header text
4. Check ALL rows in that column contain expected value
5. Report mismatches if any

**Generated Code Structure**:
```typescript
// Step X: Verify table column
await page.waitForTimeout(3000);
try {
    // Parse Text Value: "Diagnosis=Acute leukemia"
    const [columnName, expectedValue] = "Diagnosis=Acute leukemia".split('=').map(s => s.trim());
    
    // Find table
    const tableSelector = "visible_table"; // or from XPath column
    let table;
    if (tableSelector === 'visible_table') {
        table = page.locator('table').first();
    } else {
        table = page.locator(tableSelector).first();
    }
    
    await table.waitFor({ state: 'visible', timeout: 10000 });
    
    // Find column index
    const headers = await table.locator('thead th, thead td').allTextContents();
    let columnIndex = -1;
    for (let i = 0; i < headers.length; i++) {
        if (headers[i].toLowerCase().includes(columnName.toLowerCase())) {
            columnIndex = i;
            break;
        }
    }
    
    if (columnIndex === -1) {
        throw new Error(`Column "${columnName}" not found. Available: ${headers.join(', ')}`);
    }
    
    // Verify all rows
    const rows = await table.locator('tbody tr').all();
    const totalRows = rows.length;
    let matchingRows = 0;
    const mismatches = [];
    
    for (let i = 0; i < totalRows; i++) {
        const cells = await rows[i].locator('td').all();
        if (columnIndex < cells.length) {
            const cellText = (await cells[columnIndex].textContent() || '').trim();
            if (cellText.toLowerCase().includes(expectedValue.toLowerCase())) {
                matchingRows++;
            } else {
                mismatches.push(`Row ${i+1}: "${cellText}"`);
            }
        }
    }
    
    if (matchingRows !== totalRows) {
        throw new Error(`Table verification failed: ${matchingRows}/${totalRows} rows match. Mismatches: ${mismatches.slice(0, 5).join('; ')}`);
    }
    
    console.log(`✅ Step X: Table verification passed: All ${totalRows} rows in "${columnName}" contain "${expectedValue}"`);
    await page.screenshot({ path: 'storage/screenshots/pw_stepX_table.png' });
} catch (e) {
    console.log(`❌ Step X: Table verification failed: ${e}`);
    await page.screenshot({ path: 'storage/screenshots/pw_stepX_table_failed.png' });
    criticalFailures.push(`Step X: Table verification failed`);
}
```

### Phase 4: Update Excel Reading Logic

**File**: `REFACTOR/generator/excel_generator_ts.py` - `generate_playwright_ts_from_excel()`

**Changes**:
1. When `action == 'verify'`, read `functions` column
2. Read `text_value` column
3. Pass both to `generate_verify_code_ts()`:
   ```python
   elif action == 'verify':
       functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else None
       text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else None
       
       if xpath and xpath != 'N/A':
           element_name = object_type or 'element'
           element_id = lookup_element_id_by_xpath(...)
           test_body += generate_verify_code_ts(
               step, xpath, row_url, element_name, 
               element_id=element_id,
               functions=functions,      # NEW
               text_value=text_value     # NEW
           )
   ```

### Phase 5: Error Handling & Edge Cases

**Text Verification**:
- Handle empty text
- Handle case-insensitive matching
- Handle partial vs exact match (default: partial/contains)

**Table Verification**:
- Handle table not found
- Handle column not found
- Handle empty table (no rows)
- Handle multiple tables (use first visible)
- Handle pagination (verify current page only, or all pages)

**Parsing**:
- Handle `Text Value` format: `ColumnName=ExpectedValue`
- Support multiple values: `ColumnName=Value1,Value2` (optional enhancement)
- Support special characters in column names

## Files to Modify

### Primary Files
1. **`REFACTOR/generator/excel_generator_ts.py`**
   - Update `generate_verify_code_ts()` function signature
   - Add text verification logic
   - Add table verification logic
   - Update `generate_playwright_ts_from_excel()` to pass functions/text_value

### Supporting Files (Optional)
2. **`REFACTOR/generator/excel_generator.py`** (Python generator - if still used)
   - Similar updates for Python test generation

3. **`utils/table_verification.py`** (if needed)
   - May need helper function for column index finding

## Testing Scenarios

### Test Case 1: Text Verification
```
Step 10: Verify button text is "Submit"
- Element: //button[@id="submit"]
- Functions: text
- Text Value: "Submit"
- Expected: Pass if button text contains "Submit"
```

### Test Case 2: Table Verification (Filtered)
```
Step 20: Verify all rows in Diagnosis column contain "Acute leukemia"
- XPath: visible_table
- Functions: table
- Text Value: Diagnosis=Acute leukemia
- Expected: Pass if all visible rows have "Acute leukemia" in Diagnosis column
```

### Test Case 3: Table Verification (Specific Table)
```
Step 21: Verify filtered Treatment Type column
- XPath: #data-table
- Functions: table
- Text Value: Treatment Type=Chemotherapy
- Expected: Pass if all rows in #data-table have "Chemotherapy" in Treatment Type column
```

### Test Case 4: Visibility Verification (Backward Compatible)
```
Step 5: Verify element is visible (default behavior)
- XPath: //button[@id="login"]
- Functions: (empty)
- Text Value: (empty)
- Expected: Pass if element is visible (current behavior)
```

## Backward Compatibility

- **Default Behavior**: If `Functions` is empty/not provided, use current visibility verification
- **No Breaking Changes**: Existing Excel files without `Functions` column will work as before
- **Optional Columns**: `Functions` and `Text Value` are optional for verify action

## Implementation Steps

1. ✅ **Plan Approval** (this document)
2. Update `generate_verify_code_ts()` function signature
3. Implement text verification logic
4. Implement table verification logic
5. Update Excel reading to pass functions/text_value
6. Test with sample Excel files
7. Update documentation

## Estimated Effort

- **Complexity**: Medium
- **Files Modified**: 1-2 files
- **Lines of Code**: ~200-300 lines
- **Testing**: 4-5 test scenarios

## Benefits

1. **Comprehensive Verification**: Support text, table, and visibility checks
2. **Filtered Table Support**: Verify filtered results after applying filters
3. **Backward Compatible**: Existing tests continue to work
4. **Flexible**: Easy to add more verification types in future (value, attribute, etc.)

## Future Enhancements (Not in Scope)

- Verify element value (for inputs)
- Verify element attributes
- Verify element state (enabled/disabled, checked/unchecked)
- Verify multiple columns in table
- Verify table row count
- Verify table sorting

