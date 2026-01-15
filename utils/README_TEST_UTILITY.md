# 🧪 Element Matching Test Utility

**Test element matching logic locally WITHOUT deploying to server!**

Perfect for developers to:
- ✅ Validate story steps before running on server
- ✅ Debug element selection issues
- ✅ Test new matching logic
- ✅ Understand how metadata filtering works

---

## 🚀 Quick Start

```bash
# Run default test (Diagnosis ambiguity test)
python utils/test_element_matching.py

# Use server registry (downloads fresh copy)
python utils/test_element_matching.py --server

# Test your custom story
python utils/test_element_matching.py --story "Step 1: Click diagnosis tab"

# Test specific step
python utils/test_element_matching.py --step 5 --element "diagnosis"
```

---

## 📖 Usage Examples

### **Example 1: Test Default Story**
Tests the problematic Diagnosis case (parent, child, tab disambiguation):

```bash
python utils/test_element_matching.py
```

**Output:**
```
🧪 RUNNING FULL TEST SUITE
================================================================================

TEST CASE: Step 4 - Should match TOP-LEVEL Diagnosis accordion
✅ PASS

TEST CASE: Step 5 - Should match NESTED Diagnosis accordion
✅ PASS

TEST CASE: Step 6 - Should match checkbox
✅ PASS

TEST CASE: Step 8 - Should match Diagnosis TAB
✅ PASS

📊 TEST RESULTS: 4 passed, 0 failed
```

---

### **Example 2: Test Custom Story**

```bash
python utils/test_element_matching.py --story "
Step 1: Navigate to https://clinicalcommons.ccdi.cancer.gov/explore
Step 2: In the Diagnosis section, click nested Diagnosis
Step 3: Click Treatment tab
"
```

---

### **Example 3: Test Single Element**

```bash
python utils/test_element_matching.py --step 5 --element "diagnosis" --story "Step 5: In the expanded Diagnosis section, click nested Diagnosis"
```

**Output:**
```
🧪 SINGLE STEP TEST
================================================================================

🔍 MATCHING: 'diagnosis'
Step metadata: {'type': 'accordion', 'nested': True, 'parent_hint': 'diagnosis'}

✅ Found 13 name matches
📋 After type filter (accordion): 10 matches
🔗 After nested filter: 6 matches (only nested)
👨‍👧 After parent hint filter ('diagnosis'): 6 matches

✅ SELECTED: Diagnosis accordion nested in Diagnosis
   Selector: [role='button'][id='Diagnosis']

✅ SUCCESS: Found element
```

---

### **Example 4: Use Local Registry**

```bash
python utils/test_element_matching.py --registry element_maps/clinicalcommons.ccdi.cancer.gov/explore_page.json
```

---

## 🎯 Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--story` | `-s` | Custom test story (multi-line string) |
| `--step` | | Test only specific step number |
| `--element` | `-e` | Element name to test (use with --step) |
| `--registry` | `-r` | Path to element registry JSON file |
| `--server` | | Download and use fresh registry from server |
| `--verbose` | `-v` | Show detailed matching process |
| `--help` | `-h` | Show help message |

---

## 🔍 What It Tests

The utility simulates the **exact same matching logic** used by the agent:

### **1. Story Metadata Extraction**
- Detects `type` (accordion, tab, checkbox, button)
- Detects `location` (sidebar, table, main content)
- Detects `nested` keyword
- **Extracts `parent_hint`** from context ("in the Diagnosis section" → "diagnosis")
- Detects `depth` preference ("top-level", "first level")

### **2. Element Matching Filters**
1. **Name matching** (word boundaries, no partial matches)
2. **Type filtering** (accordion vs tab vs checkbox)
3. **Location filtering** (sidebar vs table)
4. **Nested filtering** (has parent or not)
5. **Parent hint filtering** (matches parent_text/parent_id)
6. **Depth filtering** (prefers specified depth)
7. **Final selection** (exact match > depth > name length)

---

## 📊 Understanding Output

### **Matching Process Example:**

```
🔍 MATCHING: 'diagnosis'
================================================================================
Step metadata: {'type': 'accordion', 'nested': True, 'parent_hint': 'diagnosis'}

Searching for: 'diagnosis'

✅ Found 13 name matches:
  - Age at Diagnosis (days) accordion
  - Diagnosis accordion (top-level)
  - Diagnosis accordion nested in Diagnosis  ← Target
  - Diagnosis tab
  - ...

📋 After type filter (accordion): 10 matches
🔗 After nested filter: 6 matches (only nested)
👨‍👧 After parent hint filter ('diagnosis'): 6 matches

🏆 FINAL MATCHES (sorted by score):
  1. Diagnosis accordion nested in Diagnosis  ← SELECTED
     depth=1, parent=Diagnosis accordion
     selector=[role='button'][id='Diagnosis']

✅ SELECTED: Diagnosis accordion nested in Diagnosis
```

### **Key Indicators:**

- `✅ Found N name matches` - Initial word-boundary search results
- `📋 After type filter` - Filtered by element type
- `📍 After location filter` - Filtered by page location
- `🔗 After nested filter` - Filtered by parent relationship
- `👨‍👧 After parent hint filter` - **NEW!** Filtered by parent context
- `📊 After depth filter` - **NEW!** Filtered by hierarchy level
- `🏆 FINAL MATCHES` - Top 5 candidates sorted by best match score
- `✅ SELECTED` - The winner!

---

## 💡 Use Cases

### **Before Deploying to Server:**
```bash
# 1. Write your story
cat > my_story.txt << 'EOF'
Step 1: Navigate to https://clinicalcommons.ccdi.cancer.gov/explore
Step 2: Click Diagnosis to expand
Step 3: In Diagnosis section, click nested Diagnosis
EOF

# 2. Test it locally
python utils/test_element_matching.py --story "$(cat my_story.txt)"

# 3. If all pass, deploy!
```

### **Debugging Failed Tests:**
```bash
# Test failed on step 5?
python utils/test_element_matching.py --step 5 --element "diagnosis" --verbose

# Check what metadata was extracted
# Check which filters reduced the matches
# See why wrong element was selected
```

### **Comparing Local vs Server Registry:**
```bash
# Test with local registry
python utils/test_element_matching.py --registry element_maps/local.json

# Test with server registry
python utils/test_element_matching.py --server

# Compare results
```

---

## 🐛 Troubleshooting

### **"No matches found"**
- Check if element exists in registry
- Try without word boundaries (add to name list manually)
- Check if metadata extraction captured correct type/location

### **"Wrong element selected"**
- Check step text - does it have enough context?
- Add keywords: "nested", "top-level", "in the X section"
- Check final selection score - why did wrong one rank higher?

### **"Registry not found"**
- Use `--server` to download from server
- Use `--registry path/to/file.json` to specify local file
- Check file exists at specified path

---

## 🎓 Learning Tool

This utility is also great for understanding:
- How metadata extraction works from story text
- How different filters narrow down candidates
- Why certain elements are selected over others
- How to write better story steps for disambiguation

---

## 🔧 Developer Notes

**File Location:** `utils/test_element_matching.py`

**Dependencies:**
- Python 3.6+
- Standard library only (json, re, argparse, pathlib)
- No external packages needed

**Extending:**
- Add new test cases in the `test_cases` list
- Modify metadata extraction logic in `parse_story_metadata()`
- Add new filters in `match_elements()`
- Compare with agent logic in `agent/bedrock_playwright_agent.py`

---

## 📝 Related Files

- **Agent matching logic:** `agent/bedrock_playwright_agent.py` (lines 173-320)
- **Story parser:** `agent/bedrock_playwright_agent.py` (lines 64-112)
- **Element registry:** `element_maps/*/explore_page.json`
- **Parser:** `utils/playwright_tree_parser.py`

---

**Happy Testing! 🎉**

*Remember: Test locally, deploy confidently!*






