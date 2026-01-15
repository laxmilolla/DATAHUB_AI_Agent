# Parser File Usage Documentation

**Generated:** January 3, 2026  
**Analysis Date:** January 3, 2026 19:23:50  
**Execution Method:** Web UI Parser (`/parser` route)

---

## 🔗 Links & URLs

### Web Interface
- **Parser Page:** `http://13.222.91.163:5000/parser`
- **API Endpoint:** `http://13.222.91.163:5000/api/parse-html` (POST)
- **Save Endpoint:** `http://13.222.91.163:5000/api/save-element-map` (POST)
- **Registry API:** `http://13.222.91.163:5000/api/parser/registry` (GET/PUT)

### Parsed URLs
- **Target URL:** `https://clinicalcommons.ccdi.cancer.gov/explore` (or user-provided URL)
- **Domain:** `clinicalcommons.ccdi.cancer.gov` / `ccdi.cancer.gov`
- **Page Name:** `explore`

---

## 📁 Files Used During Parser Execution

### 1. **Entry Point - API Route Handler**

**File:** `api/routes.py`  
**Size:** 33 KB  
**Last Modified:** January 3, 2026 18:40  
**Location:** `/home/ubuntu/DATAHUB_AI_Agent/api/routes.py`

**Functions Used:**
- `parse_html()` - Main route handler for `/api/parse-html`
- `parse_with_playwright()` - Async function that orchestrates browser and parsing

**Imports:**
```python
from flask import Blueprint, request, jsonify, current_app
from playwright.async_api import async_playwright
from utils.playwright_tree_parser import parse_with_tree
```

**Responsibilities:**
- Receives POST request with URL and page name
- Launches Playwright browser
- Navigates to target URL
- Calls parser function
- Returns JSON response with element map

---

### 2. **Core Parser - Tree-Based DOM Parser**

**File:** `utils/playwright_tree_parser.py`  
**Size:** 38 KB  
**Last Modified:** January 2, 2026 20:52  
**Location:** `/home/ubuntu/DATAHUB_AI_Agent/utils/playwright_tree_parser.py`

**Classes:**
- `PlaywrightTreeParser` - Main parser class

**Key Functions:**
- `parse_with_tree(page)` - Entry point function
- `PlaywrightTreeParser.parse()` - Main parsing logic
- `PlaywrightTreeParser._find_top_level_accordions()` - Finds accordion elements
- `PlaywrightTreeParser._expand_accordion_branch()` - Expands accordions
- `PlaywrightTreeParser._scroll_to_load_all()` - Handles lazy loading
- `PlaywrightTreeParser._parse_branch()` - Parses individual branches

**Imports:**
```python
from utils.xpath_builder import XPathBuilder
from playwright.async_api import Page
```

**Responsibilities:**
- Builds hierarchical DOM tree using JavaScript
- Expands accordions branch-by-branch
- Extracts interactive elements (accordions, checkboxes, tabs, buttons)
- Handles virtual scrolling and lazy loading
- Creates parent-child relationships

---

### 3. **XPath Builder - Selector Generation**

**File:** `utils/xpath_builder.py`  
**Size:** 28 KB  
**Last Modified:** December 31, 2025 22:11  
**Location:** `/home/ubuntu/DATAHUB_AI_Agent/utils/xpath_builder.py`

**Classes:**
- `XPathBuilder` - Generates XPath selectors for elements

**Key Functions:**
- `build_xpath()` - Main XPath generation
- `register_xpath()` - Registers XPath for element

**Evidence from Logs:**
```
INFO:utils.xpath_builder:✅ XPath registered: CREATE COHORT button
INFO:utils.xpath_builder:   Method: text_only
INFO:utils.xpath_builder:   XPath: //button[normalize-space(.)='CREATE COHORT']
```

**Responsibilities:**
- Generates XPath selectors for discovered elements
- Handles duplicate elements with positional XPaths
- Falls back to different XPath strategies (ID, text, positional)
- Registers XPaths in element registry

---

### 4. **Element Registry - Storage & Management**

**File:** `utils/element_registry.py`  
**Size:** 15 KB  
**Last Modified:** January 2, 2026 19:16  
**Location:** `/home/ubuntu/DATAHUB_AI_Agent/utils/element_registry.py`

**Classes:**
- `ElementRegistry` - Manages element maps

**Key Functions:**
- `get_registry()` - Singleton function to get registry instance
- `ElementRegistry.save_map()` - Saves parsed elements to JSON
- `ElementRegistry.load_map()` - Loads existing element maps
- `ElementRegistry.get_map_path()` - Generates file paths

**File Structure:**
```
element_maps/
  └── clinicalcommons.ccdi.cancer.gov/
      └── explore_page.json
```

**Responsibilities:**
- Stores parsed elements in JSON format
- Manages element map files by domain/page
- Provides caching for loaded maps
- Handles versioning and timestamps

---

## 🔄 Execution Flow

```
1. User accesses: http://13.222.91.163:5000/parser
   ↓
2. User submits URL via web form
   ↓
3. POST /api/parse-html
   ↓
4. api/routes.py::parse_html()
   ├─ Launches Playwright browser
   ├─ Navigates to target URL
   └─ Calls parse_with_tree()
      ↓
5. utils/playwright_tree_parser.py::parse_with_tree()
   ├─ Creates PlaywrightTreeParser instance
   └─ Calls parser.parse()
      ↓
6. utils/playwright_tree_parser.py::PlaywrightTreeParser.parse()
   ├─ Finds top-level accordions
   ├─ Expands each branch
   ├─ Parses elements using JavaScript
   └─ Uses XPathBuilder for selectors
      ↓
7. utils/xpath_builder.py::XPathBuilder
   ├─ Generates XPath for each element
   └─ Registers XPath in registry
      ↓
8. utils/element_registry.py::ElementRegistry.save_map()
   ├─ Saves to element_maps/{domain}/{page}_page.json
   └─ Updates cache
      ↓
9. api/routes.py returns JSON response
   ↓
10. POST /api/save-element-map (saves to registry)
```

---

## 📊 Dependencies

### Direct Dependencies
- `playwright` - Browser automation library
- `flask` - Web framework
- Python standard library: `json`, `asyncio`, `pathlib`, `sys`, `datetime`

### Internal Dependencies
- `utils.xpath_builder` ← Used by `playwright_tree_parser.py`
- `utils.element_registry` ← Used by `routes.py` (for saving)
- `utils.playwright_tree_parser` ← Used by `routes.py`

---

## 📝 Related Files (Not Directly Used in This Execution)

### Imported but Not Used
- `utils/html_parser.py` - Alternative HTML parser (imported in routes.py but not used)
- `agent/bedrock_playwright_agent.py` - AI agent (imported but not used for parsing)

### Supporting Files
- `web/templates/parser.html` - Frontend UI template
- `web/static/js/parser.js` - Frontend JavaScript
- `web/static/js/tree_viewer.js` - Tree viewer functionality
- `web/static/css/style.css` - Styling

---

## 🎯 Key Insights

1. **Parser Architecture:** Branch-by-branch traversal approach (one accordion at a time)
2. **XPath Strategy:** Multiple fallback strategies (ID → text → positional)
3. **Storage:** JSON-based element registry with domain/page organization
4. **Browser:** Playwright Chromium in headless mode
5. **Viewport:** 1920x1080 for full element visibility

---

## 📈 Execution Statistics

**From Flask Logs (19:23:50):**
- ✅ Parser executed successfully (200 OK)
- ✅ Element map saved successfully (200 OK)
- ✅ XPath builder registered multiple elements
- ✅ No errors reported

**File Sizes:**
- Total Python code: ~114 KB (routes + parser + xpath + registry)
- Largest file: `playwright_tree_parser.py` (38 KB)
- Most recently modified: `routes.py` (Jan 3, 2026)

---

## 🔍 Debugging & Monitoring

**Log Files:**
- Flask debug log: `~/DATAHUB_AI_Agent/flask_debug.log`
- Contains XPath builder output and HTTP requests

**Key Log Patterns:**
```
INFO:utils.xpath_builder:✅ XPath registered: {element_name}
INFO:werkzeug:{timestamp} "POST /api/parse-html HTTP/1.1" 200
```

---

## 📚 References

- **Parser Implementation:** `utils/playwright_tree_parser.py`
- **API Routes:** `api/routes.py`
- **XPath Generation:** `utils/xpath_builder.py`
- **Storage:** `utils/element_registry.py`
- **Web UI:** `http://13.222.91.163:5000/parser`

---

**Document Version:** 1.0  
**Last Updated:** January 3, 2026






