// Playwright Selector Helper for Browser Console
// Copy and paste this entire code into browser DevTools Console
// Then you can use: playwright.$($0)

(function() {
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
                // Escape quotes in text
                const escapedText = text.replace(/'/g, "\\'").replace(/"/g, '\\"');
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
                const escapedText = text.replace(/'/g, "\\'").substring(0, 30);
                selectors.push(`${tag}:has-text('${escapedText}')`);
            }
            
            // Strategy 8: Simple tag selector (fallback)
            selectors.push(tag);
            
            // Return all suggestions
            console.log('\n🎯 Playwright Selector Suggestions:');
            selectors.forEach((sel, idx) => {
                console.log(`  ${idx + 1}. ${sel}`);
            });
            
            // Return best selector (prefer ID, then text, then href)
            return selectors[0];
        }
    };
    
    console.log('✅ Playwright selector helper loaded!');
    console.log('💡 Usage:');
    console.log('   1. Select an element (right-click → Inspect)');
    console.log('   2. In Console, type: playwright.$($0)');
    console.log('   3. Press Enter - it will show selector suggestions');
    console.log('   4. Copy the selector you want');
})();


