# 🧪 Element Matching Test Utility - Quick Reference

**Location:** `utils/test_element_matching.py`

---

## 🚀 Quick Commands

```bash
# Default test (recommended for first time)
python utils/test_element_matching.py

# Test with fresh server registry
python utils/test_element_matching.py --server

# Test your custom story
python utils/test_element_matching.py --story "Step 1: Click diagnosis"

# Test single step
python utils/test_element_matching.py --step 5 -e "diagnosis"
```

---

## 💡 Common Use Cases

### **Before Deploying:**
```bash
# Test your story locally first!
python utils/test_element_matching.py --story "$(cat my_story.txt)"
# ✅ All pass? → Deploy to server
# ❌ Some fail? → Fix story wording
```

### **Debugging Failed Test:**
```bash
# Agent clicked wrong element on step 5?
python utils/test_element_matching.py --step 5 -e "element_name" --verbose
# See exactly why it picked that element
```

### **Understanding Metadata:**
```bash
# Want to see what metadata is extracted?
python utils/test_element_matching.py --story "Step 1: In the Diagnosis section, click nested Diagnosis"
# Output shows: {'type': 'accordion', 'nested': True, 'parent_hint': 'diagnosis'}
```

---

## 📊 Reading the Output

```
✅ Found 13 name matches          ← How many elements match the name
📋 After type filter: 10          ← Narrowed by type (accordion/tab/etc)
📍 After location filter: 8       ← Narrowed by location (sidebar/table)
🔗 After nested filter: 6         ← Narrowed by parent relationship
👨‍👧 After parent hint: 2          ← Narrowed by parent context (NEW!)
📊 After depth filter: 1          ← Narrowed by hierarchy level (NEW!)

✅ SELECTED: Element Name         ← The winner!
   Selector: [role='button'][...]
```

---

## 🎯 What Helps Element Matching?

### **Keywords that Work:**
- **Type:** "tab", "accordion", "checkbox", "button"
- **Location:** "sidebar", "table", "main", "left", "bottom"
- **Nesting:** "nested", "inner", "within", "inside"
- **Context:** "in the X section", "under Y"
- **Level:** "top-level", "main", "primary"

### **Good Story Examples:**
```
✅ "In left sidebar, click Diagnosis to expand"
   → Extracts: type=accordion, location=sidebar

✅ "In the expanded Diagnosis section, click nested Diagnosis"
   → Extracts: type=accordion, nested=True, parent_hint=diagnosis

✅ "In bottom table tabs, click Diagnosis tab"
   → Extracts: type=tab, location=table

✅ "Click checkbox for Acute leukemia"
   → Extracts: type=checkbox
```

### **Vague Stories (harder to match):**
```
❌ "Click Diagnosis"
   → Ambiguous: parent? child? tab? accordion?

❌ "Select the item"
   → No type, no location, no context
```

---

## 🔧 Options Reference

| Flag | What It Does | Example |
|------|-------------|---------|
| `-s, --story` | Test custom story | `--story "Step 1: Click X"` |
| `--step` | Test one step | `--step 5` |
| `-e, --element` | Element to find | `-e "diagnosis"` |
| `-r, --registry` | Use local registry | `-r element_maps/local.json` |
| `--server` | Download from server | `--server` |
| `-v, --verbose` | Show all details | `-v` |

---

## 🎓 Tips

1. **Always test locally before deploying**
   - Catches issues early
   - No need to restart Flask
   - Instant feedback

2. **Use descriptive step text**
   - More keywords = better matching
   - "In the X section, click nested Y" > "Click Y"

3. **Check what metadata was extracted**
   - The tool shows what it detected
   - Add missing keywords if needed

4. **Compare with agent logs**
   - Tool uses same logic as agent
   - What passes locally should pass on server

---

## 📖 Full Documentation

See `utils/README_TEST_UTILITY.md` for complete documentation.

---

**Pro Tip:** Bookmark this file! 🔖

Use it every time before deploying stories to the server.



