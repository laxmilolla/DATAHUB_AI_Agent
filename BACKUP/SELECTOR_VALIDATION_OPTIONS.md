# Selector Validation Utility - Options

## Problem Statement
We've been facing issues with:
- Wrong selectors matching main page elements instead of modal elements
- Dropdown selectors matching labels instead of buttons
- Registry selectors becoming stale or incorrect
- No way to test selectors before they're used in production

## Option 1: **Pre-Execution Selector Validator** ⭐ RECOMMENDED
**What it does:** Validates all selectors in registry files before test execution starts

**Implementation:**
- Script: `utils/selector_validator.py`
- Command: `python utils/selector_validator.py --page data-submissions --modal`
- Validates:
  - Selectors are scoped correctly (modal vs main page)
  - Elements are visible and accessible
  - Dropdowns can be opened
  - Inputs can be filled
- Output: Report of broken/invalid selectors

**Pros:**
- ✅ Catches issues before they cause test failures
- ✅ Can be run manually or in CI/CD
- ✅ Non-intrusive (doesn't change agent code)
- ✅ Can validate entire registry at once

**Cons:**
- ⚠️ Requires browser to be open/managed
- ⚠️ May need user to navigate to page first

**Usage:**
```bash
# Validate all selectors for a page
python utils/selector_validator.py --page data-submissions

# Validate modal selectors specifically
python utils/selector_validator.py --page data-submissions --modal

# Validate specific element
python utils/selector_validator.py --page data-submissions --element "Study"
```

---

## Option 2: **Interactive Element Tester** (Like test_study_dropdown.py)
**What it does:** General-purpose script to test any element interactively

**Implementation:**
- Script: `utils/test_element.py`
- Command: `python utils/test_element.py --url <url> --element "Study" --type dropdown`
- Features:
  - Connect to existing browser (CDP)
  - Test specific element by name/selector
  - List all options for dropdowns
  - Test input fields
  - Take screenshots

**Pros:**
- ✅ Quick debugging of specific elements
- ✅ Can test before adding to registry
- ✅ User-friendly (connect to their browser)

**Cons:**
- ⚠️ Manual process (not automated)
- ⚠️ One element at a time

**Usage:**
```bash
# Test a dropdown
python utils/test_element.py --url https://hub-stage.datacommons.cancer.gov/data-submissions \
  --element "Study" --type dropdown --modal

# Test an input field
python utils/test_element.py --url <url> --element "Submission Name" --type input --modal

# List all elements on page
python utils/test_element.py --url <url> --list-all
```

---

## Option 3: **Registry Health Checker**
**What it does:** Validates all registry files and reports issues

**Implementation:**
- Script: `utils/registry_health_check.py`
- Command: `python utils/registry_health_check.py`
- Checks:
  - Duplicate selectors
  - Invalid CSS/XPath syntax
  - Missing required fields
  - Selectors that match multiple elements
  - Modal vs main-page conflicts

**Pros:**
- ✅ Fast (no browser needed)
- ✅ Can catch syntax errors
- ✅ Can detect conflicts

**Cons:**
- ⚠️ Can't verify if selectors actually work
- ⚠️ Can't test visibility/accessibility

**Usage:**
```bash
# Check all registries
python utils/registry_health_check.py

# Check specific page
python utils/registry_health_check.py --page data-submissions
```

---

## Option 4: **Runtime Selector Validation** (Built into Agent)
**What it does:** Validates selector before using it, falls back if invalid

**Implementation:**
- Modify `browser_click.py` and `browser_fill.py`
- Before using selector:
  1. Check if element exists
  2. Check if it's visible
  3. Check if it's in correct context (modal vs main)
  4. If invalid, try discovery/XPath generation

**Pros:**
- ✅ Automatic validation
- ✅ Self-healing (falls back to discovery)
- ✅ No manual steps needed

**Cons:**
- ⚠️ Adds overhead to every action
- ⚠️ May slow down execution
- ⚠️ Requires code changes to agent

**Code Example:**
```python
async def _validate_selector(self, selector: str, expected_context: str = None) -> bool:
    """Validate selector before use"""
    try:
        element = self.page.locator(selector).first
        if await element.count() == 0:
            return False
        if not await element.is_visible():
            return False
        if expected_context == "modal":
            is_in_modal = await element.locator('xpath=ancestor::*[@data-testid="create-submission-dialog"]').count() > 0
            if not is_in_modal:
                return False
        return True
    except:
        return False
```

---

## Option 5: **Discovery + Validation Workflow**
**What it does:** When discovering elements, immediately validate them

**Implementation:**
- Modify `discovery_tracker.py`
- After generating XPath/selector:
  1. Test if selector works
  2. Verify element is accessible
  3. Check context (modal vs main)
  4. Only save if validation passes

**Pros:**
- ✅ Catches bad selectors at discovery time
- ✅ Prevents bad entries in registry
- ✅ Automatic quality control

**Cons:**
- ⚠️ May slow down discovery
- ⚠️ Requires code changes

---

## Option 6: **Hybrid Approach** ⭐⭐ BEST LONG-TERM
**Combine Options 1 + 2 + 3:**

1. **Pre-execution validator** (Option 1) - Run before tests
2. **Interactive tester** (Option 2) - For debugging
3. **Registry health check** (Option 3) - For syntax validation
4. **Runtime validation** (Option 4) - Lightweight checks during execution

**Implementation Plan:**
1. Create `utils/selector_validator.py` (Option 1)
2. Generalize `test_study_dropdown.py` → `utils/test_element.py` (Option 2)
3. Create `utils/registry_health_check.py` (Option 3)
4. Add lightweight validation to agent tools (Option 4)

---

## Recommendation

**Start with Option 1 + Option 2** (Hybrid, but simpler):

1. **Create `utils/test_element.py`** - Generalize the test script we just created
   - Can test any element interactively
   - Useful for debugging before adding to registry
   - No code changes to agent needed

2. **Create `utils/selector_validator.py`** - Pre-execution validator
   - Validates entire registry before tests run
   - Can be integrated into CI/CD
   - Catches issues early

**Why this approach:**
- ✅ Quick to implement (we already have test_study_dropdown.py as a template)
- ✅ Non-intrusive (doesn't require agent code changes)
- ✅ Can be used immediately
- ✅ Can add Option 4 later if needed

---

## Next Steps

1. **Generalize test_study_dropdown.py** → `utils/test_element.py`
   - Make it work for any element type (dropdown, input, button)
   - Support both modal and main page
   - Add better error messages

2. **Create `utils/selector_validator.py`**
   - Load registry files
   - Test each selector
   - Generate validation report

3. **Document usage** in README or separate guide

4. **Optional:** Add to CI/CD pipeline to validate registries before deployment

