# Instruction → Playwright → XPath/Test Case Generator

## What You Want

1. **Input:** You provide test instructions (natural language)
   ```
   Go to https://hub-stage.datacommons.cancer.gov/
   Click on Login link
   Enter username: test@example.com
   Enter password: Test123!
   Click Submit
   ```

2. **Process:** System runs Playwright and executes these instructions
   - Uses AI Agent to interpret instructions
   - Executes actions in browser
   - Records XPaths used for each action
   - Takes screenshots

3. **Output:** System tells you:
   - What XPaths were used for each step
   - Generated test cases (Excel format)
   - Screenshots of execution

## Architecture

```
User Instructions (Text)
    ↓
AI Agent (Claude via Bedrock)
    ↓
Playwright Execution
    ↓
XPath Recording (Discovery Tracker)
    ↓
Test Case Generation (Excel)
    ↓
Output: Excel file with Steps, URLs, XPaths, Actions
```

## Components Needed

### 1. Instruction Parser
- Takes natural language instructions
- Breaks into steps
- Uses existing `StoryParser` or similar

### 2. Playwright Executor
- Uses existing `Agent.execute_story()`
- Executes instructions step by step
- Records actions taken

### 3. XPath Recorder
- Uses existing `DiscoveryTracker`
- Records XPath for each element used
- Maps step → XPath → URL

### 4. Test Case Generator
- Takes execution results
- Extracts: Step, URL, XPath, Action, Text Value
- Generates Excel file (reuse `excel_generator.py`)

## Flow

```
1. User enters instructions
2. System executes via Agent
3. During execution:
   - Records each action
   - Records XPath used
   - Records URL
   - Records action type (click, fill, navigate)
   - Records text values entered
4. After execution:
   - Compiles all recorded data
   - Generates Excel file
   - Shows XPaths used
   - Provides download link
```

## Implementation Plan

### Phase 1: Simple Execution + Recording
- Create endpoint: `POST /api/instructions/execute`
- Takes instructions text
- Runs Agent.execute_story()
- Records actions with XPaths
- Returns JSON with steps and XPaths

### Phase 2: Excel Generation
- After execution, generate Excel from recorded data
- Use existing `excel_generator.py` logic
- Output: Excel file with all steps

### Phase 3: UI
- Simple page: Instructions textarea + Execute button
- Shows progress
- Shows XPaths used
- Download Excel button

## API Endpoints

```
POST /api/instructions/execute
Body: { "instructions": "Go to X, click Y..." }
Returns: {
  "execution_id": "...",
  "steps": [
    {
      "step_number": 1,
      "action": "navigate",
      "url": "https://...",
      "xpath": "//button[@id='login']",
      "description": "Navigate to login page"
    },
    ...
  ],
  "excel_file": "/path/to/generated.xlsx"
}

GET /api/instructions/<execution_id>/excel
Returns: Excel file download
```

## UI Flow

1. User goes to `/instructions` page
2. Enters instructions in textarea
3. Clicks "Execute & Generate Test Cases"
4. System shows:
   - Progress (executing...)
   - Live XPaths as they're discovered
   - Screenshots
5. When done:
   - Shows summary table with all XPaths
   - "Download Excel" button
   - "View Screenshots" link

## Benefits

✅ Simple: Just give instructions, get XPaths and test cases
✅ No manual setup needed (can still support it)
✅ Reuses existing Agent infrastructure
✅ Outputs Excel format (can be used in main execution area)
✅ Records actual XPaths used (not guessed)

## Next Steps

1. Create `/api/instructions/execute` endpoint
2. Enhance execution recording to capture XPaths
3. Create Excel generator from execution data
4. Create simple UI page
5. Test with real instructions

