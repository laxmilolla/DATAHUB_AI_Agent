/*Excel-Generated Playwright Test
Generated from: test_case_experiment.xlsx*/

// Load environment variables from .env file (for TOTP_SECRET_KEY, etc.)
// Check multiple locations: same dir, parent, home, or 3 levels up
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { URL } from 'url';

let envFile: string | null = null;
try {
  const dotenv = require('dotenv');
  const testFileDir = __dirname;
  const projectRoot = path.join(__dirname, '../..');
  const possibleEnvLocations = [
    path.join(testFileDir, '.env'),  // Same directory as test file
    path.join(path.dirname(testFileDir), '.env'),  // Parent directory
    path.join(projectRoot, '.env'),  // Project root (DATAHUB_AI_Agent/.env)
    path.join(require('os').homedir(), '.env'),  // Home directory
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
} catch (e) {
  if (e.code === 'MODULE_NOT_FOUND') {
    console.log("⚠️  dotenv not installed - environment variables must be set manually");
  } else {
    console.log(`⚠️  Failed to load .env file: ${e}`);
  }
}

// ============================================================================
// MULTI-REGISTRY SUPPORT (loads all registries for pages visited in test)
// ============================================================================
// Automatically detects and loads all registry files needed based on URLs in Excel
const REGISTRY_PATHS = [
    'element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json',
    'element_maps/hub-stage.datacommons.cancer.gov/home_page.json',
    'element_maps/secure.login.gov/home_page.json',
];

// Load registries per domain/page (for dynamic loading based on current page)
// NO MERGE: Keep registries separate to avoid conflicts when same element name exists in multiple registries
const REGISTRIES_BY_PATH: { [key: string]: any } = {};  // registry_path -> registryData
let loadedCount = 0;

// Resolve registry paths: try multiple locations for flexibility
// 1. Relative to test file directory (for local execution with zip package)
// 2. Relative to project root (for server execution: storage/excel_tests -> project root)
//    Test file: /home/ubuntu/DATAHUB_AI_Agent/storage/excel_tests/test.spec.ts
//    2 levels up: /home/ubuntu/DATAHUB_AI_Agent/ (correct)
//    3 levels up: /home/ubuntu/ (wrong - registry files not there)
const testFileDir = __dirname;
const projectRoot = path.join(__dirname, '../..');

for (const registryPathStr of REGISTRY_PATHS) {
    try {
        let registryPath: string | null = null;
        
        // Try 1: Relative to test file directory (for local zip package)
        const localPath = path.join(testFileDir, registryPathStr);
        if (fs.existsSync(localPath)) {
            registryPath = localPath;
        } else {
            // Try 2: Relative to project root (for server execution)
            const serverPath = path.join(projectRoot, registryPathStr);
            if (fs.existsSync(serverPath)) {
                registryPath = serverPath;
            }
        }
        
        if (registryPath) {
            const registryData = JSON.parse(fs.readFileSync(registryPath, 'utf-8'));
            // Store per-path for dynamic loading (NO MERGE - prevents conflicts)
            REGISTRIES_BY_PATH[registryPathStr] = registryData;
            loadedCount++;
            console.log(`✅ Loaded registry: ${Object.keys(registryData.elements || {}).length} elements from ${path.basename(registryPathStr)}`);
        } else {
            console.log(`⚠️  Registry file not found: ${registryPathStr} (checked: ${path.join(testFileDir, registryPathStr)} and ${path.join(projectRoot, registryPathStr)})`);
        }
    } catch (e) {
        console.log(`⚠️  Failed to load registry ${registryPathStr}: ${e}`);
    }
}

if (loadedCount > 0) {
    const totalElements = Object.values(REGISTRIES_BY_PATH).reduce((sum: number, reg: any) => sum + Object.keys(reg.elements || {}).length, 0);
    const totalIds = Object.values(REGISTRIES_BY_PATH).reduce((sum: number, reg: any) => sum + Object.keys(reg.id_index || {}).length, 0);
    console.log(`✅ Loaded ${loadedCount} registries: ${totalElements} total elements, ${totalIds} total IDs (separate, not merged)`);
}

function getRegistryForPage(pageUrl: string | null): any {
    /* Get registry for current page based on URL */
    if (!pageUrl) {
        return null;
    }
    
    const parsed = new URL(pageUrl);
    const domain = parsed.hostname.split(':')[0];  // Remove port if present
    
    // Extract page name from URL path
    const pathParts = parsed.pathname.split('/').filter(p => p);
    let pageName: string;
    if (pathParts.length === 0) {
        pageName = 'home';
    } else if (pathParts[pathParts.length - 1] === 'explore') {
        pageName = 'explore';
    } else {
        // Get last path segment, remove query params
        pageName = pathParts[pathParts.length - 1].split('?')[0].split('#')[0];
        // Remove file extension if present
        if (pageName.includes('.')) {
            pageName = pageName.split('.')[0];
        }
    }
    
    // Try to find matching registry file
    let bestMatch: any = null;
    let bestScore = 0;
    
    for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {
        // Check if registry path matches domain
        if (!registryPathStr.includes(domain)) {
            continue;
        }
        
        let score = 0;
        // Score based on how well the registry path matches the page
        
        // Exact page name match gets highest score
        if (registryPathStr.includes(pageName)) {
            score += 10;
        }
        
        // Check for specific page patterns in registry path
        const registryFilename = registryPathStr.split('/').at(-1) || '';
        
        // Match page name in filename (e.g., LoginMFA.aspx_page.json for LoginMFA.aspx)
        if (registryFilename.toLowerCase().includes(pageName.toLowerCase())) {
            score += 8;
        }
        
        // Match common patterns
        if (registryFilename.toLowerCase().includes('home') && (!pathParts || pathParts.length === 0 || pathParts[pathParts.length - 1] === '')) {
            score += 5;
        }
        
        // Match domain exactly
        if (registryPathStr.includes(domain)) {
            score += 3;
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestMatch = registryData;
        }
    }
    
    // If we found a good match, return it
    if (bestMatch && bestScore >= 3) {
        return bestMatch;
    }
    
    // Fallback: return first registry that matches domain
    for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {
        if (registryPathStr.includes(domain)) {
            return registryData;
        }
    }
    
    return null;
}

function getXpathById(elementId: string, pageUrl?: string): string {
    /* Get XPath from registry by unique ID - prefers registry for current page, searches all registries for same domain if not found */
    if (!elementId) {
        throw new Error(`❌ element_id is required`);
    }
    
    // STEP 1: Try to get registry for current page first
    if (pageUrl) {
        const pageRegistry = getRegistryForPage(pageUrl);
        if (pageRegistry) {
            const currentRegistry = pageRegistry.elements || {};
            const currentIdIndex = pageRegistry.id_index || {};
            
            // Check if element_id exists in current page registry
            if (elementId in currentIdIndex) {
                const registryKey = currentIdIndex[elementId];
                if (registryKey in currentRegistry) {
                    const xpath = currentRegistry[registryKey].xpath;
                    if (xpath) {
                        return xpath;
                    }
                }
            }
        }
    }
    
    // STEP 2: If not found in page-specific registry, search all registries for same domain
    if (pageUrl) {
        const parsed = new URL(pageUrl);
        const domain = parsed.hostname.split(':')[0];  // Remove port if present
        
        // Search all registries for this domain
        for (const [registryPathStr, registryData] of Object.entries(REGISTRIES_BY_PATH)) {
            if (registryPathStr.includes(domain)) {
                const idIndex = registryData.id_index || {};
                const elements = registryData.elements || {};
                
                if (elementId in idIndex) {
                    const registryKey = idIndex[elementId];
                    if (registryKey in elements) {
                        const xpath = elements[registryKey].xpath;
                        if (xpath) {
                            return xpath;
                        }
                    }
                }
            }
        }
    }
    
    // STEP 3: Last resort - search ALL registries (cross-domain fallback)
    for (const registryData of Object.values(REGISTRIES_BY_PATH)) {
        const idIndex = registryData.id_index || {};
        const elements = registryData.elements || {};
        
        if (elementId in idIndex) {
            const registryKey = idIndex[elementId];
            if (registryKey in elements) {
                const xpath = elements[registryKey].xpath;
                if (xpath) {
                    return xpath;
                }
            }
        }
    }
    
    // Not found in any registry
    throw new Error(`❌ element_id '${elementId}' not found in any registry id_index`);
}



test('test_excel_generated', async ({ page }) => {
    /* Auto-generated test from Excel file */
    // Set test timeout to 5 minutes (300000ms) to allow for multiple steps with waits
    test.setTimeout(300000);
    
    const criticalFailures: string[] = [];
    
    // Set viewport to match AI agent (tabs visible, not hidden in "More" dropdown)
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Generate timestamp if needed
    const TIMESTAMP = new Date().toISOString().replace(/[-:]/g, '').split('.')[0].replace('T', '_');
    
    try {
            // Step 1: Navigate to https://hub-stage.datacommons.cancer.gov/
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                await page.goto('https://hub-stage.datacommons.cancer.gov/');
                await page.waitForLoadState('networkidle');
                console.log(`📍 Step 1: Navigated to https://hub-stage.datacommons.cancer.gov/`);
                await page.screenshot({ path: 'storage/screenshots/pw_step1_navigate.png' });
            } catch (e) {
                console.log(`❌ Step 1: Navigation failed: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step1_navigate_failed.png' });
            }
            
            // Step 1a: Wait 3000ms
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                await page.waitForTimeout(3000);
                console.log(`⏱️  Step 1a: Waited 3000ms`);
                await page.screenshot({ path: 'storage/screenshots/pw_step1a_wait.png' });
            } catch (e) {
                console.log(`❌ Step 1a: Wait failed: ${e}`);
            }
            // Step 2: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 2: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 2: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 2: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Optional step - continue if element not found
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/' || page.url();
                    const xpath = getXpathById('ID_c1bf258c', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 2: Using registry element_id: ID_c1bf258c`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 2: Registry lookup failed for element_id ID_c1bf258c: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step2_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_c1bf258c: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 2: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 2: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 2: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 2: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 2: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 2: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 2: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step2_button.png' });
            } catch (e) {
                console.log(`ℹ️  Step 2: Element not found (optional) - continuing`);
            }
            
            // Step 3: Click link
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 3: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 3: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 3: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/' || page.url();
                    const xpath = getXpathById('ID_f0a2425a', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 3: Using registry element_id: ID_f0a2425a`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 3: Registry lookup failed for element_id ID_f0a2425a: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step3_link_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_f0a2425a: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 3: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 3: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 3: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 3: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 3: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 3: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 3: Clicked link`);
                await page.screenshot({ path: 'storage/screenshots/pw_step3_link.png' });
            } catch (e) {
                console.log(`❌ Step 3: Failed to click link: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step3_link_failed.png' });
                criticalFailures.push(`Step 3: Click failed`);
            }
            
            // Step 4: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://secure.login.gov';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 4: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 4: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 4: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://secure.login.gov' || page.url();
                    const xpath = getXpathById('ID_bee97879', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 4: Using registry element_id: ID_bee97879`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 4: Registry lookup failed for element_id ID_bee97879: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step4_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_bee97879: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 4: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 4: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 4: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 4: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 4: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 4: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 4: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step4_button.png' });
            } catch (e) {
                console.log(`❌ Step 4: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step4_button_failed.png' });
                criticalFailures.push(`Step 4: Click failed`);
            }
            
            // Step 5: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://secure.login.gov';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 5: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 5: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 5: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://secure.login.gov' || page.url();
                    const xpath = getXpathById('ID_b92fade3', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 5: Using registry element_id: ID_b92fade3`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 5: Registry lookup failed for element_id ID_b92fade3: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step5_input_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_b92fade3: ${registry_error}`);
                }
                await element.fill('Laxmi_AI_test@yahoo.com');
                console.log(`✅ Step 5: Filled input with Laxmi_AI_test@yahoo.com`);
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step5_input.png' });
            } catch (e) {
                console.log(`❌ Step 5: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step5_input_failed.png' });
                criticalFailures.push(`Step 5: Fill failed`);
            }
            
            // Step 6: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://secure.login.gov';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 6: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 6: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 6: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://secure.login.gov' || page.url();
                    const xpath = getXpathById('ID_096dd456', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 6: Using registry element_id: ID_096dd456`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 6: Registry lookup failed for element_id ID_096dd456: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step6_input_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_096dd456: ${registry_error}`);
                }
                await element.fill('Testnci123456789!');
                console.log(`✅ Step 6: Filled input with Testnci123456789!`);
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step6_input.png' });
            } catch (e) {
                console.log(`❌ Step 6: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step6_input_failed.png' });
                criticalFailures.push(`Step 6: Fill failed`);
            }
            
            // Step 7: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://secure.login.gov';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 7: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 7: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 7: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://secure.login.gov' || page.url();
                    const xpath = getXpathById('ID_33b5218d', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 7: Using registry element_id: ID_33b5218d`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 7: Registry lookup failed for element_id ID_33b5218d: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step7_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_33b5218d: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 7: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 7: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 7: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 7: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 7: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 7: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 7: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step7_button.png' });
            } catch (e) {
                console.log(`❌ Step 7: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step7_button_failed.png' });
                criticalFailures.push(`Step 7: Click failed`);
            }
            
            // Step 8: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://secure.login.gov';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 8: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 8: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 8: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // TOTP field - code will be generated automatically
            try {
                // TOTP field - try multiple selectors (fallback approach)
                const totpSelectors = [
                    'input.one-time-code-input__input',
                    "input[autocomplete='one-time-code']",
                    "input[type='text'][name='code']",
                    "input[name='code']:not([type='hidden'])",
                    'lg-one-time-code-input input[type=\'text\']',
                    'lg-validated-field input[type=\'text\']',
                    'lg-one-time-code-input input',
                    'input.one-time-code',
                    `xpath=//input[@class=\'one-time-code-input__input\']`,  // Fallback to provided XPath
                ];
                let selectorFound = false;
                let element: any = null;
                for (const totpSel of totpSelectors) {
                    try {
                        const testElem = page.locator(totpSel).first();
                        if (await testElem.isVisible({ timeout: 2000 })) {
                            element = testElem;
                            selectorFound = true;
                            console.log(`✅ Step 8: Found TOTP field with selector: ${totpSel}`);
                            break;
                        }
                    } catch {
                        continue;
                    }
                }
                if (!selectorFound) {
                    // Fallback to original selector
                    const selector = `xpath=//input[@class=\'one-time-code-input__input\']`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`⚠️  Step 8: TOTP field not found with fallback selectors, using original selector`);
                }
                // Generate TOTP code
                try {
                    const totp = require('otplib').totp;
                    const secretKey = process.env.TOTP_SECRET_KEY;
                    if (!secretKey) {
                        throw new Error('TOTP_SECRET_KEY not found in environment variables');
                    }
                    const totpCode = totp.generate(secretKey);
                    console.log(`🔐 Step 8: Generated TOTP code: ${totpCode.substring(0, 2)}****`);
                    
                    // For TOTP: focus, clear, then type with delay (most reliable method)
                    // CRITICAL: Minimize wait times - TOTP codes expire quickly!
                    await element.focus();
                    await page.waitForTimeout(50);  // Reduced - TOTP expires!
                    await element.fill('');
                    await page.waitForTimeout(50);  // Reduced - TOTP expires!
                    await element.type(totpCode, { delay: 30 });  // Reduced delay - TOTP expires!
                    await page.waitForTimeout(50);  // Minimal wait - TOTP expires quickly!
                    // CRITICAL: Keep focus on element to prevent auto-clear - don't take screenshot yet!
                    await element.focus();  // Re-focus to prevent field from being cleared
                    // Verify TOTP code is still in the field
                    const currentValue = await element.inputValue();
                    if (currentValue !== totpCode) {
                        console.log(`⚠️  Step 8: TOTP code was cleared! Re-entering...`);
                        await element.fill('');
                        await element.type(totpCode, { delay: 20 });
                        await element.focus();
                    }
                    console.log(`✅ Step 8: Filled TOTP code using type() method`);
                } catch (e) {
                    console.log(`❌ Step 8: Failed to generate/fill TOTP code: ${e}`);
                    // Try fallback fill() method
                    try {
                        await element.focus();
                        await element.fill('');
                        await element.fill(totpCode);
                        await element.focus();  // Keep focus to prevent clear
                        await page.waitForTimeout(50);  // Minimal wait - TOTP expires quickly!
                        // Verify value is still there
                        const currentValue = await element.inputValue();
                        if (currentValue !== totpCode) {
                            console.log(`⚠️  Step 8: TOTP cleared in fallback! Re-entering...`);
                            await element.fill(totpCode);
                            await element.focus();
                        }
                        console.log(`✅ Step 8: Filled TOTP code using fill() fallback`);
                    } catch (fill_error) {
                        console.log(`❌ Step 8: fill() fallback also failed: ${fill_error}`);
                        throw fill_error;
                    }
                }
                // CRITICAL: Don't take screenshot immediately after TOTP - field might be cleared on focus loss
                // Screenshot will be taken in next step if needed
                await page.waitForTimeout(50);  // Minimal wait - TOTP expires quickly!
            } catch (e) {
                console.log(`❌ Step 8: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step8_input_failed.png' });
                criticalFailures.push(`Step 8: Fill failed`);
            }
            
            // Step 9: Wait 5000ms
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                await page.waitForTimeout(5000);
                console.log(`⏱️  Step 9: Waited 5000ms`);
                await page.screenshot({ path: 'storage/screenshots/pw_step9_wait.png' });
            } catch (e) {
                console.log(`❌ Step 9: Wait failed: ${e}`);
            }
            // Step 10: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://secure.login.gov';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 10: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 10: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 10: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://secure.login.gov' || page.url();
                    const xpath = getXpathById('ID_33b5218d', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 10: Using registry element_id: ID_33b5218d`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 10: Registry lookup failed for element_id ID_33b5218d: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step10_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_33b5218d: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 10: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 10: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 10: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 10: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 10: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 10: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 10: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step10_button.png' });
            } catch (e) {
                console.log(`❌ Step 10: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step10_button_failed.png' });
                criticalFailures.push(`Step 10: Click failed`);
            }
            
            // Step 14: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 14: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 14: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 14: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_8fcff2a7', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 14: Using registry element_id: ID_8fcff2a7`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 14: Registry lookup failed for element_id ID_8fcff2a7: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step14_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_8fcff2a7: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 14: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 14: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 14: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 14: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 14: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 14: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 14: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step14_button.png' });
            } catch (e) {
                console.log(`❌ Step 14: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step14_button_failed.png' });
                criticalFailures.push(`Step 14: Click failed`);
            }
            
            // Step 15: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 15: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 15: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 15: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_38253381', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 15: Using registry element_id: ID_38253381`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 15: Registry lookup failed for element_id ID_38253381: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step15_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_38253381: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 15: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 15: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 15: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 15: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 15: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 15: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 15: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step15_button.png' });
            } catch (e) {
                console.log(`❌ Step 15: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step15_button_failed.png' });
                criticalFailures.push(`Step 15: Click failed`);
            }
            
            // Step 16: Click dropdown
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 16: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 16: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 16: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Modal step - wait for modal and scope selector
            // Wait for modal to be visible
            try {
                const modal = page.locator('[role="dialog"], [data-testid="create-submission-dialog"]').first();
                await modal.waitFor({ state: 'visible', timeout: 10000 });
                console.log(`✅ Step 16: Modal is visible`);
            } catch (modal_error) {
                console.log(`⚠️  Step 16: Modal not found, continuing anyway: ${modal_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_70bc9e6a', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 16: Using registry element_id: ID_70bc9e6a`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 16: Registry lookup failed for element_id ID_70bc9e6a: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step16_dropdown_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_70bc9e6a: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 16: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 16: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 16: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 16: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 16: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 16: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 16: Clicked dropdown`);
                await page.screenshot({ path: 'storage/screenshots/pw_step16_dropdown.png' });
            } catch (e) {
                console.log(`❌ Step 16: Failed to click dropdown: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step16_dropdown_failed.png' });
                criticalFailures.push(`Step 16: Click failed`);
            }
            
            // Step 16b: Click option
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 16b: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 16b: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 16b: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Modal step - wait for modal and scope selector
            // Wait for modal to be visible
            try {
                const modal = page.locator('[role="dialog"], [data-testid="create-submission-dialog"]').first();
                await modal.waitFor({ state: 'visible', timeout: 10000 });
                console.log(`✅ Step 16b: Modal is visible`);
            } catch (modal_error) {
                console.log(`⚠️  Step 16b: Modal not found, continuing anyway: ${modal_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_0aad039e', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 16b: Using registry element_id: ID_0aad039e`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 16b: Registry lookup failed for element_id ID_0aad039e: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step16b_option_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_0aad039e: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 16b: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 16b: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 16b: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 16b: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 16b: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 16b: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 16b: Clicked option`);
                await page.screenshot({ path: 'storage/screenshots/pw_step16b_option.png' });
            } catch (e) {
                console.log(`❌ Step 16b: Failed to click option: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step16b_option_failed.png' });
                criticalFailures.push(`Step 16b: Click failed`);
            }
            
            // Step 17: Click dropdown
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 17: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 17: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 17: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Modal step - wait for modal and scope selector
            // Wait for modal to be visible
            try {
                const modal = page.locator('[role="dialog"], [data-testid="create-submission-dialog"]').first();
                await modal.waitFor({ state: 'visible', timeout: 10000 });
                console.log(`✅ Step 17: Modal is visible`);
            } catch (modal_error) {
                console.log(`⚠️  Step 17: Modal not found, continuing anyway: ${modal_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_d2542a0d', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 17: Using registry element_id: ID_d2542a0d`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 17: Registry lookup failed for element_id ID_d2542a0d: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step17_dropdown_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_d2542a0d: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 17: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 17: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 17: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 17: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 17: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 17: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 17: Clicked dropdown`);
                await page.screenshot({ path: 'storage/screenshots/pw_step17_dropdown.png' });
            } catch (e) {
                console.log(`❌ Step 17: Failed to click dropdown: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step17_dropdown_failed.png' });
                criticalFailures.push(`Step 17: Click failed`);
            }
            
            // Step 17b: Click option
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 17b: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 17b: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 17b: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Modal step - wait for modal and scope selector
            // Wait for modal to be visible
            try {
                const modal = page.locator('[role="dialog"], [data-testid="create-submission-dialog"]').first();
                await modal.waitFor({ state: 'visible', timeout: 10000 });
                console.log(`✅ Step 17b: Modal is visible`);
            } catch (modal_error) {
                console.log(`⚠️  Step 17b: Modal not found, continuing anyway: ${modal_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_23274a72', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 17b: Using registry element_id: ID_23274a72`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 17b: Registry lookup failed for element_id ID_23274a72: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step17b_option_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_23274a72: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                try {
                    await element.click();
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 17b: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            console.log(`✅ Step 17b: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 17b: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 17b: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 17b: Click failed, trying force click...`);
                        await element.click({ force: true });
                        console.log(`✅ Step 17b: Force click succeeded`);
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 17b: Clicked option`);
                await page.screenshot({ path: 'storage/screenshots/pw_step17b_option.png' });
            } catch (e) {
                console.log(`❌ Step 17b: Failed to click option: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step17b_option_failed.png' });
                criticalFailures.push(`Step 17b: Click failed`);
            }
            
            // Step 18: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 18: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 18: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 18: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Modal step - wait for modal
            try {
                const modal = page.locator('[role="dialog"], [data-testid="create-submission-dialog"]').first();
                await modal.waitFor({ state: 'visible', timeout: 10000 });
                console.log(`✅ Step 18: Modal is visible`);
            } catch (modal_error) {
                console.log(`⚠️  Step 18: Modal not found, continuing anyway: ${modal_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_d8cd705a', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 18: Using registry element_id: ID_d8cd705a`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 18: Registry lookup failed for element_id ID_d8cd705a: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step18_input_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_d8cd705a: ${registry_error}`);
                }
                // Replace ${TIMESTAMP} with actual timestamp value
                const fillValue = '${TIMESTAMP}'.replace('${TIMESTAMP}', TIMESTAMP);
                await element.fill(fillValue);
                console.log(`✅ Step 18: Filled input with ${fillValue}`);
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step18_input.png' });
            } catch (e) {
                console.log(`❌ Step 18: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step18_input_failed.png' });
                criticalFailures.push(`Step 18: Fill failed`);
            }
            
            // Step 19: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            // Ensure we're on the correct page before interacting with elements
            try {
                const currentPageUrl = page.url();
                const expectedUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions';
                // Normalize URLs for comparison (remove trailing slashes, query params)
                const normalizeUrl = (u: string) => u.split('?')[0].split('#')[0].replace(/\/$/, '');
                if (normalizeUrl(currentPageUrl) !== normalizeUrl(expectedUrl)) {
                    console.log(`⚠️  Step 19: Not on expected page. Current: ${currentPageUrl}, Expected: ${expectedUrl}. Navigating...`);
                    await page.goto(expectedUrl);
                    await page.waitForLoadState('networkidle');
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 19: Navigated to expected page: ${expectedUrl}`);
                }
            } catch (nav_error) {
                console.log(`⚠️  Step 19: Navigation check failed, continuing anyway: ${nav_error}`);
            }
            // Modal step - wait for modal and scope selector
            // Wait for modal to be visible
            try {
                const modal = page.locator('[role="dialog"], [data-testid="create-submission-dialog"]').first();
                await modal.waitFor({ state: 'visible', timeout: 10000 });
                console.log(`✅ Step 19: Modal is visible`);
            } catch (modal_error) {
                console.log(`⚠️  Step 19: Modal not found, continuing anyway: ${modal_error}`);
            }
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL (from row) for registry lookup - this is the page where element should be
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_d8409dab', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 19: Using registry element_id: ID_d8409dab`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 19: Registry lookup failed for element_id ID_d8409dab: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step19_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_d8409dab: ${registry_error}`);
                }
                // Wait for Create button to be enabled (form validation may disable it)
                // Wait up to 10 seconds for button to become enabled
                let buttonEnabled = false;
                for (let attempt = 0; attempt < 50; attempt++) {  // Wait up to 10 seconds (50 * 200ms)
                    try {
                        const isDisabled = await element.evaluate('el => el.disabled || el.hasAttribute("disabled")');
                        if (!isDisabled) {
                            buttonEnabled = true;
                            console.log(`✅ Step 19: Create button is enabled (attempt ${attempt + 1})`);
                            break;
                        } else {
                            if (attempt % 10 === 0) {  // Print every 2 seconds
                                console.log(`⏳ Step 19: Waiting for Create button to be enabled... (attempt ${attempt + 1}/50)`);
                            }
                        }
                    } catch (check_error) {
                        console.log(`⚠️  Step 19: Error checking button state: ${check_error}`);
                    }
                    await page.waitForTimeout(200);
                }
                
                if (!buttonEnabled) {
                    console.log(`⚠️  Step 19: Create button still disabled after 10 seconds, trying force click`);
                    // Scroll into view if needed
                    await element.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(500);
                    // Try force click as fallback
                    await element.click({ force: true });
                    console.log(`✅ Step 19: Clicked Create button with { force: true }`);
                } else {
                    // Scroll into view if needed
                    await element.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(500);  // Wait after scroll
                    // Robust click with fallbacks (JavaScript + force)
                    try {
                        await element.click();
                    } catch (click_error) {
                        if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                            console.log(`⚠️  Step 19: Click timeout, trying JavaScript click...`);
                            try {
                                await element.evaluate('el => el.click()');
                                console.log(`✅ Step 19: JavaScript click succeeded`);
                            } catch (js_error) {
                                console.log(`⚠️  Step 19: JavaScript click failed, trying force click...`);
                                await element.click({ force: true });
                                console.log(`✅ Step 19: Force click succeeded`);
                            }
                        } else {
                            console.log(`⚠️  Step 19: Click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 19: Force click succeeded`);
                        }
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 19: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step19_button.png' });
            } catch (e) {
                console.log(`❌ Step 19: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step19_button_failed.png' });
                criticalFailures.push(`Step 19: Click failed`);
            }
            

        if (criticalFailures.length > 0) {
            console.log(`\n❌ Test completed with ${criticalFailures.length} failure(s)`);
            for (const failure of criticalFailures) {
                console.log(`  - ${failure}`);
            }
            throw new Error("Test failed");
        } else {
            console.log("✅ Test completed successfully");
        }
    } catch (e) {
        console.log(`❌ Test failed: ${e}`);
        throw e;
    }
});
