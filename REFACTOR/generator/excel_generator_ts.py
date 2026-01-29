"""
Excel-Based Playwright TypeScript Generator
Reads Excel file with Step, URL, XPath, Action, etc. and generates TypeScript Playwright code
Registry-aware: Uses element registry instead of hard-coded XPaths
Looks up XPaths in existing registry JSON - registry is NOT updated from Excel
"""
import pandas as pd
import re
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlparse
import sys

# Add utils to path for ElementRegistry import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.element_registry import ElementRegistry

# Import all reusable functions from Python generator
from REFACTOR.generator.excel_generator import (
    escape_xpath,
    escape_text,
    detect_registry_files_from_urls,
    lookup_element_id_by_xpath
)


def build_excel_reading_functions_code(excel_filename: str) -> str:
    """
    Build TypeScript code for reading credentials and expected results from Excel file.
    
    Args:
        excel_filename: Name of the Excel file (e.g., 'test_case.xlsx')
        
    Returns:
        String containing TypeScript Excel reading functions
    """
    excel_filename_escaped = excel_filename.replace("'", "\\'").replace('"', '\\"')
    
    code = f'''// ============================================================================
// EXCEL READING FUNCTIONS
// ============================================================================
// Read credentials and expected results from Excel file at runtime (no hard-coded data)

// Cache for parsed Excel workbook (parse once per test run)
let excelCache: any = null;
const EXCEL_FILENAME = '{excel_filename_escaped}';

// Get Excel file path (try multiple locations)
function getExcelPath(): string {{
    const testFileDir = __dirname;
    const possibleLocations = [
        path.join(testFileDir, EXCEL_FILENAME),  // Same directory as test file
        path.join(path.dirname(testFileDir), EXCEL_FILENAME),  // Parent directory
        path.join(testFileDir, '..', '..', EXCEL_FILENAME),  // Two levels up
        path.join(testFileDir, '..', '..', 'storage', 'excel_files', EXCEL_FILENAME),  // Excel files directory
    ];
    
    for (const loc of possibleLocations) {{
        if (fs.existsSync(loc)) {{
            return loc;
        }}
    }}
    
    throw new Error(`Excel file "${{EXCEL_FILENAME}}" not found. Checked: ${{possibleLocations.join(', ')}}`);
}}

// Load Excel workbook (cached)
function loadExcelWorkbook(): any {{
    if (!excelCache) {{
        try {{
            const XLSX = require('xlsx');
            const excelPath = getExcelPath();
            excelCache = XLSX.readFile(excelPath);
            console.log(`✅ Loaded Excel file: ${{excelPath}}`);
        }} catch (e) {{
            throw new Error(`Failed to load Excel file: ${{e.message}}`);
        }}
    }}
    return excelCache;
}}

// Read credentials from Excel "Credentials" tab
async function readCredentialsFromExcel(): Promise<{{ [key: string]: string }}> {{
    try {{
        const workbook = loadExcelWorkbook();
        const sheet = workbook.Sheets['Credentials'];
        
        if (!sheet) {{
            console.log('⚠️  Credentials tab not found in Excel, using .env fallback');
            return {{}};
        }}
        
        const XLSX = require('xlsx');
        const data = XLSX.utils.sheet_to_json(sheet);
        const credentials: {{ [key: string]: string }} = {{}};
        
        for (const row of data) {{
            const email = String(row['Email'] || row['email'] || '').trim();
            const secret = String(row['TOTP_secret'] || row['totp_secret'] || '').trim();
            if (secret) {{
                credentials[email || ''] = secret;
            }}
        }}
        
        console.log(`✅ Loaded ${{Object.keys(credentials).length}} credential(s) from Excel`);
        return credentials;
    }} catch (e) {{
        console.log(`⚠️  Failed to read credentials from Excel: ${{e.message}}, using .env fallback`);
        return {{}};
    }}
}}

// Read expected results from Excel Expected_* tab
async function readExpectedResultsFromExcel(tabName: string): Promise<Array<{{
    row_number: string;
    column_name: string;
    expected_value: string;
    match_type: string;
    action_on_error: string;
}}>> {{
    try {{
        const workbook = loadExcelWorkbook();
        const sheet = workbook.Sheets[tabName];
        
        if (!sheet) {{
            throw new Error(`Tab "${{tabName}}" not found in Excel file`);
        }}
        
        const XLSX = require('xlsx');
        const data = XLSX.utils.sheet_to_json(sheet);
        
        return data.map((row: any) => {{
            // Handle various column name formats
            const rowNum = String(row['Row Number'] || row['row_number'] || row['Row'] || row['row'] || '');
            const colName = String(row['Column Name'] || row['column_name'] || row['Column'] || row['column'] || '');
            const expValue = String(row['Expected Value'] || row['expected_value'] || row['Expected'] || row['expected'] || '');
            const matchType = String(row['Match Type'] || row['match_type'] || row['Match'] || row['match'] || 'exact').toLowerCase();
            const actionOnError = String(row['Action On Error'] || row['action_on_error'] || row['Action'] || row['action'] || 'fail').toLowerCase();
            
            return {{
                row_number: rowNum,
                column_name: colName,
                expected_value: expValue,
                match_type: matchType || 'exact',
                action_on_error: actionOnError || 'fail'
            }};
        }}).filter((r: any) => r.column_name && r.expected_value);
    }} catch (e) {{
        throw new Error(`Failed to read expected results from "${{tabName}}": ${{e.message}}`);
    }}
}}
'''
    return code


def read_expected_results_tabs(excel_file: Path) -> Dict[str, List[Dict]]:
    """
    Read Expected_* tabs from Excel file and parse expected results.
    
    Args:
        excel_file: Path to Excel file
        
    Returns:
        Dict mapping tab names to lists of expected result dictionaries
        Format: {
            "Expected_Upload_Activities": [
                {"row_number": 1, "column_name": "Status", "expected_value": "Pass", "match_type": "exact", "action_on_error": "fail"},
                ...
            ],
            ...
        }
    """
    expected_results = {}
    
    try:
        # Get all sheet names
        excel_file_obj = pd.ExcelFile(excel_file)
        
        # Find all Expected_* tabs
        expected_tabs = [name for name in excel_file_obj.sheet_names if name.startswith('Expected_')]
        
        for tab_name in expected_tabs:
            try:
                df = pd.read_excel(excel_file, sheet_name=tab_name)
                
                # Normalize column names
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                
                # Map column name variations to standard names
                column_mapping = {
                    'row': 'row_number',
                    'row_num': 'row_number',
                    'row_number': 'row_number',
                    'column': 'column_name',
                    'col': 'column_name',
                    'column_name': 'column_name',
                    'expected': 'expected_value',
                    'value': 'expected_value',
                    'expected_value': 'expected_value',
                    'match': 'match_type',
                    'type': 'match_type',
                    'match_type': 'match_type',
                    'action': 'action_on_error',
                    'error_action': 'action_on_error',
                    'action_on_error': 'action_on_error',
                    'required': 'required'
                }
                
                # Apply column mapping
                df.columns = [column_mapping.get(col, col) for col in df.columns]
                
                # Check required columns
                required_columns = ['row_number', 'column_name', 'expected_value']
                missing = [col for col in required_columns if col not in df.columns]
                
                if missing:
                    print(f"⚠️  Tab '{tab_name}' missing required columns: {missing}. Skipping.")
                    continue
                
                # Set defaults for optional columns
                if 'match_type' not in df.columns:
                    df['match_type'] = 'exact'
                if 'action_on_error' not in df.columns:
                    df['action_on_error'] = 'fail'
                
                # Parse rows into list of dictionaries
                results = []
                for idx, row in df.iterrows():
                    row_num = str(row.get('row_number', '')).strip()
                    column_name = str(row.get('column_name', '')).strip() if pd.notna(row.get('column_name')) else ''
                    expected_value = str(row.get('expected_value', '')).strip() if pd.notna(row.get('expected_value')) else ''
                    match_type = str(row.get('match_type', 'exact')).strip().lower() if pd.notna(row.get('match_type')) else 'exact'
                    action_on_error = str(row.get('action_on_error', 'fail')).strip().lower() if pd.notna(row.get('action_on_error')) else 'fail'
                    
                    if column_name and expected_value:
                        results.append({
                            'row_number': row_num,
                            'column_name': column_name,
                            'expected_value': expected_value,
                            'match_type': match_type,
                            'action_on_error': action_on_error
                        })
                
                if results:
                    expected_results[tab_name] = results
                    print(f"✅ Loaded {len(results)} expected results from '{tab_name}' tab")
                else:
                    print(f"⚠️  Tab '{tab_name}' has no valid expected results")
                    
            except Exception as e:
                print(f"⚠️  Error reading tab '{tab_name}': {e}. Skipping.")
                continue
                
    except Exception as e:
        print(f"⚠️  Error reading expected results tabs: {e}")
    
    return expected_results


def build_validation_functions_code(expected_results: Dict[str, List[Dict]]) -> str:
    """
    Build TypeScript code for Validation() and Validate_file() functions.
    
    Args:
        expected_results: Dict mapping tab names to expected results (used to determine if validation functions are needed)
        
    Returns:
        String containing TypeScript validation functions code
    """
    if not expected_results:
        return ""
    
    # Note: Expected results are now read from Excel at runtime, not embedded as const
    # We still check expected_results to determine if validation functions are needed
    code = f'''// ============================================================================
// VALIDATION FUNCTIONS
// ============================================================================
// Expected results are read from Excel at runtime (no hard-coded data)

// Helper function to find column index in table headers
function findColumnIndex(headers: string[], columnName: string): number {{
    // Try exact match first (case-insensitive)
    for (let i = 0; i < headers.length; i++) {{
        if (headers[i].toLowerCase().trim() === columnName.toLowerCase().trim()) {{
            return i;
        }}
    }}
    
    // Try partial match
    for (let i = 0; i < headers.length; i++) {{
        if (headers[i].toLowerCase().includes(columnName.toLowerCase())) {{
            return i;
        }}
    }}
    
    return -1; // Not found
}}

// Helper function to match values based on match type
function matchValue(actual: string, expected: string, matchType: string): boolean {{
    const actualTrimmed = (actual || '').trim();
    const expectedTrimmed = (expected || '').trim();
    
    if (matchType === 'empty_check') {{
        return !actualTrimmed || actualTrimmed === '' || actualTrimmed.toLowerCase().includes('0 errors');
    }} else if (matchType === 'exact') {{
        return actualTrimmed.toLowerCase() === expectedTrimmed.toLowerCase();
    }} else if (matchType === 'contains') {{
        return actualTrimmed.toLowerCase().includes(expectedTrimmed.toLowerCase());
    }}
    
    // Default to exact match
    return actualTrimmed.toLowerCase() === expectedTrimmed.toLowerCase();
}}

// Helper function to switch to a web tab
async function switchToWebTab(page: any, tabName: string): Promise<void> {{
    try {{
        // Find tab by text (case-insensitive partial match)
        // Supports both button and link elements with role="tab"
        const tabNameLower = tabName.toLowerCase();
        // Try role="tab" first (Material-UI tabs use this)
        let tabElement = page.locator(`//*[@role="tab" and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${{tabNameLower}}')]`).first();
        try {{
            await tabElement.waitFor({{ state: 'visible', timeout: 5000 }});
        }} catch {{
            // Fallback to button search if role="tab" not found
            tabElement = page.locator(`//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${{tabNameLower}}')]`).first();
            await tabElement.waitFor({{ state: 'visible', timeout: 5000 }});
        }}
        await tabElement.click();
        await page.waitForTimeout(1000); // Wait for tab content to load
        console.log(`✅ Switched to tab: ${{tabName}}`);
    }} catch (e) {{
        throw new Error(`Failed to switch to tab "${{tabName}}": ${{e}}`);
    }}
}}

// Helper function to wait for table to be stable
async function waitForTableStable(page: any): Promise<void> {{
    // Wait for table rows to be visible
    await page.waitForSelector('tbody tr', {{ state: 'visible', timeout: 10000 }});
    
    // Wait a bit more for any animations/transitions
    await page.waitForTimeout(1000);
}}

// Helper function to read table from UI
async function readTableFromUI(page: any, tableXPath?: string): Promise<{{ headers: string[], rows: string[][] }}> {{
    let table;
    
    // Use provided XPath if available, otherwise use generic pattern
    if (tableXPath) {{
        try {{
            table = page.locator(`xpath=${{tableXPath}}`).first();
            await table.waitFor({{ state: 'visible', timeout: 5000 }});
            console.log(`✅ Found table using XPath: ${{tableXPath}}`);
        }} catch (e) {{
            console.log(`⚠️  Table not found with XPath ${{tableXPath}}, trying generic selector`);
            // Fallback to generic table selector
            table = page.locator('table').first();
            await table.waitFor({{ state: 'visible', timeout: 10000 }});
        }}
    }} else {{
        // Find table using generic pattern (first visible table)
        table = page.locator('table').first();
        await table.waitFor({{ state: 'visible', timeout: 10000 }});
    }}
    
    // Read table headers (generic: thead th or thead td)
    const headerElements = await table.locator('thead th, thead td').all();
    const headers: string[] = [];
    for (const header of headerElements) {{
        const text = (await header.textContent() || '').trim();
        if (text) headers.push(text);
    }}
    
    // Read table rows (generic: tbody tr)
    const rowElements = await table.locator('tbody tr').all();
    const rows: string[][] = [];
    
    for (const rowElement of rowElements) {{
        const cellElements = await rowElement.locator('td').all();
        const row: string[] = [];
        for (const cell of cellElements) {{
            const text = (await cell.textContent() || '').trim();
            row.push(text);
        }}
        if (row.length > 0) rows.push(row);
    }}
    
    return {{ headers, rows }};
}}

// Helper function to click error link and validate error details
async function clickErrorLinkAndValidate(page: any, rowIndex: number, columnIndex: number): Promise<void> {{
    try {{
        // Find the error link in the specified cell
        const row = page.locator(`tbody tr:nth-child(${{rowIndex + 1}})`);
        const cell = row.locator(`td:nth-child(${{columnIndex + 1}})`);
        const link = cell.locator('a').first();
        
        // Click the link
        await link.click();
        
        // Wait for error details to appear (modal)
        // Use generic ARIA dialog pattern (W3C standard)
        await page.waitForSelector('[role="dialog"]', {{ timeout: 5000 }});
        
        // Extract error details
        const errorText = await page.locator('[role="dialog"]').first().textContent();
        console.log(`Error details: ${{errorText}}`);
        
        // Close dialog if it's a modal
        const closeButton = page.locator('[role="dialog"] button[aria-label*="Close"]').first();
        await closeButton.click();
        await page.waitForTimeout(500);
    }} catch (e) {{
        throw new Error(`Failed to click error link: ${{e}}`);
    }}
}}

// Helper function to write validation results to JSON file
async function writeValidationResults(executionId: string, step: string, webTabName: string, excelTabName: string, mismatches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}>, matches?: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}>): Promise<void> {{
    try {{
        const fs = require('fs');
        const path = require('path');
        
        // Get execution_id from environment or generate fallback
        const execId = process.env.EXECUTION_ID || executionId || `independent_${{Date.now()}}`;
        
        // Create validation results directory
        const resultsDir = path.join(__dirname, '../../storage/validation_results');
        if (!fs.existsSync(resultsDir)) {{
            fs.mkdirSync(resultsDir, {{ recursive: true }});
        }}
        
        const resultsFile = path.join(resultsDir, `${{execId}}.json`);
        
        // Read existing results or create new
        let allResults: any = {{}};
        if (fs.existsSync(resultsFile)) {{
            try {{
                allResults = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
            }} catch (e) {{
                allResults = {{}};
            }}
        }}
        
        // Add this validation result
        if (!allResults.validations) {{
            allResults.validations = [];
        }}
        
        allResults.validations.push({{
            step: step,
            webTabName: webTabName,
            excelTabName: excelTabName,
            timestamp: new Date().toISOString(),
            mismatches: mismatches,
            matches: matches || []
        }});
        
        // Write back to file
        fs.writeFileSync(resultsFile, JSON.stringify(allResults, null, 2), 'utf8');
        console.log(`📝 Validation results written to: ${{resultsFile}}`);
    }} catch (e) {{
        console.log(`⚠️  Failed to write validation results: ${{e}}`);
        // Don't throw - this is non-critical
    }}
}}

// Helper function to format mismatches as console table
function formatMismatchesConsole(step: string, webTabName: string, excelTabName: string, mismatches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}>): string {{
    if (mismatches.length === 0) {{
        return '';
    }}
    
    let output = `\\n❌ Validation Mismatches (Step ${{step}}, Tab: ${{webTabName}}, Expected: ${{excelTabName}})\\n`;
    output += '═'.repeat(100) + '\\n';
    output += `${{'Row'.padEnd(6)}} | ${{'Column'.padEnd(25)}} | ${{'Expected'.padEnd(20)}} | ${{'Actual'.padEnd(20)}} | Match Type\\n`;
    output += '─'.repeat(100) + '\\n';
    
    for (const mismatch of mismatches) {{
        const row = String(mismatch.row).padEnd(6);
        const col = mismatch.column.substring(0, 25).padEnd(25);
        const exp = mismatch.expected.substring(0, 20).padEnd(20);
        const act = mismatch.actual.substring(0, 20).padEnd(20);
        const matchType = mismatch.matchType;
        output += `${{row}} | ${{col}} | ${{exp}} | ${{act}} | ${{matchType}}\\n`;
    }}
    
    output += '═'.repeat(100) + '\\n';
    return output;
}}

// Validation function for UI table data
async function Validation(page: any, webTabName: string, excelTabName: string, tableXPath?: string, step?: string, executionId?: string): Promise<{{ success: boolean, mismatches?: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}>, matches?: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}> }}> {{
    console.log(`🔍 Validation: Validating "${{webTabName}}" tab against "${{excelTabName}}" expected results`);
    
    const mismatches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}> = [];
    const matches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}> = [];
    
    // Get expected results from Excel (read at runtime)
    const expectedResults = await readExpectedResultsFromExcel(excelTabName);
    if (!expectedResults || expectedResults.length === 0) {{
        throw new Error(`No expected results found for tab: ${{excelTabName}}`);
    }}
    
    // Step 1: Check if table is already visible (if XPath provided)
    let tableFound = false;
    if (tableXPath) {{
        try {{
            const tableLocator = page.locator(`xpath=${{tableXPath}}`).first();
            const isVisible = await tableLocator.isVisible({{ timeout: 2000 }});
            if (isVisible) {{
                console.log(`✅ Table already visible on current page, skipping tab switch`);
                tableFound = true;
            }}
        }} catch (e) {{
            console.log(`⚠️  Table not visible on current page, will try switching tabs`);
        }}
    }}
    
    // Step 2: Switch to web tab only if table not found
    if (!tableFound && webTabName) {{
        try {{
            await switchToWebTab(page, webTabName);
        }} catch (e) {{
            // If tab switching fails but we have XPath, try reading table anyway
            if (tableXPath) {{
                console.log(`⚠️  Tab switch failed, but will try reading table using XPath`);
            }} else {{
                throw e; // Re-throw if no XPath fallback
            }}
        }}
    }}
    
    // Step 3: Wait for table to be stable
    await waitForTableStable(page);
    
    // Step 4: Read current table from UI (use XPath if provided)
    const table = await readTableFromUI(page, tableXPath);
    
    if (table.headers.length === 0) {{
        throw new Error('Table has no headers');
    }}
    
    if (table.rows.length === 0) {{
        throw new Error('Table has no rows');
    }}
    
    // Step 4: Validate file-level checks (row count, etc.)
    const fileLevelChecks = expectedResults.filter(e => e.row_number === '*');
    for (const check of fileLevelChecks) {{
        if (check.column_name.toLowerCase() === 'row count') {{
            const expectedCount = parseInt(check.expected_value);
            if (table.rows.length !== expectedCount) {{
                // Add as mismatch instead of throwing
                mismatches.push({{
                    row: 0,
                    column: 'Row Count',
                    expected: String(expectedCount),
                    actual: String(table.rows.length),
                    matchType: 'exact'
                }});
            }} else {{
                // Add as match for success display
                matches.push({{
                    row: 0,
                    column: 'Row Count',
                    expected: String(expectedCount),
                    actual: String(table.rows.length),
                    matchType: 'exact'
                }});
            }}
        }}
    }}
    
    // Step 5: Validate row-by-row data
    const rowChecks = expectedResults.filter(e => e.row_number !== '*');
    for (const check of rowChecks) {{
        const rowIndex = parseInt(check.row_number) - 1; // Convert to 0-based
        
        if (rowIndex < 0 || rowIndex >= table.rows.length) {{
            throw new Error(`Row ${{check.row_number}} not found in table (table has ${{table.rows.length}} rows)`);
        }}
        
        const columnIndex = findColumnIndex(table.headers, check.column_name);
        if (columnIndex === -1) {{
            throw new Error(`Column "${{check.column_name}}" not found in table. Available columns: ${{table.headers.join(', ')}}`);
        }}
        
        if (columnIndex >= table.rows[rowIndex].length) {{
            throw new Error(`Column index ${{columnIndex}} out of range for row ${{check.row_number}}`);
        }}
        
        const actualValue = table.rows[rowIndex][columnIndex];
        
        if (!matchValue(actualValue, check.expected_value, check.match_type)) {{
            // Handle error action
            if (check.action_on_error === 'click_link') {{
                await clickErrorLinkAndValidate(page, rowIndex, columnIndex);
            }}
            
            // Collect mismatch instead of throwing
            mismatches.push({{
                row: parseInt(check.row_number),
                column: check.column_name,
                expected: check.expected_value,
                actual: actualValue,
                matchType: check.match_type
            }});
        }} else {{
            // Collect match for success display
            matches.push({{
                row: parseInt(check.row_number),
                column: check.column_name,
                expected: check.expected_value,
                actual: actualValue,
                matchType: check.match_type
            }});
        }}
    }}
    
    // Write results to JSON file if step and executionId provided
    if (step && executionId) {{
        await writeValidationResults(executionId, step, webTabName, excelTabName, mismatches, matches);
    }}
    
    // Format and display mismatches in console
    if (mismatches.length > 0) {{
        const consoleOutput = formatMismatchesConsole(step || '?', webTabName, excelTabName, mismatches);
        console.log(consoleOutput);
        return {{ success: false, mismatches: mismatches }};
    }}
    
    console.log(`✅ Validation passed: All checks for "${{excelTabName}}" passed`);
    return {{ success: true, matches: matches }};
}}

// Helper function to parse TSV file
function parseTSV(content: string): {{ headers: string[], rows: string[][] }} {{
    const lines = content.split('\\n').filter(line => line.trim());
    if (lines.length === 0) {{
        throw new Error('File is empty');
    }}
    
    // First line is headers
    const headers = lines[0].split('\\t').map(h => h.trim());
    
    // Remaining lines are data rows
    const rows: string[][] = [];
    for (let i = 1; i < lines.length; i++) {{
        const values = lines[i].split('\\t').map(v => v.trim());
        rows.push(values);
    }}
    
    return {{ headers, rows }};
}}

// Helper function to parse CSV file
function parseCSV(content: string): {{ headers: string[], rows: string[][] }} {{
    const lines = content.split('\\n').filter(line => line.trim());
    if (lines.length === 0) {{
        throw new Error('File is empty');
    }}
    
    // Simple CSV parsing (handles quoted values)
    function parseCSVLine(line: string): string[] {{
        const result: string[] = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {{
            const char = line[i];
            if (char === '"') {{
                inQuotes = !inQuotes;
            }} else if (char === ',' && !inQuotes) {{
                result.push(current.trim());
                current = '';
            }} else {{
                current += char;
            }}
        }}
        result.push(current.trim());
        return result;
    }}
    
    // First line is headers
    const headers = parseCSVLine(lines[0]);
    
    // Remaining lines are data rows
    const rows: string[][] = [];
    for (let i = 1; i < lines.length; i++) {{
        const values = parseCSVLine(lines[i]);
        rows.push(values);
    }}
    
    return {{ headers, rows }};
}}

// Validation function for file content
async function Validate_file(fileLocation: string, excelTabName: string, step?: string, executionId?: string): Promise<{{ success: boolean, mismatches?: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}>, matches?: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}> }}> {{
    console.log(`🔍 Validate_file: Validating file "${{fileLocation}}" against "${{excelTabName}}" expected results`);
    
    const mismatches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}> = [];
    const matches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string }}> = [];
    
    // Step 1: Resolve file path
    const projectRoot = path.resolve(__dirname, '../../');
    const filePath = path.resolve(projectRoot, fileLocation);
    
    // Step 2: Check file exists
    if (!fs.existsSync(filePath)) {{
        throw new Error(`File not found: ${{filePath}}`);
    }}
    
    // Step 3: Read and parse file
    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const extension = path.extname(filePath).toLowerCase();
    
    let fileData: {{ headers: string[], rows: string[][] }};
    if (extension === '.tsv') {{
        fileData = parseTSV(fileContent);
    }} else if (extension === '.csv') {{
        fileData = parseCSV(fileContent);
    }} else {{
        throw new Error(`Unsupported file type: ${{extension}}. Supported: .tsv, .csv`);
    }}
    
    // Step 4: Get expected results
    // Get expected results from Excel (read at runtime)
    const expectedResults = await readExpectedResultsFromExcel(excelTabName);
    if (!expectedResults || expectedResults.length === 0) {{
        throw new Error(`No expected results found for tab: ${{excelTabName}}`);
    }}
    
    // Step 5: Validate file-level checks
    const fileLevelChecks = expectedResults.filter(e => e.row_number === '*');
    for (const check of fileLevelChecks) {{
        if (check.column_name.toLowerCase() === 'row count') {{
            const expectedCount = parseInt(check.expected_value);
            if (fileData.rows.length !== expectedCount) {{
                mismatches.push({{
                    row: 0,
                    column: 'Row Count',
                    expected: String(expectedCount),
                    actual: String(fileData.rows.length),
                    matchType: 'exact'
                }});
            }} else {{
                matches.push({{
                    row: 0,
                    column: 'Row Count',
                    expected: String(expectedCount),
                    actual: String(fileData.rows.length),
                    matchType: 'exact'
                }});
            }}
        }} else if (check.column_name.toLowerCase() === 'column count') {{
            const expectedCount = parseInt(check.expected_value);
            if (fileData.headers.length !== expectedCount) {{
                mismatches.push({{
                    row: 0,
                    column: 'Column Count',
                    expected: String(expectedCount),
                    actual: String(fileData.headers.length),
                    matchType: 'exact'
                }});
            }} else {{
                matches.push({{
                    row: 0,
                    column: 'Column Count',
                    expected: String(expectedCount),
                    actual: String(fileData.headers.length),
                    matchType: 'exact'
                }});
            }}
        }}
    }}
    
    // Step 6: Validate row-by-row data
    const rowChecks = expectedResults.filter(e => e.row_number !== '*');
    for (const check of rowChecks) {{
        const rowIndex = parseInt(check.row_number) - 1; // Convert to 0-based
        
        if (rowIndex < 0 || rowIndex >= fileData.rows.length) {{
            throw new Error(`Row ${{check.row_number}} not found in file (file has ${{fileData.rows.length}} rows)`);
        }}
        
        const columnIndex = findColumnIndex(fileData.headers, check.column_name);
        if (columnIndex === -1) {{
            throw new Error(`Column "${{check.column_name}}" not found in file. Available columns: ${{fileData.headers.join(', ')}}`);
        }}
        
        if (columnIndex >= fileData.rows[rowIndex].length) {{
            throw new Error(`Column index ${{columnIndex}} out of range for row ${{check.row_number}}`);
        }}
        
        const actualValue = fileData.rows[rowIndex][columnIndex];
        
        if (!matchValue(actualValue, check.expected_value, check.match_type)) {{
            // Collect mismatch instead of throwing
            mismatches.push({{
                row: parseInt(check.row_number),
                column: check.column_name,
                expected: check.expected_value,
                actual: actualValue,
                matchType: check.match_type
            }});
        }} else {{
            // Collect match for success display
            matches.push({{
                row: parseInt(check.row_number),
                column: check.column_name,
                expected: check.expected_value,
                actual: actualValue,
                matchType: check.match_type
            }});
        }}
    }}
    
    // Write results to JSON file if step and executionId provided
    if (step && executionId) {{
        await writeValidationResults(executionId, step, fileLocation, excelTabName, mismatches, matches);
    }}
    
    // Format and display mismatches in console
    if (mismatches.length > 0) {{
        const consoleOutput = formatMismatchesConsole(step || '?', fileLocation, excelTabName, mismatches);
        console.log(consoleOutput);
        return {{ success: false, mismatches: mismatches }};
    }}
    
    console.log(`✅ Validate_file passed: All checks for "${{excelTabName}}" passed`);
    return {{ success: true, matches: matches }};
}}

// Validation function for data view - automatically validates all node types
async function Validate_data_view(page: any, folderPath: string, dropdownXPath: string, tableXPath?: string, sortByColumn?: string, step?: string, executionId?: string): Promise<{{ success: boolean, nodeResults?: Array<{{ nodeType: string, success: boolean, mismatches?: Array<{{ row: number, column: string, expected: string, actual: string }}>, error?: string }}> }}> {{
    console.log(`🔍 Validate_data_view: Validating data view for folder "${{folderPath}}"`);
    
    const nodeResults: Array<{{ nodeType: string, success: boolean, mismatches?: Array<{{ row: number, column: string, expected: string, actual: string }}>, error?: string }}> = [];
    
    // Step 1: Resolve folder path
    const projectRoot = path.resolve(__dirname, '../../');
    const resolvedFolderPath = path.resolve(projectRoot, folderPath);
    
    // Step 2: Check folder exists
    if (!fs.existsSync(resolvedFolderPath)) {{
        throw new Error(`Folder not found: ${{resolvedFolderPath}}`);
    }}
    
    if (!fs.statSync(resolvedFolderPath).isDirectory()) {{
        throw new Error(`Path is not a directory: ${{resolvedFolderPath}}`);
    }}
    
    // Step 3: Find all TSV files in folder
    const files = fs.readdirSync(resolvedFolderPath);
    const tsvFiles = files.filter(f => f.toLowerCase().endsWith('.tsv'));
    
    if (tsvFiles.length === 0) {{
        throw new Error(`No TSV files found in folder: ${{resolvedFolderPath}}`);
    }}
    
    console.log(`📁 Found ${{tsvFiles.length}} TSV file(s): ${{tsvFiles.join(', ')}}`);
    
    // Step 4: Extract node types from filenames
    // Pattern: "GC_Data_Loading_Template_consent_group_v9.0.0.tsv" -> "consent_group"
    // Pattern: "study.tsv" -> "study"
    const nodeTypes = tsvFiles.map(f => {{
        const basename = path.basename(f, '.tsv').toLowerCase();
        // Try to extract node type from pattern: GC_Data_Loading_Template_nodeType_vVersion
        const templateMatch = basename.match(/gc_data_loading_template_(.+?)_v\\d+\\.\\d+\\.\\d+/);
        if (templateMatch) {{
            return templateMatch[1]; // Return the node type part
        }}
        // If no version pattern, try to extract after "template_" or use whole name
        const simpleMatch = basename.match(/template_(.+)/);
        if (simpleMatch) {{
            return simpleMatch[1];
        }}
        // Fallback: use the whole filename without extension
        return basename;
    }});
    
    // Step 5: Switch to "Data View" tab if not already on it
    try {{
        await switchToWebTab(page, 'Data View');
        console.log(`✅ Switched to Data View tab`);
    }} catch (tabError) {{
        // Tab might already be active or tab name might be different - continue anyway
        console.log(`⚠️  Could not switch to Data View tab (may already be active): ${{tabError}}`);
    }}
    await page.waitForTimeout(1000); // Wait for tab content to load
    
    // Step 6: Click dropdown to open it (only if not already open)
    console.log(`🖱️  Clicking dropdown: ${{dropdownXPath}}`);
    const dropdown = page.locator(`xpath=${{dropdownXPath}}`).first();
    await dropdown.waitFor({{ state: 'visible', timeout: 10000 }});
    
    // Check if dropdown is already open
    const isExpanded = await dropdown.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {{
        await dropdown.click();
        await page.waitForTimeout(500); // Wait for dropdown menu to appear
    }} else {{
        console.log(`✅ Dropdown is already open`);
    }}
    
    // Step 7: For each node type, select it and validate
    for (let i = 0; i < nodeTypes.length; i++) {{
        const nodeType = nodeTypes[i];
        const tsvFile = tsvFiles[i];
        const tsvFilePath = path.join(resolvedFolderPath, tsvFile);
        
        console.log(`\\n📊 Validating node type: ${{nodeType}} (file: ${{tsvFile}})`);
        
        try {{
            // Select the node type option from dropdown
            // Material-UI Select: options are in a listbox, find by text content
            const optionXPath = `//li[contains(@role, 'option') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${{nodeType}}')]`;
            const option = page.locator(`xpath=${{optionXPath}}`).first();
            await option.waitFor({{ state: 'visible', timeout: 5000 }});
            await option.click();
            await page.waitForTimeout(1000); // Wait for selection to apply
            
            // Wait for table to update after dropdown selection
            await waitForTableStable(page);
            
            // Read table from UI
            const uiTable = await readTableFromUI(page, tableXPath);
            console.log(`✅ Read UI table: ${{uiTable.headers.length}} columns, ${{uiTable.rows.length}} rows`);
            
            // Read TSV file
            const tsvContent = fs.readFileSync(tsvFilePath, 'utf-8');
            const tsvData = parseTSV(tsvContent);
            console.log(`✅ Read TSV file: ${{tsvData.headers.length}} columns, ${{tsvData.rows.length}} rows`);
            
            // Determine sort column for this node type
            let sortColumnForNode: string | undefined = undefined;
            if (sortByColumn) {{
                try {{
                    // Try to parse as JSON object (node type mapping)
                    const sortMapping = JSON.parse(sortByColumn);
                    if (typeof sortMapping === 'object' && sortMapping !== null) {{
                        // Use nodeType-specific column if available, otherwise try lowercase/underscore variations
                        sortColumnForNode = sortMapping[nodeType] || sortMapping[nodeType.toLowerCase()] || sortMapping[nodeType.replace(/_/g, '')];
                        if (sortColumnForNode) {{
                            console.log(`📋 Using node-specific sort column for "${{nodeType}}": ${{sortColumnForNode}}`);
                        }}
                    }}
                }} catch (e) {{
                    // Not JSON, treat as single column name (use for all node types)
                    sortColumnForNode = sortByColumn;
                }}
            }}
            
            // Auto-detect sort column if not provided or not found
            if (!sortColumnForNode) {{
                // Look for column ending in _id or ID (case-insensitive)
                const idColumn = tsvData.headers.find(h => {{
                    const lower = h.toLowerCase();
                    return lower.endsWith('_id') || lower.endsWith('id') || lower === 'id';
                }});
                if (idColumn) {{
                    sortColumnForNode = idColumn;
                    console.log(`🔍 Auto-detected sort column: ${{sortColumnForNode}}`);
                }}
            }}
            
            // Sort TSV rows by sortColumnForNode if determined
            if (sortColumnForNode) {{
                const sortColIdx = tsvData.headers.findIndex(h => h.toLowerCase() === sortColumnForNode.toLowerCase());
                if (sortColIdx >= 0) {{
                    tsvData.rows.sort((a, b) => {{
                        const valA = (a[sortColIdx] || '').trim().toLowerCase();
                        const valB = (b[sortColIdx] || '').trim().toLowerCase();
                        return valA.localeCompare(valB);
                    }});
                    console.log(`✅ Sorted TSV by column: ${{sortColumnForNode}}`);
                }} else {{
                    console.log(`⚠️  Sort column "${{sortColumnForNode}}" not found in TSV headers: ${{tsvData.headers.join(', ')}}`);
                }}
            }}
            
            // Sort UI rows by sortColumnForNode if determined (after TSV is sorted)
            if (sortColumnForNode) {{
                // Find UI column that matches sortColumnForNode (case-insensitive)
                const uiSortColIdx = uiTable.headers.findIndex(h => h.toLowerCase() === sortColumnForNode.toLowerCase());
                if (uiSortColIdx >= 0) {{
                    uiTable.rows.sort((a, b) => {{
                        const valA = (a[uiSortColIdx] || '').trim().toLowerCase();
                        const valB = (b[uiSortColIdx] || '').trim().toLowerCase();
                        return valA.localeCompare(valB);
                    }});
                    console.log(`✅ Sorted UI table by column: ${{uiTable.headers[uiSortColIdx]}}`);
                }} else {{
                    console.log(`⚠️  Sort column "${{sortColumnForNode}}" not found in UI headers: ${{uiTable.headers.join(', ')}}`);
                }}
            }}
            
            // Compare data
            const mismatches: Array<{{ row: number, column: string, expected: string, actual: string }}> = [];
            
            // Compare headers (case-insensitive)
            if (uiTable.headers.length !== tsvData.headers.length) {{
                mismatches.push({{
                    row: 0,
                    column: 'Header Count',
                    expected: String(tsvData.headers.length),
                    actual: String(uiTable.headers.length),
                    matchType: 'exact'
                }});
            }}
            
            // Compare row count
            if (uiTable.rows.length !== tsvData.rows.length) {{
                mismatches.push({{
                    row: 0,
                    column: 'Row Count',
                    expected: String(tsvData.rows.length),
                    actual: String(uiTable.rows.length),
                    matchType: 'exact'
                }});
            }}
            
            // Compare data rows (only if headers and row counts match)
            if (uiTable.headers.length === tsvData.headers.length && uiTable.rows.length === tsvData.rows.length) {{
                // Map TSV headers to UI table headers (case-insensitive)
                // Special mapping: Automation_status → Status
                const headerMap: number[] = [];
                for (const tsvHeader of tsvData.headers) {{
                    // Special mapping: Automation_status → Status
                    let mappedHeader = tsvHeader;
                    if (tsvHeader.toLowerCase() === 'automation_status') {{
                        mappedHeader = 'Status';
                    }}
                    
                    const uiIndex = uiTable.headers.findIndex(h => h.toLowerCase() === mappedHeader.toLowerCase());
                    headerMap.push(uiIndex >= 0 ? uiIndex : -1);
                }}
                
                // Compare each row
                for (let rowIdx = 0; rowIdx < Math.min(uiTable.rows.length, tsvData.rows.length); rowIdx++) {{
                    const uiRow = uiTable.rows[rowIdx];
                    const tsvRow = tsvData.rows[rowIdx];
                    
                    for (let colIdx = 0; colIdx < tsvData.headers.length; colIdx++) {{
                        const uiColIdx = headerMap[colIdx];
                        if (uiColIdx >= 0 && uiColIdx < uiRow.length) {{
                            const expected = (tsvRow[colIdx] || '').trim();
                            const actual = (uiRow[uiColIdx] || '').trim();
                            
                            if (expected !== actual) {{
                                mismatches.push({{
                                    row: rowIdx + 1,
                                    column: tsvData.headers[colIdx],
                                    expected: expected,
                                    actual: actual,
                                    matchType: 'exact'
                                }});
                            }}
                        }}
                    }}
                }}
            }}
            
            // Store results
            if (mismatches.length > 0) {{
                console.log(`❌ Node type "${{nodeType}}" validation failed: ${{mismatches.length}} mismatch(es)`);
                nodeResults.push({{
                    nodeType: nodeType,
                    success: false,
                    mismatches: mismatches.map(m => ({{
                        row: m.row,
                        column: m.column,
                        expected: m.expected,
                        actual: m.actual
                    }}))
                }});
            }} else {{
                console.log(`✅ Node type "${{nodeType}}" validation passed`);
                nodeResults.push({{
                    nodeType: nodeType,
                    success: true
                }});
            }}
            
        }} catch (error: any) {{
            console.log(`❌ Error validating node type "${{nodeType}}": ${{error.message}}`);
            nodeResults.push({{
                nodeType: nodeType,
                success: false,
                error: error.message
            }});
        }}
        
        // Re-open dropdown for next iteration (if not last)
        if (i < nodeTypes.length - 1) {{
            await dropdown.click();
            await page.waitForTimeout(500);
        }}
    }}
    
    // Step 8: Determine overall success
    const allSuccess = nodeResults.every(r => r.success);
    const successCount = nodeResults.filter(r => r.success).length;
    
    // Step 9: Write comprehensive validation results report
    if (step && executionId) {{
        try {{
            const fs = require('fs');
            const path = require('path');
            
            const execId = process.env.EXECUTION_ID || executionId || `independent_${{Date.now()}}`;
            const resultsDir = path.join(__dirname, '../../storage/validation_results');
            if (!fs.existsSync(resultsDir)) {{
                fs.mkdirSync(resultsDir, {{ recursive: true }});
            }}
            
            const resultsFile = path.join(resultsDir, `${{execId}}.json`);
            
            // Read existing results or create new
            let allResults: any = {{}};
            if (fs.existsSync(resultsFile)) {{
                try {{
                    allResults = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
                }} catch (e) {{
                    allResults = {{}};
                }}
            }}
            
            if (!allResults.validations) {{
                allResults.validations = [];
            }}
            
            // Collect all mismatches from all node types
            const allMismatches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string, nodeType: string }}> = [];
            const allMatches: Array<{{ row: number, column: string, expected: string, actual: string, matchType: string, nodeType: string }}> = [];
            
            nodeResults.forEach(nodeResult => {{
                if (nodeResult.mismatches) {{
                    nodeResult.mismatches.forEach(m => {{
                        allMismatches.push({{
                            ...m,
                            matchType: 'exact',
                            nodeType: nodeResult.nodeType
                        }});
                    }});
                }}
            }});
            
            // Add comprehensive data view validation result
            allResults.validations.push({{
                step: step,
                webTabName: 'Data View',
                excelTabName: 'Validate_data_view',
                validationType: 'data_view',
                timestamp: new Date().toISOString(),
                summary: {{
                    totalNodeTypes: nodeResults.length,
                    passed: successCount,
                    failed: nodeResults.length - successCount,
                    success: allSuccess
                }},
                nodeResults: nodeResults.map(nr => ({{
                    nodeType: nr.nodeType,
                    success: nr.success,
                    mismatches: nr.mismatches || [],
                    error: nr.error || null
                }})),
                mismatches: allMismatches,
                matches: allMatches
            }});
            
            // Write back to file
            fs.writeFileSync(resultsFile, JSON.stringify(allResults, null, 2), 'utf8');
            console.log(`📝 Comprehensive validation results written to: ${{resultsFile}}`);
        }} catch (writeError: any) {{
            console.log(`⚠️  Failed to write validation results: ${{writeError.message}}`);
        }}
    }}
    
    if (allSuccess) {{
        console.log(`✅ Validate_data_view passed: All ${{nodeResults.length}} node type(s) validated successfully`);
    }} else {{
        console.log(`❌ Validate_data_view failed: ${{successCount}}/${{nodeResults.length}} node type(s) passed`);
    }}
    
    return {{
        success: allSuccess,
        nodeResults: nodeResults
    }};
}}
'''
    
    return code


def build_registry_code_ts(registry_files: List[str]) -> str:
    """
    Build TypeScript registry loading code and helper functions
    
    Args:
        registry_files: List of relative registry file paths
    
    Returns:
        String containing TypeScript registry loading code and helper functions
    """
    if not registry_files:
        return ""
    
    # Format registry paths list
    registry_paths_list_str = "[\n"
    for reg_path in registry_files:
        registry_paths_list_str += f"    '{reg_path}',\n"
    registry_paths_list_str += "]"
    
    code = f'''// ============================================================================
// MULTI-REGISTRY SUPPORT (URL-FREE APPROACH)
// ============================================================================
// Loads all registry files - no URL matching needed, lookup by element_id only
const REGISTRY_PATHS = {registry_paths_list_str};

// Load registries - NO MERGE: Keep registries separate to avoid conflicts when same element name exists in multiple registries
const REGISTRIES_BY_PATH: {{ [key: string]: any }} = {{}};  // registry_path -> registryData
let loadedCount = 0;

// Resolve registry paths: try multiple locations for flexibility
// 1. Relative to test file directory (for local zip package)
// 2. One level up from test file (for Test/ directory: Test/ -> project root)
// 3. Two levels up from test file (for server: storage/excel_tests/ -> project root)
const testFileDir = __dirname;
const possibleRoots = [
    testFileDir,  // Same directory (for zip package with element_maps/)
    path.join(__dirname, '..'),  // One level up (Test/ -> project root)
    path.join(__dirname, '../..'),  // Two levels up (storage/excel_tests/ -> project root)
];

for (const registryPathStr of REGISTRY_PATHS) {{
    try {{
        let registryPath: string | null = null;
        const checkedPaths: string[] = [];
        
        // Try each possible root location
        for (const root of possibleRoots) {{
            const candidatePath = path.join(root, registryPathStr);
            checkedPaths.push(candidatePath);
            if (fs.existsSync(candidatePath)) {{
                registryPath = candidatePath;
                break;
            }}
        }}
        
        if (registryPath) {{
            const registryData = JSON.parse(fs.readFileSync(registryPath, 'utf-8'));
            // Store per-path for dynamic loading (NO MERGE - prevents conflicts)
            REGISTRIES_BY_PATH[registryPathStr] = registryData;
            loadedCount++;
            console.log(`✅ Loaded registry: ${{Object.keys(registryData.elements || {{}}).length}} elements from ${{path.basename(registryPathStr)}}`);
        }} else {{
            console.log(`⚠️  Registry file not found: ${{registryPathStr}} (checked: ${{checkedPaths.join(', ')}})`);
        }}
    }} catch (e) {{
        console.log(`⚠️  Failed to load registry ${{registryPathStr}}: ${{e}}`);
    }}
}}

if (loadedCount > 0) {{
    const totalElements = Object.values(REGISTRIES_BY_PATH).reduce((sum: number, reg: any) => sum + Object.keys(reg.elements || {{}}).length, 0);
    const totalIds = Object.values(REGISTRIES_BY_PATH).reduce((sum: number, reg: any) => sum + Object.keys(reg.id_index || {{}}).length, 0);
    console.log(`✅ Loaded ${{loadedCount}} registries: ${{totalElements}} total elements, ${{totalIds}} total IDs (separate, not merged)`);
}}

function getXpathById(elementId: string): string {{
    /* Get XPath from registry by unique element_id - searches ALL registries (URL-free approach) */
    if (!elementId) {{
        throw new Error(`❌ element_id is required`);
    }}
    
    // Search ALL registries by element_id (no URL matching needed)
    for (const registryData of Object.values(REGISTRIES_BY_PATH)) {{
        const idIndex = registryData.id_index || {{}};
        const elements = registryData.elements || {{}};
        
        if (elementId in idIndex) {{
            const registryKey = idIndex[elementId];
            if (registryKey in elements) {{
                const xpath = elements[registryKey].xpath;
                if (xpath) {{
                    return xpath;
                }}
            }}
        }}
    }}
    
    // Not found in any registry
    throw new Error(`❌ element_id '${{elementId}}' not found in any registry id_index`);
}}

'''
    return code


def generate_navigate_code_ts(step: str, url: str, indent: int = 12, wait_time: Optional[int] = None) -> str:
    """Generate TypeScript navigation code
    
    Args:
        wait_time: Wait time in milliseconds before navigation (from Excel wait_time column, default 1000ms)
    """
    ind = ' ' * indent
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms_before = int(wait_time) if wait_time else 1000
    code = f"{ind}// Step {step}: Navigate to {url}\n"
    code += f"{ind}await page.waitForTimeout({wait_ms_before});  // Wait before step (from Excel wait_time: {wait_ms_before}ms)\n"
    code += f"{ind}try {{\n"
    code += f"{ind}    await page.goto('{url}');\n"
    code += f"{ind}    await page.waitForLoadState('networkidle');\n"
    code += f"{ind}    console.log(`📍 Step {step}: Navigated to {url}`);\n"
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_navigate.png' }});\n"
    code += f"{ind}}} catch (e) {{\n"
    code += f"{ind}    console.log(`❌ Step {step}: Navigation failed: ${{e}}`);\n"
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_navigate_failed.png' }});\n"
    code += f"{ind}}}\n"
    code += f"{ind}\n"
    return code


def generate_wait_code_ts(step: str, wait_time: int, indent: int = 12, previous_was_click: bool = False) -> str:
    """Generate TypeScript wait code
    
    Args:
        step: Step number/identifier
        wait_time: Wait time in milliseconds (from Excel - follow exactly, default 1000ms)
        indent: Indentation level
        previous_was_click: If True, previous step was a click that might cause navigation/redirect
    """
    ind = ' ' * indent
    wait_ms = int(wait_time) if wait_time else 1000
    
    # Follow Excel wait_time exactly - no hard-coded logic
    # If user wants to skip wait after TOTP, they should set wait_time to 0 in Excel
    code = f"{ind}// Step {step}: Wait {wait_ms}ms\n"
    code += f"{ind}await page.waitForTimeout({wait_ms});  // Wait before step (from Excel wait_time: {wait_ms}ms)\n"
    code += f"{ind}try {{\n"
    code += f"{ind}    await page.waitForTimeout({wait_ms});\n"
    # If previous step was a click, wait for page to fully load (handles redirects/navigation)
    if previous_was_click:
        code += f"{ind}    // Previous step was a click - wait for page to fully load after potential redirect\n"
        code += f"{ind}    await page.waitForLoadState('networkidle');\n"
        code += f"{ind}    await page.waitForLoadState('domcontentloaded');\n"
        code += f"{ind}    console.log(`✅ Step {step}: Page fully loaded after click redirect`);\n"
    code += f"{ind}    console.log(`⏱️  Step {step}: Waited {wait_ms}ms`);\n"
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_wait.png' }});\n"
    code += f"{ind}}} catch (e) {{\n"
    code += f"{ind}    console.log(`❌ Step {step}: Wait failed: ${{e}}`);\n"
    code += f"{ind}}}\n"
    return code


def generate_wait_for_code_ts(step: str, xpath: str, url: str, element_name: str, wait_type: str, is_optional: bool, indent: int = 12, element_id: Optional[str] = None, wait_time: Optional[int] = None, is_modal: bool = False, text_value: Optional[str] = None) -> str:
    """Generate TypeScript code to wait for an element to be visible/clickable/enabled
    
    Args:
        step: Step number/identifier
        xpath: Element XPath
        url: Page URL (for backward compatibility, not used for lookup)
        element_name: Element name/description
        wait_type: Type of wait: 'visible', 'clickable', or 'enabled'
        is_optional: Whether step is optional
        indent: Indentation level
        element_id: Element ID from registry (optional)
        wait_time: Timeout in milliseconds (default 10000ms)
        is_modal: Whether element is in a modal dialog
        text_value: Text value for dynamic XPath replacement
    """
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    timeout_ms = int(wait_time) if wait_time else 10000
    
    # Replace {text_value} placeholder if text_value is provided
    if text_value and '{text_value}' in xpath:
        text_value_escaped = escape_xpath(text_value)
        xpath_escaped = xpath_escaped.replace('{text_value}', text_value_escaped)
    
    # Normalize wait_type
    wait_type_lower = wait_type.lower().strip() if wait_type else 'visible'
    if wait_type_lower not in ['visible', 'clickable', 'enabled']:
        wait_type_lower = 'visible'  # Default to visible
    
    code = f"{ind}// Step {step}: Wait for {element_name or 'element'} to be {wait_type_lower}\n"
    
    if is_optional:
        code += f"{ind}// Optional step - continue if element not found\n"
        code += f"{ind}try {{\n"
    else:
        code += f"{ind}try {{\n"
    
    # Use registry lookup if element_id is available
    code += f"{ind}    let element;\n"
    if element_id:
        element_id_escaped = escape_xpath(element_id)
        code += f"{ind}    // Try registry lookup first\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        // URL-free lookup: search all registries by element_id\n"
        code += f"{ind}        let xpath = getXpathById('{element_id_escaped}');\n"
        # Replace {text_value} placeholder if text_value is provided
        if text_value:
            text_value_escaped = escape_xpath(text_value)
            code += f"{ind}        // Replace {{text_value}} placeholder with actual value from Excel\n"
            code += f"{ind}        if (xpath.includes('{{text_value}}')) {{\n"
            code += f"{ind}            xpath = xpath.replace(/\\{{text_value\\}}/g, '{text_value_escaped}');\n"
            code += f"{ind}            console.log(`✅ Step {step}: Replaced {{text_value}} with: {text_value_escaped}`);\n"
            code += f"{ind}        }}\n"
        code += f"{ind}        const selector = `xpath=${{xpath}}`;\n"
        if is_modal:
            code += f"{ind}        // Scope element lookup to modal context\n"
            code += f"{ind}        element = modalContext.locator(selector).nth(0);\n"
        else:
            code += f"{ind}        element = page.locator(selector).nth(0);\n"
        code += f"{ind}        console.log(`✅ Step {step}: Using registry element_id: {element_id_escaped}`);\n"
        code += f"{ind}    }} catch (registry_error) {{\n"
        code += f"{ind}        // Registry lookup failed - test must fail\n"
        code += f"{ind}        console.log(`❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
        code += f"{ind}    }}\n"
    else:
        # No element_id - use XPath directly
        code += f"{ind}    const selector = `xpath={xpath_escaped}`;\n"
        if is_modal:
            code += f"{ind}    // Scope element lookup to modal context\n"
            code += f"{ind}    element = modalContext.locator(selector).nth(0);\n"
        else:
            code += f"{ind}    element = page.locator(selector).nth(0);\n"
    
    # Generate wait logic based on wait_type
    if wait_type_lower == 'visible':
        code += f"{ind}    // Wait for element to be visible\n"
        code += f"{ind}    await element.waitFor({{ state: 'visible', timeout: {timeout_ms} }});\n"
        code += f"{ind}    console.log(`✅ Step {step}: Element is visible`);\n"
    
    elif wait_type_lower == 'clickable':
        code += f"{ind}    // Wait for element to be clickable (visible + enabled)\n"
        code += f"{ind}    await element.waitFor({{ state: 'visible', timeout: {timeout_ms} }});\n"
        code += f"{ind}    // Check if element is enabled (not disabled)\n"
        code += f"{ind}    let elementEnabled = false;\n"
        code += f"{ind}    const maxAttempts = Math.floor({timeout_ms} / 200);  // Poll every 200ms\n"
        code += f"{ind}    for (let attempt = 0; attempt < maxAttempts; attempt++) {{\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            const isDisabled = await element.evaluate('el => el.disabled || el.hasAttribute(\"disabled\")');\n"
        code += f"{ind}            if (!isDisabled) {{\n"
        code += f"{ind}                elementEnabled = true;\n"
        code += f"{ind}                console.log(`✅ Step {step}: Element is clickable (attempt ${{attempt + 1}})`);\n"
        code += f"{ind}                break;\n"
        code += f"{ind}            }} else {{\n"
        code += f"{ind}                if (attempt % 10 === 0) {{  // Print every 2 seconds\n"
        code += f"{ind}                    console.log(`⏳ Step {step}: Waiting for element to be enabled... (attempt ${{attempt + 1}}/${{maxAttempts}})`);\n"
        code += f"{ind}                }}\n"
        code += f"{ind}            }}\n"
        code += f"{ind}        }} catch (check_error) {{\n"
        code += f"{ind}            console.log(`⚠️  Step {step}: Error checking element state: ${{check_error}}`);\n"
        code += f"{ind}        }}\n"
        code += f"{ind}        await page.waitForTimeout(200);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    \n"
        code += f"{ind}    if (!elementEnabled) {{\n"
        code += f"{ind}        throw new Error(`Step {step}: Element did not become clickable within {timeout_ms}ms timeout`);\n"
        code += f"{ind}    }}\n"
    
    elif wait_type_lower == 'enabled':
        code += f"{ind}    // Wait for element to be enabled (not disabled)\n"
        code += f"{ind}    await element.waitFor({{ state: 'visible', timeout: {timeout_ms} }});\n"
        code += f"{ind}    let elementEnabled = false;\n"
        code += f"{ind}    const maxAttempts = Math.floor({timeout_ms} / 200);  // Poll every 200ms\n"
        code += f"{ind}    for (let attempt = 0; attempt < maxAttempts; attempt++) {{\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            const isDisabled = await element.evaluate('el => el.disabled || el.hasAttribute(\"disabled\")');\n"
        code += f"{ind}            if (!isDisabled) {{\n"
        code += f"{ind}                elementEnabled = true;\n"
        code += f"{ind}                console.log(`✅ Step {step}: Element is enabled (attempt ${{attempt + 1}})`);\n"
        code += f"{ind}                break;\n"
        code += f"{ind}            }} else {{\n"
        code += f"{ind}                if (attempt % 10 === 0) {{  // Print every 2 seconds\n"
        code += f"{ind}                    console.log(`⏳ Step {step}: Waiting for element to be enabled... (attempt ${{attempt + 1}}/${{maxAttempts}})`);\n"
        code += f"{ind}                }}\n"
        code += f"{ind}            }}\n"
        code += f"{ind}        }} catch (check_error) {{\n"
        code += f"{ind}            console.log(`⚠️  Step {step}: Error checking element state: ${{check_error}}`);\n"
        code += f"{ind}        }}\n"
        code += f"{ind}        await page.waitForTimeout(200);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    \n"
        code += f"{ind}    if (!elementEnabled) {{\n"
        code += f"{ind}        throw new Error(`Step {step}: Element did not become enabled within {timeout_ms}ms timeout`);\n"
        code += f"{ind}    }}\n"
    
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_wait_for.png' }});\n"
    code += f"{ind}}} catch (e) {{\n"
    if is_optional:
        code += f"{ind}    console.log(`⚠️  Step {step}: Wait for element failed (optional step, continuing): ${{e}}`);\n"
    else:
        code += f"{ind}    console.log(`❌ Step {step}: Wait for element failed: ${{e}}`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_wait_for_failed.png' }});\n"
        code += f"{ind}    throw new Error(`Step {step}: Element did not become {wait_type_lower} within timeout: ${{e}}`);\n"
    code += f"{ind}}}\n"
    
    return code


def generate_click_code_ts(step: str, xpath: str, url: str, element_name: str, is_optional: bool, indent: int = 12, element_id: Optional[str] = None, next_url: Optional[str] = None, wait_time: Optional[int] = None, object_type: Optional[str] = None, is_modal: bool = False, text_value: Optional[str] = None, functions: Optional[str] = None) -> str:
    """Generate TypeScript click code - registry-aware
    
    Args:
        wait_time: Wait time in milliseconds before and after click (from Excel wait_time column, default 1000ms)
        object_type: Object type from Excel (dropdown, button, etc.) - used to verify dropdown opens
        is_modal: Whether this element is inside a modal dialog (from Excel Modal column)
        text_value: Text value from Excel - used to replace {text_value} placeholder in XPath
        functions: Functions column from Excel - used to detect file upload steps (e.g., "File Upload:storage/test_files")
    """
    ind = ' ' * indent
    # Replace {text_value} placeholder with actual value if provided
    if text_value and '{text_value}' in xpath:
        xpath = xpath.replace('{text_value}', text_value)
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    # Check if this is a radio button or checkbox (use check() instead of click())
    is_radio_or_checkbox = element_name and ('radio' in element_name.lower() or 'checkbox' in element_name.lower())
    
    # Check if this is a dropdown (need to verify menu opens after click)
    is_dropdown = object_type and object_type.lower() == 'dropdown'
    
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms_before = int(wait_time) if wait_time else 1000
    
    # Detect file upload step from functions column (e.g., "File Upload:storage/test_files")
    is_file_upload = False
    file_path = None
    is_folder_upload = False
    
    # Detect Validate_data_view function call
    is_validate_data_view = False
    validate_data_view_params = None
    
    if functions:
        # Handle case where functions might be float/NaN - convert to string first
        if pd.notna(functions):
            func_str = str(functions).strip()
        else:
            func_str = ''
            functions = None
        
        if func_str:
            # Check for Validate_data_view() function call
            # Use a more flexible regex that handles quotes inside strings
            validate_data_view_match = re.match(r'Validate_data_view\s*\(\s*["\']((?:[^"\'\\]|\\.)+)["\']\s*,\s*["\']((?:[^"\'\\]|\\.)+)["\'](?:\s*,\s*["\']((?:[^"\'\\]|\\.)+)["\'])?\s*\)', func_str, re.IGNORECASE)
            if validate_data_view_match:
                is_validate_data_view = True
                folder_path = validate_data_view_match.group(1).replace('\\"', '"').replace("\\'", "'")
                dropdown_xpath = validate_data_view_match.group(2).replace('\\"', '"').replace("\\'", "'")
                table_xpath = validate_data_view_match.group(3).replace('\\"', '"').replace("\\'", "'") if validate_data_view_match.lastindex >= 3 and validate_data_view_match.group(3) else None
                validate_data_view_params = {
                    'folder_path': folder_path,
                    'dropdown_xpath': dropdown_xpath,
                    'table_xpath': table_xpath,
                    'sort_by_column': sort_by_column
                }
            
            if 'file upload' in func_str.lower():
                is_file_upload = True
            # Parse file path from functions: "File Upload:storage/test_files" or "File Upload:storage/test_files:filename" or "File Upload:storage/test_files/cds/"
            if ':' in func_str:
                parts = func_str.split(':')
                if len(parts) >= 2:
                    # Get path after "File Upload:"
                    path_part = ':'.join(parts[1:]).strip()
                    # Handle both folder and file paths
                    if path_part:
                        file_path = path_part
                        # Check if path ends with / - indicates folder upload
                        if path_part.endswith('/'):
                            is_folder_upload = True
                        # Check if filename is empty, "*", or "all" - indicates folder upload
                        elif len(parts) >= 3:
                            filename_part = parts[2].strip()
                            if not filename_part or filename_part in ['*', 'all', 'ALL']:
                                is_folder_upload = True
                        elif len(parts) == 2:
                            # Only folder path provided, no filename - check if it's a folder by checking if it ends with /
                            # (This case is already handled above, but keeping for backward compatibility)
                            pass
    
    code = f"{ind}// Step {step}: Click {element_name or 'element'}\n"
    if is_file_upload:
        code += f"{ind}// File upload step - will handle file dialog\n"
    if is_validate_data_view:
        code += f"{ind}// Data View validation step - will validate all node types automatically\n"
    code += f"{ind}await page.waitForTimeout({wait_ms_before});  // Wait before step (from Excel wait_time: {wait_ms_before}ms)\n"
    
    # File upload handling: Set up filechooser listener before clicking
    if is_file_upload and file_path:
        # Resolve file path (relative to project root)
        code += f"{ind}// Set up filechooser listener for file upload\n"
        code += f"{ind}let fileChooserResolve: ((fileChooser: FileChooser) => void) | null = null;\n"
        code += f"{ind}const fileChooserPromise = new Promise<FileChooser>((resolve) => {{\n"
        code += f"{ind}    fileChooserResolve = resolve;\n"
        code += f"{ind}}});\n"
        code += f"{ind}page.once('filechooser', (fileChooser) => {{\n"
        code += f"{ind}    if (fileChooserResolve) fileChooserResolve(fileChooser);\n"
        code += f"{ind}}});\n"
        # Resolve file path (handle both relative and absolute paths)
        code += f"{ind}// Resolve file path (relative to project root: storage/excel_tests/../../)\n"
        code += f"{ind}const projectRoot = path.resolve(__dirname, '../../');\n"
        code += f"{ind}const resolvedPath = path.resolve(projectRoot, '{file_path}');\n"
        if is_folder_upload:
            code += f"{ind}// Folder upload - get all files in folder\n"
            code += f"{ind}const fs = require('fs');\n"
            code += f"{ind}let resolvedFilePaths: string[] = [];\n"
            code += f"{ind}try {{\n"
            code += f"{ind}    const folderStats = fs.statSync(resolvedPath);\n"
            code += f"{ind}    if (folderStats.isDirectory()) {{\n"
            code += f"{ind}        const files = fs.readdirSync(resolvedPath);\n"
            code += f"{ind}        resolvedFilePaths = files\n"
            code += f"{ind}            .map((file: string) => path.resolve(resolvedPath, file))\n"
            code += f"{ind}            .filter((filePath: string) => {{\n"
            code += f"{ind}                try {{\n"
            code += f"{ind}                    return fs.statSync(filePath).isFile();\n"
            code += f"{ind}                }} catch {{\n"
            code += f"{ind}                    return false;\n"
            code += f"{ind}                }}\n"
            code += f"{ind}            }});\n"
            code += f"{ind}        console.log(`📁 Step {step}: Folder upload - found ${{resolvedFilePaths.length}} file(s) in folder: ${{resolvedPath}}`);\n"
            code += f"{ind}        if (resolvedFilePaths.length === 0) {{\n"
            code += f"{ind}            throw new Error(`No files found in folder: ${{resolvedPath}}`);\n"
            code += f"{ind}        }}\n"
            code += f"{ind}    }} else {{\n"
            code += f"{ind}        // Single file upload\n"
            code += f"{ind}        resolvedFilePaths = [resolvedPath];\n"
            code += f"{ind}        console.log(`📁 Step {step}: File upload - resolved path: ${{resolvedPath}}`);\n"
            code += f"{ind}    }}\n"
            code += f"{ind}}} catch (pathError) {{\n"
            code += f"{ind}    // Fallback to single file if folder check fails\n"
            code += f"{ind}    resolvedFilePaths = [resolvedPath];\n"
            code += f"{ind}    console.log(`📁 Step {step}: File upload - resolved path: ${{resolvedPath}}`);\n"
            code += f"{ind}}}\n"
        else:
            code += f"{ind}const resolvedFilePath = resolvedPath;\n"
            code += f"{ind}console.log(`📁 Step {step}: File upload - resolved path: ${{resolvedFilePath}}`);\n"
    
    # Modal detection: Wait for modal to be visible and scope element lookup to modal context
    if is_modal:
        code += f"{ind}// Modal step - wait for modal to be visible and scope element lookup to modal\n"
        code += f"{ind}// Check if modal context needs to be detected (reuse if already detected)\n"
        code += f"{ind}if (modalContext === page) {{\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        // Try ARIA dialog pattern first (generic W3C standard)\n"
        code += f"{ind}        const ariaModal = page.locator('[role=\"dialog\"]').first;\n"
        code += f"{ind}        await ariaModal.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}        modalContext = ariaModal;\n"
        code += f"{ind}        console.log(`✅ Step {step}: Modal detected (ARIA pattern), scoping element lookup to modal`);\n"
        code += f"{ind}    }} catch (ariaError) {{\n"
        code += f"{ind}        // ARIA modal not found - try Material-UI dialog pattern\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            const muiModal = page.locator('.MuiDialog-root.MuiModal-root').first;\n"
        code += f"{ind}            await muiModal.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}            modalContext = muiModal;\n"
        code += f"{ind}            console.log(`✅ Step {step}: Modal detected (Material-UI pattern), scoping element lookup to modal`);\n"
        code += f"{ind}        }} catch (muiError) {{\n"
        code += f"{ind}            console.log(`⚠️  Step {step}: Modal not found, using page context: ${{muiError}}`);\n"
        code += f"{ind}            // Continue with page context if modal not found\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
        code += f"{ind}}} else {{\n"
        code += f"{ind}    console.log(`✅ Step {step}: Reusing existing modal context`);\n"
        code += f"{ind}}}\n"
    
    if is_optional:
        code += f"{ind}// Optional step - continue if element not found\n"
        code += f"{ind}try {{\n"
    else:
        code += f"{ind}try {{\n"
    
    # Use registry lookup if element_id is available
    if element_id:
        element_id_escaped = escape_xpath(element_id)
        # URL-free approach: Lookup by element_id only (searches all registries)
        code += f"{ind}    let element;\n"
        code += f"{ind}    // Try registry lookup first\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        // URL-free lookup: search all registries by element_id\n"
        code += f"{ind}        let xpath = getXpathById('{element_id_escaped}');\n"
        # Replace {text_value} placeholder if text_value is provided
        if text_value:
            text_value_escaped = escape_xpath(text_value)
            code += f"{ind}        // Replace {{text_value}} placeholder with actual value from Excel\n"
            code += f"{ind}        if (xpath.includes('{{text_value}}')) {{\n"
            code += f"{ind}            xpath = xpath.replace(/\\{{text_value\\}}/g, '{text_value_escaped}');\n"
            code += f"{ind}            console.log(`✅ Step {step}: Replaced {{text_value}} with: {text_value_escaped}`);\n"
            code += f"{ind}        }}\n"
        code += f"{ind}        const selector = `xpath=${{xpath}}`;\n"
        if is_modal:
            code += f"{ind}        // Scope element lookup to modal context\n"
            code += f"{ind}        element = modalContext.locator(selector).nth(0);\n"
        else:
            code += f"{ind}        element = page.locator(selector).nth(0);\n"
        code += f"{ind}        await element.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}        console.log(`✅ Step {step}: Using registry element_id: {element_id_escaped}`);\n"
        code += f"{ind}    }} catch (registry_error) {{\n"
        code += f"{ind}        // Registry lookup failed - test must fail\n"
        code += f"{ind}        console.log(`❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
        code += f"{ind}    }}\n"
    else:
        # No element_id - test must fail (element not in registry)
        code += f"{ind}    // Element not found in registry - test must fail\n"
        code += f"{ind}    throw new Error(`Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.`);\n"
    
    # Skip normal click if Validate_data_view is detected (it handles clicking itself)
    if not is_validate_data_view:
        # For Create button, wait for it to be enabled and scroll into view
        is_create_button = 'create-data-submission-dialog-create-button' in xpath_escaped
        if is_create_button:
            code += f"{ind}    // Wait for Create button to be enabled (form validation may disable it)\n"
            code += f"{ind}    // Wait up to 10 seconds for button to become enabled\n"
            code += f"{ind}    let buttonEnabled = false;\n"
            code += f"{ind}    for (let attempt = 0; attempt < 50; attempt++) {{  // Wait up to 10 seconds (50 * 200ms)\n"
            code += f"{ind}        try {{\n"
            code += f"{ind}            const isDisabled = await element.evaluate('el => el.disabled || el.hasAttribute(\"disabled\")');\n"
            code += f"{ind}            if (!isDisabled) {{\n"
            code += f"{ind}                buttonEnabled = true;\n"
            code += f"{ind}                console.log(`✅ Step {step}: Create button is enabled (attempt ${{attempt + 1}})`);\n"
            code += f"{ind}                break;\n"
            code += f"{ind}            }} else {{\n"
            code += f"{ind}                if (attempt % 10 === 0) {{  // Print every 2 seconds\n"
            code += f"{ind}                    console.log(`⏳ Step {step}: Waiting for Create button to be enabled... (attempt ${{attempt + 1}}/50)`);\n"
            code += f"{ind}                }}\n"
            code += f"{ind}            }}\n"
            code += f"{ind}        }} catch (check_error) {{\n"
            code += f"{ind}            console.log(`⚠️  Step {step}: Error checking button state: ${{check_error}}`);\n"
            code += f"{ind}        }}\n"
            code += f"{ind}        await page.waitForTimeout(200);\n"
            code += f"{ind}    }}\n"
            code += f"{ind}    \n"
            code += f"{ind}    if (!buttonEnabled) {{\n"
            code += f"{ind}        console.log(`⚠️  Step {step}: Create button still disabled after 10 seconds, trying force click`);\n"
            code += f"{ind}        // Scroll into view if needed\n"
            code += f"{ind}        await element.scrollIntoViewIfNeeded();\n"
            code += f"{ind}        await page.waitForTimeout(500);\n"
            code += f"{ind}        // Try force click as fallback\n"
            code += f"{ind}        await element.click({{ force: true }});\n"
            code += f"{ind}        console.log(`✅ Step {step}: Clicked Create button with {{ force: true }}`);\n"
            code += f"{ind}    }} else {{\n"
            code += f"{ind}        // Scroll into view if needed\n"
            code += f"{ind}        await element.scrollIntoViewIfNeeded();\n"
            code += f"{ind}        await page.waitForTimeout(500);  // Wait after scroll\n"
            if is_radio_or_checkbox:
                # Use check() for radio buttons and checkboxes (Playwright best practice)
                code += f"{ind}            // Use check() for radio-button/checkbox (Playwright best practice)\n"
                code += f"{ind}            try {{\n"
                code += f"{ind}                await element.check();\n"
                code += f"{ind}                console.log(`✅ Step {step}: Check succeeded`);\n"
                code += f"{ind}            }} catch (check_error) {{\n"
                code += f"{ind}                console.log(`⚠️  Step {step}: check() failed, trying setChecked(true)...`);\n"
                code += f"{ind}                try {{\n"
                code += f"{ind}                    await element.setChecked(true);\n"
                code += f"{ind}                    console.log(`✅ Step {step}: setChecked(true) succeeded`);\n"
                code += f"{ind}                }} catch (setChecked_error) {{\n"
                code += f"{ind}                    console.log(`⚠️  Step {step}: setChecked() failed, trying force check...`);\n"
                code += f"{ind}                    await element.check({{ force: true }});\n"
                code += f"{ind}                    console.log(`✅ Step {step}: Force check succeeded`);\n"
                code += f"{ind}                }}\n"
                code += f"{ind}            }}\n"
            else:
                # Robust click with fallbacks (JavaScript + force)
                code += f"{ind}            // Robust click with fallbacks (JavaScript + force)\n"
                code += f"{ind}            try {{\n"
                code += f"{ind}                await element.click();\n"
                code += f"{ind}            }} catch (click_error) {{\n"
                code += f"{ind}                if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {{\n"
                code += f"{ind}                    console.log(`⚠️  Step {step}: Click timeout, trying JavaScript click...`);\n"
                code += f"{ind}                    try {{\n"
                code += f"{ind}                        await element.evaluate('el => el.click()');\n"
                code += f"{ind}                        console.log(`✅ Step {step}: JavaScript click succeeded`);\n"
                code += f"{ind}                    }} catch (js_error) {{\n"
                code += f"{ind}                        console.log(`⚠️  Step {step}: JavaScript click failed, trying force click...`);\n"
                code += f"{ind}                        await element.click({{ force: true }});\n"
                code += f"{ind}                        console.log(`✅ Step {step}: Force click succeeded`);\n"
                code += f"{ind}                    }}\n"
                code += f"{ind}                }} else {{\n"
                code += f"{ind}                    console.log(`⚠️  Step {step}: Click failed, trying force click...`);\n"
                code += f"{ind}                    await element.click({{ force: true }});\n"
                code += f"{ind}                    console.log(`✅ Step {step}: Force click succeeded`);\n"
                code += f"{ind}                }}\n"
                code += f"{ind}            }}\n"
            code += f"{ind}        }}\n"
        else:
            # Scroll into view if needed
            code += f"{ind}        // Scroll into view if needed\n"
            code += f"{ind}        try {{\n"
            code += f"{ind}            await element.scrollIntoViewIfNeeded();\n"
            code += f"{ind}        }} catch {{\n"
            code += f"{ind}            // Continue if scroll fails\n"
            code += f"{ind}        }}\n"
            code += f"{ind}        await page.waitForTimeout(500);  // Wait after scroll\n"
            if is_radio_or_checkbox:
                # Use check() for radio buttons and checkboxes (Playwright best practice)
                code += f"{ind}            // Use check() for radio-button/checkbox (Playwright best practice)\n"
                code += f"{ind}            let checkSucceeded = false;\n"
                code += f"{ind}            try {{\n"
                code += f"{ind}                await element.check();\n"
                code += f"{ind}                checkSucceeded = true;\n"
                code += f"{ind}                console.log(`✅ Step {step}: Check succeeded`);\n"
                code += f"{ind}            }} catch (check_error) {{\n"
                code += f"{ind}                console.log(`⚠️  Step {step}: check() failed, trying setChecked(true)...`);\n"
                code += f"{ind}                try {{\n"
                code += f"{ind}                    await element.setChecked(true);\n"
                code += f"{ind}                    checkSucceeded = true;\n"
                code += f"{ind}                    console.log(`✅ Step {step}: setChecked(true) succeeded`);\n"
                code += f"{ind}                }} catch (setChecked_error) {{\n"
                code += f"{ind}                    console.log(`⚠️  Step {step}: setChecked() failed, trying force check...`);\n"
                code += f"{ind}                    await element.check({{ force: true }});\n"
                code += f"{ind}                    checkSucceeded = true;\n"
                code += f"{ind}                    console.log(`✅ Step {step}: Force check succeeded`);\n"
                code += f"{ind}                }}\n"
                code += f"{ind}            }}\n"
                code += f"{ind}            if (!checkSucceeded) {{\n"
                code += f"{ind}                throw new Error(`Step {step}: All check methods failed`);\n"
                code += f"{ind}            }}\n"
            else:
                # Robust click with fallbacks (JavaScript + force)
                code += f"{ind}            // Robust click with fallbacks (JavaScript + force)\n"
                code += f"{ind}            let clickSucceeded = false;\n"
                code += f"{ind}            try {{\n"
                code += f"{ind}                await element.click();\n"
                code += f"{ind}                clickSucceeded = true;\n"
                code += f"{ind}                console.log(`✅ Step {step}: Click succeeded`);\n"
                code += f"{ind}            }} catch (click_error) {{\n"
                code += f"{ind}                if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {{\n"
                code += f"{ind}                    console.log(`⚠️  Step {step}: Click timeout, trying JavaScript click...`);\n"
                code += f"{ind}                    try {{\n"
                code += f"{ind}                        await element.evaluate('el => el.click()');\n"
                code += f"{ind}                        clickSucceeded = true;\n"
                code += f"{ind}                        console.log(`✅ Step {step}: JavaScript click succeeded`);\n"
                code += f"{ind}                    }} catch (js_error) {{\n"
                code += f"{ind}                        console.log(`⚠️  Step {step}: JavaScript click failed, trying force click...`);\n"
                code += f"{ind}                        await element.click({{ force: true }});\n"
                code += f"{ind}                        clickSucceeded = true;\n"
                code += f"{ind}                        console.log(`✅ Step {step}: Force click succeeded`);\n"
                code += f"{ind}                    }}\n"
                code += f"{ind}                }} else {{\n"
                code += f"{ind}                    console.log(`⚠️  Step {step}: Click failed, trying force click...`);\n"
                code += f"{ind}                    await element.click({{ force: true }});\n"
                code += f"{ind}                    clickSucceeded = true;\n"
                code += f"{ind}                    console.log(`✅ Step {step}: Force click succeeded`);\n"
                code += f"{ind}                }}\n"
                code += f"{ind}            }}\n"
                code += f"{ind}            if (!clickSucceeded) {{\n"
                code += f"{ind}                throw new Error(`Step {step}: All click methods failed`);\n"
                code += f"{ind}            }}\n"
    
    # Validate_data_view function call - automatically validates all node types
    # This handles clicking dropdown and validating all node types automatically
    if is_validate_data_view and validate_data_view_params:
        # Validate_data_view handles everything - no normal click needed
        folder_path = validate_data_view_params['folder_path']
        dropdown_xpath = validate_data_view_params['dropdown_xpath']
        table_xpath = validate_data_view_params.get('table_xpath')
        sort_by_column = validate_data_view_params.get('sort_by_column')
        
        folder_path_escaped = folder_path.replace("'", "\\'").replace('"', '\\"')
        dropdown_xpath_escaped = dropdown_xpath.replace("'", "\\'").replace('"', '\\"').replace('`', '\\`')
        table_xpath_escaped = table_xpath.replace("'", "\\'").replace('"', '\\"').replace('`', '\\`') if table_xpath else None
        sort_by_column_escaped = sort_by_column.replace("'", "\\'").replace('"', '\\"') if sort_by_column else None
        
        code += f"{ind}    // Call Validate_data_view function - automatically validates all node types\n"
        code += f"{ind}    const executionId = process.env.EXECUTION_ID || `independent_${{Date.now()}}`;\n"
        if table_xpath_escaped and sort_by_column_escaped:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, `{table_xpath_escaped}`, '{sort_by_column_escaped}', '{step}', executionId);\n"
        elif table_xpath_escaped:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, `{table_xpath_escaped}`, undefined, '{step}', executionId);\n"
        elif sort_by_column_escaped:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, undefined, '{sort_by_column_escaped}', '{step}', executionId);\n"
        else:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, undefined, undefined, '{step}', executionId);\n"
        code += f"{ind}    if (!dataViewResult.success) {{\n"
        code += f"{ind}        const failedNodes = dataViewResult.nodeResults?.filter(r => !r.success).map(r => r.nodeType).join(', ') || 'unknown';\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_data_view_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Step {step}: Data View validation failed for node type(s): ${{failedNodes}}`);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    console.log(`✅ Step {step}: Data View validation passed for all node types`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_data_view.png' }});\n"
    
    # File upload handling: Wait for filechooser and set files
    if is_file_upload and file_path:
        code += f"{ind}    // Handle file upload dialog\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        const fileChooser = await Promise.race([\n"
        code += f"{ind}            fileChooserPromise,\n"
        code += f"{ind}            new Promise<FileChooser>((_, reject) => setTimeout(() => reject(new Error('FileChooser timeout')), 5000))\n"
        code += f"{ind}        ]);\n"
        if is_folder_upload:
            code += f"{ind}        // Upload all files from folder\n"
            code += f"{ind}        await fileChooser.setFiles(resolvedFilePaths);\n"
            code += f"{ind}        console.log(`✅ Step {step}: Successfully uploaded ${{resolvedFilePaths.length}} file(s) from folder:`);\n"
            code += f"{ind}        resolvedFilePaths.forEach((filePath: string, index: number) => {{\n"
            code += f"{ind}            console.log(`  ${{index + 1}}. ${{filePath}}`);\n"
            code += f"{ind}        }});\n"
        else:
            code += f"{ind}        await fileChooser.setFiles(resolvedFilePath);\n"
            code += f"{ind}        console.log(`✅ Step {step}: File uploaded successfully: ${{resolvedFilePath}}`);\n"
        code += f"{ind}        await page.waitForTimeout(500);  // Brief wait after file upload\n"
        code += f"{ind}    }} catch (fileUploadError) {{\n"
        code += f"{ind}        console.log(`⚠️  Step {step}: File upload handling failed: ${{fileUploadError}}`);\n"
        code += f"{ind}        // Try alternative: find file input directly and set files\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            const fileInput = page.locator('input[type=\"file\"]').first;\n"
        if is_folder_upload:
            code += f"{ind}            await fileInput.setInputFiles(resolvedFilePaths);\n"
            code += f"{ind}            console.log(`✅ Step {step}: Successfully uploaded ${{resolvedFilePaths.length}} file(s) via direct file input:`);\n"
            code += f"{ind}            resolvedFilePaths.forEach((filePath: string, index: number) => {{\n"
            code += f"{ind}                console.log(`  ${{index + 1}}. ${{filePath}}`);\n"
            code += f"{ind}            }});\n"
        else:
            code += f"{ind}            await fileInput.setInputFiles(resolvedFilePath);\n"
            code += f"{ind}            console.log(`✅ Step {step}: File uploaded via direct file input: ${{resolvedFilePath}}`);\n"
        code += f"{ind}            await page.waitForTimeout(500);\n"
        code += f"{ind}        }} catch (directUploadError) {{\n"
        code += f"{ind}            console.log(`❌ Step {step}: Direct file input upload also failed: ${{directUploadError}}`);\n"
        code += f"{ind}            throw new Error(`Step {step}: File upload failed - both filechooser and direct input methods failed`);\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
    
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms = int(wait_time) if wait_time else 1000
    code += f"{ind}    await page.waitForTimeout({wait_ms});  // Wait after click (from Excel wait_time: {wait_ms}ms)\n"
    
    # Dropdown verification: If this is a dropdown, verify the menu (listbox) becomes visible
    if is_dropdown:
        code += f"{ind}    // Verify dropdown menu opened (generic ARIA listbox pattern)\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        // Wait for dropdown menu (listbox) to become visible\n"
        code += f"{ind}        // Use generic ARIA pattern: [role=\"listbox\"] (W3C standard)\n"
        code += f"{ind}        const dropdownMenu = page.locator('[role=\"listbox\"]').first;\n"
        code += f"{ind}        await dropdownMenu.waitFor({{ state: 'visible', timeout: 5000 }});\n"
        code += f"{ind}        console.log(`✅ Step {step}: Dropdown menu opened successfully`);\n"
        code += f"{ind}    }} catch (dropdown_error) {{\n"
        code += f"{ind}        // Dropdown menu did not open - this is a failure\n"
        code += f"{ind}        console.log(`❌ Step {step}: Dropdown menu did not open after click: ${{dropdown_error}}`);\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_dropdown_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Step {step}: Dropdown click succeeded but menu did not open. This indicates the dropdown click did not work correctly.`);\n"
        code += f"{ind}    }}\n"
    
    # State-based modal wait: Check if modal exists and wait for it to disappear (generic patterns, no hard-coding)
    # Skip modal wait if Validate_data_view is detected (it handles its own waits)
    if not is_validate_data_view:
        code += f"{ind}    // Check if modal exists and wait for it to disappear (generic patterns)\n"
    code += f"{ind}    try {{\n"
    code += f"{ind}        // Try ARIA dialog pattern first (generic W3C standard)\n"
    code += f"{ind}        const ariaModal = page.locator('[role=\"dialog\"]').first;\n"
    code += f"{ind}        let modalFound = false;\n"
    code += f"{ind}        try {{\n"
    code += f"{ind}            const isVisible = await ariaModal.isVisible({{ timeout: 100 }});\n"
    code += f"{ind}            if (isVisible) {{\n"
    code += f"{ind}                modalFound = true;\n"
    code += f"{ind}                console.log(`⏳ Step {step}: Modal detected (ARIA pattern), waiting for it to close...`);\n"
    code += f"{ind}                await ariaModal.waitFor({{ state: 'hidden', timeout: 5000 }});\n"
    code += f"{ind}                console.log(`✅ Step {step}: Modal closed (ARIA pattern)`);\n"
    code += f"{ind}            }}\n"
    code += f"{ind}        }} catch (ariaError) {{\n"
    code += f"{ind}            // ARIA modal not found or not visible - try Material-UI pattern\n"
    code += f"{ind}        }}\n"
    code += f"{ind}        \n"
    code += f"{ind}        // If ARIA pattern didn't find visible modal, try Material-UI dialog pattern (generic framework pattern)\n"
    code += f"{ind}        if (!modalFound) {{\n"
    code += f"{ind}            const muiModal = page.locator('.MuiDialog-root.MuiModal-root').first;\n"
    code += f"{ind}            try {{\n"
    code += f"{ind}                const isVisible = await muiModal.isVisible({{ timeout: 100 }});\n"
    code += f"{ind}                if (isVisible) {{\n"
    code += f"{ind}                    console.log(`⏳ Step {step}: Modal detected (Material-UI pattern), waiting for it to close...`);\n"
    code += f"{ind}                    await muiModal.waitFor({{ state: 'hidden', timeout: 5000 }});\n"
    code += f"{ind}                    console.log(`✅ Step {step}: Modal closed (Material-UI pattern)`);\n"
    code += f"{ind}                }}\n"
    code += f"{ind}            }} catch (muiError) {{\n"
    code += f"{ind}                // Material-UI modal not found or not visible - no modal to wait for\n"
    code += f"{ind}            }}\n"
    code += f"{ind}        }}\n"
    code += f"{ind}    }} catch (modal_wait_error) {{\n"
    code += f"{ind}        // Non-blocking: Continue even if modal wait times out or fails\n"
    code += f"{ind}        console.log(`⚠️  Step {step}: Modal wait timeout or no modal found (continuing anyway): ${{modal_wait_error}}`);\n"
    code += f"{ind}    }}\n"
    
    element_display = element_name or 'element'
    if is_radio_or_checkbox:
        code += f"{ind}    console.log(`✅ Step {step}: Checked {element_display}`);\n"
    else:
        code += f"{ind}    console.log(`✅ Step {step}: Clicked {element_display}`);\n"
    
    # If next step is on a different URL, wait for navigation to complete
    # This handles redirects after form submissions (e.g., TOTP submit → data-submissions page)
    if next_url and next_url != 'N/A' and url and url != 'N/A':
        # Normalize URLs for comparison (remove trailing slashes, query params, fragments)
        try:
            current_parsed = urlparse(url)
            next_parsed = urlparse(next_url)
            current_base = f"{current_parsed.scheme}://{current_parsed.netloc}{current_parsed.path.rstrip('/')}"
            next_base = f"{next_parsed.scheme}://{next_parsed.netloc}{next_parsed.path.rstrip('/')}"
            
            if current_base != next_base:
                # URLs are different - wait for navigation
                code += f"{ind}    // Next step is on different URL - wait for navigation to complete\n"
                code += f"{ind}    try {{\n"
                code += f"{ind}        await page.waitForLoadState('networkidle', {{ timeout: 15000 }});\n"
                code += f"{ind}        await page.waitForLoadState('domcontentloaded');\n"
                code += f"{ind}        console.log(`✅ Step {step}: Navigation completed to ${{page.url()}}`);\n"
                code += f"{ind}    }} catch (nav_error) {{\n"
                code += f"{ind}        console.log(`⚠️  Step {step}: Navigation wait timeout (page may have already navigated): ${{nav_error}}`);\n"
                code += f"{ind}    }}\n"
        except Exception:
            # If URL parsing fails, skip navigation wait
            pass
    
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}.png' }});\n"
    
    if is_optional:
        code += f"{ind}}} catch (e) {{\n"
        code += f"{ind}    console.log(`ℹ️  Step {step}: Element not found (optional) - continuing`);\n"
        code += f"{ind}}}\n"
    else:
        code += f"{ind}}} catch (e) {{\n"
        element_display = element_name or 'element'
        if is_radio_or_checkbox:
            code += f"{ind}    console.log(`❌ Step {step}: Failed to check {element_display}: ${{e}}`);\n"
            code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_failed.png' }});\n"
            code += f"{ind}    criticalFailures.push(`Step {step}: Check failed`);\n"
        else:
            code += f"{ind}    console.log(`❌ Step {step}: Failed to click {element_display}: ${{e}}`);\n"
            code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_failed.png' }});\n"
            code += f"{ind}    criticalFailures.push(`Step {step}: Click failed`);\n"
        code += f"{ind}}}\n"
    
    code += f"{ind}\n"
    return code


def generate_fill_code_ts(step: str, xpath: str, text_value: str, url: str, element_name: str, functions: str, is_optional: bool, indent: int = 12, element_id: Optional[str] = None, user_email: Optional[str] = None, wait_time: Optional[int] = None, is_modal: bool = False) -> str:
    """Generate TypeScript fill code - registry-aware
    
    Args:
        wait_time: Wait time in milliseconds before and after fill (from Excel wait_time column, default 1000ms)
        is_modal: Whether this element is inside a modal dialog (from Excel Modal column)
    """
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    text_escaped = escape_text(text_value)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'input'
    
    # Handle TOTP
    is_totp = 'TOTP' in str(functions).upper() if functions else False
    if is_totp:
        text_escaped = "${TOTP_CODE}"  # Will be replaced at runtime
    
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms_before = int(wait_time) if wait_time else 1000
    
    code = f"{ind}// Step {step}: Fill {element_name or 'input'}\n"
    code += f"{ind}await page.waitForTimeout({wait_ms_before});  // Wait before step (from Excel wait_time: {wait_ms_before}ms)\n"
    
    # Modal detection: Wait for modal to be visible and scope element lookup to modal context
    if is_modal:
        code += f"{ind}// Modal step - wait for modal to be visible and scope element lookup to modal\n"
        code += f"{ind}// Check if modal context needs to be detected (reuse if already detected)\n"
        code += f"{ind}if (modalContext === page) {{\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        // Try ARIA dialog pattern first (generic W3C standard)\n"
        code += f"{ind}        const ariaModal = page.locator('[role=\"dialog\"]').first;\n"
        code += f"{ind}        await ariaModal.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}        modalContext = ariaModal;\n"
        code += f"{ind}        console.log(`✅ Step {step}: Modal detected (ARIA pattern), scoping element lookup to modal`);\n"
        code += f"{ind}    }} catch (ariaError) {{\n"
        code += f"{ind}        // ARIA modal not found - try Material-UI dialog pattern\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            const muiModal = page.locator('.MuiDialog-root.MuiModal-root').first;\n"
        code += f"{ind}            await muiModal.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}            modalContext = muiModal;\n"
        code += f"{ind}            console.log(`✅ Step {step}: Modal detected (Material-UI pattern), scoping element lookup to modal`);\n"
        code += f"{ind}        }} catch (muiError) {{\n"
        code += f"{ind}            console.log(`⚠️  Step {step}: Modal not found, using page context: ${{muiError}}`);\n"
        code += f"{ind}            // Continue with page context if modal not found\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
        code += f"{ind}}} else {{\n"
        code += f"{ind}    console.log(`✅ Step {step}: Reusing existing modal context`);\n"
        code += f"{ind}}}\n"
    
    if is_totp:
        code += f"{ind}// TOTP field - code will be generated automatically\n"
    
    if is_optional:
        code += f"{ind}// Optional step - continue if element not found\n"
        code += f"{ind}try {{\n"
    else:
        code += f"{ind}try {{\n"
    
    if is_totp:
        # For TOTP, try multiple selectors first (don't wait for original selector yet)
        code += f"{ind}    // TOTP field - try multiple selectors (fallback approach)\n"
        code += f"{ind}    const totpSelectors = [\n"
        code += f"{ind}        'input.one-time-code-input__input',\n"
        code += f"{ind}        \"input[autocomplete='one-time-code']\",\n"
        code += f"{ind}        \"input[type='text'][name='code']\",\n"
        code += f"{ind}        \"input[name='code']:not([type='hidden'])\",\n"
        code += f"{ind}        'lg-one-time-code-input input[type=\\'text\\']',\n"
        code += f"{ind}        'lg-validated-field input[type=\\'text\\']',\n"
        code += f"{ind}        'lg-one-time-code-input input',\n"
        code += f"{ind}        'input.one-time-code',\n"
        code += f"{ind}        `xpath={xpath_escaped}`,  // Fallback to provided XPath\n"
        code += f"{ind}    ];\n"
        code += f"{ind}    let selectorFound = false;\n"
        code += f"{ind}    let element: any = null;\n"
        code += f"{ind}    for (const totpSel of totpSelectors) {{\n"
        code += f"{ind}        try {{\n"
        if is_modal:
            code += f"{ind}            const testElem = modalContext.locator(totpSel).first();\n"
        else:
            code += f"{ind}            const testElem = page.locator(totpSel).first();\n"
        code += f"{ind}            if (await testElem.isVisible({{ timeout: 2000 }})) {{\n"
        code += f"{ind}                element = testElem;\n"
        code += f"{ind}                selectorFound = true;\n"
        code += f"{ind}                console.log(`✅ Step {step}: Found TOTP field with selector: ${{totpSel}}`);\n"
        code += f"{ind}                break;\n"
        code += f"{ind}            }}\n"
        code += f"{ind}        }} catch {{\n"
        code += f"{ind}            continue;\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    if (!selectorFound) {{\n"
        code += f"{ind}        // Fallback to original selector\n"
        code += f"{ind}        const selector = `xpath={xpath_escaped}`;\n"
        if is_modal:
            code += f"{ind}        element = modalContext.locator(selector).nth(0);\n"
        else:
            code += f"{ind}        element = page.locator(selector).nth(0);\n"
        code += f"{ind}        await element.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}        console.log(`⚠️  Step {step}: TOTP field not found with fallback selectors, using original selector`);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    // Generate TOTP code using Python script (pyotp) - same as Python tests\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        const {{ execSync }} = require('child_process');\n"
        code += f"{ind}        const path = require('path');\n"
        code += f"{ind}        const fs = require('fs');\n"
        code += f"{ind}        \n"
        code += f"{ind}        // Find generate_totp.py script (check multiple locations)\n"
        code += f"{ind}        const testFileDir = __dirname;\n"
        code += f"{ind}        const possibleScriptLocations = [\n"
        code += f"{ind}            path.join(testFileDir, 'generate_totp.py'),  // Same directory as test file\n"
        code += f"{ind}            path.join(path.dirname(testFileDir), 'generate_totp.py'),  // Parent directory\n"
        code += f"{ind}            path.join(testFileDir, '..', '..', 'Test', 'generate_totp.py'),  // Test directory\n"
        code += f"{ind}        ];\n"
        code += f"{ind}        \n"
        code += f"{ind}        let scriptPath = null;\n"
        code += f"{ind}        for (const loc of possibleScriptLocations) {{\n"
        code += f"{ind}            if (fs.existsSync(loc)) {{\n"
        code += f"{ind}                scriptPath = loc;\n"
        code += f"{ind}                break;\n"
        code += f"{ind}            }}\n"
        code += f"{ind}        }}\n"
        code += f"{ind}        \n"
        code += f"{ind}        if (!scriptPath) {{\n"
        code += f"{ind}            throw new Error('generate_totp.py script not found. Checked: ' + possibleScriptLocations.join(', '));\n"
        code += f"{ind}        }}\n"
        code += f"{ind}        \n"
        if user_email:
            # Sanitize email for environment variable name (replace @ with _, . with _)
            email_sanitized = user_email.replace('@', '_').replace('.', '_').upper()
            code += f"{ind}        // TOTP key is unique per user - lookup key for this email/username\n"
            code += f"{ind}        const userEmail = '{user_email}';\n"
            code += f"{ind}        const emailSanitized = userEmail.replace(/[@.]/g, '_').toUpperCase();\n"
            code += f"{ind}        // Read credentials from Excel at runtime, then fallback to .env\n"
            code += f"{ind}        const credentials = await readCredentialsFromExcel();\n"
            code += f"{ind}        const secretKey = credentials[userEmail] || credentials[''] || process.env[`TOTP_SECRET_KEY_TS_${{emailSanitized}}`] || process.env.TOTP_SECRET_KEY_TS || process.env.TOTP_SECRET_KEY;\n"
            code += f"{ind}        if (!secretKey) {{\n"
            code += f"{ind}            throw new Error(`TOTP secret not found in Excel credentials['${{userEmail}}'] or credentials[''] or environment variables (TOTP_SECRET_KEY_TS_${{emailSanitized}}/TOTP_SECRET_KEY_TS/TOTP_SECRET_KEY) for user: ${{userEmail}}`);\n"
            code += f"{ind}        }}\n"
            code += f"{ind}        console.log(`🔐 Step {step}: Using TOTP key for user: ${{userEmail}}`);\n"
            code += f"{ind}        // Pass secret key to Python script\n"
            code += f"{ind}        const totpCode = execSync(`python3 ${{scriptPath}} ${{secretKey}}`, {{ encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }}).trim();\n"
        else:
            code += f"{ind}        // Read credentials from Excel at runtime, then fallback to .env\n"
            code += f"{ind}        const credentials = await readCredentialsFromExcel();\n"
            code += f"{ind}        const secretKey = credentials[''] || process.env.TOTP_SECRET_KEY_TS || process.env.TOTP_SECRET_KEY;\n"
            code += f"{ind}        if (!secretKey) {{\n"
            code += f"{ind}            throw new Error('TOTP_SECRET_KEY_TS (or TOTP_SECRET_KEY) not found in Excel credentials or environment variables');\n"
            code += f"{ind}        }}\n"
            code += f"{ind}        // Pass secret key to Python script\n"
            code += f"{ind}        const totpCode = execSync(`python3 ${{scriptPath}} ${{secretKey}}`, {{ encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }}).trim();\n"
        code += f"{ind}        console.log(`🔐 Step {step}: Generated TOTP code using pyotp (Python): ${{totpCode.substring(0, 2)}}****`);\n"
        code += f"{ind}        \n"
        code += f"{ind}        // For TOTP: clear field first, then use type() with delay (more reliable than fill())\n"
        code += f"{ind}        await element.fill('');\n"
        code += f"{ind}        await element.type(totpCode, {{ delay: 10 }});\n"
        code += f"{ind}        await page.waitForTimeout(200);\n"
        code += f"{ind}        console.log(`✅ Step {step}: Filled TOTP code using type() method`);\n"
        code += f"{ind}    }} catch (e) {{\n"
        code += f"{ind}        console.log(`❌ Step {step}: Failed to generate/fill TOTP code: ${{e}}`);\n"
        code += f"{ind}        throw e;\n"
        code += f"{ind}    }}\n"
    else:
        # Use registry lookup if element_id is available
        if element_id:
            element_id_escaped = escape_xpath(element_id)
            # URL-free approach: Lookup by element_id only (searches all registries)
            # Declare element variable outside try block so it's in scope for fill handling
            code += f"{ind}    let element;\n"
            code += f"{ind}    // Try registry lookup first\n"
            code += f"{ind}    try {{\n"
            code += f"{ind}        // URL-free lookup: search all registries by element_id\n"
            code += f"{ind}        const xpath = getXpathById('{element_id_escaped}');\n"
            code += f"{ind}        const selector = `xpath=${{xpath}}`;\n"
            if is_modal:
                code += f"{ind}        // Scope element lookup to modal context\n"
                code += f"{ind}        element = modalContext.locator(selector).nth(0);\n"
            else:
                code += f"{ind}        element = page.locator(selector).nth(0);\n"
            code += f"{ind}        await element.waitFor({{ state: 'visible', timeout: 10000 }});\n"
            code += f"{ind}        console.log(`✅ Step {step}: Using registry element_id: {element_id_escaped}`);\n"
            code += f"{ind}    }} catch (registry_error) {{\n"
            code += f"{ind}        // Registry lookup failed - test must fail\n"
            code += f"{ind}        console.log(`❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
            code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png' }});\n"
            code += f"{ind}        throw new Error(`Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
            code += f"{ind}    }}\n"
        else:
            # No element_id - test must fail (element not in registry)
            code += f"{ind}    // Element not found in registry - test must fail\n"
            code += f"{ind}    throw new Error(`Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.`);\n"
        
        # Handle TIMESTAMP variable replacement
        if '${TIMESTAMP}' in text_escaped:
            code += f"{ind}    // Replace ${{TIMESTAMP}} with actual timestamp value\n"
            code += f"{ind}    const fillValue = '{text_escaped}'.replace('${{TIMESTAMP}}', TIMESTAMP);\n"
            code += f"{ind}    await element.fill(fillValue);\n"
            element_display = element_name or 'input'
            code += f"{ind}    console.log(`✅ Step {step}: Filled {element_display} with ${{fillValue}}`);\n"
        else:
            code += f"{ind}    await element.fill('{text_escaped}');\n"
            element_display = element_name or 'input'
            code += f"{ind}    console.log(`✅ Step {step}: Filled {element_display} with {text_escaped}`);\n"
    
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms = int(wait_time) if wait_time else 1000
    # If this is a TOTP step, use same wait pattern as Python (200ms already done above, now add wait_time)
    if is_totp:
        code += f"{ind}    await page.waitForTimeout({wait_ms});  // Wait after fill (from Excel wait_time: {wait_ms}ms)\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}.png' }});\n"
    else:
        code += f"{ind}    await page.waitForTimeout({wait_ms});  // Wait after fill (from Excel wait_time: {wait_ms}ms)\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}.png' }});\n"
    
    if is_optional:
        code += f"{ind}}} catch (e) {{\n"
        code += f"{ind}    console.log(`ℹ️  Step {step}: Element not found (optional) - continuing`);\n"
        code += f"{ind}}}\n"
    else:
        code += f"{ind}}} catch (e) {{\n"
        element_display = element_name or 'input'
        code += f"{ind}    console.log(`❌ Step {step}: Failed to fill {element_display}: ${{e}}`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_failed.png' }});\n"
        code += f"{ind}    criticalFailures.push(`Step {step}: Fill failed`);\n"
        code += f"{ind}}}\n"
    
    code += f"{ind}\n"
    return code


def generate_verify_code_ts(step: str, xpath: str, url: str, element_name: str, indent: int = 12, element_id: Optional[str] = None, functions: Optional[str] = None, text_value: Optional[str] = None, wait_time: Optional[int] = None) -> str:
    """
    Generate TypeScript verify code - registry-aware
    Supports multiple verification types:
    - visibility (default): Verify element is visible
    - text: Verify element text content matches expected value
    - table: Verify all rows in table column contain expected value
    
    Args:
        wait_time: Wait time in milliseconds before verification (from Excel wait_time column, default 1000ms)
    """
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    # Determine verification type from functions column
    verification_type = 'visibility'  # Default
    is_validation_function = False
    is_validate_file_function = False
    validation_params = None
    
    if functions:
        # Handle case where functions might be float/NaN - convert to string first
        if pd.notna(functions):
            functions_str = str(functions).strip()
        else:
            functions_str = ''
            functions = None
        
        if functions_str:
            functions_upper = functions_str.upper()
            
            # Check for Validation() function call
            validation_match = re.match(r'Validation\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)', functions_str, re.IGNORECASE)
            if validation_match:
                is_validation_function = True
                web_tab_name = validation_match.group(1)
                excel_tab_name = validation_match.group(2)
                verification_type = 'validation'
                validation_params = {'web_tab_name': web_tab_name, 'excel_tab_name': excel_tab_name}
            
            # Check for Validate_file() function call
            elif re.match(r'Validate_file\s*\(', functions_str, re.IGNORECASE):
                validate_file_match = re.match(r'Validate_file\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)', functions_str, re.IGNORECASE)
                if validate_file_match:
                    file_location = validate_file_match.group(1)
                    excel_tab_name = validate_file_match.group(2)
                    verification_type = 'validate_file'
                    validation_params = {'file_location': file_location, 'excel_tab_name': excel_tab_name}
            
            # Check for Validate_data_view() function call
            elif re.match(r'Validate_data_view\s*\(', functions_str, re.IGNORECASE):
                # Use a more flexible regex that handles quotes inside strings
                # Match: Validate_data_view("path", "xpath", "optional_xpath")
                validate_data_view_match = re.match(r'Validate_data_view\s*\(\s*["\']((?:[^"\'\\]|\\.)+)["\']\s*,\s*["\']((?:[^"\'\\]|\\.)+)["\'](?:\s*,\s*["\']((?:[^"\'\\]|\\.)+)["\'])?\s*\)', functions_str, re.IGNORECASE)
                if validate_data_view_match:
                    verification_type = 'validate_data_view'
                    folder_path = validate_data_view_match.group(1).replace('\\"', '"').replace("\\'", "'")
                    dropdown_xpath = validate_data_view_match.group(2).replace('\\"', '"').replace("\\'", "'")
                    table_xpath = validate_data_view_match.group(3).replace('\\"', '"').replace("\\'", "'") if validate_data_view_match.lastindex >= 3 and validate_data_view_match.group(3) else None
                    validation_params = {'folder_path': folder_path, 'dropdown_xpath': dropdown_xpath, 'table_xpath': table_xpath}
            
            # Legacy table/text verification
            elif 'TABLE' in functions_upper:
                verification_type = 'table'
            elif 'TEXT' in functions_upper:
                verification_type = 'text'
    
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms_before = int(wait_time) if wait_time else 1000
    
    code = f"{ind}// Step {step}: Verify {element_name or 'element'}"
    if verification_type == 'text':
        code += f" (text verification)"
    elif verification_type == 'table':
        code += f" (table verification)"
    elif verification_type == 'validation':
        code += f" (UI table validation)"
    elif verification_type == 'validate_file':
        code += f" (file content validation)"
    elif verification_type == 'validate_data_view':
        code += f" (Data View - automatic node type validation)"
    code += f"\n"
    code += f"{ind}await page.waitForTimeout({wait_ms_before});  // Wait before step (from Excel wait_time: {wait_ms_before}ms)\n"
    code += f"{ind}try {{\n"
    
    # VALIDATION FUNCTION CALL
    if verification_type == 'validation' and validation_params:
        web_tab_name = validation_params['web_tab_name']
        excel_tab_name = validation_params['excel_tab_name']
        web_tab_escaped = web_tab_name.replace("'", "\\'").replace('"', '\\"')
        excel_tab_escaped = excel_tab_name.replace("'", "\\'").replace('"', '\\"')
        # Pass XPath to Validation function if available (for table element)
        xpath_escaped_for_js = xpath.replace("'", "\\'").replace('"', '\\"').replace('`', '\\`') if xpath and xpath != 'N/A' else None
        code += f"{ind}    // Call Validation function\n"
        code += f"{ind}    // Get execution_id from environment or generate fallback\n"
        code += f"{ind}    const executionId = process.env.EXECUTION_ID || `independent_${{Date.now()}}`;\n"
        if xpath_escaped_for_js:
            code += f"{ind}    const validationResult = await Validation(page, '{web_tab_escaped}', '{excel_tab_escaped}', `{xpath_escaped_for_js}`, '{step}', executionId);\n"
        else:
            code += f"{ind}    const validationResult = await Validation(page, '{web_tab_escaped}', '{excel_tab_escaped}', undefined, '{step}', executionId);\n"
        code += f"{ind}    if (!validationResult.success) {{\n"
        code += f"{ind}        const mismatchCount = validationResult.mismatches ? validationResult.mismatches.length : 0;\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_validation_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Step {step}: Validation failed for tab '{web_tab_escaped}' - ${{mismatchCount}} mismatch(es) found`);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    console.log(`✅ Step {step}: Validation passed for '{web_tab_escaped}' tab`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_validation.png' }});\n"
    
    # VALIDATE_FILE FUNCTION CALL
    elif verification_type == 'validate_file' and validation_params:
        file_location = validation_params['file_location']
        excel_tab_name = validation_params['excel_tab_name']
        file_location_escaped = file_location.replace("'", "\\'").replace('"', '\\"')
        excel_tab_escaped = excel_tab_name.replace("'", "\\'").replace('"', '\\"')
        code += f"{ind}    // Call Validate_file function\n"
        code += f"{ind}    // Get execution_id from environment or generate fallback\n"
        code += f"{ind}    const executionId = process.env.EXECUTION_ID || `independent_${{Date.now()}}`;\n"
        code += f"{ind}    const validationResult = await Validate_file('{file_location_escaped}', '{excel_tab_escaped}', '{step}', executionId);\n"
        code += f"{ind}    if (!validationResult.success) {{\n"
        code += f"{ind}        const mismatchCount = validationResult.mismatches ? validationResult.mismatches.length : 0;\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_file_validation_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Step {step}: File validation failed for '{file_location_escaped}' - ${{mismatchCount}} mismatch(es) found`);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    console.log(`✅ Step {step}: File validation passed for '{file_location_escaped}'`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_file_validation.png' }});\n"
    
    # VALIDATE_DATA_VIEW FUNCTION CALL
    elif verification_type == 'validate_data_view' and validation_params:
        folder_path = validation_params['folder_path']
        dropdown_xpath = validation_params['dropdown_xpath']
        table_xpath = validation_params.get('table_xpath')
        sort_by_column = validation_params.get('sort_by_column')
        
        folder_path_escaped = folder_path.replace("'", "\\'").replace('"', '\\"')
        dropdown_xpath_escaped = dropdown_xpath.replace("'", "\\'").replace('"', '\\"').replace('`', '\\`')
        table_xpath_escaped = table_xpath.replace("'", "\\'").replace('"', '\\"').replace('`', '\\`') if table_xpath else None
        sort_by_column_escaped = sort_by_column.replace("'", "\\'").replace('"', '\\"') if sort_by_column else None
        
        code += f"{ind}    // Call Validate_data_view function - automatically validates all node types\n"
        code += f"{ind}    const executionId = process.env.EXECUTION_ID || `independent_${{Date.now()}}`;\n"
        if table_xpath_escaped and sort_by_column_escaped:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, `{table_xpath_escaped}`, '{sort_by_column_escaped}', '{step}', executionId);\n"
        elif table_xpath_escaped:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, `{table_xpath_escaped}`, undefined, '{step}', executionId);\n"
        elif sort_by_column_escaped:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, undefined, '{sort_by_column_escaped}', '{step}', executionId);\n"
        else:
            code += f"{ind}    const dataViewResult = await Validate_data_view(page, '{folder_path_escaped}', `{dropdown_xpath_escaped}`, undefined, undefined, '{step}', executionId);\n"
        code += f"{ind}    if (!dataViewResult.success) {{\n"
        code += f"{ind}        const failedNodes = dataViewResult.nodeResults?.filter(r => !r.success).map(r => r.nodeType).join(', ') || 'unknown';\n"
        code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_data_view_failed.png' }});\n"
        code += f"{ind}        throw new Error(`Step {step}: Data View validation failed for node type(s): ${{failedNodes}}`);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    console.log(`✅ Step {step}: Data View validation passed for all node types`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_data_view.png' }});\n"
    
    # LEGACY TABLE/TEXT/VISIBILITY VERIFICATION
    elif verification_type in ['table', 'text', 'visibility']:
        # TABLE VERIFICATION
        if verification_type == 'table':
            # Parse Text Value: "ColumnName=ExpectedValue"
            if not text_value or '=' not in text_value:
                code += f"{ind}    throw new Error(`Step {step}: Table verification requires Text Value in format 'ColumnName=ExpectedValue'`);\n"
            else:
                parts = text_value.split('=', 1)
                column_name = parts[0].strip()
                expected_value = parts[1].strip()
                column_name_escaped = column_name.replace("'", "\\'").replace('"', '\\"')
                expected_value_escaped = expected_value.replace("'", "\\'").replace('"', '\\"')
                
                # Determine table selector from XPath
                table_selector = xpath.strip() if xpath and xpath != 'N/A' else 'visible_table'
                table_selector_escaped = table_selector.replace("'", "\\'").replace('"', '\\"')
                
                code += f"{ind}    // Table verification: Check all rows in '{column_name}' column contain '{expected_value}'\n"
                code += f"{ind}    const columnName = '{column_name_escaped}';\n"
                code += f"{ind}    const expectedValue = '{expected_value_escaped}';\n"
                code += f"{ind}    \n"
                code += f"{ind}    // Find table\n"
                if table_selector == 'visible_table':
                    code += f"{ind}    const table = page.locator('table').first();\n"
                else:
                    # Check if XPath or CSS selector
                    if table_selector.startswith('//') or table_selector.startswith('('):
                        code += f"{ind}    const table = page.locator(`xpath={table_selector_escaped}`).first();\n"
                    else:
                        code += f"{ind}    const table = page.locator('{table_selector_escaped}').first();\n"
                
                code += f"{ind}    await table.waitFor({{ state: 'visible', timeout: 10000 }});\n"
                code += f"{ind}    \n"
                code += f"{ind}    // Find column index by header text\n"
                code += f"{ind}    const headers = await table.locator('thead th, thead td').allTextContents();\n"
                code += f"{ind}    let columnIndex = -1;\n"
                code += f"{ind}    for (let i = 0; i < headers.length; i++) {{\n"
                code += f"{ind}        if (headers[i].toLowerCase().includes(columnName.toLowerCase())) {{\n"
                code += f"{ind}            columnIndex = i;\n"
                code += f"{ind}            break;\n"
                code += f"{ind}        }}\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
                code += f"{ind}    if (columnIndex === -1) {{\n"
                code += f"{ind}        throw new Error(`Step {step}: Column \\\"${{columnName}}\\\" not found. Available columns: ${{headers.join(', ')}}`);\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
                code += f"{ind}    // Verify all rows contain expected value\n"
                code += f"{ind}    const rows = await table.locator('tbody tr').all();\n"
                code += f"{ind}    const totalRows = rows.length;\n"
                code += f"{ind}    \n"
                code += f"{ind}    if (totalRows === 0) {{\n"
                code += f"{ind}        throw new Error(`Step {step}: Table has no rows to verify`);\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
                code += f"{ind}    let matchingRows = 0;\n"
                code += f"{ind}    const mismatches = [];\n"
                code += f"{ind}    \n"
                code += f"{ind}    for (let i = 0; i < totalRows; i++) {{\n"
                code += f"{ind}        const cells = await rows[i].locator('td').all();\n"
                code += f"{ind}        if (columnIndex < cells.length) {{\n"
                code += f"{ind}            const cellText = (await cells[columnIndex].textContent() || '').trim();\n"
                code += f"{ind}            if (cellText.toLowerCase().includes(expectedValue.toLowerCase())) {{\n"
                code += f"{ind}                matchingRows++;\n"
                code += f"{ind}            }} else {{\n"
                code += f"{ind}                mismatches.push(`Row ${{i+1}}: \\\"${{cellText}}\\\"`);\n"
                code += f"{ind}            }}\n"
                code += f"{ind}        }}\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
                code += f"{ind}    if (matchingRows !== totalRows) {{\n"
                code += f"{ind}        const mismatchDetails = mismatches.slice(0, 5).join('; ');\n"
                code += f"{ind}        throw new Error(`Step {step}: Table verification failed: ${{matchingRows}}/${{totalRows}} rows match. Mismatches: ${{mismatchDetails}}`);\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
            code += f"{ind}    console.log(`✅ Step {step}: Table verification passed: All ${{totalRows}} rows in \\\"${{columnName}}\\\" column contain \\\"${{expectedValue}}\\\"`);\n"
            code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_table.png' }});\n"
        
        # TEXT VERIFICATION
        elif verification_type == 'text':
            if not text_value:
                code += f"{ind}    throw new Error(`Step {step}: Text verification requires Text Value`);\n"
            else:
                expected_text = text_value.strip().strip('"').strip("'")
            expected_text_escaped = expected_text.replace("'", "\\'").replace('"', '\\"')
            
            # Use registry lookup if element_id is available
            if element_id:
                element_id_escaped = escape_xpath(element_id)
                code += f"{ind}    // Text verification: Check element text contains '{expected_text}'\n"
                code += f"{ind}    let element;\n"
                code += f"{ind}    // Try registry lookup first\n"
                code += f"{ind}    try {{\n"
                code += f"{ind}        // URL-free lookup: search all registries by element_id\n"
                code += f"{ind}        const xpath = getXpathById('{element_id_escaped}');\n"
                code += f"{ind}        const selector = `xpath=${{xpath}}`;\n"
                code += f"{ind}        element = page.locator(selector).nth(0);\n"
                code += f"{ind}        await element.waitFor({{ state: 'visible', timeout: 10000 }});\n"
                code += f"{ind}        console.log(`✅ Step {step}: Using registry element_id: {element_id_escaped}`);\n"
                code += f"{ind}    }} catch (registry_error) {{\n"
                code += f"{ind}        console.log(`❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
                code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png' }});\n"
                code += f"{ind}        throw new Error(`Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
                code += f"{ind}    // Verify text content\n"
                code += f"{ind}    const elementText = (await element.textContent() || '').trim();\n"
                code += f"{ind}    const expectedText = '{expected_text_escaped}';\n"
                code += f"{ind}    \n"
                code += f"{ind}    if (!elementText || !elementText.toLowerCase().includes(expectedText.toLowerCase())) {{\n"
                code += f"{ind}        throw new Error(`Step {step}: Text verification failed: expected text containing \\\"${{expectedText}}\\\", got \\\"${{elementText || 'empty'}}\\\"`);\n"
                code += f"{ind}    }}\n"
                code += f"{ind}    \n"
                code += f"{ind}    console.log(`✅ Step {step}: Text verification passed: \\\"${{elementText}}\\\" contains \\\"${{expectedText}}\\\"`);\n"
                code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_text.png' }});\n"
            else:
                code += f"{ind}    // Element not found in registry - test must fail\n"
                code += f"{ind}    throw new Error(`Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.`);\n"
        
        # VISIBILITY VERIFICATION (default)
        elif verification_type == 'visibility':
            # Use registry lookup if element_id is available
            if element_id:
                element_id_escaped = escape_xpath(element_id)
                # URL-free approach: Lookup by element_id only (searches all registries)
                # Declare element variable outside try block so it's in scope
                code += f"{ind}    let element;\n"
                code += f"{ind}    // Try registry lookup first\n"
                code += f"{ind}    try {{\n"
                code += f"{ind}        // URL-free lookup: search all registries by element_id\n"
                code += f"{ind}        const xpath = getXpathById('{element_id_escaped}');\n"
                code += f"{ind}        const selector = `xpath=${{xpath}}`;\n"
                code += f"{ind}        element = page.locator(selector).nth(0);\n"
                code += f"{ind}        await element.waitFor({{ state: 'visible', timeout: 10000 }});\n"
                code += f"{ind}        console.log(`✅ Step {step}: Using registry element_id: {element_id_escaped}`);\n"
                code += f"{ind}    }} catch (registry_error) {{\n"
                code += f"{ind}        // Registry lookup failed - test must fail\n"
                code += f"{ind}        console.log(`❌ Step {step}: Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
                code += f"{ind}        await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_registry_failed.png' }});\n"
                code += f"{ind}        throw new Error(`Registry lookup failed for element_id {element_id_escaped}: ${{registry_error}}`);\n"
                code += f"{ind}    }}\n"
            else:
                # No element_id - test must fail (element not in registry)
                code += f"{ind}    // Element not found in registry - test must fail\n"
                code += f"{ind}    throw new Error(`Step {step}: Element not found in registry. XPath: {xpath_escaped}. Please add element to registry first.`);\n"
            element_display = element_name or 'element'
            code += f"{ind}    console.log(`✅ Step {step}: Verified {element_display} is visible`);\n"
            code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}.png' }});\n"
    
    code += f"{ind}}} catch (e) {{\n"
    element_display = element_name or 'element'
    verification_type_display = verification_type if verification_type != 'visibility' else ''
    if verification_type == 'validation':
        verification_type_display = 'UI table validation'
    elif verification_type == 'validate_file':
        verification_type_display = 'file validation'
    code += f"{ind}    console.log(`❌ Step {step}: Failed to verify {element_display}{' (' + verification_type_display + ')' if verification_type_display else ''}: ${{e}}`);\n"
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_failed.png' }});\n"
    code += f"{ind}    criticalFailures.push(`Step {step}: Verify failed`);\n"
    code += f"{ind}}}\n"
    code += f"{ind}\n"
    return code


def generate_playwright_ts_from_excel(excel_file: Path, output_file: Path) -> Dict:
    """
    Generate TypeScript Playwright test from Excel file
    
    Expected Excel columns:
    - Step: Step number/identifier
    - URL: Page URL
    - XPath: Element XPath
    - Object Type: button/input/link/etc. (optional)
    - Action: click/fill/verify/wait/wait_for/navigate
    - Functions: TOTP, etc. (optional). For wait_for: visible/clickable/enabled
    - Text Value: For fill actions (optional)
    - Wait Time: For wait actions in ms (optional). For wait_for: timeout in ms (default 10000ms)
    - Optional: true/false (optional)
    
    Returns:
        Dict with success status and info
    """
    try:
        # Read Excel file (main test steps sheet)
        df = pd.read_excel(excel_file)
        
        # Note: Credentials and expected results are now read from Excel at runtime
        # No need to parse them during code generation - they'll be read by generated code
        # We still read expected_results here to check if validation functions are needed
        expected_results = read_expected_results_tabs(excel_file)
        
        # Normalize column names (case-insensitive, handle spaces)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Detect registry files (URL-free approach: loads all registries if URLs missing)
        project_root = output_file.parent.parent.parent  # Go up from storage/excel_tests to project root
        element_maps_dir = project_root / 'element_maps'
        
        # Load registry files - NO auto-population, only lookup existing XPaths
        # Registry must already contain all XPaths from Excel
        urls = df['url'].dropna().unique().tolist() if 'url' in df.columns else []
        registry_files = detect_registry_files_from_urls(urls, element_maps_dir) if element_maps_dir.exists() else []
        
        # Generate registry code
        registry_code = build_registry_code_ts(registry_files)
        
        # Generate validation functions code
        validation_functions_code = build_validation_functions_code(expected_results)
        
        # Generate code
        test_body = ""
        errors = []
        current_url = None
        previous_action = None  # Track previous action to detect if wait should wait for page load
        previous_was_totp = False  # Track if previous step was TOTP fill
        user_email = None  # Track email/username from fill steps (for TOTP key lookup)
        
        for idx, row in df.iterrows():
            step = str(row.get('step', idx + 1)).strip()
            url = str(row.get('url', '')).strip() if pd.notna(row.get('url')) else None
            xpath = str(row.get('xpath', '')).strip() if pd.notna(row.get('xpath')) else None
            action = str(row.get('action', '')).strip().lower() if pd.notna(row.get('action')) else 'click'
            object_type = str(row.get('object_type', '')).strip() if pd.notna(row.get('object_type')) else ''
            functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else ''
            text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else ''
            wait_time = row.get('wait_time', None)
            is_optional = str(row.get('optional', '')).strip().lower() in ['true', 'yes', '1', 'y']
            is_modal = str(row.get('modal', '')).strip().lower() in ['true', 'yes', '1', 'y']
            sort_by_column = str(row.get('sort_by_column', '')).strip() if pd.notna(row.get('sort_by_column')) and str(row.get('sort_by_column')).strip() else None
            
            # Update current URL
            if url and url != 'N/A':
                current_url = url
            
            # Generate code based on action
            if action == 'navigate':
                if url:
                    # Pass wait_time from Excel to use before navigation
                    wait_ms = int(wait_time) if pd.notna(wait_time) and wait_time else None
                    test_body += generate_navigate_code_ts(step, url, wait_time=wait_ms)
                else:
                    errors.append(f"Step {step}: Navigate action requires URL")
                previous_action = 'navigate'
            
            elif action == 'wait':
                # If previous action was a click, wait for page load (handles redirects)
                previous_was_click = (previous_action == 'click')
                # Follow Excel wait_time exactly - no hard-coded logic
                test_body += generate_wait_code_ts(step, wait_time or 1000, previous_was_click=previous_was_click)
                previous_action = 'wait'
            
            elif action == 'wait_for':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    
                    # Parse wait type from Functions column (visible/clickable/enabled)
                    wait_type = 'visible'  # Default
                    if functions:
                        func_str = str(functions).strip().lower()
                        if 'clickable' in func_str:
                            wait_type = 'clickable'
                        elif 'enabled' in func_str:
                            wait_type = 'enabled'
                        elif 'visible' in func_str:
                            wait_type = 'visible'
                    
                    # Lookup element_id from registry by XPath (URL-free approach)
                    element_id = lookup_element_id_by_xpath(xpath, registry_files, element_maps_dir) if registry_files else None
                    
                    # row_url still needed for generate_wait_for_code_ts signature (for backward compatibility), but not used for lookup
                    row_url = url if url and url != 'N/A' else current_url or ''
                    # Pass wait_time from Excel as timeout (default 10000ms)
                    timeout_ms = int(wait_time) if pd.notna(wait_time) and wait_time else None
                    # Pass text_value for dynamic XPath replacement (e.g., {text_value} placeholder)
                    wait_text_value = str(text_value).strip() if pd.notna(text_value) and text_value else None
                    
                    test_body += generate_wait_for_code_ts(
                        step, xpath, row_url, element_name, wait_type, is_optional,
                        element_id=element_id, wait_time=timeout_ms, is_modal=is_modal, text_value=wait_text_value
                    )
                    previous_action = 'wait_for'
                else:
                    errors.append(f"Step {step}: Wait_for action requires XPath")
            
            elif action == 'click':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    
                    # Lookup element_id from registry by XPath (URL-free approach)
                    element_id = lookup_element_id_by_xpath(xpath, registry_files, element_maps_dir) if registry_files else None
                    
                    # Check if next step is on a different URL (for navigation wait after click)
                    next_url_for_wait = None
                    if idx + 1 < len(df):
                        next_row = df.iloc[idx + 1]
                        next_step_url = str(next_row.get('url', '')).strip() if pd.notna(next_row.get('url')) else None
                        if next_step_url and next_step_url != 'N/A':
                            next_url_for_wait = next_step_url
                    
                    # row_url still needed for generate_click_code_ts signature (for navigation wait logic), but not for registry lookup
                    row_url = url if url and url != 'N/A' else current_url or ''
                    # Pass wait_time from Excel to use after click
                    wait_ms = int(wait_time) if pd.notna(wait_time) and wait_time else None
                    # Pass text_value for dynamic XPath replacement (e.g., {text_value} placeholder)
                    click_text_value = str(text_value).strip() if pd.notna(text_value) and text_value else None
                    # Pass functions for file upload detection
                    click_functions = str(functions).strip() if pd.notna(functions) and functions else None
                    test_body += generate_click_code_ts(step, xpath, row_url, element_name, is_optional, element_id=element_id, next_url=next_url_for_wait, wait_time=wait_ms, object_type=object_type, text_value=click_text_value, functions=click_functions)
                    previous_action = 'click'
                    previous_was_totp = False  # Reset after click
                else:
                    errors.append(f"Step {step}: Click action requires XPath")
            
            elif action == 'fill':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'input'
                    # Check if this is a TOTP fill
                    is_totp = 'TOTP' in str(functions).upper() if functions else False
                    
                    # Track email/username from fill steps (for TOTP key lookup)
                    # Detect if this is an email/username field (contains @ or is likely a username field)
                    if text_value and '@' in text_value:
                        user_email = text_value  # Store email for TOTP key lookup
                    elif text_value and ('email' in element_name.lower() or 'user' in element_name.lower() or 'username' in element_name.lower()):
                        user_email = text_value  # Store username for TOTP key lookup
                    
                    # Lookup element_id from registry by XPath (URL-free approach)
                    element_id = lookup_element_id_by_xpath(xpath, registry_files, element_maps_dir) if registry_files else None
                    # Pass wait_time from Excel to use after fill
                    wait_ms = int(wait_time) if pd.notna(wait_time) and wait_time else None
                    test_body += generate_fill_code_ts(step, xpath, text_value, row_url, element_name, functions, is_optional, element_id=element_id, user_email=user_email, wait_time=wait_ms, is_modal=is_modal)
                    previous_action = 'fill'
                    previous_was_totp = is_totp  # Track if this was TOTP
                else:
                    errors.append(f"Step {step}: Fill action requires XPath")
            
            elif action == 'verify':
                # For table verification, XPath can be table selector (e.g., 'visible_table', '#data-table')
                # For text/visibility verification, XPath is required
                functions = str(row.get('functions', '')).strip() if pd.notna(row.get('functions')) else None
                text_value = str(row.get('text_value', '')).strip() if pd.notna(row.get('text_value')) else None
                is_table_verification = functions and 'TABLE' in str(functions).upper()
                
                if not is_table_verification and (not xpath or xpath == 'N/A'):
                    errors.append(f"Step {step}: Verify action requires XPath (unless Functions=table)")
                else:
                    element_name = object_type or 'element'
                    # Lookup element_id from registry by XPath (URL-free approach)
                    # For table verification, don't require element_id (table selector is in XPath)
                    element_id = None
                    if not is_table_verification:
                        element_id = lookup_element_id_by_xpath(xpath, registry_files, element_maps_dir) if registry_files else None
                    # row_url still needed for generate_verify_code_ts signature (for backward compatibility), but not used for lookup
                    row_url = url if url and url != 'N/A' else current_url or ''
                    # Pass wait_time from Excel to use before verification
                    wait_ms = int(wait_time) if pd.notna(wait_time) and wait_time else None
                    test_body += generate_verify_code_ts(
                        step, xpath, row_url, element_name, 
                        element_id=element_id,
                        functions=functions,
                        text_value=text_value,
                        wait_time=wait_ms
                    )
                    previous_action = 'verify'
            
            else:
                errors.append(f"Step {step}: Unknown action '{action}'")
        
        # Build full test script
        # Note: Credentials are now read from Excel at runtime, not embedded in code
        test_name = "test_excel_generated"
        excel_filename = excel_file.name
        
        # Generate Excel reading helper functions
        excel_reading_code = build_excel_reading_functions_code(excel_filename)
        
        test_script = f'''/*Excel-Generated Playwright Test
Generated from: {excel_file.name}*/

// Load environment variables from .env file (for TOTP_SECRET_KEY, etc.)
// Check multiple locations: same dir, parent, home, or 3 levels up
import {{ test, expect, type FileChooser }} from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import {{ URL }} from 'url';

let envFile: string | null = null;
try {{
  const dotenv = require('dotenv');
  const testFileDir = __dirname;
  const projectRoot = path.join(__dirname, '../..');
  const possibleEnvLocations = [
    path.join(testFileDir, '.env'),  // Same directory as test file
    path.join(path.dirname(testFileDir), '.env'),  // Parent directory
    path.join(projectRoot, '.env'),  // Project root (DATAHUB_AI_Agent/.env)
    path.join(require('os').homedir(), '.env'),  // Home directory
  ];
  
  for (const loc of possibleEnvLocations) {{
    if (fs.existsSync(loc)) {{
      envFile = loc;
      dotenv.config({{ path: loc }});
      console.log(`✅ Loaded environment variables from ${{envFile}}`);
      break;
    }}
  }}
  
  if (!envFile) {{
    console.log(`⚠️  .env file not found. Checked locations:`);
    for (const loc of possibleEnvLocations) {{
      console.log(`   - ${{loc}}`);
    }}
    console.log(`   Please create a .env file with TOTP_SECRET_KEY_TS=your_secret_key (TypeScript tests use TOTP_SECRET_KEY_TS, different from Python's TOTP_SECRET_KEY)`);
  }}
}} catch (e) {{
  if (e.code === 'MODULE_NOT_FOUND') {{
    console.log("⚠️  dotenv not installed - environment variables must be set manually");
  }} else {{
    console.log(`⚠️  Failed to load .env file: ${{e}}`);
  }}
}}

{excel_reading_code}

{registry_code}

{validation_functions_code}

test('{test_name}', async ({{ page }}) => {{
    /* Auto-generated test from Excel file */
    // Set test timeout to 5 minutes (300000ms) to allow for multiple steps with waits
    test.setTimeout(300000);
    
    const criticalFailures: string[] = [];
    
    // Set viewport to match AI agent (tabs visible, not hidden in "More" dropdown)
    await page.setViewportSize({{ width: 1920, height: 1080 }});
    
    // Generate timestamp if needed
    const TIMESTAMP = new Date().toISOString().replace(/[-:]/g, '').split('.')[0].replace('T', '_');
    
    // Modal context - shared across all modal steps
    let modalContext = page;  // Default to page context, will be updated when modal is detected
    
    try {{
{test_body}
        if (criticalFailures.length > 0) {{
            console.log(`\\n❌ Test completed with ${{criticalFailures.length}} failure(s)`);
            for (const failure of criticalFailures) {{
                console.log(`  - ${{failure}}`);
            }}
            throw new Error("Test failed");
        }} else {{
            console.log("✅ Test completed successfully");
        }}
    }} catch (e) {{
        console.log(`❌ Test failed: ${{e}}`);
        throw e;
    }}
}});
'''
        
        # Validate generated TypeScript - check for common syntax errors
        validation_errors = []
        
        # Check for Python syntax patterns
        python_syntax_patterns = [
            r'urlparse\(',
            r'\[.*for.*in.*\]',  # List comprehensions
            r'\.items\(\)',
            r'#\s+(Remove|Extract|Check|Match)',  # Python-style comments in code
            r'if\s+.*\s+in\s+[^:]+:',  # Python 'in' operator in if statements
            r'parsed\s*=\s*urlparse',  # Python assignment
            r'pathParts\s*=\s*\[.*for',  # Python list comprehension
        ]
        
        for pattern in python_syntax_patterns:
            import re
            matches = re.findall(pattern, test_script)
            if matches:
                validation_errors.append(f"Found Python syntax pattern '{pattern}': {matches[:3]}")
        
        # Check for unclosed catch blocks (catch without closing brace before next try/catch/if/function)
        # Count opening and closing braces in catch blocks
        catch_blocks = re.findall(r'} catch \([^)]+\) \{', test_script)
        # Count closing braces that should match catch blocks
        # This is a simple check - if we have N catch blocks, we should have N closing braces after them
        # More sophisticated: check that every catch has a matching closing brace before the next catch/try/if/function
        
        # Check for catch blocks with :any (old syntax)
        if re.search(r'catch\s*\([^)]+:\s*any\s*\)', test_script):
            validation_errors.append("Found catch blocks with ':any' type annotation (should be removed)")
        
        # Check for missing closing braces after criticalFailures.push
        # Pattern: criticalFailures.push(...) followed by something that's not a closing brace
        if re.search(r'criticalFailures\.push\([^)]+\);\s*\n\s*(?!})', test_script):
            validation_errors.append("Found criticalFailures.push without closing brace")
        
        if validation_errors:
            errors.extend([f"TypeScript validation failed: {err}" for err in validation_errors])
            print(f"⚠️  TypeScript validation warnings: {validation_errors}")
        
        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        return {
            'success': len(errors) == 0,
            'output_file': str(output_file),
            'rows_processed': len(df),
            'errors': errors,
            'validation_warnings': validation_errors if validation_errors else []
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'rows_processed': 0,
            'errors': [str(e)]
        }

