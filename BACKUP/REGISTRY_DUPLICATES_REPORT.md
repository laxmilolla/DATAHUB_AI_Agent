# Registry Duplicates Report

## Summary
- **Total registry files checked:** 206
- **Files with within-file duplicates:** 2
- **Cross-file duplicates found:** 5 issues

---

## 🔴 CRITICAL: Cross-File Duplicates

### 1. "Data Submissions" Element Duplicated
**Issue:** Same element exists in both main page and modal registries
- **Files:**
  - `hub-stage.datacommons.cancer.gov/home_page.json`
  - `hub-stage.datacommons.cancer.gov/data-submissions-modal_page.json`
- **Selector:** `div[role='button']:has-text('Data Submissions')`
- **Impact:** ⚠️ **HIGH** - Could cause confusion when modal is open
- **Recommendation:** Remove from modal registry (it's a main page navigation element)

### 2. Generic XPath Used Across Multiple Files
**Issue:** Weak XPath `(//*)[1]` used in multiple files
- **Files:**
  - `secure.login.gov/home_page.json` → 'password'
  - `secure.login.gov/authenticator_page.json` → 'totp'
  - `hub-stage.datacommons.cancer.gov/home_page.json` → 'text'
- **Impact:** ⚠️ **MEDIUM** - Weak XPath, not unique
- **Recommendation:** Regenerate XPaths for these elements

### 3. Duplicate Element Names Across Files
**Issue:** Same element name used in different files (may be intentional, but worth reviewing)

#### a) "text" element
- `hub-stage.datacommons.cancer.gov/home_page.json`
- `secure.login.gov/authenticator_page.json`
- **Impact:** ⚠️ **LOW** - Different contexts, likely intentional

#### b) "Submit" element
- `secure.login.gov/home_page.json`
- `secure.login.gov/authenticator_page.json`
- **Impact:** ⚠️ **LOW** - Different pages, likely intentional

---

## ⚠️ Within-File Duplicates

### 1. `hub-stage.datacommons.cancer.gov/home_page.json`

#### Duplicate Selector: `text=Login`
- **Elements:**
  - `'Login'` (context: main-page)
  - `'verify_Login'` (context: main-page)
- **Impact:** ⚠️ **MEDIUM** - Two elements with same selector
- **Recommendation:** 
  - Check if `verify_Login` is actually different from `Login`
  - If same element, remove duplicate
  - If different, use more specific selector

### 2. `secure.login.gov/authenticator_page.json`

#### Duplicate Selector: `input.one-time-code-input__input`
- **Elements:**
  - `'text'` (context: main-page)
  - `'input.one-time-code-input__input'` (context: main-page)
  - `'totp'` (context: main-page)
- **Impact:** ⚠️ **MEDIUM** - Three elements pointing to same input
- **Recommendation:**
  - Consolidate to single element name (preferably `'totp'`)
  - Remove redundant entries

#### Duplicate XPath: `//input[@class='one-time-code-input__input'...]`
- **Elements:**
  - `'text'` (context: main-page)
  - `'input.one-time-code-input__input'` (context: main-page)
- **Impact:** ⚠️ **MEDIUM** - Same XPath for different element names
- **Recommendation:** Remove duplicate entries

---

## 📋 Action Items

### High Priority
1. ✅ **Remove "Data Submissions" from modal registry**
   - File: `hub-stage.datacommons.cancer.gov/data-submissions-modal_page.json`
   - Element: `'Data Submissions'`
   - Reason: This is a main page navigation element, not a modal element

### Medium Priority
2. ✅ **Fix duplicate "Login" selector in home_page.json**
   - Check if `verify_Login` is needed
   - If not needed, remove it
   - If needed, use more specific selector

3. ✅ **Consolidate TOTP input elements in authenticator_page.json**
   - Keep only `'totp'` element
   - Remove `'text'` and `'input.one-time-code-input__input'` entries

4. ✅ **Regenerate weak XPaths**
   - Replace `(//*)[1]` XPaths with more specific ones
   - Files affected:
     - `secure.login.gov/home_page.json` → 'password'
     - `secure.login.gov/authenticator_page.json` → 'totp'
     - `hub-stage.datacommons.cancer.gov/home_page.json` → 'text'

### Low Priority
5. ⚠️ **Review duplicate names across files**
   - "text" and "Submit" names are duplicated but in different contexts
   - These may be intentional (different pages)
   - No action needed unless causing issues

---

## 🔍 Notes

- Most duplicates are in execution-specific registries (`exec_*` directories)
- Main production registries (`hub-stage.datacommons.cancer.gov/`) have fewer issues
- The "Data Submissions" duplicate is the most critical as it could cause incorrect element selection when modal is open

