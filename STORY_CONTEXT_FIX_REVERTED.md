# Story Context Fix - REVERTED (Issue Identified)

## What Was Changed (Now Reverted)
Attempted to enhance story context selection to distinguish between tabs and accordions when multiple steps mention the same element name (e.g., "Diagnosis").

## What Went Wrong

### The Problem
When the agent tried to click the **nested Diagnosis accordion** (Step 5):

1. The enhanced logic found **5 steps** mentioning "Diagnosis":
   - Step 4: Click DIAGNOSIS accordion (parent)
   - Step 5: Click nested Diagnosis accordion ✅ (SHOULD SELECT THIS)
   - Step 9: Click Diagnosis tab (bottom table)
   - Step 11: Verify Diagnosis column

2. Since the selector was generic `text=Diagnosis`, no element type could be extracted

3. The fallback logic used: `best_match_idx = max(matching_step_indices)`
   - This selected **Step 11** (the LAST matching step)
   - **Wrong!** Should have selected Step 5 (the NEXT step in sequence)

4. With Step 11 context ("verify table"), the registry selected **"Diagnosis tab"** instead of **"nested accordion"**

5. Result: Agent skipped Step 5 and jumped to Step 9, clicking the tab prematurely ❌

### Root Cause
The "sequential flow" fallback was flawed:
```python
# WRONG: Picks the LAST matching step
best_match_idx = max(matching_step_indices)  # Picked Step 11 instead of Step 5
```

This assumed "later in story = more likely", but that's wrong when the agent is in the middle of a workflow.

## What Was Reverted
Reverted to the original simpler logic that:
1. Finds the FIRST step mentioning the element name
2. Uses `last_clicked_element` for sequential hints
3. Looks for "nested" keyword after clicking parent

This worked correctly for:
- ✅ Nested accordions (after clicking parent)
- ✅ Checkboxes (using element name match)
- ✅ Sequential flow

## The Original Issue (Still Unresolved)
The original problem that prompted this fix:
- When clicking "Diagnosis" after a checkbox, the agent sometimes couldn't distinguish between:
  - **Diagnosis tab** (Step 9 - bottom data table)
  - **Diagnosis accordion** (Step 4 - left sidebar)

However, logs from recent tests showed the original logic was **actually working correctly** - it was selecting the tab when appropriate.

## Lessons Learned
1. ❌ Don't use `max(matching_step_indices)` for "sequential flow" - it picks the wrong step
2. ✅ Sequential flow needs to consider what step was JUST completed, not what's "latest" in the story
3. ✅ The original "first match" approach was simpler and more reliable
4. ✅ If disambiguation is needed, it should be in the **registry scoring**, not story context selection

## Status
- ✅ Reverted to original working logic
- ✅ Flask restarted with clean cache
- ✅ Ready for testing
- 📝 The tab vs accordion issue may need a different approach (registry-based, not story-based)

## Date
December 31, 2025











