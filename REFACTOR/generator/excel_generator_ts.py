"""
Excel-Based Playwright TypeScript Generator
Reads Excel file with Step, URL, XPath, Action, etc. and generates TypeScript Playwright code
Registry-aware: Uses element registry instead of hard-coded XPaths
Auto-populates registries from Excel before test generation
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
    populate_registry_from_excel,
    lookup_element_id_by_xpath
)


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
// MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
// ============================================================================
// Automatically detects and loads all registry files needed based on URLs in Excel
const REGISTRY_PATHS = {registry_paths_list_str};

// Load registries per domain/page (for dynamic loading based on current page)
// NO MERGE: Keep registries separate to avoid conflicts when same element name exists in multiple registries
const REGISTRIES_BY_PATH: {{ [key: string]: any }} = {{}};  // registry_path -> registryData
let loadedCount = 0;

// Resolve project root: go up 3 levels from test file (storage/excel_tests -> storage -> project root)
const projectRoot = path.join(__dirname, '../../..');

for (const registryPathStr of REGISTRY_PATHS) {{
    try {{
        // Resolve registry path relative to project root (not test file directory)
        const registryPath = path.join(projectRoot, registryPathStr);
        
        if (fs.existsSync(registryPath)) {{
            const registryData = JSON.parse(fs.readFileSync(registryPath, 'utf-8'));
            // Store per-path for dynamic loading (NO MERGE - prevents conflicts)
            REGISTRIES_BY_PATH[registryPathStr] = registryData;
            loadedCount++;
            console.log(`✅ Loaded registry: ${{Object.keys(registryData.elements || {{}}).length}} elements from ${{path.basename(registryPathStr)}}`);
        }} else {{
            console.log(`⚠️  Registry file not found: ${{registryPath}} (resolved from ${{registryPathStr}})`);
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

function getRegistryForPage(pageUrl: string | null): any {{
    /* Get registry for current page based on URL */
    if (!pageUrl) {{
        return null;
    }}
    
    const parsed = new URL(pageUrl);
    const domain = parsed.hostname.split(':')[0];  // Remove port if present
    
    // Extract page name from URL path
    const pathParts = parsed.pathname.split('/').filter(p => p);
    let pageName: string;
    if (pathParts.length === 0) {{
        pageName = 'home';
    }} else if (pathParts[pathParts.length - 1] === 'explore') {{
        pageName = 'explore';
    }} else {{
        // Get last path segment, remove query params
        pageName = pathParts[pathParts.length - 1].split('?')[0].split('#')[0];
        // Remove file extension if present
        if (pageName.includes('.')) {{
            pageName = pageName.split('.')[0];
        }}
    }}
    
    // Try to find matching registry file
    let bestMatch: any = null;
    let bestScore = 0;
    
    for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {{
        // Check if registry path matches domain
        if (!registryPathStr.includes(domain)) {{
            continue;
        }}
        
        let score = 0;
        // Score based on how well the registry path matches the page
        
        // Exact page name match gets highest score
        if (registryPathStr.includes(pageName)) {{
            score += 10;
        }}
        
        // Check for specific page patterns in registry path
        const registryFilename = registryPathStr.split('/').at(-1) || '';
        
        // Match page name in filename (e.g., LoginMFA.aspx_page.json for LoginMFA.aspx)
        if (registryFilename.toLowerCase().includes(pageName.toLowerCase())) {{
            score += 8;
        }}
        
        // Match common patterns
        if (registryFilename.toLowerCase().includes('home') && (!pathParts || pathParts.length === 0 || pathParts[pathParts.length - 1] === '')) {{
            score += 5;
        }}
        
        // Match domain exactly
        if (registryPathStr.includes(domain)) {{
            score += 3;
        }}
        
        if (score > bestScore) {{
            bestScore = score;
            bestMatch = registryData;
        }}
    }}
    
    // If we found a good match, return it
    if (bestMatch && bestScore >= 3) {{
        return bestMatch;
    }}
    
    // Fallback: return first registry that matches domain
    for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {{
        if (registryPathStr.includes(domain)) {{
            return registryData;
        }}
    }}
    
    return null;
}}

function getXpathById(elementId: string, pageUrl?: string): string {{
    /* Get XPath from registry by unique ID - prefers registry for current page, searches all registries for same domain if not found */
    if (!elementId) {{
        throw new Error(`❌ element_id is required`);
    }}
    
    // STEP 1: Try to get registry for current page first
    if (pageUrl) {{
        const pageRegistry = getRegistryForPage(pageUrl);
        if (pageRegistry) {{
            const currentRegistry = pageRegistry.elements || {{}};
            const currentIdIndex = pageRegistry.id_index || {{}};
            
            // Check if element_id exists in current page registry
            if (elementId in currentIdIndex) {{
                const registryKey = currentIdIndex[elementId];
                if (registryKey in currentRegistry) {{
                    const xpath = currentRegistry[registryKey].xpath;
                    if (xpath) {{
                        return xpath;
                    }}
                }}
            }}
        }}
    }}
    
    // STEP 2: If not found in page-specific registry, search all registries for same domain
    if (pageUrl) {{
        const parsed = new URL(pageUrl);
        const domain = parsed.hostname.split(':')[0];  // Remove port if present
        
        // Search all registries for this domain
        for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {{
            if (registryPathStr.includes(domain)) {{
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
        }}
    }}
    
    // STEP 3: Last resort - search ALL registries (cross-domain fallback)
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


def generate_navigate_code_ts(step: str, url: str, indent: int = 12) -> str:
    """Generate TypeScript navigation code"""
    ind = ' ' * indent
    code = f"{ind}// Step {step}: Navigate to {url}\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
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


def generate_wait_code_ts(step: str, wait_time: int, indent: int = 12) -> str:
    """Generate TypeScript wait code"""
    ind = ' ' * indent
    wait_ms = int(wait_time) if wait_time else 1000
    code = f"{ind}// Step {step}: Wait {wait_ms}ms\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    code += f"{ind}try {{\n"
    code += f"{ind}    await page.waitForTimeout({wait_ms});\n"
    code += f"{ind}    console.log(`⏱️  Step {step}: Waited {wait_ms}ms`);\n"
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_wait.png' }});\n"
    code += f"{ind}}} catch (e) {{\n"
    code += f"{ind}    console.log(`❌ Step {step}: Wait failed: ${{e}}`);\n"
    code += f"{ind}}}\n"
    return code


def generate_click_code_ts(step: str, xpath: str, url: str, element_name: str, is_optional: bool, indent: int = 12, is_modal_step: bool = False, element_id: Optional[str] = None) -> str:
    """Generate TypeScript click code - registry-aware"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    code = f"{ind}// Step {step}: Click {element_name or 'element'}\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    
    # Scope XPath to modal if needed
    if is_modal_step:
        if not xpath_escaped.startswith('(//*[@data-testid="create-submission-dialog"])'):
            xpath_escaped = f'(//*[@data-testid="create-submission-dialog"])//{xpath_escaped.lstrip("/")}'
        
        code += f"{ind}// Modal step - wait for modal and scope selector\n"
        code += f"{ind}// Wait for modal to be visible\n"
        code += f"{ind}try {{\n"
        code += f"{ind}    const modal = page.locator('[role=\"dialog\"], [data-testid=\"create-submission-dialog\"]').first();\n"
        code += f"{ind}    await modal.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}    console.log(`✅ Step {step}: Modal is visible`);\n"
        code += f"{ind}}} catch (modal_error) {{\n"
        code += f"{ind}    console.log(`⚠️  Step {step}: Modal not found, continuing anyway: ${{modal_error}}`);\n"
        code += f"{ind}}}\n"
    
    if is_optional:
        code += f"{ind}// Optional step - continue if element not found\n"
        code += f"{ind}try {{\n"
    else:
        code += f"{ind}try {{\n"
    
    # Use registry lookup if element_id is available
    if element_id:
        element_id_escaped = escape_xpath(element_id)
        # Use URL from Excel row, fallback to undefined if empty
        url_param = f"'{url}'" if url and url != 'N/A' else 'undefined'
        # Declare element variable outside try block so it's in scope for click handling
        code += f"{ind}    let element;\n"
        code += f"{ind}    // Try registry lookup first\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        const xpath = getXpathById('{element_id_escaped}', {url_param});\n"
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
    
    # For Create button in modal (Step 19), wait for it to be enabled and scroll into view
    is_create_button = ('create-data-submission-dialog-create-button' in xpath_escaped or 
                       ('create' in str(step).lower() and is_modal_step))
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
        code += f"{ind}        // Robust click with fallbacks (JavaScript + force)\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            await element.click();\n"
        code += f"{ind}        }} catch (click_error) {{\n"
        code += f"{ind}            if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {{\n"
        code += f"{ind}                console.log(`⚠️  Step {step}: Click timeout, trying JavaScript click...`);\n"
        code += f"{ind}                try {{\n"
        code += f"{ind}                    await element.evaluate('el => el.click()');\n"
        code += f"{ind}                    console.log(`✅ Step {step}: JavaScript click succeeded`);\n"
        code += f"{ind}                }} catch (js_error) {{\n"
        code += f"{ind}                    console.log(`⚠️  Step {step}: JavaScript click failed, trying force click...`);\n"
        code += f"{ind}                    await element.click({{ force: true }});\n"
        code += f"{ind}                    console.log(`✅ Step {step}: Force click succeeded`);\n"
        code += f"{ind}                }}\n"
        code += f"{ind}            }} else {{\n"
        code += f"{ind}                console.log(`⚠️  Step {step}: Click failed, trying force click...`);\n"
        code += f"{ind}                await element.click({{ force: true }});\n"
        code += f"{ind}                console.log(`✅ Step {step}: Force click succeeded`);\n"
        code += f"{ind}            }}\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
    else:
        # Robust click with fallbacks for all non-Create button clicks
        code += f"{ind}    // Scroll into view if needed\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        await element.scrollIntoViewIfNeeded();\n"
        code += f"{ind}    }} catch {{\n"
        code += f"{ind}        // Continue if scroll fails\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    await page.waitForTimeout(500);  // Wait after scroll\n"
        code += f"{ind}    // Robust click with fallbacks (JavaScript + force)\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        await element.click();\n"
        code += f"{ind}    }} catch (click_error) {{\n"
        code += f"{ind}        if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {{\n"
        code += f"{ind}            console.log(`⚠️  Step {step}: Click timeout, trying JavaScript click...`);\n"
        code += f"{ind}            try {{\n"
        code += f"{ind}                await element.evaluate('el => el.click()');\n"
        code += f"{ind}                console.log(`✅ Step {step}: JavaScript click succeeded`);\n"
        code += f"{ind}            }} catch (js_error) {{\n"
        code += f"{ind}                console.log(`⚠️  Step {step}: JavaScript click failed, trying force click...`);\n"
        code += f"{ind}                await element.click({{ force: true }});\n"
        code += f"{ind}                console.log(`✅ Step {step}: Force click succeeded`);\n"
        code += f"{ind}            }}\n"
        code += f"{ind}        }} else {{\n"
        code += f"{ind}            console.log(`⚠️  Step {step}: Click failed, trying force click...`);\n"
        code += f"{ind}            await element.click({{ force: true }});\n"
        code += f"{ind}            console.log(`✅ Step {step}: Force click succeeded`);\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
    code += f"{ind}    await page.waitForTimeout(1000);  // Wait after click\n"
    element_display = element_name or 'element'
    code += f"{ind}    console.log(`✅ Step {step}: Clicked {element_display}`);\n"
    code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}.png' }});\n"
    
    if is_optional:
        code += f"{ind}}} catch (e) {{\n"
        code += f"{ind}    console.log(`ℹ️  Step {step}: Element not found (optional) - continuing`);\n"
        code += f"{ind}}}\n"
    else:
        code += f"{ind}}} catch (e) {{\n"
        element_display = element_name or 'element'
        code += f"{ind}    console.log(`❌ Step {step}: Failed to click {element_display}: ${{e}}`);\n"
        code += f"{ind}    await page.screenshot({{ path: 'storage/screenshots/pw_step{step}_{safe_name}_failed.png' }});\n"
        code += f"{ind}    criticalFailures.push(`Step {step}: Click failed`);\n"
        code += f"{ind}}}\n"
    
    code += f"{ind}\n"
    return code


def generate_fill_code_ts(step: str, xpath: str, text_value: str, url: str, element_name: str, functions: str, is_optional: bool, indent: int = 12, is_modal_step: bool = False, element_id: Optional[str] = None) -> str:
    """Generate TypeScript fill code - registry-aware"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    text_escaped = escape_text(text_value)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'input'
    
    # Handle TOTP
    is_totp = 'TOTP' in str(functions).upper() if functions else False
    if is_totp:
        text_escaped = "${TOTP_CODE}"  # Will be replaced at runtime
    
    # Scope XPath to modal if needed
    if is_modal_step:
        if not xpath_escaped.startswith('(//*[@data-testid="create-submission-dialog"])'):
            xpath_escaped = f'(//*[@data-testid="create-submission-dialog"])//{xpath_escaped.lstrip("/")}'
    
    code = f"{ind}// Step {step}: Fill {element_name or 'input'}\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    
    if is_modal_step:
        code += f"{ind}// Modal step - wait for modal\n"
        code += f"{ind}try {{\n"
        code += f"{ind}    const modal = page.locator('[role=\"dialog\"], [data-testid=\"create-submission-dialog\"]').first();\n"
        code += f"{ind}    await modal.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}    console.log(`✅ Step {step}: Modal is visible`);\n"
        code += f"{ind}}} catch (modal_error) {{\n"
        code += f"{ind}    console.log(`⚠️  Step {step}: Modal not found, continuing anyway: ${{modal_error}}`);\n"
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
        code += f"{ind}        element = page.locator(selector).nth(0);\n"
        code += f"{ind}        await element.waitFor({{ state: 'visible', timeout: 10000 }});\n"
        code += f"{ind}        console.log(`⚠️  Step {step}: TOTP field not found with fallback selectors, using original selector`);\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    // Generate TOTP code\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        const totp = require('otplib').totp;\n"
        code += f"{ind}        const secretKey = process.env.TOTP_SECRET_KEY;\n"
        code += f"{ind}        if (!secretKey) {{\n"
        code += f"{ind}            throw new Error('TOTP_SECRET_KEY not found in environment variables');\n"
        code += f"{ind}        }}\n"
        code += f"{ind}        const totpCode = totp.generate(secretKey);\n"
        code += f"{ind}        console.log(`🔐 Step {step}: Generated TOTP code: ${{totpCode.substring(0, 2)}}****`);\n"
        code += f"{ind}        \n"
        code += f"{ind}        // For TOTP: clear field first, then use type() with delay (more reliable than fill())\n"
        code += f"{ind}        await element.fill('');\n"
        code += f"{ind}        await element.type(totpCode, {{ delay: 10 }});\n"
        code += f"{ind}        await page.waitForTimeout(200);\n"
        code += f"{ind}        console.log(`✅ Step {step}: Filled TOTP code using type() method`);\n"
        code += f"{ind}    }} catch (e) {{\n"
        code += f"{ind}        console.log(`❌ Step {step}: Failed to generate/fill TOTP code: ${{e}}`);\n"
        code += f"{ind}        // Try fallback fill() method\n"
        code += f"{ind}        try {{\n"
        code += f"{ind}            await element.fill(totpCode);\n"
        code += f"{ind}            console.log(`✅ Step {step}: Filled TOTP code using fill() fallback`);\n"
        code += f"{ind}        }} catch (fill_error) {{\n"
        code += f"{ind}            console.log(`❌ Step {step}: fill() fallback also failed: ${{fill_error}}`);\n"
        code += f"{ind}            throw fill_error;\n"
        code += f"{ind}        }}\n"
        code += f"{ind}    }}\n"
    else:
        # Use registry lookup if element_id is available
        if element_id:
            element_id_escaped = escape_xpath(element_id)
            # Use URL from Excel row, fallback to undefined if empty
            url_param = f"'{url}'" if url and url != 'N/A' else 'undefined'
            # Declare element variable outside try block so it's in scope for fill handling
            code += f"{ind}    let element;\n"
            code += f"{ind}    // Try registry lookup first\n"
            code += f"{ind}    try {{\n"
            code += f"{ind}        const xpath = getXpathById('{element_id_escaped}', {url_param});\n"
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
    
    code += f"{ind}    await page.waitForTimeout(500);  // Wait after fill\n"
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


def generate_verify_code_ts(step: str, xpath: str, url: str, element_name: str, indent: int = 12, element_id: Optional[str] = None) -> str:
    """Generate TypeScript verify code - registry-aware"""
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    code = f"{ind}// Step {step}: Verify {element_name or 'element'}\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    code += f"{ind}try {{\n"
    
    # Use registry lookup if element_id is available
    if element_id:
        element_id_escaped = escape_xpath(element_id)
        # Use URL from Excel row, fallback to undefined if empty
        url_param = f"'{url}'" if url and url != 'N/A' else 'undefined'
        # Declare element variable outside try block so it's in scope
        code += f"{ind}    let element;\n"
        code += f"{ind}    // Try registry lookup first\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        const xpath = getXpathById('{element_id_escaped}', {url_param});\n"
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
    code += f"{ind}    console.log(`❌ Step {step}: Failed to verify {element_display}: ${{e}}`);\n"
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
    - Action: click/fill/verify/wait/navigate
    - Functions: TOTP, etc. (optional)
    - Text Value: For fill actions (optional)
    - Wait Time: For wait actions in ms (optional)
    - Optional: true/false (optional)
    
    Returns:
        Dict with success status and info
    """
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        
        # Normalize column names (case-insensitive, handle spaces)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Detect registry files from URLs in Excel
        project_root = output_file.parent.parent.parent  # Go up from storage/excel_tests to project root
        element_maps_dir = project_root / 'element_maps'
        
        # STEP 1: Auto-populate registries from Excel (Excel → JSON)
        # This ensures all XPaths from Excel are in registries before test generation
        # JSON becomes the source of truth, test code references JSON
        populate_registry_from_excel(df, element_maps_dir)
        
        # Get unique URLs from Excel
        urls = df['url'].dropna().unique().tolist() if 'url' in df.columns else []
        registry_files = detect_registry_files_from_urls(urls, element_maps_dir) if element_maps_dir.exists() else []
        
        # Generate registry code
        registry_code = build_registry_code_ts(registry_files)
        
        # Generate code
        test_body = ""
        errors = []
        current_url = None
        
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
            
            # Update current URL
            if url and url != 'N/A':
                current_url = url
            
            # Generate code based on action
            if action == 'navigate':
                if url:
                    test_body += generate_navigate_code_ts(step, url)
                else:
                    errors.append(f"Step {step}: Navigate action requires URL")
            
            elif action == 'wait':
                test_body += generate_wait_code_ts(step, wait_time or 1000)
            
            elif action == 'click':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    # Check if this is a modal step (after "Create a Data Submission" button click)
                    # Steps 16-19 are modal steps (dropdowns and form fields in the modal)
                    is_modal_step = False
                    try:
                        step_num = int(str(step).replace('a', '').replace('b', ''))
                        if step_num >= 16:  # Steps 16+ are in the modal
                            is_modal_step = True
                    except:
                        # If step is not a number (e.g., '16b'), check if it contains '16' or '17' or '18' or '19'
                        if '16' in str(step) or '17' in str(step) or '18' in str(step) or '19' in str(step):
                            is_modal_step = True
                    
                    # Lookup element_id from registry - use URL from this row (not current_url)
                    row_url = url if url and url != 'N/A' else current_url or ''
                    element_id = lookup_element_id_by_xpath(xpath, row_url, registry_files, element_maps_dir) if registry_files else None
                    test_body += generate_click_code_ts(step, xpath, row_url, element_name, is_optional, is_modal_step=is_modal_step, element_id=element_id)
                else:
                    errors.append(f"Step {step}: Click action requires XPath")
            
            elif action == 'fill':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'input'
                    # Check if this is a modal step (after "Create a Data Submission" button click)
                    # Steps 16-19 are modal steps (dropdowns and form fields in the modal)
                    is_modal_step = False
                    try:
                        step_num = int(str(step).replace('a', '').replace('b', ''))
                        if step_num >= 16:  # Steps 16+ are in the modal
                            is_modal_step = True
                    except:
                        # If step is not a number (e.g., '16b'), check if it contains '16' or '17' or '18' or '19'
                        if '16' in str(step) or '17' in str(step) or '18' in str(step) or '19' in str(step):
                            is_modal_step = True
                    
                    # Lookup element_id from registry - use URL from this row (not current_url)
                    row_url = url if url and url != 'N/A' else current_url or ''
                    element_id = lookup_element_id_by_xpath(xpath, row_url, registry_files, element_maps_dir) if registry_files else None
                    test_body += generate_fill_code_ts(step, xpath, text_value, row_url, element_name, functions, is_optional, is_modal_step=is_modal_step, element_id=element_id)
                else:
                    errors.append(f"Step {step}: Fill action requires XPath")
            
            elif action == 'verify':
                if xpath and xpath != 'N/A':
                    element_name = object_type or 'element'
                    # Lookup element_id from registry - use URL from this row (not current_url)
                    row_url = url if url and url != 'N/A' else current_url or ''
                    element_id = lookup_element_id_by_xpath(xpath, row_url, registry_files, element_maps_dir) if registry_files else None
                    test_body += generate_verify_code_ts(step, xpath, row_url, element_name, element_id=element_id)
                else:
                    errors.append(f"Step {step}: Verify action requires XPath")
            
            else:
                errors.append(f"Step {step}: Unknown action '{action}'")
        
        # Build full test script
        test_name = "test_excel_generated"
        test_script = f'''/*Excel-Generated Playwright Test
Generated from: {excel_file.name}*/

// Load environment variables from .env file (for TOTP_SECRET_KEY, etc.)
// Check multiple locations: same dir, parent, home, or 3 levels up
import {{ test, expect }} from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import {{ URL }} from 'url';

let envFile: string | null = null;
try {{
  const dotenv = require('dotenv');
  const testFileDir = __dirname;
  const possibleEnvLocations = [
    path.join(testFileDir, '.env'),  // Same directory as test file
    path.join(path.dirname(testFileDir), '.env'),  // Parent directory
    path.join(require('os').homedir(), '.env'),  // Home directory
    path.join(path.dirname(path.dirname(path.dirname(testFileDir))), '.env'),  // 3 levels up
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
    console.log(`   Please create a .env file with TOTP_SECRET_KEY=your_secret_key`);
  }}
}} catch (e) {{
  if (e.code === 'MODULE_NOT_FOUND') {{
    console.log("⚠️  dotenv not installed - environment variables must be set manually");
  }} else {{
    console.log(`⚠️  Failed to load .env file: ${{e}}`);
  }}
}}

{registry_code}

test('{test_name}', async ({{ page }}) => {{
    /* Auto-generated test from Excel file */
    const criticalFailures: string[] = [];
    
    // Set viewport to match AI agent (tabs visible, not hidden in "More" dropdown)
    await page.setViewportSize({{ width: 1920, height: 1080 }});
    
    // Generate timestamp if needed
    const TIMESTAMP = new Date().toISOString().replace(/[-:]/g, '').split('.')[0].replace('T', '_');
    
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

