# Story Context Selection Fix - Tab vs Accordion Disambiguation

## Problem
When the agent tried to click "Diagnosis", it was selecting the wrong story step and consequently the wrong element:
- **Expected:** Step 9 (Click Diagnosis **tab** in bottom data table)
- **Actual:** Step 4 (Click DIAGNOSIS **accordion** in left sidebar)

This caused the agent to click the accordion instead of the tab, and the table verification failed because the Diagnosis column was not visible.

## Root Cause
The story context selection logic in `bedrock_playwright_agent.py` was:
1. Finding the first step that mentioned "Diagnosis"
2. Stopping immediately without considering element type
3. Not distinguishing between different UI element types (tab, accordion, checkbox, etc.)

## Solution
Enhanced the story context selection logic to:

### 1. Collect All Matching Steps
Instead of stopping at the first match, now collects ALL steps that mention the element name.

### 2. Disambiguate by Element Type
When multiple steps mention the same element name, the agent now:
- Extracts the element type from the selector (`tab`, `accordion`, `checkbox`, etc.)
- Checks which step mentions that type
- Prefers the step that matches the element type

Example:
- Element: `text=Diagnosis` with `role=tab`
- Step 4: "click on DIAGNOSIS to **expand** it" → Contains "expand" (accordion keyword)
- Step 9: "click on Diagnosis **tab**" → Contains "tab" (tab keyword)
- **Result:** Selects Step 9 ✅

### 3. Location-Based Disambiguation
If element type doesn't resolve ambiguity, uses location keywords:
- Tabs: Look for "bottom", "data table"
- Accordions: Look for "sidebar", "filter"

### 4. Sequential Flow Fallback
If still ambiguous, prefers later steps (assumes sequential workflow).

### 5. Registry Candidate Selection Enhancement
When multiple registry candidates have the same score, the agent now:
- Checks the story context for element type keywords
- Prefers the candidate whose type matches the story context

Example:
- Story: "click on Diagnosis **tab**"
- Candidate A: "Diagnosis accordion" (score=195)
- Candidate B: "Diagnosis tab" (score=195)
- **Result:** Selects Candidate B (tab matches story) ✅

## Code Changes

### File: `agent/bedrock_playwright_agent.py`

**Lines 1281-1327:** Enhanced story context selection
- Collects all matching steps instead of stopping at first match
- Extracts element type from selector
- Matches step content against element type keywords
- Falls back to location keywords and sequential flow

**Lines 368-398:** Enhanced registry candidate selection
- When multiple candidates are tied in score, uses story context
- Checks for element type keywords in story
- Prefers candidate whose type matches story context

## Testing
After deploying this fix, when the agent encounters "Diagnosis" in Step 9 context:
1. ✅ Should identify it as a **tab** (not accordion)
2. ✅ Should select Step 9 (not Step 4)
3. ✅ Should click the "Diagnosis tab (bottom data table)" element
4. ✅ Should verify the Diagnosis column in the table

## Expected Log Output
```
🔍 Found 2 steps mentioning 'Diagnosis' - checking element type...
✅ Step 9 mentions 'tab' (matches element type)
📚 Using step 9 of 11 matching steps: 'Step 9: In the bottom data table tabs , click on Diagnosis tab'
🏆 Top registry candidates:
   • Diagnosis accordion (left sidebar filter panel): 195 pts
   • Diagnosis tab (bottom data table): 195 pts
🔍 2 candidates tied at 195 pts - using story context to disambiguate...
✅ Story mentions 'tab' - preferring: Diagnosis tab (bottom data table)
✅ Selected: Diagnosis tab (bottom data table) (score=195)
```

## Date
December 31, 2025











