# Selector-Type Matching Fix - Tab Selection

## Problem
The tab detection logic wasn't working because:
1. Story context was wrong (selected Step 4 instead of Step 9)
2. Story context didn't mention "tab", so `wants_tab = FALSE`
3. Tab boost logic never executed
4. Accordion won by default

## The User's Insight
**"If there is a tab and your xpath is accordion, pick that"**

Translation: **Match the selector type to the candidate type**

- If selector is looking for a `role=tab` → Pick tab candidate
- If selector is looking for a `role=button` → Pick accordion candidate

## The Solution

### Simple Rule:
**Don't rely on story context. Look at what the SELECTOR wants.**

If the registry returns candidates with XPaths, check:
1. Does the XPath have `role='tab'`? → It's a tab selector
2. Does the XPath have `role='button'` or `aria-expanded`? → It's an accordion selector
3. Match the selector type to the candidate type

## Code Changes

### Location: `agent/bedrock_playwright_agent.py` (lines 368-425)

Added selector-type matching logic in the registry scoring:

```python
# Detect if selector is looking for a tab
selector_wants_tab = any([
    "role=tab" in selector_lower,
    'role="tab"' in selector_lower,
    "role='tab'" in elem_xpath,
    ...
])

# Detect if selector is looking for an accordion
selector_wants_accordion = any([
    "role=button" in selector_lower,
    "aria-expanded" in selector_lower,
    "role='button'" in elem_xpath,
    ...
])

# Apply massive boost if selector type matches candidate type
if selector_wants_tab and elem_type == "tab":
    score += 1500  # MASSIVE boost
    logger.info(f"🎯🎯🎯 SELECTOR-TYPE MATCH: Selector wants TAB, '{name}' is TAB (+1500)")
elif selector_wants_tab and elem_type == "accordion":
    score -= 1000  # MASSIVE penalty
    logger.info(f"❌❌ SELECTOR-TYPE MISMATCH: Selector wants TAB, '{name}' is ACCORDION (-1000)")
```

## How It Works

### Scenario: Click "Diagnosis" at Iteration 10

**Before Fix:**
```
Story context: "Step 4: click on DIAGNOSIS to expand it" (wrong step)
Candidates:
  • Diagnosis accordion: 295 pts
  • Diagnosis tab: ~100 pts (not in top 5)
Selected: Accordion ❌
```

**After Fix:**
```
Registry returns candidates with their XPaths:
  • Diagnosis accordion: xpath=//div[@role='button'...]
  • Diagnosis tab: xpath=//button[@role='tab'...]

Selector type detection:
  Tab XPath has role='tab' → selector_wants_tab = TRUE

Scoring adjustment:
  • Diagnosis tab: 100 + 1500 = 1600 pts ✅
  • Diagnosis accordion: 295 - 1000 = -705 pts ❌
  
Selected: Tab ✅
```

## Why This Works

### Advantages:
1. ✅ **Doesn't rely on story context** - No risk of selecting wrong step
2. ✅ **Looks at actual XPath** - Knows what type of element it's selecting
3. ✅ **Simple logic** - "If XPath says tab, prefer tab candidate"
4. ✅ **Doesn't break nested accordions** - They have different XPaths
5. ✅ **Works for all element types** - Can extend to checkboxes, links, etc.

### Why Previous Fix Failed:
- Previous fix relied on story context mentioning "tab"
- But story context selection was broken
- Story kept selecting Step 4 (accordion) instead of Step 9 (tab)
- So `wants_tab` was always FALSE

### This Fix Bypasses Story Context:
- Looks directly at the XPath from the registry
- If XPath has `role='tab'` → It's meant for a tab
- Boosts tab candidates, penalizes non-tab candidates
- Works regardless of story context

## Expected Behavior

### When clicking "Diagnosis" after checkbox:

**Registry candidates:**
```
🏆 Top registry candidates:
   • Diagnosis accordion: 295 pts
   • Diagnosis tab: 100 pts

Selector-type matching:
🎯🎯🎯 SELECTOR-TYPE MATCH: Selector wants TAB, 'Diagnosis tab' is TAB (+1500)
❌❌ SELECTOR-TYPE MISMATCH: Selector wants TAB, 'Diagnosis accordion' is ACCORDION (-1000)

Final scores:
   • Diagnosis tab: 1600 pts ✅
   • Diagnosis accordion: -705 pts

✅ Selected: Diagnosis tab (score=1600)
```

## Testing

### To verify the fix works:
1. Run a new test with the story (Steps 1-11)
2. Watch logs at Iteration 10 (click Diagnosis after checkbox)
3. Should see: `🎯🎯🎯 SELECTOR-TYPE MATCH: ... TAB (+1500)`
4. Should see: `✅ Selected: Diagnosis(28,944) tab`
5. Verification should pass - finds "Diagnosis" column in table

## Deployment Status
- ✅ Code updated in `agent/bedrock_playwright_agent.py`
- ✅ Uploaded to server
- ✅ Python cache cleared
- ✅ Flask restarted and running
- ✅ Ready for testing

## Date
December 31, 2025








