# Table Verification - What You Can Do

## Overview
Table verification allows you to verify that **ALL rows** in a filtered table contain a specific value in a specific column. This is useful for validating that filters are working correctly or that data matches expected criteria.

---

## Excel Format

### Required Columns:
- **Action**: `verify`
- **Functions**: `TABLE` (or `table`)
- **Text Value**: `ColumnName=ExpectedValue` (format: `ColumnName=value`)
- **XPath**: Table selector (optional - defaults to first visible table)

### Example:
```
Step | Action  | XPath                          | Functions | Text Value
-----|---------|--------------------------------|-----------|------------------
22   | verify  | //table[@data-testid="generic-table"] | TABLE | Submission Name=spandana
```

---

## What Table Verification Does

### 1. **Finds the Table**
- Uses XPath from Excel (or defaults to first visible `table` element)
- Supports:
  - XPath selectors: `//table[@data-testid="generic-table"]`
  - CSS selectors: `#data-table`, `.my-table`
  - Generic: `visible_table` (finds first visible table)

### 2. **Locates the Column**
- Reads table headers (`<th>` or `<td>` in `<thead>`)
- Finds column by **partial match** (case-insensitive)
- Example: `"Submission Name"` matches `"Submission Name"`, `"Submission Name Filter"`, etc.

### 3. **Verifies ALL Rows**
- Checks **every row** in `<tbody>`
- Verifies that the cell text in the specified column **contains** the expected value
- Case-insensitive matching
- Partial match (e.g., `"spandana"` matches `"Spandana"`, `"spandana test"`, etc.)

### 4. **Reports Results**
- ✅ **Pass**: All rows contain the expected value
- ❌ **Fail**: Any row doesn't contain the expected value
- Error message shows: `X/Y rows match` and lists mismatches (up to 5)

---

## Use Cases

### 1. **Verify Filter Results**
After applying a filter, verify all visible rows match the filter criteria:

```
Step 21: Fill filter input with "spandana"
Step 22: Verify all rows have "spandana" in "Submission Name" column
```

**Excel Entry:**
```
Step | Action | XPath                          | Functions | Text Value
-----|--------|--------------------------------|-----------|------------------
21   | fill   | //input[@id="organization-filter"] |         | spandana
22   | verify | //table[@data-testid="generic-table"] | TABLE | Submission Name=spandana
```

### 2. **Verify Data Consistency**
Check that all rows in a column have the same value:

```
Step 15: Verify all rows have "Active" status
```

**Excel Entry:**
```
Step | Action | XPath                          | Functions | Text Value
-----|--------|--------------------------------|-----------|------------------
15   | verify | visible_table                  | TABLE     | Status=Active
```

### 3. **Verify After Sorting**
After sorting a table, verify the sort order:

```
Step 10: Click "Name" column header to sort
Step 11: Verify all names start with "A"
```

**Excel Entry:**
```
Step | Action | XPath                          | Functions | Text Value
-----|--------|--------------------------------|-----------|------------------
10   | click  | //th[contains(text(), "Name")] |           |
11   | verify | visible_table                  | TABLE     | Name=A
```

### 4. **Verify Specific Table**
When page has multiple tables, verify a specific one:

```
Step 20: Verify filtered results table (not summary table)
```

**Excel Entry:**
```
Step | Action | XPath                          | Functions | Text Value
-----|--------|--------------------------------|-----------|------------------
20   | verify | #results-table                 | TABLE     | Diagnosis=Acute leukemia
```

---

## How It Works (Technical Details)

### Column Matching
- **Exact match first**: Tries exact case-insensitive match
- **Partial match fallback**: If no exact match, finds column containing the text
- Example: `"Name"` matches `"Submission Name"`, `"Patient Name"`, etc.

### Row Verification
- Iterates through all `<tbody><tr>` elements
- Gets cell text from the column index
- Checks if cell text **contains** expected value (case-insensitive)
- Example: `"spandana"` matches:
  - ✅ `"spandana"`
  - ✅ `"Spandana"`
  - ✅ `"spandana test"`
  - ✅ `"Test spandana"`
  - ❌ `"spandan"` (doesn't contain full word)

### Error Reporting
If verification fails, you'll see:
```
Table verification failed: 3/5 rows match. Mismatches: Row 2: "john"; Row 4: "jane"
```

---

## Important Notes

### ✅ What Works:
- **Partial text matching**: `"spandana"` matches `"Spandana Test"`
- **Case-insensitive**: `"SPANDANA"` = `"spandana"`
- **Multiple tables**: Specify XPath to target specific table
- **Filtered results**: Verifies only visible rows (after filters applied)
- **Empty cells**: Handled gracefully (empty string doesn't match)

### ⚠️ Limitations:
- **All rows must match**: If even one row doesn't contain the value, verification fails
- **Partial match only**: Uses `includes()` - doesn't support exact match or regex
- **Single column**: Can only verify one column at a time
- **Text only**: Doesn't verify numbers, dates, or formatted values

### 💡 Best Practices:
1. **Wait after filter**: Add wait time after applying filters (e.g., 2000ms) to allow table to update
2. **Use specific XPath**: If page has multiple tables, use specific XPath selector
3. **Clear column names**: Use exact column header text from the table
4. **Verify after action**: Place verify step immediately after filter/sort action

---

## Example: Complete Filter + Verify Flow

```
Step | Action | XPath                          | Functions | Text Value        | Wait Time
-----|--------|--------------------------------|-----------|-------------------|----------
20   | fill   | //input[@id="organization-filter"] |         | ALL              | 2000
21   | fill   | //input[@data-testid="submission-name-input"] | | Spandana        | 2000
22   | verify | //table[@data-testid="generic-table"] | TABLE | Submission Name=spandana |
```

**What happens:**
1. Step 20: Fill filter with "ALL" → wait 2 seconds
2. Step 21: Fill submission name filter with "Spandana" → wait 2 seconds (for API/debounce)
3. Step 22: Verify all visible rows have "spandana" in "Submission Name" column

---

## Generated Code Example

When you use table verification, the generated TypeScript code:

```typescript
// Step 22: Verify table (table verification)
await page.waitForTimeout(3000);  // Wait 3 seconds before step
try {
    // Table verification: Check all rows in 'Submission Name' column contain 'spandana'
    const columnName = 'Submission Name';
    const expectedValue = 'spandana';
    
    // Find table
    const table = page.locator('xpath=//table[@data-testid="generic-table"]').first();
    await table.waitFor({ state: 'visible', timeout: 10000 });
    
    // Find column index by header text
    const headers = await table.locator('thead th, thead td').allTextContents();
    let columnIndex = -1;
    for (let i = 0; i < headers.length; i++) {
        if (headers[i].toLowerCase().includes(columnName.toLowerCase())) {
            columnIndex = i;
            break;
        }
    }
    
    if (columnIndex === -1) {
        throw new Error(`Step 22: Column "Submission Name" not found. Available columns: ${headers.join(', ')}`);
    }
    
    // Verify all rows contain expected value
    const rows = await table.locator('tbody tr').all();
    const totalRows = rows.length;
    
    if (totalRows === 0) {
        throw new Error(`Step 22: Table has no rows to verify`);
    }
    
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
        const mismatchDetails = mismatches.slice(0, 5).join('; ');
        throw new Error(`Step 22: Table verification failed: ${matchingRows}/${totalRows} rows match. Mismatches: ${mismatchDetails}`);
    }
    
    console.log(`✅ Step 22: Table verification passed: All ${totalRows} rows in "Submission Name" column contain "spandana"`);
    await page.screenshot({ path: 'storage/screenshots/pw_step22_table_table.png' });
} catch (e) {
    console.log(`❌ Step 22: Table verification failed: ${e}`);
    throw e;
}
```

---

## Summary

**Table verification allows you to:**
- ✅ Verify all rows in a filtered table match criteria
- ✅ Check data consistency across rows
- ✅ Validate filter/sort functionality
- ✅ Target specific tables with XPath
- ✅ Get detailed error messages with mismatch details

**Format:** `Functions=TABLE`, `Text Value=ColumnName=ExpectedValue`

**Example:** `Submission Name=spandana` verifies all rows in "Submission Name" column contain "spandana"
