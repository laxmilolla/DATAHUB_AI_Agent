# Experiment Area - Minimal Optimized Plan

## Overview
Interactive browser session where user sets up preconditions manually, then provides test instructions. System executes and outputs Excel file.

## Architecture

### Components (Minimal)

1. **Experiment Page** (`web/templates/experiment.html`)
   - Browser viewport (iframe or embedded)
   - Preconditions section (manual setup)
   - Instructions input (text area)
   - Record/Execute button
   - Download Excel button

2. **Experiment API** (`REFACTOR/api/experiment_routes.py`)
   - `POST /api/experiment/start` - Start browser session
   - `POST /api/experiment/execute` - Execute instructions (returns actions + screenshots)
   - `GET /api/experiment/<session_id>/status` - Get execution status (for polling)
   - `GET /api/experiment/<session_id>/screenshots` - Get list of screenshots
   - `GET /api/experiment/<session_id>/excel` - Download Excel
   - `POST /api/experiment/<session_id>/stop` - Stop session

3. **Experiment Runner** (`REFACTOR/experiment/experiment_runner.py`)
   - Reuse existing `agent/core/agent.py` (Agent class)
   - Run in headful mode (`headless=False`)
   - Record all actions to list
   - Convert actions to Excel format

4. **Excel Generator** (Reuse existing)
   - `REFACTOR/generator/excel_generator.py` - Already exists
   - Just need to convert actions list to Excel format

## Flow

```
1. User opens Experiment Area
   → Start browser session (headful=True)
   → Show browser viewport (visible)

2. User manually:
   - Logs in
   - Navigates to pages
   - Sets up preconditions
   → System records these as "precondition steps"

3. User enters test instructions:
   "Fill the form with test data and click submit"
   → Click "Execute Test"
   → System executes using Agent (same as main execution)
   → Shows execution status: "Step 1/5: Clicking button..."
   → Screenshots appear in real-time as test runs
   → User can see progress and verify correctness

4. After execution completes:
   → All screenshots displayed in grid
   → System combines:
     - Precondition steps (manual)
     - Test steps (from instructions) + screenshots
   → Generates Excel file

5. User downloads Excel
   → Can use in main Excel Test Generator
```

## Implementation Plan

### Phase 1: Basic Experiment Page (2 files)
- `web/templates/experiment.html` - UI with browser viewport
- `REFACTOR/api/experiment_routes.py` - API endpoints

### Phase 2: Experiment Runner (1 file)
- `REFACTOR/experiment/experiment_runner.py` - Reuse Agent class, run headful

### Phase 3: Excel Generation (Reuse existing)
- Convert actions to Excel using existing `excel_generator.py` helpers

## Code Reuse

✅ **Reuse:**
- `agent/core/agent.py` - Agent class (execute_story)
- `REFACTOR/generator/excel_generator.py` - Excel generation logic
- `utils/element_registry.py` - Element registry
- Playwright browser management

🆕 **New:**
- Experiment page UI
- Experiment API routes
- Session management (store browser session state)
- Action recording wrapper

## Minimal Files Needed

1. `web/templates/experiment.html` (~300 lines)
   - Browser viewport
   - Instructions input
   - Screenshot grid display
   - Status updates
   - Download Excel button

2. `web/static/js/experiment.js` (~150 lines)
   - Execute instructions
   - Poll for status/screenshots
   - Update screenshot grid in real-time
   - Handle Excel download

3. `REFACTOR/api/experiment_routes.py` (~200 lines)
   - Start/stop browser session
   - Execute instructions (async)
   - Status polling endpoint
   - Screenshot list endpoint
   - Excel download

4. `REFACTOR/experiment/experiment_runner.py` (~100 lines)
   - Thin wrapper around Agent
   - Run in headful mode
   - Return actions + screenshots

**Total: ~750 lines of new code**

## Technical Details

### Browser Session Management
```python
# Store session state
sessions = {
    'session_id': {
        'browser': browser_instance,
        'page': page_instance,
        'precondition_steps': [],
        'test_steps': [],
        'agent': Agent()
    }
}
```

### Recording Actions & Screenshots
```python
# Wrap Agent.execute_story to record actions and screenshots
async def execute_and_record(agent, instructions, session_id):
    results = await agent.execute_story(instructions)
    # Extract actions and screenshots from results
    actions = results['actions_taken']
    screenshots = results['screenshots']  # List of screenshot filenames
    
    # Return both for display and Excel generation
    return {
        'actions': actions,
        'screenshots': screenshots,
        'status': results['status']
    }
```

### Excel Generation
```python
# Convert actions to Excel format (include screenshot paths)
def actions_to_excel(actions, screenshots, output_path):
    # Use existing excel_generator helpers
    # Create DataFrame with Step, URL, XPath, Action, etc.
    # Optionally add Screenshot column with paths
    # Save to Excel
```

## UI Layout

```
┌─────────────────────────────────────────┐
│  Experiment Area                       │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐  │
│  │  Browser Viewport (headful)      │  │
│  │  [Live browser display]           │  │
│  │                                   │  │
│  └─────────────────────────────────┘  │
│                                         │
│  Preconditions:                         │
│  [✓] Logged in                         │
│  [✓] Navigated to /data-submissions    │
│                                         │
│  Test Instructions:                    │
│  ┌─────────────────────────────────┐  │
│  │ Fill form and click submit       │  │
│  └─────────────────────────────────┘  │
│                                         │
│  [▶ Execute Test]  [📥 Download Excel] │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │  Execution Status                │  │
│  │  Step 1/5: Clicking button...    │  │
│  └─────────────────────────────────┘  │
│                                         │
│  Screenshots:                           │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐          │
│  │ 📸 │ │ 📸 │ │ 📸 │ │ 📸 │          │
│  └────┘ └────┘ └────┘ └────┘          │
│                                         │
└─────────────────────────────────────────┘
```

## Screenshot Display (Like Excel Experiment)

### Real-time Screenshot Updates
- Show screenshots as test executes
- Display in grid layout (like results page)
- Click to view full size
- Show step number/description for each screenshot
- Auto-scroll to latest screenshot

### Screenshot Storage
- Save screenshots to `storage/screenshots/experiment_<session_id>_*.png`
- Link screenshots to execution steps
- Include in Excel generation (screenshot paths)

## Next Steps

1. Create experiment page UI
2. Add experiment API routes
3. Create experiment runner (thin wrapper)
4. Test end-to-end flow
5. Deploy

## Screenshot Display Implementation

### Frontend (experiment.js)
```javascript
// Poll for screenshots during execution
async function pollScreenshots(sessionId) {
    const response = await fetch(`/api/experiment/${sessionId}/screenshots`);
    const data = await response.json();
    
    // Update screenshot grid
    updateScreenshotGrid(data.screenshots);
}

// Update screenshot grid (like results page)
function updateScreenshotGrid(screenshots) {
    const grid = document.getElementById('screenshots-grid');
    grid.innerHTML = screenshots.map((screenshot, idx) => `
        <div class="screenshot-item">
            <img src="/api/screenshots/${screenshot}" 
                 onclick="window.open('/api/screenshots/${screenshot}', '_blank')">
            <div class="screenshot-label">Step ${idx + 1}</div>
        </div>
    `).join('');
    
    // Auto-scroll to latest
    grid.scrollLeft = grid.scrollWidth;
}
```

### Backend (experiment_routes.py)
```python
@bp_experiment.route('/api/experiment/<session_id>/screenshots')
def get_screenshots(session_id):
    # Return list of screenshot filenames for this session
    screenshots = sessions[session_id].get('screenshots', [])
    return jsonify({'screenshots': screenshots})
```

## Estimated Effort

- UI: 3 hours (including screenshot grid)
- JavaScript: 2 hours (polling, real-time updates)
- API: 1.5 hours (screenshot endpoints)
- Runner: 1 hour
- Testing: 1.5 hours
- **Total: ~9 hours**

