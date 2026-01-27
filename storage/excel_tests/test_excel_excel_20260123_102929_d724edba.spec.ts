/*Excel-Generated Playwright Test
Generated from: excel_20260123_102929_d724edba.xlsx*/

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
    console.log(`   Please create a .env file with TOTP_SECRET_KEY_TS=your_secret_key (TypeScript tests use TOTP_SECRET_KEY_TS, different from Python's TOTP_SECRET_KEY)`);
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
    'element_maps/auth.nih.gov/LoginMFA_page.json',
    'element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json',
    'element_maps/hub-stage.datacommons.cancer.gov/home_page.json',
    'element_maps/ras.nih.gov/consent_page.json',
    'element_maps/secure.login.gov/home_page.json',
    'element_maps/secure.login.gov/sms_page.json',
];

// Load registries per domain/page (for dynamic loading based on current page)
// NO MERGE: Keep registries separate to avoid conflicts when same element name exists in multiple registries
const REGISTRIES_BY_PATH: { [key: string]: any } = {};  // registry_path -> registryData
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

for (const registryPathStr of REGISTRY_PATHS) {
    try {
        let registryPath: string | null = null;
        const checkedPaths: string[] = [];
        
        // Try each possible root location
        for (const root of possibleRoots) {
            const candidatePath = path.join(root, registryPathStr);
            checkedPaths.push(candidatePath);
            if (fs.existsSync(candidatePath)) {
                registryPath = candidatePath;
                break;
            }
        }
        
        if (registryPath) {
            const registryData = JSON.parse(fs.readFileSync(registryPath, 'utf-8'));
            // Store per-path for dynamic loading (NO MERGE - prevents conflicts)
            REGISTRIES_BY_PATH[registryPathStr] = registryData;
            loadedCount++;
            console.log(`✅ Loaded registry: ${Object.keys(registryData.elements || {}).length} elements from ${path.basename(registryPathStr)}`);
        } else {
            console.log(`⚠️  Registry file not found: ${registryPathStr} (checked: ${checkedPaths.join(', ')})`);
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
            // Optional step - continue if element not found
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
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
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 2: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 2: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 2: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 2: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 2: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 2: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 2: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 2: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 2: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step2_button.png' });
            } catch (e) {
                console.log(`ℹ️  Step 2: Element not found (optional) - continuing`);
            }
            
            // Step 3: Click link
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
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
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 3: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 3: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 3: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 3: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 3: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 3: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 3: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 3: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 3: Clicked link`);
                // Next step is on different URL - wait for navigation to complete
                try {
                    await page.waitForLoadState('networkidle', { timeout: 15000 });
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 3: Navigation completed to ${page.url()}`);
                } catch (nav_error) {
                    console.log(`⚠️  Step 3: Navigation wait timeout (page may have already navigated): ${nav_error}`);
                }
                await page.screenshot({ path: 'storage/screenshots/pw_step3_link.png' });
            } catch (e) {
                console.log(`❌ Step 3: Failed to click link: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step3_link_failed.png' });
                criticalFailures.push(`Step 3: Click failed`);
            }
            
            // Step 4: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://auth.nih.gov/CertAuthV3/forms/nihl/LoginMFA.aspx' || page.url();
                    const xpath = getXpathById('ID_c20d27bc', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 4: Using registry element_id: ID_c20d27bc`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 4: Registry lookup failed for element_id ID_c20d27bc: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step4_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_c20d27bc: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 4: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 4: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 4: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 4: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 4: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 4: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 4: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 4: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 4: Clicked button`);
                // Next step is on different URL - wait for navigation to complete
                try {
                    await page.waitForLoadState('networkidle', { timeout: 15000 });
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 4: Navigation completed to ${page.url()}`);
                } catch (nav_error) {
                    console.log(`⚠️  Step 4: Navigation wait timeout (page may have already navigated): ${nav_error}`);
                }
                await page.screenshot({ path: 'storage/screenshots/pw_step4_button.png' });
            } catch (e) {
                console.log(`❌ Step 4: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step4_button_failed.png' });
                criticalFailures.push(`Step 4: Click failed`);
            }
            
            // Step 5: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
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
                await element.fill('qualityassurance2.crdc@gmail.com');
                console.log(`✅ Step 5: Filled input with qualityassurance2.crdc@gmail.com`);
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step5_input.png' });
            } catch (e) {
                console.log(`❌ Step 5: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step5_input_failed.png' });
                criticalFailures.push(`Step 5: Fill failed`);
            }
            
            // Step 6: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
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
                await element.fill('Aryan@nih123');
                console.log(`✅ Step 6: Filled input with Aryan@nih123`);
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step6_input.png' });
            } catch (e) {
                console.log(`❌ Step 6: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step6_input_failed.png' });
                criticalFailures.push(`Step 6: Fill failed`);
            }
            
            // Step 7: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
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
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 7: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 7: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 7: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 7: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 7: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 7: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 7: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 7: All click methods failed`);
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
                // Generate TOTP code using Python script (pyotp) - same as Python tests
                try {
                    const { execSync } = require('child_process');
                    const path = require('path');
                    const fs = require('fs');
                    
                    // Find generate_totp.py script (check multiple locations)
                    const testFileDir = __dirname;
                    const possibleScriptLocations = [
                        path.join(testFileDir, 'generate_totp.py'),  // Same directory as test file
                        path.join(path.dirname(testFileDir), 'generate_totp.py'),  // Parent directory
                        path.join(testFileDir, '..', '..', 'Test', 'generate_totp.py'),  // Test directory
                    ];
                    
                    let scriptPath = null;
                    for (const loc of possibleScriptLocations) {
                        if (fs.existsSync(loc)) {
                            scriptPath = loc;
                            break;
                        }
                    }
                    
                    if (!scriptPath) {
                        throw new Error('generate_totp.py script not found. Checked: ' + possibleScriptLocations.join(', '));
                    }
                    
                    // TOTP key is unique per user - lookup key for this email/username
                    const userEmail = 'Aryan@nih123';
                    const emailSanitized = userEmail.replace(/[@.]/g, '_').toUpperCase();
                    // Try user-specific key first: TOTP_SECRET_KEY_TS_<EMAIL>, then fallback to generic keys
                    const secretKey = process.env[`TOTP_SECRET_KEY_TS_${emailSanitized}`] || process.env.TOTP_SECRET_KEY_TS || process.env.TOTP_SECRET_KEY;
                    if (!secretKey) {
                        throw new Error(`TOTP_SECRET_KEY_TS_${emailSanitized} (or TOTP_SECRET_KEY_TS or TOTP_SECRET_KEY) not found in environment variables for user: ${userEmail}`);
                    }
                    console.log(`🔐 Step 8: Using TOTP key for user: ${userEmail}`);
                    // Pass secret key to Python script
                    const totpCode = execSync(`python3 ${scriptPath} ${secretKey}`, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
                    console.log(`🔐 Step 8: Generated TOTP code using pyotp (Python): ${totpCode.substring(0, 2)}****`);
                    
                    // For TOTP: clear field first, then use type() with delay (more reliable than fill())
                    await element.fill('');
                    await element.type(totpCode, { delay: 10 });
                    await page.waitForTimeout(200);
                    console.log(`✅ Step 8: Filled TOTP code using type() method`);
                } catch (e) {
                    console.log(`❌ Step 8: Failed to generate/fill TOTP code: ${e}`);
                    throw e;
                }
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step8_input.png' });
            } catch (e) {
                console.log(`❌ Step 8: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step8_input_failed.png' });
                criticalFailures.push(`Step 8: Fill failed`);
            }
            
            // Step 9: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://secure.login.gov/login/two_factor/sms' || page.url();
                    const xpath = getXpathById('ID_fcabe4f4', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 9: Using registry element_id: ID_fcabe4f4`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 9: Registry lookup failed for element_id ID_fcabe4f4: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step9_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_fcabe4f4: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 9: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 9: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 9: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 9: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 9: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 9: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 9: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 9: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 9: Clicked button`);
                // Next step is on different URL - wait for navigation to complete
                try {
                    await page.waitForLoadState('networkidle', { timeout: 15000 });
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 9: Navigation completed to ${page.url()}`);
                } catch (nav_error) {
                    console.log(`⚠️  Step 9: Navigation wait timeout (page may have already navigated): ${nav_error}`);
                }
                await page.screenshot({ path: 'storage/screenshots/pw_step9_button.png' });
            } catch (e) {
                console.log(`❌ Step 9: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step9_button_failed.png' });
                criticalFailures.push(`Step 9: Click failed`);
            }
            
            // Step 10: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://ras.nih.gov/auth/oauth/v2/authorize/consent' || page.url();
                    const xpath = getXpathById('ID_grant_button_consent', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 10: Using registry element_id: ID_grant_button_consent`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 10: Registry lookup failed for element_id ID_grant_button_consent: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step10_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_grant_button_consent: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 10: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 10: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 10: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 10: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 10: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 10: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 10: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 10: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 10: Clicked button`);
                // Next step is on different URL - wait for navigation to complete
                try {
                    await page.waitForLoadState('networkidle', { timeout: 15000 });
                    await page.waitForLoadState('domcontentloaded');
                    console.log(`✅ Step 10: Navigation completed to ${page.url()}`);
                } catch (nav_error) {
                    console.log(`⚠️  Step 10: Navigation wait timeout (page may have already navigated): ${nav_error}`);
                }
                await page.screenshot({ path: 'storage/screenshots/pw_step10_button.png' });
            } catch (e) {
                console.log(`❌ Step 10: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step10_button_failed.png' });
                criticalFailures.push(`Step 10: Click failed`);
            }
            
            // Step 11: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_1bcedbdb', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 11: Using registry element_id: ID_1bcedbdb`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 11: Registry lookup failed for element_id ID_1bcedbdb: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step11_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_1bcedbdb: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 11: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 11: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 11: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 11: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 11: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 11: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 11: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 11: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 11: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step11_button.png' });
            } catch (e) {
                console.log(`❌ Step 11: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step11_button_failed.png' });
                criticalFailures.push(`Step 11: Click failed`);
            }
            
            // Step 12: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_9bc56a38', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 12: Using registry element_id: ID_9bc56a38`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 12: Registry lookup failed for element_id ID_9bc56a38: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step12_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_9bc56a38: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 12: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 12: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 12: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 12: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 12: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 12: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 12: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 12: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 12: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step12_button.png' });
            } catch (e) {
                console.log(`❌ Step 12: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step12_button_failed.png' });
                criticalFailures.push(`Step 12: Click failed`);
            }
            
            // Step 13: Click dropdown
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_988a2a2e', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 13: Using registry element_id: ID_988a2a2e`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 13: Registry lookup failed for element_id ID_988a2a2e: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step13_dropdown_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_988a2a2e: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 13: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 13: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 13: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 13: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 13: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 13: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 13: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 13: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 13: Clicked dropdown`);
                await page.screenshot({ path: 'storage/screenshots/pw_step13_dropdown.png' });
            } catch (e) {
                console.log(`❌ Step 13: Failed to click dropdown: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step13_dropdown_failed.png' });
                criticalFailures.push(`Step 13: Click failed`);
            }
            
            // Step 14: Click option
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_7824b1a8', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 14: Using registry element_id: ID_7824b1a8`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 14: Registry lookup failed for element_id ID_7824b1a8: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step14_option_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_7824b1a8: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 14: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 14: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 14: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 14: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 14: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 14: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 14: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 14: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 14: Clicked option`);
                await page.screenshot({ path: 'storage/screenshots/pw_step14_option.png' });
            } catch (e) {
                console.log(`❌ Step 14: Failed to click option: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step14_option_failed.png' });
                criticalFailures.push(`Step 14: Click failed`);
            }
            
            // Step 15: Click dropdown
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_7011a92f', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 15: Using registry element_id: ID_7011a92f`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 15: Registry lookup failed for element_id ID_7011a92f: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step15_dropdown_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_7011a92f: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 15: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 15: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 15: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 15: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 15: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 15: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 15: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 15: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 15: Clicked dropdown`);
                await page.screenshot({ path: 'storage/screenshots/pw_step15_dropdown.png' });
            } catch (e) {
                console.log(`❌ Step 15: Failed to click dropdown: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step15_dropdown_failed.png' });
                criticalFailures.push(`Step 15: Click failed`);
            }
            
            // Step 16: Click option
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_383e84d1', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 16: Using registry element_id: ID_383e84d1`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 16: Registry lookup failed for element_id ID_383e84d1: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step16_option_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_383e84d1: ${registry_error}`);
                }
                // Scroll into view if needed
                try {
                    await element.scrollIntoViewIfNeeded();
                } catch {
                    // Continue if scroll fails
                }
                await page.waitForTimeout(500);  // Wait after scroll
                // Robust click with fallbacks (JavaScript + force)
                let clickSucceeded = false;
                try {
                    await element.click();
                    clickSucceeded = true;
                    console.log(`✅ Step 16: Click succeeded`);
                } catch (click_error) {
                    if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                        console.log(`⚠️  Step 16: Click timeout, trying JavaScript click...`);
                        try {
                            await element.evaluate('el => el.click()');
                            clickSucceeded = true;
                            console.log(`✅ Step 16: JavaScript click succeeded`);
                        } catch (js_error) {
                            console.log(`⚠️  Step 16: JavaScript click failed, trying force click...`);
                            await element.click({ force: true });
                            clickSucceeded = true;
                            console.log(`✅ Step 16: Force click succeeded`);
                        }
                    } else {
                        console.log(`⚠️  Step 16: Click failed, trying force click...`);
                        await element.click({ force: true });
                        clickSucceeded = true;
                        console.log(`✅ Step 16: Force click succeeded`);
                    }
                }
                if (!clickSucceeded) {
                    throw new Error(`Step 16: All click methods failed`);
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 16: Clicked option`);
                await page.screenshot({ path: 'storage/screenshots/pw_step16_option.png' });
            } catch (e) {
                console.log(`❌ Step 16: Failed to click option: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step16_option_failed.png' });
                criticalFailures.push(`Step 16: Click failed`);
            }
            
            // Step 17: Fill input
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_3c797626', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 17: Using registry element_id: ID_3c797626`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 17: Registry lookup failed for element_id ID_3c797626: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step17_input_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_3c797626: ${registry_error}`);
                }
                // Replace ${TIMESTAMP} with actual timestamp value
                const fillValue = '${TIMESTAMP}'.replace('${TIMESTAMP}', TIMESTAMP);
                await element.fill(fillValue);
                console.log(`✅ Step 17: Filled input with ${fillValue}`);
                await page.waitForTimeout(500);  // Wait after fill
                await page.screenshot({ path: 'storage/screenshots/pw_step17_input.png' });
            } catch (e) {
                console.log(`❌ Step 17: Failed to fill input: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step17_input_failed.png' });
                criticalFailures.push(`Step 17: Fill failed`);
            }
            
            // Step 18: Click button
            await page.waitForTimeout(3000);  // Wait 3 seconds before step
            try {
                let element;
                // Try registry lookup first
                try {
                    // Use Excel URL for registry lookup (where element should be), fallback to page.url()
                    const lookupUrl = 'https://hub-stage.datacommons.cancer.gov/data-submissions' || page.url();
                    const xpath = getXpathById('ID_fd60dbc8', lookupUrl);
                    const selector = `xpath=${xpath}`;
                    element = page.locator(selector).nth(0);
                    await element.waitFor({ state: 'visible', timeout: 10000 });
                    console.log(`✅ Step 18: Using registry element_id: ID_fd60dbc8`);
                } catch (registry_error) {
                    // Registry lookup failed - test must fail
                    console.log(`❌ Step 18: Registry lookup failed for element_id ID_fd60dbc8: ${registry_error}`);
                    await page.screenshot({ path: 'storage/screenshots/pw_step18_button_registry_failed.png' });
                    throw new Error(`Registry lookup failed for element_id ID_fd60dbc8: ${registry_error}`);
                }
                // Wait for Create button to be enabled (form validation may disable it)
                // Wait up to 10 seconds for button to become enabled
                let buttonEnabled = false;
                for (let attempt = 0; attempt < 50; attempt++) {  // Wait up to 10 seconds (50 * 200ms)
                    try {
                        const isDisabled = await element.evaluate('el => el.disabled || el.hasAttribute("disabled")');
                        if (!isDisabled) {
                            buttonEnabled = true;
                            console.log(`✅ Step 18: Create button is enabled (attempt ${attempt + 1})`);
                            break;
                        } else {
                            if (attempt % 10 === 0) {  // Print every 2 seconds
                                console.log(`⏳ Step 18: Waiting for Create button to be enabled... (attempt ${attempt + 1}/50)`);
                            }
                        }
                    } catch (check_error) {
                        console.log(`⚠️  Step 18: Error checking button state: ${check_error}`);
                    }
                    await page.waitForTimeout(200);
                }
                
                if (!buttonEnabled) {
                    console.log(`⚠️  Step 18: Create button still disabled after 10 seconds, trying force click`);
                    // Scroll into view if needed
                    await element.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(500);
                    // Try force click as fallback
                    await element.click({ force: true });
                    console.log(`✅ Step 18: Clicked Create button with { force: true }`);
                } else {
                    // Scroll into view if needed
                    await element.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(500);  // Wait after scroll
                    // Robust click with fallbacks (JavaScript + force)
                    try {
                        await element.click();
                    } catch (click_error) {
                        if (click_error.toString().toLowerCase().includes('timeout') || click_error.toString().includes('Timeout')) {
                            console.log(`⚠️  Step 18: Click timeout, trying JavaScript click...`);
                            try {
                                await element.evaluate('el => el.click()');
                                console.log(`✅ Step 18: JavaScript click succeeded`);
                            } catch (js_error) {
                                console.log(`⚠️  Step 18: JavaScript click failed, trying force click...`);
                                await element.click({ force: true });
                                console.log(`✅ Step 18: Force click succeeded`);
                            }
                        } else {
                            console.log(`⚠️  Step 18: Click failed, trying force click...`);
                            await element.click({ force: true });
                            console.log(`✅ Step 18: Force click succeeded`);
                        }
                    }
                }
                await page.waitForTimeout(1000);  // Wait after click
                console.log(`✅ Step 18: Clicked button`);
                await page.screenshot({ path: 'storage/screenshots/pw_step18_button.png' });
            } catch (e) {
                console.log(`❌ Step 18: Failed to click button: ${e}`);
                await page.screenshot({ path: 'storage/screenshots/pw_step18_button_failed.png' });
                criticalFailures.push(`Step 18: Click failed`);
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
