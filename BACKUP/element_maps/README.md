# Element Map System - Regression Testing with Self-Learning

This system provides intelligent element mapping for QA automation with self-learning capabilities and Git-based regression testing.

## 🎯 Key Features

1. **Parse HTML once** - Extract all interactive elements automatically
2. **Self-learning** - Agent discovers new elements during tests
3. **Git versioning** - Track UI changes over time
4. **Regression detection** - Compare versions to detect breaking changes
5. **Fast execution** - Use cached selectors instead of discovery

---

## 📋 Quick Start

### 1. Create Initial Element Map

```bash
# Save page HTML to a file
curl https://caninecommons.cancer.gov/#/explore > explore_page.html

# Parse HTML and create element map
cd ~/DATAHUB_AI_Agent
python utils/create_element_map.py \
  --html explore_page.html \
  --url https://caninecommons.cancer.gov/#/explore \
  --print

# Output:
# ✅ Parsed 15 elements
# 💾 Saved to: element_maps/caninecommons.cancer.gov/explore_page.json
# 📸 Created baseline: element_maps/caninecommons.cancer.gov/versions/explore_page_v1.0.json
```

### 2. Commit to Git (Baseline)

```bash
cd ~/DATAHUB_AI_Agent
git add element_maps/
git commit -m "Baseline element map for explore page"
git push
```

### 3. Run Tests

The agent automatically:
- ✅ Uses selectors from element map (fast!)
- 🔍 Discovers new elements if not in map
- 📝 Records successful discoveries
- 💾 Saves to map when test passes

```python
# Your test story:
story = """
1. Go to https://caninecommons.cancer.gov/#/explore
2. Click on Study dropdown
3. Click on OSA01
"""

# Agent will:
# - Find "Study dropdown" in element map
# - Use: #Study[role='button']
# - Click succeeds! ✅
```

### 4. Check for UI Changes (Regression)

```bash
# Compare current vs baseline
python utils/compare_maps.py \
  --domain caninecommons.cancer.gov \
  --page explore

# Output shows:
# ❌ CHANGED (2):
#    • Study dropdown
#      Before: #Study[role='button']
#      After:  #StudyFilter[role='button']
```

---

## 📊 Element Map Format

```json
{
  "page": "explore",
  "url": "https://caninecommons.cancer.gov/#/explore",
  "version": "1.2",
  "timestamp": "2025-12-25T22:00:00Z",
  "elements": {
    "Study dropdown": {
      "selector": "#Study[role='button']",
      "type": "accordion",
      "aria_expanded": "false",
      "description": "Accordion section for Study",
      "alternatives": [
        "[role='button'][aria-expanded]:has-text('Study')",
        ".customExpansionPanelSummaryRoot:has-text('Study')"
      ],
      "source": "initial_parse",
      "usage_count": 25,
      "last_used": "2025-12-25T22:15:00Z"
    },
    "OSA01 checkbox": {
      "selector": "input[type='checkbox'][value='OSA01']",
      "type": "checkbox",
      "source": "llm_discovery",
      "discovered_in": "exec_50269c08",
      "discovered_at": "2025-12-25T22:10:00Z",
      "usage_count": 5
    }
  },
  "statistics": {
    "total_elements": 12,
    "parsed_elements": 10,
    "discovered_elements": 2
  }
}
```

---

## 🔄 Workflow

### Initial Setup (One-Time Per Page)

1. **Collect HTML**
   ```bash
   # Visit page in browser, View Source, Copy HTML
   # Or use curl/wget to fetch it
   ```

2. **Parse & Create Map**
   ```bash
   python utils/create_element_map.py --html page.html --url <URL>
   ```

3. **Commit Baseline**
   ```bash
   git add element_maps/
   git commit -m "Baseline for <page>"
   ```

### Running Tests

```python
# Tests automatically use element maps
# No changes needed to your test code!
```

**What happens:**
1. Agent checks element map first
2. Finds selector → Uses it (fast!)
3. Not found → LLM discovers selector
4. Test passes → New selector added to map
5. Map auto-saves with updated version

### After Test Passes

```bash
# Check what was learned
git diff element_maps/

# Commit new discoveries
git add element_maps/
git commit -m "Added OSA01 checkbox selector (discovered in test)"
git push
```

### Regression Testing

```bash
# Developer changes UI
# Run tests → Some fail

# Compare maps
python utils/compare_maps.py --domain <domain> --page <page>

# See exactly what changed:
# ❌ Study dropdown: #Study → #StudyFilter
# ❌ OSA01 checkbox: value='OSA01' → value='OSA-01'

# Review changes
# If approved:
git add element_maps/
git commit -m "Update baseline: UI changes approved"
```

---

## 🎓 Best Practices

### 1. Create Maps for Key Pages

```bash
# Home page
python utils/create_element_map.py --html home.html --url https://site.com/#/

# Explore page
python utils/create_element_map.py --html explore.html --url https://site.com/#/explore

# Detail page
python utils/create_element_map.py --html detail.html --url https://site.com/#/detail
```

### 2. Commit After Each Successful Test Run

```bash
# After tests pass
git diff element_maps/
git add element_maps/
git commit -m "Test run exec_XYZ: discovered 3 new elements"
```

### 3. Use Descriptive Names in Stories

Good:
```
"Click on Study dropdown"  # Matches "Study dropdown" in map
"Click OSA01 checkbox"     # Matches "OSA01 checkbox" in map
```

Bad:
```
"Click Study"              # May not match exactly
"Click checkbox"           # Too generic
```

### 4. Review Discovered Elements

```bash
# Check what was discovered
cat element_maps/caninecommons.cancer.gov/explore_page.json | \
  jq '.elements[] | select(.source == "llm_discovery")'
```

### 5. Create Baselines Before Major Changes

```bash
# Before UI refresh
python -c "from utils.element_registry import get_registry; \
  get_registry().create_baseline('caninecommons.cancer.gov', 'explore')"

# Run tests on new UI
# Compare
python utils/compare_maps.py --domain ... --page ... --baseline 1.0
```

---

## 📁 File Structure

```
element_maps/
├── README.md                           ← This file
├── caninecommons.cancer.gov/
│   ├── home_page.json                  ← Current map
│   ├── explore_page.json               ← Current map
│   └── versions/                       ← Historical versions
│       ├── explore_page_v1.0.json      ← Baseline
│       ├── explore_page_v1.5.json      ← Added elements
│       └── explore_page_v2.0.json      ← UI changed
└── otherdomain.com/
    └── ...
```

---

## 🚀 Advanced Usage

### Parse HTML from Clipboard

```bash
# macOS
pbpaste > page.html
python utils/create_element_map.py --html page.html --url <URL>

# Linux
xclip -o > page.html
python utils/create_element_map.py --html page.html --url <URL>
```

### Compare Specific Versions

```bash
python utils/compare_maps.py \
  --domain caninecommons.cancer.gov \
  --page explore \
  --baseline 1.0
```

### Export for CI/CD

```bash
# In your CI pipeline
if ! python utils/compare_maps.py --domain ... --page ...; then
  echo "UI changes detected! Review before merging."
  exit 1
fi
```

---

## ❓ FAQ

**Q: Do I need to parse HTML for every test?**
A: No! Parse once per page, commit to Git, done.

**Q: What if UI changes?**
A: Run comparison tool to see exactly what changed. Update baseline if approved.

**Q: Can I manually edit element maps?**
A: Yes! They're JSON files. Edit selectors, add alternatives, etc.

**Q: What if element name doesn't match exactly?**
A: System does fuzzy matching. "Study" matches "Study dropdown".

**Q: Does this work with dynamic elements?**
A: Yes! LLM discovers them during tests, then they're saved to the map.

---

## 🎊 Benefits Summary

| Before | After |
|--------|-------|
| LLM discovers selectors every test | Uses cached selectors (fast!) |
| No idea what selectors work | Map tracks successful selectors |
| Tests fail, unsure why | Compare maps → see exact changes |
| Manual selector maintenance | Self-learning from successful tests |
| No version history | Full Git history of UI changes |

**This is production-grade QA automation!** 🚀
