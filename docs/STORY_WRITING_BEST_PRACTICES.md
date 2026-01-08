# Story Writing Best Practices

## 📋 Overview

This guide provides best practices for writing effective test stories that work optimally with the AI Test Generation Agent. These patterns have been validated through extensive testing.

---

## 🎯 Key Principle: Context Over Keywords

**The AI uses surrounding context to disambiguate elements, not just keywords in the element name.**

### ✅ **GOOD Pattern:**
Provide rich context about WHERE the element is located, but keep the element name simple.

```
Step 8: After More dropdown opens, the data table has tabs like Participants, 
Studies, Diagnosis. Click on the "Treatment" (it will show a count in parentheses)
```

**Why this works:**
- ✅ "data table has tabs" establishes the location context
- ✅ "Treatment" is simple and matches the actual page element text
- ✅ Visual cue "(it will show a count in parentheses)" helps verification

---

### ❌ **BAD Pattern:**
Adding type keywords ("tab", "filter") directly to the element name.

```
Step 8: Click on the "Treatment tab" in the data table
```

**Why this fails:**
- ❌ "Treatment tab" doesn't match actual page text (page just says "Treatment")
- ❌ If "filter" appears earlier in the story, the AI may get confused
- ❌ Keyword-based disambiguation can cause context bleeding from previous steps

---

## 🏗️ Story Structure Guidelines

### 1. **One Action Per Step**
```
✅ GOOD:
Step 4: In the left sidebar filter panel, click on "TREATMENT" to expand it
Step 5: Inside the TREATMENT section, click on Treatment Type

❌ BAD:
Step 4: Click on TREATMENT, then click on Treatment Type
```

### 2. **Separate Steps with Clear Context**
Each step should establish WHERE you are before stating WHAT to do.

```
✅ GOOD:
Step 4: In the left sidebar filter panel, click on "TREATMENT" to expand it
Step 7: In the data table bottom area, click the More button
Step 8: After More dropdown opens, the data table has tabs. Click on "Treatment"

❌ BAD:
Step 4: Click on TREATMENT filter
Step 7: Click More
Step 8: Click Treatment tab
```

### 3. **Use Location Context, Not Type Keywords**

**Location Phrases (GOOD):**
- "In the left sidebar filter panel"
- "In the data table bottom area"
- "In the top navigation bar"
- "In the filter section"
- "Among the data table tabs"

**Type Keywords (AVOID in element names):**
- "TREATMENT filter" → Use "TREATMENT" with context
- "Treatment tab" → Use "Treatment" with context
- "Submit button" → Use "Submit" with context

---

## 📝 Real-World Example: The Treatment Filter vs Tab Issue

### ❌ **Problem Story:**
```
Step 4: Click on "TREATMENT filter" to expand it
Step 8: Click on "Treatment tab" in the data table
```

**Issues:**
1. "TREATMENT filter" and "Treatment tab" don't exist as text on the page
2. Page has "TREATMENT" (filter) and "Treatment(8,628)" (tab)
3. AI must search for artificial names, not actual page text

---

### ✅ **Solution Story:**
```
Step 4: In the left sidebar filter panel, click on "TREATMENT" to expand it
Step 8: After More dropdown opens, the data table has tabs like Participants, 
Studies, Diagnosis. Click on "Treatment" (it will show a count in parentheses)
```

**Why this works:**
1. Uses actual page text: "TREATMENT" and "Treatment"
2. Provides clear location context for disambiguation
3. Lets the AI use surrounding context instead of keyword matching

---

## 🎨 Formatting Guidelines

### Use Newlines to Separate Steps
```
✅ GOOD (each step on its own line):
Step 1: Go to https://example.com
Step 2: Wait 2 seconds for page to load
Step 3: Click on Menu

❌ BAD (run-on text):
Go to example.com, wait 2 seconds, click Menu
```

### Include Wait Times for Dynamic Content
```
✅ GOOD:
Step 2: Wait 5 seconds for page to fully load
Step 9: Wait 3 seconds for the Treatment tab data to load

❌ BAD:
Step 2: Load the page
Step 9: View the Treatment data
```

---

## 🧪 Element Naming Patterns

### Filters/Accordions
```
✅ GOOD:
"In the left sidebar filter panel, click on TREATMENT to expand it"

❌ BAD:
"Click on TREATMENT filter"
"Click on the TREATMENT accordion"
```

### Tabs
```
✅ GOOD:
"The data table has tabs like Participants, Studies. Click on Treatment"

❌ BAD:
"Click on Treatment tab"
"Switch to the Treatment tab"
```

### Buttons
```
✅ GOOD:
"Click the More button to reveal additional tabs"
"Click Continue to dismiss the popup"

✅ ALSO GOOD (if unique):
"Click More"
"Click Continue"
```

### Checkboxes
```
✅ GOOD:
"Select the Chemotherapy checkbox"
"Click on Chemotherapy"

❌ BAD:
"Check the Chemotherapy box"
"Toggle Chemotherapy"
```

---

## 🔍 Verification Statements

### Table Column Verification
```
✅ GOOD:
"Verify that all rows in the Treatment Type column contain Chemotherapy"

✅ ALSO GOOD (more specific):
"Verify that all rows in column 'Treatment Type' contain 'Chemotherapy'"
```

### Tab State Verification
```
✅ GOOD:
"Verify the Treatment tab is now active and showing treatment data"
```

### Filter State Verification
```
✅ GOOD:
"Verify that TREATMENT section is expanded and shows Treatment Type options"
```

---

## 💡 Advanced Tips

### 1. **Use Visual Cues**
Help the AI identify the correct element by mentioning visual characteristics:
```
"Click on Treatment (it will show a count in parentheses)"
"Click the blue Submit button at the bottom"
"Select the checkbox next to Primary Tumor"
```

### 2. **Mention Siblings for Context**
```
"The data table has tabs like Participants, Studies, Diagnosis. Click on Treatment"
```
This helps the AI understand Treatment is one of several tabs in that area.

### 3. **Conditional Actions**
```
"If there is a popup with a Continue button, click it to dismiss the popup"
```
The AI handles conditional logic well when clearly stated.

### 4. **Step Grouping**
Group related actions with context:
```
"Inside the TREATMENT filter section:"
- "Click on Treatment Type to expand"
- "Select Chemotherapy checkbox"
```

---

## 📊 Testing Checklist

Before running your story, verify:

- [ ] Each step has clear location context
- [ ] Element names match actual page text
- [ ] No type keywords in element names ("filter", "tab", "button")
- [ ] Steps are numbered and separated by newlines
- [ ] Wait times are included for dynamic content
- [ ] Verification statements are specific and clear
- [ ] Conditional actions are clearly stated

---

## 🚀 Success Metrics

A well-written story should:

1. ✅ **Pass on first run** (no disambiguation errors)
2. ✅ **Be readable by humans** (clear, logical flow)
3. ✅ **Be maintainable** (easy to update if UI changes)
4. ✅ **Generate robust Playwright code** (reliable selectors)
5. ✅ **Work across similar pages** (reusable patterns)

---

## 📚 Reference Examples

### Complete Success Story
```
Step 1: Go to https://clinicalcommons.ccdi.cancer.gov/explore
Step 2: Wait 5 seconds for page to fully load
Step 3: If there is a popup with Continue button, dismiss it by clicking Continue
Step 4: In the left sidebar filter panel, click on TREATMENT to expand it
Step 5: Inside the TREATMENT filter section, click on Treatment Type to expand the checkboxes
Step 6: Select the Chemotherapy checkbox
Step 7: In the data table bottom area, click the More button to reveal additional tabs
Step 8: After More dropdown opens, the data table has tabs like Participants, Studies, Diagnosis. Click on Treatment (it will show a count in parentheses)
Step 9: Wait 3 seconds for the Treatment tab data to load
Step 10: Verify that all rows in the Treatment Type column contain Chemotherapy
```

**Result:** ✅ All 10 rows verified, test passed

---

## 🔄 Continuous Improvement

As you write more stories:

1. **Review Registry** - Use the "📋 View Registry" button to see what elements were discovered
2. **Check Screenshots** - Verify the AI is clicking the correct elements
3. **Update Patterns** - Refine your story writing based on what works
4. **Share Learnings** - Document new patterns that emerge

---

**Last Updated:** December 29, 2025  
**Version:** 1.0  
**Validated Against:** clinicalcommons.ccdi.cancer.gov










