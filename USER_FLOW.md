# AI Agent QA - User Flow Guide

## Overview
This application has two main workflows:
1. **Main App** (`/`): Execute test stories directly (login must be in story)
2. **Instructions → Excel** (`/instructions`): Converts instructions to Excel (auto-handles login)

---

## 🎯 Flow 1: Main App - Execute Test Story

**Page**: `/` (Home)

**What it does:**
- Executes test stories using AI Agent (Claude)
- **Login is NOT handled automatically** - you must include login steps in your story
- Uses Playwright to automate browser actions
- Records discovered elements and XPaths
- Generates execution results with screenshots

**User Flow:**
1. Go to `http://localhost:5000/`
2. Enter your complete test story (including login if needed)
   ```
   Example:
   Navigate to https://hub-stage.datacommons.cancer.gov/
   Click Continue button
   Click Login link
   Enter email: test@example.com
   Enter password: Test123!
   Click Submit
   Fill TOTP code
   Click Submit
   Navigate to data submissions page
   Click Program dropdown
   Select NCI
   ```
3. Click "Execute Test"
4. Agent interprets and executes each step
5. View results with discovered elements and XPaths

**Use Case**: Quick testing, validation, or when you want full control over the story

---

## 🎯 Flow 2: Instructions → Excel Test Case (Auto-Login)

**Page**: `/instructions`

**What it does:**
- Converts natural language instructions to Excel test files
- **Automatically handles login** (runs steps 1-12 from `test_case.xlsx`)
- Then executes your instructions
- Generates Excel file with all steps + XPaths

**User Flow:**
1. Go to `http://localhost:5000/instructions`
2. Enter ONLY your test instructions (no login needed)
   ```
   Example:
   On data submissions page, pick NCI from Program dropdown
   ```
3. Click "Execute Instructions"
4. System automatically:
   - **Phase 1**: Runs login steps (1-12) from `test_case.xlsx`
   - **Phase 2**: Executes your instructions
   - **Phase 3**: Generates Excel file
5. Download Excel file with all steps

**Use Case**: Creating reusable test cases when you want login handled automatically

---

## 🎯 Flow 3: Excel → Playwright Code

**Page**: `/excel-upload`

**What it does:**
- Upload Excel test file
- Validates Excel structure
- Generates Playwright Python code from Excel steps

**User Flow:**
1. Go to `http://localhost:5000/excel-upload`
2. Upload Excel file (from Flow 2 or any Excel test file)
3. Click "Generate Test"
4. System converts Excel to Python code
5. Download Python test file

**Use Case**: Converting Excel test cases to executable Python scripts

---

## 🔄 Complete Workflow Example

### **Scenario: Test "Selecting NCI from Program dropdown"**

**Option A: Using Main App (Manual Login)**
```
1. Go to http://localhost:5000/
2. Enter complete story:
   Navigate to https://hub-stage.datacommons.cancer.gov/
   Click Continue
   Click Login
   Enter email: test@example.com
   Enter password: Test123!
   Click Submit
   Fill TOTP code
   Click Submit
   Navigate to data submissions page
   Click Program dropdown
   Select NCI
3. Execute
4. View results
```

**Option B: Using Instructions Page (Auto-Login)**
```
1. Go to http://localhost:5000/instructions
2. Enter ONLY: "On data submissions page, pick NCI from Program dropdown"
3. Execute Instructions
4. System auto-logs in, then executes your instruction
5. Download Excel file
6. (Optional) Upload Excel to /excel-upload to generate Python code
```

---

## 📊 Key Differences

| Feature | Main App (`/`) | Instructions Page (`/instructions`) |
|---------|----------------|-----------------------------------|
| **Login Handling** | ❌ Manual (must include in story) | ✅ Automatic (uses test_case.xlsx) |
| **Input** | Complete test story | Just your test steps |
| **Output** | Execution results | Excel file |
| **Use Case** | Quick testing | Creating test cases |

---

## 📋 Detailed Flows

### **Main App Flow** (`/`)

```
User enters complete story (including login)
    ↓
Agent (Claude) interprets story
    ↓
Playwright executes step by step
    ↓
Records discovered elements & XPaths
    ↓
Generates execution results
    ↓
User views results, screenshots, discoveries
```

**Note**: User must include login steps in the story

---

### **Instructions Page Flow** (`/instructions`)

```
User enters test instructions (no login)
    ↓
[PHASE 1: Auto-Login]
    ↓
Reads test_case.xlsx (steps 1-12)
    ↓
Executes login automatically:
  - Navigate to hub
  - Click Continue
  - Click Login
  - Fill email/password
  - Handle TOTP
  - Wait for redirect
    ↓
[PHASE 2: Execute Instructions]
    ↓
Agent executes user's instructions
    ↓
Records XPaths for each action
    ↓
[PHASE 3: Generate Excel]
    ↓
Combines login steps + instruction steps
    ↓
Creates Excel file with all steps
    ↓
User downloads Excel
```

**Note**: Login is handled automatically

---

### **Excel Upload Flow** (`/excel-upload`)

```
Upload Excel file
    ↓
Validate structure
    ↓
Generate Playwright code:
  For each Excel row:
    - Navigate → page.goto()
    - Click → element.click()
    - Fill → element.fill()
    - Wait → page.wait_for_timeout()
    ↓
Add error handling & screenshots
    ↓
Python test file ready
```

---

## 🎬 Quick Start Guide

### **For Quick Testing (Main App)**
```
1. Start Flask: python3 api/app.py
2. Go to http://localhost:5000/
3. Enter complete story (include login)
4. Click "Execute Test"
5. View results
```

### **For Creating Test Cases (Instructions Page)**
```
1. Start Flask: python3 api/app.py
2. Go to http://localhost:5000/instructions
3. Enter test instructions (no login)
4. Click "Execute Instructions"
5. Download Excel file
```

### **For Generating Code (Excel Upload)**
```
1. Go to http://localhost:5000/excel-upload
2. Upload Excel file
3. Click "Generate Test"
4. Download Python file
```

---

## 📁 Other Pages

### **HTML Parser** (`/parser`)
- Parse webpage and extract elements
- Build element registry
- Generate XPaths

### **Element Maps** (`/element-maps`)
- Browse stored element registries
- View elements by domain/page
- Download registry JSON files

---

## 🔑 Key Points

1. **Main App** (`/`): Full control, manual login
2. **Instructions Page** (`/instructions`): Auto-login, generates Excel
3. **Excel Upload** (`/excel-upload`): Excel → Python code

**Choose based on your needs:**
- Need quick test? → Use Main App
- Creating test cases? → Use Instructions Page
- Need Python code? → Use Excel Upload
