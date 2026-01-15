# Experiment Area - Server Flow (EC2)

## Overview
When Flask runs on EC2 server, the browser runs on the server (not visible to user). User interacts via web UI, sees screenshots in real-time.

## Complete Flow

### 1. User Accesses Experiment Area
```
User Browser (Your Machine)
    ↓ HTTP Request
    GET http://13.222.91.163:5000/experiment
    ↓
EC2 Server (Flask App)
    ↓
Returns: experiment.html page
    ↓
User Browser displays UI
```

**What happens:**
- User opens browser on their machine
- Navigates to `http://13.222.91.163:5000/experiment`
- Flask serves the HTML page
- User sees the Experiment Area UI

---

### 2. User Clicks "Start Browser"
```
User Browser
    ↓ POST Request
    POST /api/experiment/start
    ↓
EC2 Server (Flask)
    ↓
Creates ExperimentRunner instance
    ↓
Starts Playwright browser (headless=False)
    ↓ Browser runs ON SERVER
    ↓
Returns: {session_id, browser_location: 'server'}
    ↓
User Browser receives response
    ↓
Shows message: "Browser Running on Server - Screenshots will appear below"
```

**What happens:**
- Browser window opens **ON THE EC2 SERVER** (not visible to user)
- Session ID created and stored in `experiment_sessions` dict
- User sees placeholder message in UI
- Browser is ready but user can't see it

---

### 3. User Manually Sets Up Preconditions
```
User Browser
    ↓ User checks preconditions checkboxes
    [✓] Logged in
    [✓] Navigated to target page
    
Note: User CANNOT actually interact with browser
      because it's running on server, not their machine.
      
      User must:
      - Either run Flask locally for visible browser
      - Or trust that screenshots show what's happening
```

**Important:** 
- User cannot see or interact with browser on server
- Preconditions are just checkboxes (user's mental note)
- Actual browser state is managed by server

---

### 4. User Enters Instructions & Clicks "Execute Test"
```
User Browser
    ↓ POST Request
    POST /api/experiment/{session_id}/execute
    Body: {instructions: "Fill form and click submit"}
    ↓
EC2 Server (Flask)
    ↓
Gets ExperimentRunner from experiment_sessions
    ↓
Calls runner.execute_instructions(instructions)
    ↓
ExperimentRunner calls Agent.execute_story()
    ↓
Agent executes instructions using Playwright
    ↓ Browser ON SERVER performs actions
    ↓ Screenshots saved to: storage/screenshots/experiment_*.png
    ↓ Actions recorded in context.actions_taken
    ↓
Returns: {success: true, message: "Execution started"}
    ↓
User Browser receives response
    ↓
Starts polling for status and screenshots
```

**What happens:**
- Agent executes instructions on server browser
- Each action triggers screenshot capture
- Screenshots saved to `storage/screenshots/` on server
- User cannot see browser window (it's on server)

---

### 5. Real-Time Screenshot Polling
```
User Browser (JavaScript)
    ↓ Every 2 seconds
    GET /api/experiment/{session_id}/screenshots
    ↓
EC2 Server (Flask)
    ↓
Gets screenshots from runner.get_screenshots()
    Returns: {screenshots: ['screenshot1.png', 'screenshot2.png', ...]}
    ↓
User Browser receives response
    ↓
Updates screenshot grid in UI
    ↓
User sees screenshots appear in real-time
```

**What happens:**
- JavaScript polls every 2 seconds
- Server returns list of screenshot filenames
- Browser displays screenshots from `/api/screenshots/{filename}`
- User sees progress visually through screenshots

---

### 6. Status Polling
```
User Browser (JavaScript)
    ↓ Every 1 second
    GET /api/experiment/{session_id}/status
    ↓
EC2 Server (Flask)
    ↓
Gets status from runner.get_status()
    Returns: {
        status: 'running',
        current_step: 3,
        total_steps: 5,
        step_description: 'Clicking button'
    }
    ↓
User Browser receives response
    ↓
Updates status text: "Step 3/5: Clicking button"
```

**What happens:**
- JavaScript polls every 1 second
- Server returns current execution status
- UI shows progress: "Step X/Y: [action]"
- User knows what's happening even though browser is invisible

---

### 7. Execution Completes
```
EC2 Server (Agent)
    ↓ Execution finishes
    context.status = 'completed'
    context.actions_taken = [all actions]
    context.screenshots = [all screenshots]
    ↓
User Browser (JavaScript)
    ↓ Polling detects status = 'completed'
    Stops polling
    Enables "Download Excel" button
    Shows final status: "✅ Completed! 5 steps executed"
```

**What happens:**
- Agent marks execution as completed
- All actions and screenshots stored in context
- User sees completion message
- Download Excel button enabled

---

### 8. User Downloads Excel
```
User Browser
    ↓ GET Request
    GET /api/experiment/{session_id}/excel
    ↓
EC2 Server (Flask)
    ↓
Gets results from runner.get_results()
    Extracts actions_taken
    Converts to DataFrame (pandas)
    Creates Excel file: storage/experiment_excel/experiment_{session_id}.xlsx
    ↓
Returns: Excel file as download
    ↓
User Browser receives file
    ↓
Downloads to user's machine
```

**What happens:**
- Server generates Excel from recorded actions
- Excel includes: Step, URL, XPath, Action, Object Type, Text Value, etc.
- File downloaded to user's local machine
- User can use Excel in main Excel Test Generator

---

## Key Points

### ✅ What Works on Server:
- Browser automation (runs on server)
- Screenshot capture (saved on server)
- Action recording (stored on server)
- Excel generation (created on server)
- Real-time screenshot display (via polling)
- Status updates (via polling)

### ❌ What Doesn't Work on Server:
- User cannot see browser window (it's on server)
- User cannot manually interact with browser (it's on server)
- Preconditions must be set up programmatically or trusted

### 🔄 Alternative: Local Flask
If user wants to see browser:
```bash
# On user's machine
cd /Users/lollal/Documents/ai-agent-qa
source venv/bin/activate
python api/app.py

# Access: http://localhost:5000/experiment
# Browser will be visible on user's screen
```

---

## File Locations on Server

```
EC2 Server: ~/DATAHUB_AI_Agent/
├── storage/
│   ├── screenshots/
│   │   └── experiment_{session_id}_*.png  ← Screenshots saved here
│   └── experiment_excel/
│       └── experiment_{session_id}.xlsx   ← Excel files saved here
├── experiment_sessions (in memory)
│   └── {session_id: {runner, status, actions, screenshots}}
└── Flask app running
    └── Serving UI and API endpoints
```

---

## Network Flow Diagram

```
┌─────────────────┐
│  User Browser   │
│  (Your Machine) │
└────────┬────────┘
         │ HTTP/HTTPS
         │
         ↓
┌─────────────────┐
│   EC2 Server     │
│  (13.222.91.163) │
│                 │
│  ┌───────────┐  │
│  │  Flask    │  │
│  │  App      │  │
│  └─────┬─────┘  │
│        │         │
│  ┌─────▼─────┐  │
│  │ Playwright │  │
│  │  Browser   │  │ ← Runs HERE (not visible to user)
│  └────────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Screenshots│  │
│  │  Storage   │  │
│  └───────────┘  │
└─────────────────┘
```

---

## Summary

**Server Flow:**
1. User accesses UI via browser → Flask serves page
2. User starts browser → Playwright starts on server (invisible)
3. User executes instructions → Agent runs on server browser
4. Screenshots captured → Saved on server
5. User polls for screenshots → Sees them in UI
6. User downloads Excel → File generated on server, downloaded to user

**Key Limitation:**
- Browser is invisible to user (runs on server)
- User relies on screenshots to see what's happening
- For visible browser, must run Flask locally

