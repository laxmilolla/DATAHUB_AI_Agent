# Code Sanity Check - Duplicates and Redundancies

## 🔴 CRITICAL DUPLICATES

### 1. **Duplicate `_is_modal_open()` Method** ⚠️ HIGH PRIORITY
**Location:**
- `agent/tools/browser_click.py` (lines 1173-1206)
- `agent/tools/browser_fill.py` (lines 40-73)

**Issue:** Exact same code duplicated in two files (33 lines each)

**Impact:**
- Maintenance burden: Changes must be made in 2 places
- Risk of inconsistency if one is updated but not the other
- Code bloat

**Recommendation:** Extract to shared utility class or base class

---

### 2. **Multiple Calls to `_is_modal_open()` in Same Execution** ⚠️ MEDIUM PRIORITY
**Location:** `agent/tools/browser_click.py`

**Calls:**
1. Line 94: At start of `execute()` method
2. Line 247: Inside `_resolve_selector()` method  
3. Line 1270: Inside `_wait_for_dropdown_menu_portal()` method

**Issue:** Same modal check performed 3 times in single execution flow

**Impact:**
- Performance: 3 DOM queries for same check
- Inconsistency risk: Results might differ between calls
- Unnecessary overhead

**Recommendation:** Cache result in instance variable or pass as parameter

---

## 🟡 REDUNDANT LOGIC

### 3. **Duplicate Selector Scoping Logic** ⚠️ MEDIUM PRIORITY
**Location:**
- `agent/tools/browser_click.py` (lines 315-360)
- `agent/tools/browser_fill.py` (lines 291-321)

**Issue:** Similar logic for scoping selectors to modal context duplicated

**Pattern:**
```python
if should_check_modal and modal_selector:
    if selector.startswith("xpath="):
        # Scope XPath
    elif selector.startswith("text="):
        # Scope text selector
    else:
        # Scope CSS selector
```

**Impact:**
- Code duplication
- Maintenance burden
- Slight differences between implementations (browser_click has `text=` handling, browser_fill doesn't)

**Recommendation:** Extract to shared method

---

### 4. **Duplicate Registry Lookup Patterns** ⚠️ LOW PRIORITY
**Location:**
- `agent/tools/browser_click.py` (lines 281-282)
- `agent/tools/browser_fill.py` (lines 254-278)

**Issue:** Similar patterns of trying multiple element name variations

**Pattern:**
```python
registry_selector = check_registry(element_name, domain, page)
if not registry_selector:
    registry_selector = check_registry(element_name.capitalize(), domain, page)
if not registry_selector:
    registry_selector = check_registry(element_name.upper(), domain, page)
```

**Impact:**
- Code duplication
- Inconsistent variations tried between files

**Recommendation:** Extract to helper method with standardized variations

---

### 5. **Duplicate URL Parsing Logic** ⚠️ LOW PRIORITY
**Location:**
- `agent/tools/browser_click.py` (lines 281-300)
- `agent/tools/browser_fill.py` (lines 196-202)
- `agent/browser/element_locator.py` (likely)

**Issue:** Similar URL parsing logic in multiple places

**Pattern:**
```python
from urllib.parse import urlparse
parsed = urlparse(current_url)
domain = parsed.netloc
page_name = path_parts[-1]
```

**Impact:**
- Code duplication
- Risk of inconsistent parsing logic

**Recommendation:** Centralize in `element_locator` or shared utility

---

### 6. **Duplicate `should_check_modal` Logic** ⚠️ MEDIUM PRIORITY
**Location:**
- `agent/tools/browser_click.py` (lines 250-256)
- `agent/tools/browser_fill.py` (lines 231-237)
- `agent/browser/element_locator.py` (lines 58-63)

**Issue:** Same logic for determining if modal context should be checked

**Pattern:**
```python
should_check_modal = (
    is_modal_open and (
        'pop up' in step_text or 'popup' in step_text or
        'dialog' in step_text or 'modal' in step_text or
        step_location == 'table' or
        'submission' in step_parent_hint or 'form' in step_parent_hint
    )
)
```

**Impact:**
- Logic duplication in 3 places
- Risk of inconsistency if one is updated

**Recommendation:** Extract to shared method

---

## 📊 SUMMARY

### Duplicates Found:
1. ✅ **`_is_modal_open()` method** - Exact duplicate (2 files)
2. ✅ **Multiple calls to `_is_modal_open()`** - Called 3x in same flow
3. ✅ **Selector scoping logic** - Similar code (2 files)
4. ✅ **Registry lookup patterns** - Similar patterns (2 files)
5. ✅ **URL parsing logic** - Similar code (3+ files)
6. ✅ **`should_check_modal` logic** - Exact duplicate (3 files)

### Impact Assessment:
- **High Priority:** #1 (duplicate method), #2 (multiple calls)
- **Medium Priority:** #3 (scoping), #6 (should_check_modal)
- **Low Priority:** #4 (registry patterns), #5 (URL parsing)

### Recommendations:
1. **Create shared utility module** (`agent/utils/modal_utils.py` or similar)
   - Extract `_is_modal_open()` 
   - Extract `should_check_modal()` logic
   - Extract selector scoping logic

2. **Cache modal state** in execution context
   - Store `is_modal_open` result in context
   - Reuse instead of calling multiple times

3. **Centralize URL parsing** in `element_locator`
   - Single source of truth for domain/page extraction

4. **Standardize registry lookup** patterns
   - Create helper method with consistent variations

---

## 🔍 DETAILED FINDINGS

### File: `agent/tools/browser_click.py`
- **Lines 94, 247, 1270:** `_is_modal_open()` called 3 times
- **Lines 315-360:** Selector scoping logic (duplicate of browser_fill)
- **Lines 250-256:** `should_check_modal` logic (duplicate)

### File: `agent/tools/browser_fill.py`
- **Lines 40-73:** `_is_modal_open()` method (duplicate of browser_click)
- **Lines 291-321:** Selector scoping logic (duplicate of browser_click)
- **Lines 231-237:** `should_check_modal` logic (duplicate)
- **Lines 254-278:** Registry lookup pattern (similar to browser_click)

### File: `agent/browser/element_locator.py`
- **Lines 58-63:** `should_prefer_modal` logic (similar to should_check_modal)
- URL parsing logic (likely duplicate)

---

## ✅ NEXT STEPS

1. **Extract `_is_modal_open()` to shared utility**
2. **Cache modal state** to avoid multiple calls
3. **Extract selector scoping** to shared method
4. **Extract `should_check_modal` logic** to shared method
5. **Review and consolidate** URL parsing logic

