"""
Python to TypeScript Converter
Converts Python Playwright test code to TypeScript .spec.ts format
"""
import re
from typing import Dict


def convert_python_to_spec_ts(python_code: str) -> str:
    """
    Convert Python Playwright test to TypeScript .spec.ts format
    
    Args:
        python_code: Python Playwright test code as string
        
    Returns:
        TypeScript .spec.ts code as string
    """
    ts_code = python_code
    
    # 1. Convert imports
    ts_code = re.sub(
        r'from playwright\.sync_api import sync_playwright, expect',
        "import { test, expect } from '@playwright/test';",
        ts_code
    )
    
    # Remove Python-specific imports, add TypeScript ones
    ts_code = re.sub(
        r'import re\n',
        "import * as fs from 'fs';\nimport * as path from 'path';\nimport { URL } from 'url';\n",
        ts_code
    )
    ts_code = re.sub(
        r'import json\n',
        "",
        ts_code
    )
    ts_code = re.sub(
        r'import os\n',
        "",
        ts_code
    )
    ts_code = re.sub(
        r'from pathlib import Path\n',
        "",
        ts_code
    )
    
    # 2. Convert .env loading section
    ts_code = convert_env_loading(ts_code)
    
    # 3. Convert REGISTRY_PATHS list syntax
    ts_code = re.sub(r'REGISTRY_PATHS = \[', 'const REGISTRY_PATHS = [', ts_code)
    
    # 4. Convert registry loading loop
    ts_code = convert_registry_loading(ts_code)
    
    # 5. Convert helper functions
    ts_code = convert_helper_functions(ts_code)
    
    # 6. Convert main test function
    ts_code = convert_test_function(ts_code)
    
    # 7. Convert all Playwright API calls (add await, camelCase)
    ts_code = convert_playwright_calls(ts_code)
    
    # 8. Convert string formatting (f-strings to template literals)
    ts_code = convert_string_formatting(ts_code)
    
    # 9. Convert exception handling
    ts_code = convert_exception_handling(ts_code)
    
    # 10. Convert Python comments to TypeScript comments
    # Convert standalone # comments (but not in strings)
    lines = ts_code.split('\n')
    converted_lines = []
    for line in lines:
        # Skip lines that are already TypeScript comments or in strings
        if '//' in line or line.strip().startswith('*') or line.strip().startswith('/'):
            converted_lines.append(line)
        else:
            # Convert # comments to // (but preserve # in strings)
            if '#' in line and not ('"' in line or "'" in line or '`' in line):
                # Simple conversion - replace # with // for comments
                # This is a basic approach - more sophisticated would need proper parsing
                if line.strip().startswith('#'):
                    converted_lines.append(line.replace('#', '//', 1))
                elif '  #' in line or '\t#' in line:
                    # Comment at end of line
                    converted_lines.append(line.replace('  #', '  //').replace('\t#', '\t//'))
                else:
                    converted_lines.append(line)
            else:
                converted_lines.append(line)
    ts_code = '\n'.join(converted_lines)
    
    # 11. Remove Python main block
    ts_code = re.sub(
        r'if __name__ == [\'"]__main__[\'"]:.*?test_\w+\(\)',
        '',
        ts_code,
        flags=re.DOTALL
    )
    
    return ts_code


def convert_env_loading(ts_code: str) -> str:
    """Convert Python .env loading to TypeScript"""
    # Replace Python dotenv loading with TypeScript version
    env_pattern = r'# Load environment variables.*?print\(f"⚠️  Failed to load \.env file: \{e\}"\)'
    
    ts_env_code = '''// Load environment variables from .env file (for TOTP_SECRET_KEY, etc.)
// Check multiple locations: same dir, parent, home, or 3 levels up
let envFile: string | null = null;
try {
  const dotenv = require('dotenv');
  const testFileDir = __dirname;
  const possibleEnvLocations = [
    path.join(testFileDir, '.env'),  // Same directory as test file
    path.join(path.dirname(testFileDir), '.env'),  // Parent directory
    path.join(require('os').homedir(), '.env'),  // Home directory
    path.join(path.dirname(path.dirname(path.dirname(testFileDir))), '.env'),  // 3 levels up
  ];
  
  for (const loc of possibleEnvLocations) {
    if (fs.existsSync(loc)) {
      envFile = loc;
      dotenv.config({ path: loc });
      console.log(`✅ Loaded environment variables from ${envFile}`);
      break;
    }
  }
  
  if (!envFile) {
    console.log(`⚠️  .env file not found. Checked locations:`);
    for (const loc of possibleEnvLocations) {
      console.log(`   - ${loc}`);
    }
    console.log(`   Please create a .env file with TOTP_SECRET_KEY=your_secret_key`);
  }
} catch (e: any) {
  if (e.code === 'MODULE_NOT_FOUND') {
    console.log("⚠️  dotenv not installed - environment variables must be set manually");
  } else {
    console.log(`⚠️  Failed to load .env file: ${e}`);
  }
}'''
    
    ts_code = re.sub(env_pattern, ts_env_code, ts_code, flags=re.DOTALL)
    return ts_code


def convert_registry_loading(ts_code: str) -> str:
    """Convert Python registry loading to TypeScript"""
    # Convert REGISTRIES_BY_PATH initialization
    ts_code = re.sub(
        r'REGISTRIES_BY_PATH = \{\}  # registry_path -> registry_data',
        "const REGISTRIES_BY_PATH: { [key: string]: any } = {};  // registry_path -> registry_data",
        ts_code
    )
    ts_code = re.sub(r'loaded_count = 0', 'let loadedCount = 0', ts_code)
    
    # Convert registry loading loop
    registry_loop_pattern = r'for registry_path_str in REGISTRY_PATHS:(.*?)loaded_count \+= 1'
    
    def replace_registry_loop(match):
        loop_body = match.group(1)
        # Convert Path operations
        loop_body = re.sub(r'registry_path = Path\(registry_path_str\)', 'const registryPath = registryPathStr', loop_body)
        loop_body = re.sub(r'registry_path\.exists\(\)', 'fs.existsSync(registryPathStr)', loop_body)
        loop_body = re.sub(r'with open\(registry_path, [\'"]r[\'"]\) as f:\s*registry_data = json\.load\(f\)', 
                          'const registryData = JSON.parse(fs.readFileSync(registryPathStr, \'utf-8\'))', loop_body)
        loop_body = re.sub(r'REGISTRIES_BY_PATH\[registry_path_str\]', 'REGISTRIES_BY_PATH[registryPathStr]', loop_body)
        loop_body = re.sub(r'len\(registry_data\.get\([\'"]elements[\'"], \{\}\)\)', 
                          'Object.keys(registryData.elements || {}).length', loop_body)
        loop_body = re.sub(r'registry_path\.name', 'path.basename(registryPathStr)', loop_body)
        loop_body = re.sub(r'loaded_count \+= 1', 'loadedCount++', loop_body)
        loop_body = re.sub(r'print\(f', 'console.log(`', loop_body)
        loop_body = re.sub(r'registry_path_str', 'registryPathStr', loop_body)
        return f'for (const registryPathStr of REGISTRY_PATHS) {{{loop_body}    loadedCount++'
    
    ts_code = re.sub(registry_loop_pattern, replace_registry_loop, ts_code, flags=re.DOTALL)
    
    # Convert summary print
    ts_code = re.sub(
        r'total_elements = sum\(len\(reg\.get\([\'"]elements[\'"], \{\}\)\) for reg in REGISTRIES_BY_PATH\.values\(\)\)',
        'const totalElements = Object.values(REGISTRIES_BY_PATH).reduce((sum: number, reg: any) => sum + Object.keys(reg.elements || {}).length, 0)',
        ts_code
    )
    ts_code = re.sub(
        r'total_ids = sum\(len\(reg\.get\([\'"]id_index[\'"], \{\}\)\) for reg in REGISTRIES_BY_PATH\.values\(\)\)',
        'const totalIds = Object.values(REGISTRIES_BY_PATH).reduce((sum: number, reg: any) => sum + Object.keys(reg.id_index || {}).length, 0)',
        ts_code
    )
    ts_code = re.sub(
        r'print\(f"✅ Loaded \{loaded_count\} registries: \{total_elements\} total elements, \{total_ids\} total IDs',
        'console.log(`✅ Loaded ${loadedCount} registries: ${totalElements} total elements, ${totalIds} total IDs',
        ts_code
    )
    
    return ts_code


def convert_helper_functions(ts_code: str) -> str:
    """Convert Python helper functions to TypeScript"""
    # Convert get_registry_for_page function
    ts_code = re.sub(
        r'def get_registry_for_page\(page_url\):',
        'function getRegistryForPage(pageUrl: string | null): any {',
        ts_code
    )
    
    # Convert get_xpath_by_id function (simpler version without page_url)
    ts_code = re.sub(
        r'def get_xpath_by_id\(element_id\):',
        'function getXpathById(elementId: string): string {',
        ts_code
    )
    ts_code = re.sub(r'"""Get registry.*?"""', '/**Get registry for current page based on URL*/', ts_code)
    ts_code = re.sub(r'if not page_url:', 'if (!pageUrl) {', ts_code)
    ts_code = re.sub(r'from urllib\.parse import urlparse', '', ts_code)
    ts_code = re.sub(r'parsed = urlparse\(page_url\)', 'const parsed = new URL(pageUrl)', ts_code)
    ts_code = re.sub(r'domain = parsed\.netloc\.split\([\'"]:[\'"]\)\[0\]', 
                    'const domain = parsed.hostname.split(\':\')[0]', ts_code)
    ts_code = re.sub(r'path_parts = \[p for p in parsed\.path\.split\([\'"]/[\'"]\) if p\]',
                    'const pathParts = parsed.pathname.split(\'/\').filter(p => p)', ts_code)
    ts_code = re.sub(r'if not path_parts:', 'if (pathParts.length === 0) {', ts_code)
    ts_code = re.sub(r'page_name = [\'"]home[\'"]', 'pageName = \'home\'', ts_code)
    ts_code = re.sub(r'page_name = [\'"]explore[\'"]', 'pageName = \'explore\'', ts_code)
    ts_code = re.sub(r'page_name =', 'let pageName: string;', ts_code, count=1)
    ts_code = re.sub(r'best_match = None', 'let bestMatch: any = null', ts_code)
    ts_code = re.sub(r'best_score = 0', 'let bestScore = 0', ts_code)
    ts_code = re.sub(r'for registry_path_str, registry_data in REGISTRIES_BY_PATH\.items\(\):',
                    'for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {', ts_code)
    ts_code = re.sub(r'score = 0', 'let score = 0', ts_code)
    ts_code = re.sub(r'if score > best_score:', 'if (score > bestScore) {', ts_code)
    ts_code = re.sub(r'best_score = score', 'bestScore = score', ts_code)
    ts_code = re.sub(r'best_match = registry_data', 'bestMatch = registryData', ts_code)
    ts_code = re.sub(r'if best_match and best_score >= 3:', 'if (bestMatch && bestScore >= 3) {', ts_code)
    ts_code = re.sub(r'return best_match', 'return bestMatch', ts_code)
    ts_code = re.sub(r'return None', 'return null', ts_code)
    
    # Convert get_xpath_by_id function (with page_url parameter)
    ts_code = re.sub(
        r'def get_xpath_by_id\(element_id, page_url=None\):',
        'function getXpathById(elementId: string, pageUrl?: string): string {',
        ts_code
    )
    ts_code = re.sub(r'if not element_id:', 'if (!elementId) {', ts_code)
    ts_code = re.sub(r'raise Exception\(f"❌ element_id is required"\)', 
                    'throw new Error(`❌ element_id is required`)', ts_code)
    ts_code = re.sub(r'if page_url:', 'if (pageUrl) {', ts_code)
    ts_code = re.sub(r'page_registry = get_registry_for_page\(page_url\)',
                    'const pageRegistry = getRegistryForPage(pageUrl)', ts_code)
    ts_code = re.sub(r'current_registry = page_registry\.get\([\'"]elements[\'"], \{\}\)',
                    'const currentRegistry = pageRegistry.elements || {}', ts_code)
    ts_code = re.sub(r'current_id_index = page_registry\.get\([\'"]id_index[\'"], \{\}\)',
                    'const currentIdIndex = pageRegistry.id_index || {}', ts_code)
    ts_code = re.sub(r'if element_id in current_id_index:',
                    'if (elementId in currentIdIndex) {', ts_code)
    ts_code = re.sub(r'registry_key = current_id_index\[element_id\]',
                    'const registryKey = currentIdIndex[elementId]', ts_code)
    ts_code = re.sub(r'if registry_key in current_registry:',
                    'if (registryKey in currentRegistry) {', ts_code)
    ts_code = re.sub(r'xpath = current_registry\[registry_key\]\.get\([\'"]xpath[\'"]\)',
                    'const xpath = currentRegistry[registryKey].xpath', ts_code)
    ts_code = re.sub(r'if xpath:', 'if (xpath) {', ts_code)
    ts_code = re.sub(r'return xpath', 'return xpath', ts_code)
    ts_code = re.sub(r'raise Exception\(f"❌ element_id', 'throw new Error(`❌ element_id', ts_code)
    
    return ts_code


def convert_test_function(ts_code: str) -> str:
    """Convert Python test function to TypeScript test() block"""
    # Convert function definition - handle both with and without docstring
    ts_code = re.sub(
        r'def (\w+)\(\):\s*""".*?"""\s*',
        r"test('\1', async ({ page }) => {\n  /**Auto-generated test from AI discovery - 1:1 mirror of AI execution*/\n",
        ts_code,
        flags=re.DOTALL
    )
    
    # Also handle without docstring
    ts_code = re.sub(
        r'def (\w+)\(\):',
        r"test('\1', async ({ page }) => {",
        ts_code
    )
    
    # Convert critical_failures initialization
    ts_code = re.sub(
        r'critical_failures = \[\]',
        'const criticalFailures: string[] = []',
        ts_code
    )
    
    # Remove sync_playwright context manager - more flexible pattern
    ts_code = re.sub(
        r'with sync_playwright\(\) as p:\s*browser = p\.chromium\.launch\(headless=(True|False)\)\s*.*?page = browser\.new_page\(viewport=\{\'width\': 1920, \'height\': 1080\}\)',
        '// Set viewport to match AI agent (tabs visible, not hidden in "More" dropdown)\n  await page.setViewportSize({ width: 1920, height: 1080 })',
        ts_code,
        flags=re.DOTALL
    )
    
    # Remove browser.close() in finally block
    ts_code = re.sub(r'finally:\s*browser\.close\(\)', '', ts_code, flags=re.DOTALL)
    
    # Remove if __name__ block
    ts_code = re.sub(
        r'if __name__ == [\'"]__main__[\'"]:.*?test_\w+\(\)',
        '',
        ts_code,
        flags=re.DOTALL
    )
    
    return ts_code


def convert_playwright_calls(ts_code: str) -> str:
    """Convert Playwright API calls to TypeScript (add await, camelCase)"""
    # Add await to page methods
    ts_code = re.sub(r'(\s+)(page\.)(goto|wait_for_load_state|wait_for_timeout|screenshot|setViewportSize)',
                    r'\1await \2\3', ts_code)
    
    # Convert method names to camelCase
    ts_code = re.sub(r'wait_for_timeout', 'waitForTimeout', ts_code)
    ts_code = re.sub(r'wait_for_load_state', 'waitForLoadState', ts_code)
    ts_code = re.sub(r'wait_for\(', 'waitFor({', ts_code)
    
    # Add await to element methods
    ts_code = re.sub(r'(\s+)(element\d*\.)(click|fill|wait_for|is_checked|input_value|evaluate|is_visible|count|scroll_into_view_if_needed|get_attribute)',
                    r'\1await \2\3', ts_code)
    
    # Convert element method names
    ts_code = re.sub(r'\.wait_for\(', '.waitFor({', ts_code)
    ts_code = re.sub(r'is_checked\(\)', 'isChecked()', ts_code)
    ts_code = re.sub(r'input_value\(\)', 'inputValue()', ts_code)
    ts_code = re.sub(r'is_visible\(', 'isVisible({', ts_code)
    ts_code = re.sub(r'scroll_into_view_if_needed\(\)', 'scrollIntoViewIfNeeded()', ts_code)
    ts_code = re.sub(r'get_attribute\(', 'getAttribute(', ts_code)
    
    # Convert wait_for parameters
    ts_code = re.sub(r'wait_for\(state=[\'"](\w+)[\'"], timeout=(\d+)\)',
                    r'waitFor({ state: \'\1\', timeout: \2 })', ts_code)
    
    # Convert screenshot parameters
    ts_code = re.sub(r'screenshot\(path=[\'"]([^\'"]+)[\'"]\)',
                    r'screenshot({ path: \'\1\' })', ts_code)
    
    # Convert page.url to page.url()
    ts_code = re.sub(r'page\.url\b', 'page.url()', ts_code)
    
    return ts_code


def convert_string_formatting(ts_code: str) -> str:
    """Convert Python f-strings to TypeScript template literals"""
    # Convert f-strings to template literals
    # Pattern: f"text {var}" -> `text ${var}`
    def convert_fstring(match):
        content = match.group(1)
        # Replace {var} with ${var}
        content = re.sub(r'\{([^}]+)\}', r'${\1}', content)
        return f'`{content}`'
    
    ts_code = re.sub(r'f"([^"]+)"', convert_fstring, ts_code)
    ts_code = re.sub(r"f'([^']+)'", convert_fstring, ts_code)
    
    # Convert print statements
    ts_code = re.sub(r'print\(', 'console.log(', ts_code)
    
    return ts_code


def convert_exception_handling(ts_code: str) -> str:
    """Convert Python exception handling to TypeScript"""
    ts_code = re.sub(r'except Exception as e:', '} catch (e: any) {', ts_code)
    ts_code = re.sub(r'except:', '} catch {', ts_code)
    ts_code = re.sub(r'raise Exception\(', 'throw new Error(', ts_code)
    ts_code = re.sub(r'raise\s*$', 'throw e', ts_code, flags=re.MULTILINE)
    ts_code = re.sub(r'raise\s*# Re-raise', 'throw e;  // Re-raise', ts_code)
    
    # Convert error message formatting
    ts_code = re.sub(r'error_msg = f\'([^\']+)\'', r'const errorMsg = `\1`', ts_code)
    ts_code = re.sub(r'error_msg', 'errorMsg', ts_code)
    ts_code = re.sub(r'critical_failures\.append\(', 'criticalFailures.push(', ts_code)
    ts_code = re.sub(r'len\(critical_failures\)', 'criticalFailures.length', ts_code)
    ts_code = re.sub(r'for failure in critical_failures:', 
                    'for (const failure of criticalFailures) {', ts_code)
    
    return ts_code

