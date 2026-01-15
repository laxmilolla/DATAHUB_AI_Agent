# 🤖 AI Agent QA - Project Handoff Document

**Date:** December 26, 2024  
**Project:** DATAHUB_AI_Agent (Self-Learning QA Automation)  
**Git Repo:** https://github.com/laxmilolla/DATAHUB_AI_Agent.git  
**EC2 Instance:** ubuntu@13.222.91.163:~/DATAHUB_AI_Agent  

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Key Features](#key-features)
4. [Element Registry System](#element-registry-system)
5. [Current Working State](#current-working-state)
6. [How to Run](#how-to-run)
7. [Recent Fixes & Improvements](#recent-fixes--improvements)
8. [File Structure](#file-structure)
9. [Testing Workflow](#testing-workflow)
10. [Next Steps](#next-steps)

---

## 🎯 Project Overview

**Mission:** Build a self-improving, regression-capable QA automation system that learns and remembers UI element selectors across test runs.

**Problem Solved:**
- Traditional automation breaks when UI changes
- Elements are re-discovered on every test run
- No historical tracking of what selectors worked
- No regression testing capability

**Solution:**
- **Element Registry:** JSON-based versioned storage of UI selectors
- **Self-Learning:** Agent discovers and saves selectors during successful runs
- **Prioritized Matching:** Smart fuzzy matching to find best selector
- **Regression Testing:** Git-versioned element maps detect UI changes
- **UI Management:** Web interface to parse HTML and manage element maps

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Story Input                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           Bedrock LLM (Claude Sonnet 4.5)               │
│  - Agentic loop for decision-making                     │
│  - Tool selection and execution                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│          BedrockPlaywrightAgent (Core Agent)            │
│  - Manages conversation with Bedrock                    │
│  - Executes browser automation tools                    │
│  - Integrates element registry                          │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌─────────────────┐
│  Playwright  │ │ Element  │ │  Flask Web UI   │
│   Browser    │ │ Registry │ │  (Management)   │
│  Automation  │ │  System  │ │                 │
└──────────────┘ └──────────┘ └─────────────────┘
```

**Key Components:**
1. **Bedrock LLM:** Drives decisions and understands context
2. **Playwright:** Executes browser automation
3. **Element Registry:** Stores and retrieves proven selectors
4. **Flask UI:** Allows manual element map creation/management

---

## 🔑 Key Features

### ✅ 1. Self-Learning Element Discovery
- During test execution, agent discovers elements using Playwright selectors
- After successful test completion, saves discovered elements to registry
- Example: `{"name": "Study dropdown", "selector": "[data-testid='Study-Facet']"}`

### ✅ 2. Prioritized Fuzzy Matching
When agent needs to click "Study dropdown":
1. **Checks registry first** (domain + page specific)
2. **Scoring algorithm:**
   - 100 points: Exact match
   - 80 points: Starts with keyword
   - 70 points: Ends with keyword
   - 60 points: Substring match
   - 40 points: Keyword match
   - +10 bonus: Accordion/dropdown types
3. **Tiebreaker:** Prefers shorter element names
4. **Keyword cleaning:** Strips technical keywords (data, testid, aria, etc.)

### ✅ 3. Graceful Fallback
- If no good match in registry → LLM takes over
- Agent uses Playwright's natural language selectors
- Prevents crashes, allows conditional steps (e.g., "click Continue if popup exists")

### ✅ 4. Regression Testing
- Element maps versioned in Git (`element_maps/domain/page.json`)
- Baseline snapshots (`versions/page_v1.0.json`)
- Can detect when UI changes break old selectors

### ✅ 5. Token Optimization
- `browser_snapshot` returns concise summaries (not full HTML)
- Prevents Bedrock token limit errors
- Format: `{title, url, element_counts, text_preview}`

### ✅ 6. Web UI for Element Management
- URL: `http://localhost:5001/element-maps`
- Features:
  - Paste HTML from browser inspect
  - Parse interactive elements
  - Edit/save element maps
  - View existing maps by domain/page

---

## 🗂️ Element Registry System

### Directory Structure:
```
element_maps/
├── README.md
├── caninecommons.cancer.gov/
│   ├── explore_page.json          # Current working map
│   └── versions/
│       └── explore_page_v1.0.json # Baseline snapshot
```

### Element Map Format (JSON):
```json
{
  "domain": "caninecommons.cancer.gov",
  "page": "explore_page",
  "created": "2024-12-26T10:30:00",
  "last_updated": "2024-12-26T12:45:00",
  "version": "1.0",
  "elements": [
    {
      "name": "Study dropdown",
      "selector": "[data-testid='Study-Facet']",
      "type": "accordion",
      "description": "Study filter accordion on explore page",
      "usage_count": 15,
      "last_used": "2024-12-26T12:45:00",
      "success_rate": 1.0
    }
  ]
}
```

### How It Works:

**1. Element Lookup (`_check_element_registry`):**
```python
# Agent needs to click "Study dropdown"
registry_result = self._check_element_registry("Study dropdown")
if registry_result:
    # Use cached selector
    selector = registry_result['selector']
else:
    # LLM discovers new selector
```

**2. Recording Discoveries:**
```python
# After successful click
self.discovered_elements.append({
    'name': 'Study dropdown',
    'selector': '[data-testid="Study-Facet"]',
    'type': 'accordion'
})
```

**3. Saving After Success:**
```python
# At end of test execution
if test_passed:
    for elem in self.discovered_elements:
        registry.add_element(domain, page, elem)
```

---

## ✅ Current Working State

### What's Deployed on EC2:
- **Path:** `/home/ubuntu/DATAHUB_AI_Agent`
- **Service:** Running on port 5001
- **Status:** ✅ Active
- **Last Deployment:** Dec 26, 2024

### What's Working:
✅ Agent navigates to `https://caninecommons.cancer.gov/#/`  
✅ Conditionally clicks "Continue" popup (doesn't crash if missing)  
✅ Clicks "Explore" button  
✅ Opens "Study" dropdown using registry lookup  
✅ Selects "GLIOMA01" from dropdown  
✅ Takes screenshots at each step  
✅ Saves execution results to `storage/executions/`  
✅ Registry prevents re-discovery of known elements  
✅ Token usage optimized (no more "Input too long" errors)  

### Known Good Test:
```
Story: "Go to https://caninecommons.cancer.gov/#/ 
        If there is a popup, click Continue 
        Click on Explore 
        Click on Study dropdown 
        Click on GLIOMA01"

Status: ✅ Passes reliably
Element Map: element_maps/caninecommons.cancer.gov/explore_page.json
```

---

## 🚀 How to Run

### **Local Development:**
```bash
# Navigate to project
cd /Users/lollal/Documents/ai-agent-qa

# Activate virtual environment
source venv/bin/activate  # or: . venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Set environment variables
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile  # or use AWS_ACCESS_KEY_ID/SECRET

# Start Flask app
python api/app.py

# Access UI
open http://localhost:5001
```

### **Run a Test (API):**
```bash
curl -X POST http://localhost:5001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "story": "Go to https://caninecommons.cancer.gov/#/ and click Explore",
    "execution_id": "test_001"
  }'
```

### **View Results:**
```bash
# Check execution logs
ls -la storage/executions/

# View screenshots
ls -la storage/screenshots/

# Open specific execution
cat storage/executions/exec_abc12345.json
```

### **EC2 Deployment:**
```bash
# SSH to EC2
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163

# Navigate to project
cd ~/DATAHUB_AI_Agent

# Check service status
sudo systemctl status ai-crdc-hub

# View logs
tail -f logs/app.log

# Restart service
sudo systemctl restart ai-crdc-hub
```

---

## 🔧 Recent Fixes & Improvements

### 🐛 **Bug Fixes:**

1. **JavaScript `return` Statement Error**
   - **Issue:** `SyntaxError: Illegal return statement` in `page.evaluate()`
   - **Fix:** Wrapped all JS code in IIFE: `(() => { ... })()`

2. **Playwright Selector in `querySelector`**
   - **Issue:** `text=Continue` not valid in `document.querySelector`
   - **Fix:** Use Playwright's `locator()` API for verification

3. **Timeout Errors on Missing Elements**
   - **Issue:** Agent crashed when "Continue" popup didn't appear
   - **Fix:** Graceful handling with shorter timeout + fallback

4. **Token Limit Exceeded**
   - **Issue:** `ValidationException: Input is too long for requested model`
   - **Fix:** Changed `browser_snapshot` to return summary instead of full HTML

5. **Wrong Element Matching**
   - **Issue:** Matched "Study Files(30) button" instead of "Study dropdown"
   - **Fix:** Enhanced prioritized scoring + keyword filtering

6. **Technical Keyword False Matches**
   - **Issue:** Keywords like "data", "testid" caused incorrect matches
   - **Fix:** Strip Playwright syntax and filter technical keywords before matching

### 🚀 **Improvements:**

1. **Smart Click Strategy:**
   - Try direct click
   - Try parent/sibling if occluded
   - Force click as last resort

2. **Dynamic URL Detection:**
   - `_get_domain_and_page()` always fetches current URL
   - Ensures correct element map lookup

3. **Discovered Element Tracking:**
   - Records all newly found elements during execution
   - Saves to registry only on successful test completion

4. **UI for Element Management:**
   - Created `/element-maps` interface
   - Parse HTML, view, edit, save element maps
   - No command-line needed

---

## 📁 File Structure

```
ai-agent-qa/
├── agent/
│   ├── __init__.py
│   ├── bedrock_agent.py              # Legacy agent (not used)
│   └── bedrock_playwright_agent.py   # 🔥 CORE AGENT (main file)
│
├── api/
│   ├── __init__.py
│   ├── app.py                        # Flask application entry
│   └── routes.py                     # API endpoints + UI routes
│
├── element_maps/                     # 🗂️ ELEMENT REGISTRY
│   ├── README.md
│   └── caninecommons.cancer.gov/
│       ├── explore_page.json
│       └── versions/
│           └── explore_page_v1.0.json
│
├── storage/
│   ├── executions/                   # Test execution results (JSON)
│   └── screenshots/                  # Browser screenshots (PNG)
│
├── utils/
│   ├── __init__.py
│   ├── compare_maps.py               # Compare element map versions
│   ├── create_element_map.py         # CLI tool to create maps
│   ├── element_registry.py           # 🔥 Registry manager
│   └── html_parser.py                # 🔥 HTML → element extraction
│
├── web/
│   ├── templates/
│   │   ├── index.html                # Home page
│   │   ├── element_maps.html         # Element map manager UI
│   │   └── results.html              # Test results viewer
│   └── static/
│       ├── css/style.css
│       └── js/app.js
│
├── scripts/
│   ├── setup.sh                      # Initial setup
│   └── start.sh                      # Start services
│
├── tests/
│   └── test_agent.py                 # Unit tests
│
├── requirements.txt                  # Python dependencies
├── QUICKSTART.md                     # Quick start guide
├── README.md                         # Project documentation
├── .env.example                      # Environment variable template
└── HANDOFF.md                        # 📄 THIS FILE

```

---

## 🧪 Testing Workflow

### **1. Manual Test via UI:**
1. Open `http://localhost:5001`
2. Enter user story (plain English)
3. Click "Execute"
4. View results + screenshots

### **2. Test with Element Map:**
```bash
# Pre-create element map
cd /Users/lollal/Documents/ai-agent-qa
python utils/create_element_map.py

# Run test - agent will use registry
curl -X POST http://localhost:5001/api/execute \
  -H "Content-Type: application/json" \
  -d '{"story": "Click Study dropdown"}'
```

### **3. Verify Registry Learning:**
```bash
# Check element map before test
cat element_maps/caninecommons.cancer.gov/explore_page.json

# Run successful test
# ...test completes...

# Check element map after - should see new elements
cat element_maps/caninecommons.cancer.gov/explore_page.json
```

### **4. Regression Testing:**
```bash
# Compare current map with baseline
python utils/compare_maps.py \
  element_maps/caninecommons.cancer.gov/explore_page.json \
  element_maps/caninecommons.cancer.gov/versions/explore_page_v1.0.json

# Output shows:
# - New elements
# - Changed selectors
# - Removed elements
```

---

## 🎯 Next Steps

### **Immediate Priorities:**

1. **Expand Element Maps:**
   - Create maps for other pages (home, detail views, etc.)
   - Use UI at `/element-maps` to paste HTML and parse

2. **Add More Test Cases:**
   - Different study selections (OSA01, GLIOMA01, etc.)
   - Multi-page workflows
   - Form filling and submissions

3. **Improve Matching Algorithm:**
   - Add similarity scoring (Levenshtein distance)
   - Weight recent successful matches higher
   - Learn from failures

4. **Monitoring & Alerts:**
   - Track element success rates
   - Alert when success rate drops below threshold
   - Suggest selector updates

### **Future Enhancements:**

1. **Multi-Site Support:**
   - Extend beyond caninecommons.cancer.gov
   - Create element maps for other sites

2. **Parallel Testing:**
   - Run multiple tests concurrently
   - Pool of browser contexts

3. **CI/CD Integration:**
   - GitHub Actions workflow
   - Automated regression tests on PR

4. **Visual Regression:**
   - Compare screenshots pixel-by-pixel
   - Detect visual changes

5. **AI-Powered Healing:**
   - When selector fails, try similar patterns
   - Learn from human corrections

---

## 💡 Key Insights & Learnings

### **What Works Well:**
- ✅ Element registry dramatically reduces test flakiness
- ✅ Fuzzy matching handles minor UI variations
- ✅ LLM fallback prevents complete failure
- ✅ Git versioning enables true regression testing
- ✅ Prioritized scoring handles ambiguous element names

### **What to Watch:**
- ⚠️ Token limits on very long conversations (mitigated by summaries)
- ⚠️ Bedrock rate limits on rapid test execution
- ⚠️ Playwright browser resource usage (clean up old processes)

### **Architecture Decisions:**
- **Why JSON over database?** Git versioning, human readability, no infra
- **Why Playwright over Selenium?** Better async support, modern API
- **Why Bedrock over OpenAI?** AWS integration, enterprise compliance
- **Why Flask over FastAPI?** Simpler for small API + UI combo

---

## 🔗 Important Links

- **GitHub Repo:** https://github.com/laxmilolla/DATAHUB_AI_Agent.git
- **EC2 Instance:** ubuntu@13.222.91.163:~/DATAHUB_AI_Agent
- **Local Dev:** http://localhost:5001
- **EC2 Prod:** http://13.222.91.163:5001 (check security groups)

---

## 📞 Contact & Context

**Developer:** Laxmi Lolla  
**Started:** December 2024  
**Current Status:** Fully functional, deployed to EC2  
**Test Site:** https://caninecommons.cancer.gov  

---

## 🎉 Summary

You now have a **self-learning QA automation agent** that:
1. ✅ Learns UI selectors during test execution
2. ✅ Saves them to Git-versioned JSON files
3. ✅ Reuses proven selectors on future runs
4. ✅ Enables true regression testing
5. ✅ Has a UI for manual element map management
6. ✅ Gracefully handles missing/conditional elements
7. ✅ Optimized for token usage and reliability

**Open this project in Cursor and you're ready to continue! 🚀**

---

*Generated: December 26, 2024*  
*For: Seamless project handoff when switching workspaces*

