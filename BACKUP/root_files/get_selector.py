#!/usr/bin/env python3
"""
Playwright Selector Generator Tool
Opens browser with Inspector to generate selectors for elements
"""
import asyncio
import sys
from playwright.async_api import async_playwright

async def main():
    if len(sys.argv) < 2:
        print("Usage: python get_selector.py <url>")
        print("\nExample:")
        print("  python get_selector.py https://hub-stage.datacommons.cancer.gov/")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("=" * 80)
    print("🎯 Playwright Selector Generator")
    print("=" * 80)
    print(f"\n🌐 Opening browser for: {url}")
    print("\n📋 INSTRUCTIONS:")
    print("  1. Browser will open in headed mode (visible)")
    print("  2. Navigate to the page")
    print("  3. Hover over any element")
    print("  4. Press Ctrl+Shift+C (or Cmd+Shift+C on Mac)")
    print("  5. Click on the element you want a selector for")
    print("  6. In the Console, type: $0")
    print("  7. Then type: playwright.$($0)")
    print("  8. Copy the suggested selector")
    print("\n💡 TIP: You can also use browser DevTools:")
    print("  - Right-click element → Inspect")
    print("  - In Console, type: playwright.$($0)")
    print("\n" + "=" * 80)
    
    async with async_playwright() as p:
        # Launch browser in HEADED mode (visible) with Inspector
        browser = await p.chromium.launch(
            headless=False,  # Visible browser
            slow_mo=1000  # Slow down actions so you can see them
        )
        
        # Create context with larger viewport
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Navigate to URL
        print(f"\n🚀 Navigating to: {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Dismiss popups if any
        try:
            continue_btn = page.locator("text='Continue'").first
            if await continue_btn.is_visible(timeout=2000):
                print("  ✅ Dismissing Continue popup")
                await continue_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Inject Playwright's console helper (full version)
        helper_script = """
            window.playwright = {
                $: function(element) {
                    if (!element) {
                        console.error('No element provided. Select an element first, then use: playwright.$($0)');
                        return null;
                    }
                    
                    const selectors = [];
                    const tag = element.tagName.toLowerCase();
                    
                    // Strategy 1: ID (most reliable)
                    if (element.id) {
                        selectors.push(`#${element.id}`);
                    }
                    
                    // Strategy 2: Text content (for links, buttons with visible text)
                    const text = element.textContent?.trim();
                    if (text && text.length > 0 && text.length < 100) {
                        const escapedText = text.replace(/'/g, "\\\\'").replace(/"/g, '\\\\"');
                        selectors.push(`text='${escapedText}'`);
                    }
                    
                    // Strategy 3: href attribute (for links)
                    if (element.href) {
                        try {
                            const url = new URL(element.href);
                            const path = url.pathname;
                            selectors.push(`a[href='${path}']`);
                        } catch(e) {
                            selectors.push(`a[href='${element.href}']`);
                        }
                    }
                    
                    // Strategy 4: name attribute
                    if (element.name) {
                        selectors.push(`${tag}[name='${element.name}']`);
                    }
                    
                    // Strategy 5: Role + aria-label
                    const role = element.getAttribute('role');
                    const ariaLabel = element.getAttribute('aria-label');
                    if (role && ariaLabel) {
                        selectors.push(`[role='${role}'][aria-label='${ariaLabel}']`);
                    }
                    
                    // Strategy 6: Class names (first 2 classes)
                    if (element.className && typeof element.className === 'string') {
                        const classes = element.className.split(' ').filter(c => c).slice(0, 2).join('.');
                        if (classes) {
                            selectors.push(`.${classes}`);
                        }
                    }
                    
                    // Strategy 7: Tag + text with has-text
                    if (text && text.length < 50) {
                        const escapedText = text.replace(/'/g, "\\\\'").substring(0, 30);
                        selectors.push(`${tag}:has-text('${escapedText}')`);
                    }
                    
                    // Strategy 8: Simple tag selector (fallback)
                    selectors.push(tag);
                    
                    // Show all suggestions
                    console.log('\\n🎯 Playwright Selector Suggestions:');
                    selectors.forEach((sel, idx) => {
                        console.log(`  ${idx + 1}. ${sel}`);
                    });
                    
                    // Return best selector
                    return selectors[0];
                }
            };
            
            console.log('✅ Playwright selector helper loaded!');
            console.log('💡 Usage:');
            console.log('   1. Select an element (right-click → Inspect)');
            console.log('   2. In Console, type: playwright.$($0)');
            console.log('   3. Press Enter - it will show selector suggestions');
            console.log('   4. Copy the selector you want');
        """
        await page.add_init_script(helper_script)
        
        print("\n✅ Browser is ready!")
        print("\n📝 HOW TO GET SELECTOR:")
        print("  1. Open browser DevTools (F12 or Right-click → Inspect)")
        print("  2. Click the 'Select element' tool (or press Ctrl+Shift+C / Cmd+Shift+C)")
        print("  3. Click on the element you want")
        print("  4. In Console tab, type: playwright.$($0)")
        print("  5. Press Enter - it will suggest a selector")
        print("  6. Copy the selector and use it in the registry")
        print("\n💡 ALTERNATIVE METHOD (if playwright.$ doesn't work):")
        print("  1. Right-click element → Inspect")
        print("  2. In Elements tab, right-click the highlighted element")
        print("  3. Copy → Copy selector (for CSS)")
        print("  4. Or use: $0.getAttribute('href') for links")
        print("\n⏸️  Browser will stay open. Press Ctrl+C in terminal to close.")
        print("=" * 80)
        
        # Keep browser open until user closes it
        try:
            await asyncio.sleep(3600)  # Keep open for 1 hour
        except KeyboardInterrupt:
            print("\n\n👋 Closing browser...")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

