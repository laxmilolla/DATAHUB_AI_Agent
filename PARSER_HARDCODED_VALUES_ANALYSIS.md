# Parser Hardcoded Values Analysis

**Analysis Date:** January 3, 2026  
**Files Analyzed:** 
- `utils/playwright_tree_parser.py`
- `api/routes.py` (parse-html route)
- `run_parser.py`

**Status:** Analysis Only - NO CODE CHANGES

---

## 🔴 Critical Hardcoded Values

### 1. **Timeouts & Delays**

#### In `api/routes.py` (parse-html route):
- **Line 314:** `timeout=30000` - Navigation timeout (30 seconds)
- **Line 315:** `await page.wait_for_timeout(3000)` - Fixed wait after navigation (3 seconds)
- **Line 323:** `timeout=2000` - Popup visibility check (2 seconds)
- **Line 325:** `await page.wait_for_timeout(1000)` - Wait after popup click (1 second)

#### In `utils/playwright_tree_parser.py`:
- **Line 210:** `timeout=2000` - Accordion click timeout (2 seconds)
- **Line 211:** `await self.page.wait_for_timeout(500)` - Wait after accordion click (500ms)
- **Line 242:** `timeout=1000` - Nested accordion click timeout (1 second)
- **Line 246:** `await self.page.wait_for_timeout(300)` - Wait after nested expansion (300ms)
- **Line 339:** `await self.page.wait_for_timeout(300)` - Wait during scrolling (300ms per step)
- **Line 349:** `await self.page.wait_for_timeout(500)` - Final wait after scrolling (500ms)

#### In `run_parser.py`:
- **Line 50:** `timeout=30000` - Navigation timeout (30 seconds)
- **Line 51:** `await page.wait_for_timeout(5000)` - Wait after navigation (5 seconds)
- **Line 59:** `timeout=2000` - Popup visibility check (2 seconds)
- **Line 62:** `await page.wait_for_timeout(1000)` - Wait after popup click (1 second)

**Impact:** These timeouts may be too short for slow networks or too long for fast ones. They're not configurable.

---

### 2. **Viewport Sizes**

#### In `api/routes.py`:
- **Line 308:** `viewport={'width': 1920, 'height': 1080}` - Fixed viewport size

#### In `run_parser.py`:
- **Line 44:** `viewport={'width': 1920, 'height': 1080}` - Fixed viewport size

**Impact:** Assumes desktop resolution. May miss elements on mobile/tablet views or different screen sizes.

---

### 3. **Browser Configuration**

#### In `api/routes.py`:
- **Line 306:** `browser = await p.chromium.launch(headless=True)` - Hardcoded to Chromium, headless mode

#### In `run_parser.py`:
- **Line 43:** `browser = await p.chromium.launch(headless=True)` - Hardcoded to Chromium, headless mode

**Impact:** Cannot test with Firefox/WebKit or in headed mode without code changes.

---

### 4. **Magic Numbers & Limits**

#### In `utils/playwright_tree_parser.py`:
- **Line 60:** `[:50]` - Truncates accordion text to 50 characters
- **Line 119:** `r'/(explore|home|dashboard|settings|profile|data)$'` - Hardcoded page name patterns
- **Line 122:** `return "home"` - Default page name fallback
- **Line 148:** `depth < 10` - Maximum depth for parent traversal (10 levels)
- **Line 162:** `.substring(0, 100)` - Truncates accordion text to 100 characters
- **Line 207:** `[:30]` - Truncates accordion text to 30 characters for selector
- **Line 240:** `[:10]` - Limits nested accordion expansion to 10 max
- **Line 337:** `for i in range(5):` - Scrolls 5 times (hardcoded scroll steps)
- **Line 404:** `maxDepth = 10` - Maximum recursion depth for nested tree building
- **Line 380:** `.substring(0, 100)` - Truncates text to 100 characters
- **Line 431:** `.substring(0, 100)` - Truncates child accordion text to 100 characters
- **Line 475:** `.substring(0, 150)` - Truncates checkbox label to 150 characters
- **Line 520:** `.substring(0, 150)` - Truncates checkbox label to 150 characters
- **Line 563:** `pos.get('x', 999) < 400` - Hardcoded X position threshold for sidebar detection (400px)
- **Line 593:** `[:30]` - Truncates text to 30 characters for selector
- **Line 626:** `[:100]` - Truncates checkbox label to 100 characters
- **Line 738:** `[:15]` - Limits button extraction to 15 buttons max
- **Line 751:** `[:50]` - Truncates button text to 50 characters
- **Line 784:** `[:10]` - Limits input extraction to 10 inputs max

**Impact:** These limits may cause elements to be missed or truncated incorrectly.

---

### 5. **Hardcoded Selectors**

#### In `api/routes.py`:
- **Line 322:** `page.locator("text='Continue'")` - Hardcoded popup dismissal selector

#### In `run_parser.py`:
- **Line 58:** `page.locator("text='Continue'")` - Hardcoded popup dismissal selector

#### In `utils/playwright_tree_parser.py`:
- **Line 135:** `'button[aria-expanded], [role="button"][aria-expanded]'` - Accordion selector
- **Line 205:** `f'button[id="{accordion_id}"]'` - Accordion by ID selector pattern
- **Line 207:** `f'button:has-text("{accordion_text[:30]}")'` - Accordion by text selector pattern
- **Line 230:** `f'#{accordion_id} + div button[aria-expanded="false"]'` - Nested accordion selector pattern
- **Line 274:** `f'#{accordion_id} + div'` - Content div selector pattern
- **Line 330:** `f'#{container_id}'` - Scrollable container selector pattern
- **Line 395:** `` `div[id="${accordion.id}"]:not([role="button"])` `` - Content div fallback selector
- **Line 410:** `'button[aria-expanded], [role="button"][aria-expanded]'` - Child accordion selector
- **Line 446:** `` `div[id="${childAccordion.id}"]:not([role="button"])` `` - Child content div selector
- **Line 455:** `'input[type="checkbox"], [role="checkbox"]'` - Checkbox selector
- **Line 500:** `'input[type="checkbox"], [role="checkbox"]'` - Root checkbox selector
- **Line 593:** `f"[role='button'][id='{node_id}']"` - Accordion selector pattern
- **Line 593:** `f"[role='button']:has-text('{text[:30]}')"` - Accordion fallback selector
- **Line 664:** `f"input[type='checkbox'][id='{cb_data.get('id')}']"` - Checkbox selector pattern
- **Line 681:** `'[role="tab"]'` - Tab selector
- **Line 710:** `f"//{tag}[@role='tab' and contains(normalize-space(.), '{tab_name}')]"` - Tab XPath pattern
- **Line 718:** `f"[role='tab']:has-text('{tab_name}')"` - Tab selector pattern
- **Line 735:** `'button:not([role="tab"]):not([aria-expanded])'` - Button selector (excluding tabs/accordions)
- **Line 762:** `f"button:has-text('{text}')"` - Button selector pattern
- **Line 781:** `'input:not([type="checkbox"])'` - Input selector (excluding checkboxes)
- **Line 807:** `f"input[type='{attrs.get('type')}']"` - Input selector pattern
- **Line 827:** `'table'` - Table selector
- **Line 862:** `f"(//table)[{table_idx + 1}]"` - Table XPath pattern
- **Line 883:** `f"(//table)[{table_idx + 1}]//thead//th[{col_index + 1}]"` - Table column XPath pattern
- **Line 885:** `f"table thead th:nth-child({col_index + 1})"` - Table column selector pattern

**Impact:** These selectors assume specific HTML structure. May break if website structure changes.

---

### 6. **Hardcoded Text Strings**

#### In `utils/playwright_tree_parser.py`:
- **Line 60:** `'Unknown'` - Default accordion text
- **Line 88:** `'⚠️  No elements found in this branch'` - Warning message
- **Line 102:** `"version": "5.0_branch"` - Hardcoded version string
- **Line 103:** `"parser_type": "playwright_tree_branch_by_branch"` - Hardcoded parser type
- **Line 122:** `return "home"` - Default page name
- **Line 193:** `'Unknown'` - Default accordion text
- **Line 219:** `'✅ Already expanded'` - Status message
- **Line 250:** `'✅ No nested accordions to expand'` - Status message
- **Line 312:** `'✅ No scrollable containers found'` - Status message
- **Line 341:** `'✅ Scrolled to bottom'` - Status message
- **Line 542:** `'⚠️  Failed to build tree for this branch'` - Error message
- **Line 564:** `"sidebar-filters"` - Location type string
- **Line 564:** `"main-content"` - Location type string
- **Line 568:** `f"{text} accordion nested in {parent_name.split(' accordion')[0]} ({location_desc})"` - Element name pattern
- **Line 570:** `f"{text} accordion ({location_desc})"` - Element name pattern
- **Line 588:** `"filter-accordion"` - Semantic type string
- **Line 588:** `"content-accordion"` - Semantic type string
- **Line 644:** `f"{label} checkbox (filter)"` - Checkbox name pattern
- **Line 660:** `"filter-checkbox"` - Semantic type string
- **Line 704:** `"main content area"` - Location string
- **Line 704:** `"top navigation"` - Location string
- **Line 706:** `f"{text} tab ({location})"` - Tab name pattern
- **Line 716:** `"role_plus_text_partial"` - Uniqueness method string
- **Line 754:** `f"{text} button"` - Button name pattern
- **Line 799:** `'input'` - Default input name
- **Line 852:** `f"data table {table_count}"` - Table name pattern
- **Line 859:** `"data-table"` - Semantic type string
- **Line 874:** `f"{col_text} column (table {table_count})"` - Column name pattern
- **Line 878:** `"data-column"` - Semantic type string
- **Line 884:** `"positional"` - Uniqueness method string

**Impact:** These strings are used for element naming and classification. Changes to naming conventions require code changes.

---

### 7. **Hardcoded URLs & Domains**

#### In `run_parser.py`:
- **Line 35:** `url = 'https://clinicalcommons.ccdi.cancer.gov/explore'` - Hardcoded test URL
- **Line 91:** `domain = 'clinicalcommons.ccdi.cancer.gov'` - Hardcoded domain
- **Line 92:** `page_name = 'explore'` - Hardcoded page name

**Impact:** Script is tied to a specific website. Cannot be used for other sites without modification.

---

### 8. **Hardcoded Page Name Patterns**

#### In `utils/playwright_tree_parser.py`:
- **Line 119:** `r'/(explore|home|dashboard|settings|profile|data)$'` - Regex pattern for page name extraction

**Impact:** Only recognizes these specific page names. Other page names default to "home".

---

### 9. **Hardcoded Location Detection Logic**

#### In `utils/playwright_tree_parser.py`:
- **Line 563:** `location = "sidebar-filters" if pos.get('x', 999) < 400 else "main-content"` - X position threshold of 400px
- **Line 704:** `location = "main content area" if box and box['y'] > 200 else "top navigation"` - Y position threshold of 200px

**Impact:** Assumes specific layout. May misclassify elements if page layout changes.

---

### 10. **Hardcoded Scroll Behavior**

#### In `utils/playwright_tree_parser.py`:
- **Line 337:** `for i in range(5):` - Scrolls exactly 5 times
- **Line 338:** `el.scrollTop = el.scrollHeight` - Scrolls to bottom each time
- **Line 339:** `await self.page.wait_for_timeout(300)` - 300ms wait between scrolls

**Impact:** May not be sufficient for pages with many lazy-loaded items. Not adaptive to content size.

---

### 11. **Hardcoded Element Type Detection**

#### In `utils/playwright_tree_parser.py`:
- **Line 381:** `type: 'accordion'` - Hardcoded type
- **Line 432:** `type: 'accordion'` - Hardcoded type
- **Line 483:** `type: 'checkbox'` - Hardcoded type
- **Line 528:** `type: 'checkbox'` - Hardcoded type
- **Line 587:** `"type": "accordion"` - Hardcoded type
- **Line 659:** `"type": "checkbox"` - Hardcoded type
- **Line 713:** `"type": "tab"` - Hardcoded type
- **Line 758:** `"type": "button"` - Hardcoded type
- **Line 804:** `"type": "input"` - Hardcoded type
- **Line 858:** `"type": "table"` - Hardcoded type
- **Line 878:** `"type": "table_column"` - Hardcoded type

**Impact:** Element types are hardcoded strings. Adding new types requires code changes.

---

### 12. **Hardcoded Checkbox Label Extraction Patterns**

#### In `utils/playwright_tree_parser.py`:
- **Line 468:** `cb.closest('li')` - Looks for `<li>` parent
- **Line 468:** `cb.closest('div[class*="item"]')` - Looks for div with "item" in class
- **Line 513:** `cb.closest('li')` - Same pattern repeated
- **Line 513:** `cb.closest('div[class*="item"]')` - Same pattern repeated
- **Line 632:** `cb_id.startswith('checkbox_')` - Assumes checkbox ID pattern
- **Line 634:** `parts = cb_id.replace('checkbox_', '', 1).split('_', 1)` - Assumes ID format

**Impact:** Assumes specific HTML structure for checkbox labels. May fail on different structures.

---

### 13. **Hardcoded Tab Name Extraction**

#### In `utils/playwright_tree_parser.py`:
- **Line 701:** `tab_name = text.split('(')[0].strip() if '(' in text else text` - Removes count from tab name (e.g., "Diagnosis(28,944)" → "Diagnosis")

**Impact:** Assumes tabs have count in parentheses. May break if format changes.

---

## 📊 Summary Statistics

| Category | Count | Files Affected |
|----------|-------|----------------|
| Timeouts/Delays | 12 | 3 files |
| Viewport Sizes | 2 | 2 files |
| Browser Config | 2 | 2 files |
| Magic Numbers | 25+ | 1 file |
| Selectors | 30+ | 1 file |
| Text Strings | 40+ | 1 file |
| URLs/Domains | 3 | 1 file |
| Location Logic | 2 | 1 file |
| Scroll Behavior | 3 | 1 file |

**Total Hardcoded Values:** 100+ instances

---

## ⚠️ Risk Assessment

### **High Risk:**
1. **Timeouts** - May cause failures on slow networks
2. **Viewport size** - May miss mobile/tablet elements
3. **Selectors** - May break if website structure changes
4. **Magic numbers** - Limits may cause missed elements

### **Medium Risk:**
1. **Browser config** - Cannot test with other browsers
2. **Location detection** - May misclassify elements
3. **Scroll behavior** - May miss lazy-loaded content

### **Low Risk:**
1. **Text strings** - Mostly cosmetic, but affects element naming
2. **Version strings** - No functional impact

---

## 💡 Recommendations (For Future Consideration)

1. **Make timeouts configurable** via environment variables or config file
2. **Make viewport configurable** or detect from page
3. **Support multiple browsers** via configuration
4. **Make limits configurable** (max depth, max elements, etc.)
5. **Extract selectors to constants** or config file
6. **Make location detection adaptive** based on page analysis
7. **Make scroll behavior adaptive** based on content size
8. **Support custom page name patterns** via configuration

---

**Document Version:** 1.0  
**Analysis Date:** January 3, 2026  
**Status:** Analysis Complete - NO CODE CHANGES MADE






