# Registry Duplicates Summary

## ✅ Completed Analysis

**Script:** `check_registry_duplicates.py`
**Total Files Checked:** 206 registry files
**Issues Found:** 2 files with within-file duplicates, 5 cross-file duplicates

---

## 🔴 Critical Issues Found

### 1. Cross-File Duplicate: "Data Submissions"
- **Location:** Both `home_page.json` and `data-submissions-modal_page.json`
- **Selector:** `div[role='button']:has-text('Data Submissions')`
- **Action:** Remove from modal registry (it's a main page navigation element)

### 2. Within-File Duplicate: "Login" in home_page.json
- **Selector:** `text=Login` used by both `'Login'` and `'verify_Login'`
- **Action:** Consolidate or use more specific selector

### 3. Within-File Duplicate: TOTP Input in authenticator_page.json
- **Selector:** `input.one-time-code-input__input` used by 3 elements (`'text'`, `'input.one-time-code-input__input'`, `'totp'`)
- **Action:** Keep only `'totp'`, remove others

### 4. Weak XPath: `(//*)[1]` used in multiple files
- **Action:** Regenerate with more specific XPaths

---

## 📊 Impact

- **High Priority:** 1 issue (Data Submissions duplicate)
- **Medium Priority:** 3 issues (Login duplicate, TOTP duplicate, weak XPaths)
- **Low Priority:** 2 issues (duplicate names across different pages - likely intentional)

---

## ✅ Next Steps

1. Review and remove "Data Submissions" from modal registry if present
2. Consolidate duplicate elements in affected files
3. Regenerate weak XPaths

**Note:** Most duplicates are in execution-specific registries (`exec_*` directories), which are less critical than main production registries.

