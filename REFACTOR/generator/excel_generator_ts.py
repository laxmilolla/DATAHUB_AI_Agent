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


def generate_wait_code_ts(step: str, wait_time: int, indent: int = 12, previous_was_click: bool = False) -> str:
    """Generate TypeScript wait code
    
    Args:
        step: Step number/identifier
        wait_time: Wait time in milliseconds (from Excel - follow exactly)
        indent: Indentation level
        previous_was_click: If True, previous step was a click that might cause navigation/redirect
    """
    ind = ' ' * indent
    wait_ms = int(wait_time) if wait_time else 1000
    
    # Follow Excel wait_time exactly - no hard-coded logic
    # If user wants to skip wait after TOTP, they should set wait_time to 0 in Excel
    code = f"{ind}// Step {step}: Wait {wait_ms}ms\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
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


def generate_click_code_ts(step: str, xpath: str, url: str, element_name: str, is_optional: bool, indent: int = 12, element_id: Optional[str] = None, next_url: Optional[str] = None, wait_time: Optional[int] = None) -> str:
    """Generate TypeScript click code - registry-aware
    
    Args:
        wait_time: Wait time in milliseconds after click (from Excel wait_time column)
    """
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    # Check if this is a radio button or checkbox (use check() instead of click())
    is_radio_or_checkbox = element_name and ('radio' in element_name.lower() or 'checkbox' in element_name.lower())
    
    code = f"{ind}// Step {step}: Click {element_name or 'element'}\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    
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
            code += f"{ind}        // Use check() for radio-button/checkbox (Playwright best practice)\n"
            code += f"{ind}        try {{\n"
            code += f"{ind}            await element.check();\n"
            code += f"{ind}            console.log(`✅ Step {step}: Check succeeded`);\n"
            code += f"{ind}        }} catch (check_error) {{\n"
            code += f"{ind}            console.log(`⚠️  Step {step}: check() failed, trying setChecked(true)...`);\n"
            code += f"{ind}            try {{\n"
            code += f"{ind}                await element.setChecked(true);\n"
            code += f"{ind}                console.log(`✅ Step {step}: setChecked(true) succeeded`);\n"
            code += f"{ind}            }} catch (setChecked_error) {{\n"
            code += f"{ind}                console.log(`⚠️  Step {step}: setChecked() failed, trying force check...`);\n"
            code += f"{ind}                await element.check({{ force: true }});\n"
            code += f"{ind}                console.log(`✅ Step {step}: Force check succeeded`);\n"
            code += f"{ind}            }}\n"
            code += f"{ind}        }}\n"
        else:
            # Robust click with fallbacks (JavaScript + force)
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
        # Scroll into view if needed
        code += f"{ind}    // Scroll into view if needed\n"
        code += f"{ind}    try {{\n"
        code += f"{ind}        await element.scrollIntoViewIfNeeded();\n"
        code += f"{ind}    }} catch {{\n"
        code += f"{ind}        // Continue if scroll fails\n"
        code += f"{ind}    }}\n"
        code += f"{ind}    await page.waitForTimeout(500);  // Wait after scroll\n"
        if is_radio_or_checkbox:
            # Use check() for radio buttons and checkboxes (Playwright best practice)
            code += f"{ind}    // Use check() for radio-button/checkbox (Playwright best practice)\n"
            code += f"{ind}    let checkSucceeded = false;\n"
            code += f"{ind}    try {{\n"
            code += f"{ind}        await element.check();\n"
            code += f"{ind}        checkSucceeded = true;\n"
            code += f"{ind}        console.log(`✅ Step {step}: Check succeeded`);\n"
            code += f"{ind}    }} catch (check_error) {{\n"
            code += f"{ind}        console.log(`⚠️  Step {step}: check() failed, trying setChecked(true)...`);\n"
            code += f"{ind}        try {{\n"
            code += f"{ind}            await element.setChecked(true);\n"
            code += f"{ind}            checkSucceeded = true;\n"
            code += f"{ind}            console.log(`✅ Step {step}: setChecked(true) succeeded`);\n"
            code += f"{ind}        }} catch (setChecked_error) {{\n"
            code += f"{ind}            console.log(`⚠️  Step {step}: setChecked() failed, trying force check...`);\n"
            code += f"{ind}            await element.check({{ force: true }});\n"
            code += f"{ind}            checkSucceeded = true;\n"
            code += f"{ind}            console.log(`✅ Step {step}: Force check succeeded`);\n"
            code += f"{ind}        }}\n"
            code += f"{ind}    }}\n"
            code += f"{ind}    if (!checkSucceeded) {{\n"
            code += f"{ind}        throw new Error(`Step {step}: All check methods failed`);\n"
            code += f"{ind}    }}\n"
        else:
            # Robust click with fallbacks (JavaScript + force)
            code += f"{ind}    // Robust click with fallbacks (JavaScript + force)\n"
            code += f"{ind}    let clickSucceeded = false;\n"
            code += f"{ind}    try {{\n"
            code += f"{ind}        await element.click();\n"
            code += f"{ind}        clickSucceeded = true;\n"
            code += f"{ind}        console.log(`✅ Step {step}: Click succeeded`);\n"
            code += f"{ind}    }} catch (click_error) {{\n"
            code += f"{ind}        if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {{\n"
            code += f"{ind}            console.log(`⚠️  Step {step}: Click timeout, trying JavaScript click...`);\n"
            code += f"{ind}            try {{\n"
            code += f"{ind}                await element.evaluate('el => el.click()');\n"
            code += f"{ind}                clickSucceeded = true;\n"
            code += f"{ind}                console.log(`✅ Step {step}: JavaScript click succeeded`);\n"
            code += f"{ind}            }} catch (js_error) {{\n"
            code += f"{ind}                console.log(`⚠️  Step {step}: JavaScript click failed, trying force click...`);\n"
            code += f"{ind}                await element.click({{ force: true }});\n"
            code += f"{ind}                clickSucceeded = true;\n"
            code += f"{ind}                console.log(`✅ Step {step}: Force click succeeded`);\n"
            code += f"{ind}            }}\n"
            code += f"{ind}        }} else {{\n"
            code += f"{ind}            console.log(`⚠️  Step {step}: Click failed, trying force click...`);\n"
            code += f"{ind}            await element.click({{ force: true }});\n"
            code += f"{ind}            clickSucceeded = true;\n"
            code += f"{ind}            console.log(`✅ Step {step}: Force click succeeded`);\n"
            code += f"{ind}        }}\n"
            code += f"{ind}    }}\n"
            code += f"{ind}    if (!clickSucceeded) {{\n"
            code += f"{ind}        throw new Error(`Step {step}: All click methods failed`);\n"
            code += f"{ind}    }}\n"
    # Use wait_time from Excel if provided, otherwise default to 1000ms
    wait_ms = int(wait_time) if wait_time else 1000
    code += f"{ind}    await page.waitForTimeout({wait_ms});  // Wait after click (from Excel wait_time: {wait_ms}ms)\n"
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


def generate_fill_code_ts(step: str, xpath: str, text_value: str, url: str, element_name: str, functions: str, is_optional: bool, indent: int = 12, element_id: Optional[str] = None, user_email: Optional[str] = None, wait_time: Optional[int] = None) -> str:
    """Generate TypeScript fill code - registry-aware
    
    Args:
        wait_time: Wait time in milliseconds after fill (from Excel wait_time column)
    """
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    text_escaped = escape_text(text_value)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'input'
    
    # Handle TOTP
    is_totp = 'TOTP' in str(functions).upper() if functions else False
    if is_totp:
        text_escaped = "${TOTP_CODE}"  # Will be replaced at runtime
    
    code = f"{ind}// Step {step}: Fill {element_name or 'input'}\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    
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
            code += f"{ind}        // Try user-specific key first: TOTP_SECRET_KEY_TS_<EMAIL>, then fallback to generic keys\n"
            code += f"{ind}        const secretKey = process.env[`TOTP_SECRET_KEY_TS_${{emailSanitized}}`] || process.env.TOTP_SECRET_KEY_TS || process.env.TOTP_SECRET_KEY;\n"
            code += f"{ind}        if (!secretKey) {{\n"
            code += f"{ind}            throw new Error(`TOTP_SECRET_KEY_TS_${{emailSanitized}} (or TOTP_SECRET_KEY_TS or TOTP_SECRET_KEY) not found in environment variables for user: ${{userEmail}}`);\n"
            code += f"{ind}        }}\n"
            code += f"{ind}        console.log(`🔐 Step {step}: Using TOTP key for user: ${{userEmail}}`);\n"
            code += f"{ind}        // Pass secret key to Python script\n"
            code += f"{ind}        const totpCode = execSync(`python3 ${{scriptPath}} ${{secretKey}}`, {{ encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }}).trim();\n"
        else:
            code += f"{ind}        // Get secret key from environment (same as Python tests)\n"
            code += f"{ind}        const secretKey = process.env.TOTP_SECRET_KEY_TS || process.env.TOTP_SECRET_KEY;\n"
            code += f"{ind}        if (!secretKey) {{\n"
            code += f"{ind}            throw new Error('TOTP_SECRET_KEY_TS (or TOTP_SECRET_KEY) not found in environment variables');\n"
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
    
    # Use wait_time from Excel if provided, otherwise default to 500ms
    wait_ms = int(wait_time) if wait_time else 500
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


def generate_verify_code_ts(step: str, xpath: str, url: str, element_name: str, indent: int = 12, element_id: Optional[str] = None, functions: Optional[str] = None, text_value: Optional[str] = None) -> str:
    """
    Generate TypeScript verify code - registry-aware
    Supports multiple verification types:
    - visibility (default): Verify element is visible
    - text: Verify element text content matches expected value
    - table: Verify all rows in table column contain expected value
    """
    ind = ' ' * indent
    xpath_escaped = escape_xpath(xpath)
    safe_name = re.sub(r'[^\w\s-]', '', element_name).replace(' ', '_')[:30] if element_name else 'element'
    
    # Determine verification type from functions column
    verification_type = 'visibility'  # Default
    if functions:
        functions_upper = str(functions).strip().upper()
        if 'TABLE' in functions_upper:
            verification_type = 'table'
        elif 'TEXT' in functions_upper:
            verification_type = 'text'
    
    code = f"{ind}// Step {step}: Verify {element_name or 'element'}"
    if verification_type == 'text':
        code += f" (text verification)"
    elif verification_type == 'table':
        code += f" (table verification)"
    code += f"\n"
    code += f"{ind}await page.waitForTimeout(3000);  // Wait 3 seconds before step\n"
    code += f"{ind}try {{\n"
    
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
    else:
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
        
        # Detect registry files (URL-free approach: loads all registries if URLs missing)
        project_root = output_file.parent.parent.parent  # Go up from storage/excel_tests to project root
        element_maps_dir = project_root / 'element_maps'
        
        # Load registry files - NO auto-population, only lookup existing XPaths
        # Registry must already contain all XPaths from Excel
        urls = df['url'].dropna().unique().tolist() if 'url' in df.columns else []
        registry_files = detect_registry_files_from_urls(urls, element_maps_dir) if element_maps_dir.exists() else []
        
        # Generate registry code
        registry_code = build_registry_code_ts(registry_files)
        
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
            
            # Update current URL
            if url and url != 'N/A':
                current_url = url
            
            # Generate code based on action
            if action == 'navigate':
                if url:
                    test_body += generate_navigate_code_ts(step, url)
                else:
                    errors.append(f"Step {step}: Navigate action requires URL")
                previous_action = 'navigate'
            
            elif action == 'wait':
                # If previous action was a click, wait for page load (handles redirects)
                previous_was_click = (previous_action == 'click')
                # Follow Excel wait_time exactly - no hard-coded logic
                test_body += generate_wait_code_ts(step, wait_time or 1000, previous_was_click=previous_was_click)
                previous_action = 'wait'
            
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
                    test_body += generate_click_code_ts(step, xpath, row_url, element_name, is_optional, element_id=element_id, next_url=next_url_for_wait, wait_time=wait_ms)
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
                    test_body += generate_fill_code_ts(step, xpath, text_value, row_url, element_name, functions, is_optional, element_id=element_id, user_email=user_email, wait_time=wait_ms)
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
                    test_body += generate_verify_code_ts(
                        step, xpath, row_url, element_name, 
                        element_id=element_id,
                        functions=functions,
                        text_value=text_value
                    )
                    previous_action = 'verify'
            
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

{registry_code}

test('{test_name}', async ({{ page }}) => {{
    /* Auto-generated test from Excel file */
    // Set test timeout to 5 minutes (300000ms) to allow for multiple steps with waits
    test.setTimeout(300000);
    
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

