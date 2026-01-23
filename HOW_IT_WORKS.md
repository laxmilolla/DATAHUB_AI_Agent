# AI Agent QA Automation - How It Works

## 🎯 Overview
An Excel-driven QA testing system that converts Excel test cases into executable Playwright TypeScript tests, then runs them automatically with screenshot capture and validation.

---

## 🏗️ Architecture

```
Excel File (Test Steps)
    ↓
Flask API (Web UI)
    ↓
Excel Validator
    ↓
TypeScript Code Generator
    ↓
Playwright Test Runner
    ↓
Results & Screenshots
```

---

## 🔄 Main Workflow: Excel-Driven
**Input:** Excel file with test steps  
**Process:**
1. User uploads Excel file via web UI (`/excel/upload`)
2. **Excel Validator** validates structure (columns: Step, URL, XPath, Action, Text Value, Wait Time, etc.)
3. **TypeScript Generator** (`excel_generator_ts.py`):
   - Reads Excel rows sequentially
   - Generates Playwright TypeScript code
   - Auto-populates element registry from Excel XPaths (Excel → JSON registry)
   - Creates `.spec.ts` file with proper waits, TOTP handling, table verification
4. **Test Runner** executes generated test:
   - Runs `npx playwright test` in background
   - Captures screenshots at each step
   - Validates assertions (table content, text presence, etc.)
5. Results displayed with step-by-step screenshots and validation status

**Key Components:**
- `REFACTOR/generator/excel_generator_ts.py` - TypeScript code generator
- `REFACTOR/generator/excel_validator.py` - Excel file validation
- `validator/typescript_test_runner.py` - Playwright test execution
- `element_maps/` - Element registry JSON files (auto-populated from Excel)

---

## 🧩 Core Components

### **1. Element Registry System**
- **Purpose:** Versioned storage of UI element selectors (XPaths)
- **Location:** `element_maps/{domain}/{page}.json`
- **Features:**
  - Auto-populated from Excel XPaths during test generation
  - Manual entry support via web UI
  - Registry lookup in generated test code
  - JSON registry becomes source of truth (test code references it)

### **2. Excel Structure**
Required columns:
- **Step** - Step number/identifier
- **URL** - Page URL to navigate to
- **XPath** - Element XPath selector
- **Action** - `click`, `fill`, `verify`, `wait`, `navigate`
- **Text Value** - Text to fill (for `fill` actions)
- **Functions** - Special functions like `TOTP` (optional)
- **Wait Time** - Wait duration in milliseconds (optional)
- **Object Type** - Element type: `button`, `input`, `link`, etc. (optional)

### **3. Code Generation Features**
- **TOTP Handling:** Auto-generates time-based codes for 2FA
- **Table Verification:** Supports `verify TABLE ColumnName=value` syntax
- **Smart Waits:** Handles page loads, debouncing, API calls
- **Registry Integration:** Generated code references JSON registry files
- **Error Handling:** Try-catch blocks, optional steps support

---

## 📊 Execution Flow

### **Excel-Driven Execution:**
```
1. Excel Upload → Validation → Metadata saved
2. User clicks "Generate TypeScript"
3. Generator reads Excel → TypeScript code created
4. Test file saved to storage/excel_tests/
5. Background thread runs: npx playwright test
6. Screenshots captured during test execution
7. Results updated: playwright_validation{}, playwright_screenshots[]
8. UI displays results with step-by-step screenshots
```

---

## 🎨 User Interface

### **Web UI (`web/templates/`):**
- **`index.html`** - Story input form
- **`excel_upload.html`** - Excel upload & validation
- **`results.html`** - Test results display with:
  - Status banner (success/failed/running)
  - Metrics (steps, passed, duration, screenshots)
  - Steps tab (with screenshots per step)
  - Playwright tab (test code & validation)
  - Download buttons (ZIP with .env, .spec.ts)

### **API Endpoints (`api/routes.py`):**
- `POST /excel/upload` - Upload Excel file (validates structure)
- `POST /excel/generate-ts` - Generate TypeScript from Excel
- `POST /executions/<id>/run-test` - Run generated Playwright test
- `GET /executions/<id>/results` - Get execution results
- `GET /api/excel/<id>/steps` - Get Excel step data
- `GET /api/excel/<id>/test-ts-zip` - Download test ZIP (with .env)
- `GET /api/screenshots/<filename>` - Serve screenshots

---

## 🔐 Key Features

### **Registry-Based Element Location:**
- Excel XPaths auto-populate JSON registry files
- Generated test code references registry (not hard-coded XPaths)
- Easy to update selectors by editing registry JSON

### **TOTP Support:**
- Auto-detects TOTP input fields
- Generates time-based codes
- Handles 2FA authentication flows

### **Table Verification:**
- Verify text in specific table columns
- Supports filtering and content checks
- Example: `verify TABLE Submission Name=spandana`

### **Screenshot Management:**
- Captured at key steps automatically
- Linked to specific actions/steps
- Displayed in results UI

---

## 📁 Key Directories

```
ai-agent-qa/
├── api/                # Flask API routes
├── web/                # Frontend templates & static files
│   ├── templates/
│   │   ├── excel_upload.html  # Excel upload UI
│   │   └── results.html        # Test results display
│   └── static/
├── REFACTOR/generator/ # Excel → TypeScript generator
│   ├── excel_generator_ts.py   # Main generator
│   ├── excel_validator.py      # Excel validation
│   └── excel_registry_helper.py # Registry population
├── validator/          # Test runner (Playwright execution)
│   └── typescript_test_runner.py
├── element_maps/       # Element registry JSON files (auto-populated)
│   └── {domain}/{page}.json
└── storage/            # Executions, screenshots, Excel files
    ├── excel_files/    # Uploaded Excel files
    ├── excel_tests/    # Generated .spec.ts files
    ├── executions/     # Execution results JSON
    └── screenshots/    # Test execution screenshots
```

---

## 🚀 Deployment

- **Server:** EC2 Ubuntu instance (`ubuntu@13.222.91.163`)
- **Path:** `~/DATAHUB_AI_Agent`
- **Process:** Flask app running on port 5000
- **Deployment:** Git pull → Restart Flask
- **Logs:** `flask.log` or `/tmp/flask.log`

---

## 💡 How It's Different

**Traditional Test Automation:**
- Static test scripts with hard-coded selectors
- Brittle XPaths scattered throughout code
- Manual maintenance when UI changes

**This System:**
- ✅ Excel-driven test definition (non-technical users)
- ✅ Registry-based element management (centralized selectors)
- ✅ Auto-generated TypeScript Playwright tests
- ✅ Automatic screenshot capture
- ✅ Table verification and TOTP support built-in
- ✅ Easy updates: Change registry JSON, regenerate test

---

**Last Updated:** January 2026  
**Browser Automation:** Playwright  
**Language:** Python (Backend) + TypeScript (Generated Tests)  
**Input Format:** Excel (.xlsx)  
**Output Format:** TypeScript Playwright (.spec.ts)
