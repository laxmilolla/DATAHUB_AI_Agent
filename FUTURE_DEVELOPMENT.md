# Future Development Roadmap - AI Test Automation System

**Document Version:** 1.0  
**Last Updated:** December 27, 2025  
**Status:** Planning Phase

---

## 🎯 Executive Summary

This document outlines the evolution from **AI Test Runner** to **AI Test Generator + CI/CD Runner**. The system will support the complete lifecycle from initial test discovery through automated CI/CD execution and intelligent re-discovery when tests fail.

**Key Benefits:**
- **Cost Savings:** 81% reduction vs manual testing
- **Speed:** 85% faster test creation and maintenance
- **Intelligence:** Self-learning system that improves over time
- **Traceability:** Complete requirement → test → execution tracking

---

## 📋 Table of Contents

1. [Core Concept: Execution ID Lifecycle](#1-core-concept-execution-id-lifecycle)
2. [Storage Architecture](#2-storage-architecture)
3. [Test Generation System](#3-test-generation-system)
4. [Metrics & Dashboards](#4-metrics--dashboards)
5. [Requirements Traceability Matrix (RTM)](#5-requirements-traceability-matrix-rtm)
6. [User Approval Workflow](#6-user-approval-workflow)
7. [Implementation Phases](#7-implementation-phases)
8. [Technical Requirements](#8-technical-requirements)
9. [API Specifications](#9-api-specifications)
10. [Success Metrics](#10-success-metrics)

---

## 1. Core Concept: Execution ID Lifecycle

### 1.1 The Three Phases

```
PHASE 1: INITIAL DISCOVERY (AI Agent - Smart but Expensive)
User writes story → AI discovers elements → User approves → exec_5489b872 created
                    ↓
PHASE 2: CI/CD EXECUTION (Playwright - Fast and Cheap)
Generated test runs daily → All pass ✅ → 150 successful runs
                    ↓
PHASE 3: SMART RE-DISCOVERY (AI Agent - Context-Aware)
Test fails ❌ → User requests re-discovery with exec_5489b872 ID
→ AI loads context → Finds changes → exec_a1b2c3d4 created
```

### 1.2 Execution ID as "DNA"

Every execution ID serves as:
- **Unique identifier** for a test discovery session
- **Link** between AI discovery and generated Playwright code
- **Context provider** for re-discovery when UI changes
- **Audit trail** for compliance and debugging
- **Version control** for test evolution

### 1.3 Key Insight

**Current Problem:** Registry only tracks usage count, not HOW elements were found.

**Solution:** Store complete discovery metadata per execution:
- Tree climbing depth
- AI disambiguation choices
- LLM reasoning
- Validation results
- Screenshots at key moments

---

## 2. Storage Architecture

### 2.1 Directory Structure

```
storage/
├── stories/                          # User stories (input)
│   ├── exec_5489b872_story.txt
│   └── exec_a1b2c3d4_story.txt
│
├── registry_snapshots/                # Registry state at execution time
│   ├── exec_5489b872_registry.json
│   └── exec_a1b2c3d4_registry.json
│
├── discovery_metadata/                # HOW elements were found (CRITICAL!)
│   ├── exec_5489b872_discovery.json
│   └── exec_a1b2c3d4_discovery.json
│
├── generated_tests/                   # Test generation records
│   ├── exec_5489b872_test.json
│   └── exec_a1b2c3d4_test.json
│
├── executions/                        # Execution results (EXISTING)
│   ├── exec_5489b872.json
│   └── exec_a1b2c3d4.json
│
├── screenshots/                       # Screenshots per execution
│   ├── exec_5489b872/
│   └── exec_a1b2c3d4/
│
└── rtm/                              # Requirements Traceability Matrix
    ├── user_stories.json
    ├── test_cases.json
    └── traceability.json
```

### 2.2 Critical New Storage: Discovery Metadata

**File:** `storage/discovery_metadata/exec_5489b872_discovery.json`

```json
{
  "execution_id": "exec_5489b872",
  "elements_discovered": [
    {
      "name": "Tumor Classification",
      "story_reference": "click on the Tumor classification",
      "original_query": "text=Tumor Classification",
      
      "discovery": {
        "method": "tree_climbing",
        "found_at_depth": 2,
        "element_matched": "<div>Tumor classification</div>",
        "ancestor_used": "<div role='button' aria-expanded='false'>",
        "ancestor_properties": {
          "tag": "div",
          "role": "button",
          "aria_expanded": "false"
        }
      },
      
      "ai_disambiguation": {
        "triggered": true,
        "candidates_count": 2,
        "chosen_index": 1,
        "llm_reasoning": "Story says 'sidebar filter dropdown' - chose accordion"
      },
      
      "selector_used": "div[role='button'][aria-expanded]:has-text('Tumor Classification')",
      
      "validation": {
        "type": "accordion_expanded",
        "pre_state": "aria-expanded=false",
        "post_state": "aria-expanded=true",
        "screenshot_before": "005_pre_click_Tumor_Classification.png",
        "screenshot_after": "006_post_click_Tumor_Classification.png"
      },
      
      "success": true
    }
  ]
}
```

**Why This Is Critical:**
- Enables intelligent re-discovery
- Powers test generation
- Provides debugging context
- Tracks learning over time

### 2.3 Storage Estimates

| Item | Size per Execution | For 1000 Executions |
|------|-------------------|---------------------|
| Story | ~1 KB | 1 MB |
| Registry Snapshot | 50-200 KB | 50-200 MB |
| Discovery Metadata | 5-20 KB | 5-20 MB |
| Execution Results | 10-50 KB | 10-50 MB |
| Test Generation Record | 2-5 KB | 2-5 MB |
| Screenshots | 1-5 MB | 1-5 GB |
| **TOTAL** | **~1-6 MB** | **~1-6 GB** |

**Conclusion:** Storage is manageable, even at scale.

---

## 3. Test Generation System

### 3.1 Concept

**Transform AI discoveries into static Playwright code for fast CI/CD execution.**

### 3.2 Generated Test Example

```typescript
// tests/generated/ccdi_tumor_filter.spec.ts
// 
// 🔗 SOURCE EXECUTION: exec_5489b872
// 📅 Generated: 2025-12-27T02:25:00Z
// ✅ Approved by: user@example.com
// 
// Re-discovery URL: http://ai-agent.local/re-discover/exec_5489b872
// View original run: http://ai-agent.local/results/exec_5489b872

import { test, expect } from '@playwright/test';

test.describe('CCDI Tumor Classification Filter', () => {
  
  test('should filter by Primary tumor classification', {
    tag: ['@ccdi', '@filters', '@exec_5489b872'],
    annotation: {
      type: 'source_execution',
      description: 'exec_5489b872'
    }
  }, async ({ page }) => {
    
    // Step 1: Navigate
    await test.step('Navigate to explore page', async () => {
      await page.goto('https://ccdi.cancer.gov/explore');
      await expect(page).toHaveTitle(/CCDI Hub/);
    });
    
    // Step 2: Expand SAMPLES filter
    // AI Note: Sidebar accordion found via AI disambiguation (chose 1 of 3)
    await test.step('Click SAMPLES filter in sidebar', async () => {
      const samplesAccordion = page.locator('div[role="button"]:has-text("SAMPLES")').first();
      await samplesAccordion.click();
      await expect(samplesAccordion).toHaveAttribute('aria-expanded', 'true');
    });
    
    // Step 3: Expand Tumor Classification
    // AI Note: Found via tree climbing at depth 2 (grandparent with role=button)
    await test.step('Click Tumor Classification filter', async () => {
      const tumorClassAccordion = page.locator('div[role="button"][aria-expanded]')
        .filter({ hasText: 'Tumor classification' });
      
      await tumorClassAccordion.click();
      await expect(tumorClassAccordion).toHaveAttribute('aria-expanded', 'true');
      await page.waitForSelector('input[id*="Tumor classification"]', { timeout: 5000 });
    });
    
    // Step 4: Select Primary checkbox
    await test.step('Select Primary checkbox', async () => {
      const primaryCheckbox = page.locator('input[type="checkbox"][id*="Primary"]').first();
      await primaryCheckbox.check();
      await expect(page).toHaveURL(/tumor_classification=Primary/);
      await expect(primaryCheckbox).toBeChecked();
    });
  });
  
});
```

### 3.3 Code Generator Components

**New File:** `utils/playwright_generator.py`

```python
class PlaywrightCodeGenerator:
    def generate_from_execution(self, exec_id: str, approved_elements: list) -> str:
        """Generate Playwright test from successful execution"""
        
        # 1. Load execution results
        execution = self._load_execution(exec_id)
        
        # 2. Load discovery metadata
        discovery = self._load_discovery_metadata(exec_id)
        
        # 3. Generate test code
        code = self._generate_test_structure(execution)
        
        # 4. Add AI discovery comments
        code = self._add_discovery_comments(code, discovery)
        
        # 5. Add traceability metadata
        code = self._add_traceability_metadata(code, exec_id)
        
        return code
```

### 3.4 Benefits

| Phase | Speed | Cost | Intelligence | Use Case |
|-------|-------|------|--------------|----------|
| AI Discovery | 60-120s | $0.05-0.10 | High | Initial automation, Re-discovery |
| Generated Tests | 5-10s | $0.00 | None | Daily CI/CD regression |

**For 100 tests run daily:**
- AI Agent: $5-10/day, 3+ hours
- Generated: $0/day, 10 minutes ✅

---

## 4. Metrics & Dashboards

### 4.1 Three-Level Approach

```
LEVEL 1: EXECUTIVE (What management cares about)
↓
LEVEL 2: OPERATIONAL (What QA teams care about)
↓
LEVEL 3: TECHNICAL (What developers care about)
```

### 4.2 Level 1: Executive Dashboard

**Key Metrics:**
- 💰 **Cost Savings:** $12,450/month (81% reduction vs manual)
- ⚡ **Time Savings:** 320 hours/month
- ✅ **Success Rate:** 99.2% (245/247 tests)
- 📈 **Test Coverage:** 247 tests across 45 pages
- 🤖 **Automation Rate:** 94% automated

**Display:**
```
┌─────────────────────────────────────────────────────┐
│  💰 Cost Saved    ⚡ Time Saved    ✅ Success Rate   │
│    $12,450          320 hours         99.2%         │
│   vs Manual        vs Manual       (245/247)        │
│   ↑ 23% MoM       ↑ 15% MoM        ↑ 2.1% MoM       │
└─────────────────────────────────────────────────────┘
```

### 4.3 Level 2: Operational Dashboard

**Key Metrics:**
- 🏥 **Test Health:** By domain (green/yellow/red)
- 🔄 **Re-Discovery Activity:** Frequency and reasons
- 🎯 **Success Rate by Method:** Tree climbing vs AI disambiguation
- 🧪 **Element Registry Growth:** Elements added over time
- 🚀 **CI/CD Performance:** Pass rate, duration trends

### 4.4 Level 3: Technical Dashboard

**Key Metrics:**
- 🔍 **Discovery Method Stats:** Tree climbing depth distribution
- 🧠 **AI Performance:** LLM tokens, cost, response time
- 💰 **Cost Breakdown:** LLM vs Infrastructure
- ⚙️ **System Performance:** Execution time, API latency
- 🗂️ **Deep Dive:** Per-execution analysis

### 4.5 API Endpoints

```python
GET /api/metrics/executive
GET /api/metrics/operational
GET /api/metrics/technical
GET /api/metrics/trends/<metric_name>?days=30
```

---

## 5. Requirements Traceability Matrix (RTM)

### 5.1 Purpose

**Answer the PM question:** "How many user stories/test cases were automated?"

### 5.2 RTM Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  RTM Summary                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ User Stories │  │ Test Cases   │  │ Automated    │ │
│  │     45       │  │     247      │  │  232 (94%)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  Coverage by Module:                                     │
│  Authentication     ████████████████████ 100% (15/15)   │
│  Data Filtering     ██████████████████░░  92% (46/50)   │
│  Search             ████████████████████ 100% (12/12)   │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Data Model

**User Story:**
```json
{
  "user_story_id": "US-015",
  "title": "Filter samples by tumor classification",
  "module": "Data Filtering",
  "test_cases": ["TC-045", "TC-046", "TC-047", ...],
  "automation_status": {
    "total_tests": 8,
    "automated": 7,
    "automation_percentage": 87.5
  },
  "execution_status": {
    "last_run": "2025-12-27T07:00:00Z",
    "pass_rate": 85.7
  }
}
```

**Test Case:**
```json
{
  "test_case_id": "TC-046",
  "user_story_id": "US-015",
  "title": "Expand Tumor Classification nested filter",
  "automation": {
    "is_automated": true,
    "execution_id": "exec_5489b872",
    "test_script": "tests/generated/ccdi_tumor_filter.spec.ts"
  },
  "last_execution": {
    "execution_id": "exec_5489b872",
    "status": "Passed",
    "timestamp": "2025-12-27T07:00:00Z"
  }
}
```

### 5.4 Export Options

- **Excel:** Multi-sheet workbook with summary, full RTM, coverage
- **PDF:** Formatted report for stakeholders
- **JIRA Integration:** Bi-directional sync with test management tools

### 5.5 API Endpoints

```python
GET /api/rtm/summary
GET /api/rtm/user-stories
GET /api/rtm/user-stories/<story_id>
GET /api/rtm/test-cases/<test_id>
GET /api/rtm/coverage/<module>
GET /api/rtm/export/excel
GET /api/rtm/export/pdf
```

---

## 6. User Approval Workflow

### 6.1 The Flow

```
1. AI Test Runs Successfully ✅
         ↓
2. User Reviews Results
   - Sees screenshots
   - Sees all actions
   - Confirms test is correct
         ↓
3. User Clicks "Approve & Generate"
         ↓
4. System Actions (Automatic):
   a. Update element registry with discoveries
   b. Generate Playwright test code
   c. Save to tests/generated/
   d. Link execution_id to generated test
   e. Create RTM entries
         ↓
5. Optional: Validate generated test
   - Run it immediately
   - Compare results
         ↓
6. Commit to Git (optional)
```

### 6.2 UI Mockup

```
┌─────────────────────────────────────────────────────────┐
│ Execution: exec_5489b872 ✅ Success                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ [View Screenshots]  [View Actions]                       │
│                                                          │
│ ┌───────────────────────────────────────────────────┐  │
│ │ 🎯 Elements Discovered in This Test               │  │
│ │                                                    │  │
│ │ 3 new successful elements found:                  │  │
│ │                                                    │  │
│ │ ☑ SAMPLES (Sidebar Accordion)                     │  │
│ │   Method: AI Disambiguation (chose 1 of 3)        │  │
│ │   Result: ✅ Expanded                             │  │
│ │                                                    │  │
│ │ ☑ Tumor Classification (Nested Accordion)         │  │
│ │   Method: Tree Climbing (depth 2)                 │  │
│ │   Result: ✅ Expanded (aria-expanded: true)       │  │
│ │                                                    │  │
│ │ ☑ Primary (Checkbox)                              │  │
│ │   Method: AI Disambiguation (chose 1 of 2)        │  │
│ │   Result: ✅ Selected (URL changed)               │  │
│ │                                                    │  │
│ │ Test Name: [ccdi_tumor_filter____________]        │  │
│ │ Language: [TypeScript ▼]                          │  │
│ │ ☑ Update element registry                         │  │
│ │ ☑ Add to RTM                                      │  │
│ │ ☐ Validate generated test immediately             │  │
│ │                                                    │  │
│ │ [Approve & Generate Test] [Review First]          │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 6.3 API Endpoint

```python
POST /api/executions/<exec_id>/approve-and-generate
Body: {
  "test_name": "ccdi_tumor_filter",
  "elements": ["SAMPLES", "Tumor Classification", "Primary"],
  "update_registry": true,
  "add_to_rtm": true,
  "validate": false,
  "language": "typescript"
}

Response: {
  "success": true,
  "test_file": "tests/generated/ccdi_tumor_filter.spec.ts",
  "registry_updated": true,
  "rtm_updated": true,
  "execution_id": "exec_5489b872"
}
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Store discovery metadata

**Tasks:**
- [ ] Create `storage/discovery_metadata/` directory
- [ ] Implement discovery metadata tracking in `bedrock_playwright_agent.py`
- [ ] Save metadata after each successful execution
- [ ] Test with existing exec_5489b872

**Deliverable:** Discovery metadata JSON files for all future executions

**Success Criteria:** Can view HOW each element was discovered

---

### Phase 2: Registry Snapshots (Weeks 3-4)
**Goal:** Capture registry state at execution time

**Tasks:**
- [ ] Create `storage/registry_snapshots/` directory
- [ ] Snapshot registry before each execution
- [ ] Implement registry comparison utility
- [ ] Add registry diff view to UI

**Deliverable:** Registry snapshots linked to executions

**Success Criteria:** Can compare registry state "then vs now"

---

### Phase 3: Test Generation (Weeks 5-8)
**Goal:** Generate Playwright tests from executions

**Tasks:**
- [ ] Implement `PlaywrightCodeGenerator` class
- [ ] Add selector generation for different discovery methods
- [ ] Create test templates
- [ ] Build approval UI
- [ ] Implement validation (run generated test immediately)
- [ ] Add Git commit integration

**Deliverable:** One-click test generation from successful executions

**Success Criteria:** Generated test passes on first run

---

### Phase 4: RTM Implementation (Weeks 9-12)
**Goal:** Full requirements traceability

**Tasks:**
- [ ] Create RTM data models (UserStory, TestCase)
- [ ] Build RTM dashboard UI
- [ ] Implement Excel/PDF export
- [ ] Add JIRA integration
- [ ] Create user story → test case linking
- [ ] Implement coverage reports

**Deliverable:** Complete RTM system

**Success Criteria:** PM can answer "How many stories automated?" instantly

---

### Phase 5: Metrics Dashboard (Weeks 13-16)
**Goal:** Executive, Operational, and Technical dashboards

**Tasks:**
- [ ] Design 3-level dashboard hierarchy
- [ ] Implement metrics calculation APIs
- [ ] Build dashboard UI (charts, cards, tables)
- [ ] Add real-time updates
- [ ] Implement ROI calculator
- [ ] Create scheduled reports

**Deliverable:** Comprehensive metrics system

**Success Criteria:** Executives can see business value at a glance

---

### Phase 6: Re-Discovery (Weeks 17-20)
**Goal:** Smart re-discovery using execution context

**Tasks:**
- [ ] Implement re-discovery API
- [ ] Load previous execution context
- [ ] Use context to guide discovery (e.g., try depth 2 first)
- [ ] Build execution comparison UI
- [ ] Show before/after diffs
- [ ] Add replacement chain tracking

**Deliverable:** Context-aware re-discovery system

**Success Criteria:** Re-discovery is 50% faster than initial discovery

---

### Phase 7: CI/CD Integration (Weeks 21-24)
**Goal:** Seamless CI/CD integration

**Tasks:**
- [ ] Create GitHub Actions workflows
- [ ] Implement failure reporting API
- [ ] Auto-trigger re-discovery on CI/CD failure
- [ ] Add test health monitoring
- [ ] Create alerting system
- [ ] Build CI/CD performance dashboard

**Deliverable:** Full CI/CD integration

**Success Criteria:** Failed CI/CD tests automatically trigger re-discovery

---

## 8. Technical Requirements

### 8.1 Backend

**New Dependencies:**
```python
# requirements.txt additions
openpyxl==3.1.2          # Excel export
reportlab==4.0.7         # PDF generation
jira==3.5.0              # JIRA integration
celery==5.3.4            # Background tasks
redis==5.0.1             # Task queue
```

**New Python Modules:**
- `utils/playwright_generator.py` - Test code generation
- `utils/rtm_manager.py` - RTM operations
- `utils/metrics_calculator.py` - Metrics computation
- `utils/jira_integration.py` - JIRA sync
- `api/metrics.py` - Metrics API endpoints
- `api/rtm.py` - RTM API endpoints
- `api/test_generation.py` - Test generation endpoints

### 8.2 Frontend

**New Pages:**
- `/dashboard` - Main metrics dashboard
- `/rtm` - Requirements traceability matrix
- `/execution/<id>/approve` - Approval workflow
- `/compare/<exec_1>/<exec_2>` - Execution comparison

**UI Components:**
- MetricsCard
- TrendChart (using Chart.js)
- RTMTable
- ApprovalPanel
- ComparisonView

### 8.3 Database (Optional)

**Consider adding PostgreSQL for:**
- User stories and test cases (RTM)
- Metrics history (time-series data)
- User management (approvals, roles)

**Schema:**
```sql
CREATE TABLE user_stories (
  id VARCHAR PRIMARY KEY,
  title TEXT,
  description TEXT,
  module VARCHAR,
  priority VARCHAR
);

CREATE TABLE test_cases (
  id VARCHAR PRIMARY KEY,
  user_story_id VARCHAR REFERENCES user_stories(id),
  title TEXT,
  is_automated BOOLEAN,
  execution_id VARCHAR
);

CREATE TABLE executions (
  id VARCHAR PRIMARY KEY,
  story TEXT,
  status VARCHAR,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);

CREATE TABLE metrics (
  id SERIAL PRIMARY KEY,
  metric_name VARCHAR,
  metric_value FLOAT,
  timestamp TIMESTAMP
);
```

### 8.4 Infrastructure

**Current:**
- AWS EC2 (Flask app)
- AWS Bedrock (LLM)
- File storage (JSON)

**Future Additions:**
- AWS RDS (PostgreSQL for RTM/metrics)
- AWS S3 (Screenshot storage, offload from EC2)
- Redis (Celery task queue)
- CloudWatch (Monitoring and alerts)

---

## 9. API Specifications

### 9.1 Test Generation APIs

```python
# Approve execution and generate test
POST /api/executions/<exec_id>/approve-and-generate
Body: {
  "test_name": "string",
  "elements": ["string"],
  "update_registry": boolean,
  "add_to_rtm": boolean,
  "validate": boolean,
  "language": "typescript" | "javascript" | "python",
  "user_story_id": "string" (optional)
}
Response: {
  "success": boolean,
  "test_file": "string",
  "test_code": "string",
  "validation_result": object (if validate=true)
}

# Generate test code (preview, no save)
POST /api/executions/<exec_id>/generate-test-preview
Body: { same as above }
Response: { "code": "string" }

# Validate generated test
POST /api/test-generation/validate
Body: { "code": "string", "exec_id": "string" }
Response: { 
  "passed": boolean, 
  "duration": float,
  "differences": [string]
}
```

### 9.2 Re-Discovery APIs

```python
# Trigger re-discovery based on previous execution
POST /api/re-discover/<exec_id>
Body: {
  "auto_approve": boolean (optional),
  "compare_screenshots": boolean (optional)
}
Response: {
  "original_exec_id": "string",
  "new_exec_id": "string",
  "status": "running" | "completed",
  "compare_url": "string"
}

# Compare two executions
GET /api/compare/<exec_id_1>/<exec_id_2>
Response: {
  "original": object,
  "updated": object,
  "differences": {
    "elements_changed": [object],
    "discovery_methods_changed": [object],
    "selectors_changed": [object]
  },
  "screenshot_diffs": [object]
}

# Report CI/CD failure
POST /api/failures/report
Body: {
  "execution_id": "string",
  "failed_at": "timestamp",
  "ci_cd_run": "string",
  "error": "string",
  "auto_re_discover": boolean
}
Response: { "success": boolean }
```

### 9.3 Metrics APIs

```python
# Get executive metrics
GET /api/metrics/executive?days=30
Response: {
  "cost_savings": float,
  "time_savings": float,
  "success_rate": float,
  "test_coverage": object,
  "automation_rate": float
}

# Get operational metrics
GET /api/metrics/operational?days=30
Response: {
  "test_health": [object],
  "re_discovery": object,
  "discovery_methods": object,
  "ci_cd_performance": object
}

# Get technical metrics
GET /api/metrics/technical?days=30
Response: {
  "tree_climbing": object,
  "ai_disambiguation": object,
  "cost_breakdown": object,
  "system_performance": object
}

# Get metric time series
GET /api/metrics/trends/<metric_name>?days=30
Response: {
  "metric": "string",
  "data": [{"timestamp": "string", "value": float}]
}
```

### 9.4 RTM APIs

```python
# Get RTM summary
GET /api/rtm/summary
Response: {
  "total_user_stories": int,
  "total_test_cases": int,
  "automated_tests": int,
  "automation_percentage": float,
  "pass_rate": float
}

# List all user stories
GET /api/rtm/user-stories?module=string&status=string
Response: [
  {
    "id": "string",
    "title": "string",
    "module": "string",
    "test_count": int,
    "automated_count": int
  }
]

# Get user story details
GET /api/rtm/user-stories/<story_id>
Response: {
  "id": "string",
  "title": "string",
  "description": "string",
  "test_cases": [object],
  "automation_status": object
}

# Export RTM
GET /api/rtm/export/excel
GET /api/rtm/export/pdf
Response: File download

# Create/Update user story
POST /api/rtm/user-stories
PUT /api/rtm/user-stories/<story_id>
Body: {
  "title": "string",
  "description": "string",
  "module": "string",
  "priority": "string"
}

# Link test case to user story
POST /api/rtm/link-test-case
Body: {
  "user_story_id": "string",
  "test_case_id": "string",
  "execution_id": "string"
}
```

---

## 10. Success Metrics

### 10.1 Adoption Metrics

**Target (6 months post-launch):**
- 90% of user stories have linked test cases
- 95% automation rate
- 50+ user stories automated
- 250+ test cases generated

### 10.2 Performance Metrics

**Target:**
- Test generation time: < 5 seconds
- Re-discovery time: < 2 minutes
- CI/CD test execution: < 15 minutes for full suite
- Dashboard load time: < 2 seconds

### 10.3 Quality Metrics

**Target:**
- Generated test first-run success: > 95%
- Test pass rate: > 98%
- Re-discovery success rate: > 90%
- False positive rate: < 2%

### 10.4 Business Metrics

**Target (vs manual testing):**
- Cost reduction: > 75%
- Time savings: > 80%
- Defects found: +25% (earlier detection)
- Test maintenance time: -70%

### 10.5 User Satisfaction Metrics

**Target:**
- PM satisfaction with RTM: 4.5+/5
- Developer satisfaction with CI/CD integration: 4.5+/5
- Executive satisfaction with cost savings: 4.5+/5
- QA satisfaction with re-discovery speed: 4.5+/5

---

## 11. Risk Assessment

### 11.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Generated tests brittle | High | Medium | Extensive validation, gradual rollout |
| LLM costs exceed budget | Medium | Low | Monitor usage, implement rate limits |
| Storage growth too fast | Medium | Low | Implement retention policies, S3 archival |
| Re-discovery accuracy low | High | Medium | Continuous improvement, user feedback loop |

### 11.2 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Low user adoption | High | Medium | Training, documentation, showcase value |
| PM doesn't use RTM | Medium | Low | Regular demos, export features |
| Executive doesn't see ROI | High | Low | Clear cost savings dashboard |
| QA resistance to AI | Medium | Medium | Gradual introduction, show time savings |

---

## 12. Open Questions

1. **Storage:**
   - Keep JSON files or migrate to PostgreSQL?
   - S3 for screenshots or keep on EC2?
   - Retention policy for old executions?

2. **Test Generation:**
   - Support Python Playwright in addition to TypeScript?
   - Generate tests in other frameworks (Selenium, Cypress)?
   - How to handle test updates when UI changes slightly?

3. **RTM:**
   - Bi-directional JIRA sync or read-only import?
   - Support other tools (Azure DevOps, Jama)?
   - Manual test case entry or only from AI discoveries?

4. **Metrics:**
   - Real-time dashboard updates (WebSocket)?
   - Scheduled email reports?
   - Slack/Teams integration for alerts?

5. **Re-Discovery:**
   - Automatic re-discovery on CI/CD failure?
   - Manual approval required before updating tests?
   - Keep historical test versions?

---

## 13. Appendix

### 13.1 Key Terms

- **Execution ID:** Unique identifier for each test discovery session (e.g., exec_5489b872)
- **Discovery Metadata:** Detailed information about HOW elements were found
- **Tree Climbing:** Technique to find interactive ancestors in DOM hierarchy
- **AI Disambiguation:** Using LLM to choose between multiple matching elements
- **Generated Test:** Static Playwright code created from AI discovery
- **RTM:** Requirements Traceability Matrix - links user stories to test cases
- **Re-Discovery:** Re-running AI discovery when a test fails due to UI changes

### 13.2 Reference Links

- Current System: http://13.222.91.163:5000
- GitHub Repo: https://github.com/laxmilolla/DATAHUB_AI_Agent
- Handoff Document: `/handoff.md`
- Validation Improvements: `/VALIDATION_IMPROVEMENTS.md`
- Screenshot Fixes: `/SCREENSHOT_FIXES.md`

### 13.3 Contact

- Project Lead: [Name]
- Technical Lead: [Name]
- Product Manager: [Name]

---

**Document Status:** Draft for Review  
**Next Steps:** Review with team, prioritize phases, begin Phase 1 implementation

**Last Updated:** December 27, 2025

