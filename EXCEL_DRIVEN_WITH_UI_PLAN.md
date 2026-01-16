# Excel-Driven Execution with UI Instructions - Plan

## Goal
Create a workflow where:
1. **Excel steps run first** (sequential, no iterations)
2. **Wait for user instruction** from UI
3. **Execute instruction** (using Agent to find elements)
4. **Capture XPaths** automatically
5. **Generate Excel** with captured XPaths

---

## Current Flow vs Desired Flow

### Current Flow:
```
Excel Login (steps 1-12) → Agent executes instructions → Generate Excel
```

### Desired Flow:
```
Excel Steps (all steps) → Wait for UI instruction → Execute → Capture XPaths → Generate Excel
```

---

## Architecture Plan

### Phase 1: Excel-Driven Execution
- Read Excel file
- Execute steps sequentially (for loop, no iterations)
- Run all steps or up to a certain step
- Keep browser open
- Wait for user instruction

### Phase 2: UI Instruction Input
- User provides instruction via web UI
- System waits for instruction
- Instruction sent to backend

### Phase 3: Execute Instruction
- Use Agent to interpret instruction
- Agent finds elements and executes
- Capture XPaths during execution
- Record actions taken

### Phase 4: Generate Excel
- Combine Excel steps + instruction steps
- Include captured XPaths
- Generate new Excel file

---

## Implementation Plan

### Option A: Two-Step API Flow

**Step 1: Start Excel Execution**
```
POST /api/excel-execution/start
Body: { "excel_file": "test_case.xlsx", "max_steps": null }
Response: { "execution_id": "...", "status": "waiting_for_instruction" }
```

**Step 2: Provide Instruction**
```
POST /api/excel-execution/<execution_id>/execute-instruction
Body: { "instruction": "Click Program dropdown, select NCI" }
Response: { "status": "executing", "xpaths": [...] }
```

**Step 3: Get Results**
```
GET /api/excel-execution/<execution_id>/results
Response: { "excel_file": "...", "steps": [...], "xpaths": [...] }
```

### Option B: Single API with Wait

**Start Execution**
```
POST /api/excel-execution/start-with-instruction
Body: { 
  "excel_file": "test_case.xlsx",
  "wait_after_step": 12,  // Wait after step 12
  "instruction": "Click Program dropdown"  // Optional, can be provided later
}
```

**If instruction provided later:**
```
POST /api/excel-execution/<execution_id>/add-instruction
Body: { "instruction": "Select NCI" }
```

---

## Code Structure

### New File: `REFACTOR/api/excel_execution_routes.py`

```python
# Excel execution state
excel_executions = {}

@bp_excel_execution.route('/api/excel-execution/start', methods=['POST'])
def start_excel_execution():
    """
    Start Excel-driven execution
    - Runs Excel steps sequentially
    - Keeps browser open
    - Waits for instruction
    """
    # 1. Read Excel
    # 2. Execute steps sequentially (for loop)
    # 3. Keep browser open
    # 4. Return execution_id
    pass

@bp_excel_execution.route('/api/excel-execution/<execution_id>/execute-instruction', methods=['POST'])
def execute_instruction(execution_id):
    """
    Execute user instruction
    - Use Agent to interpret instruction
    - Capture XPaths
    - Return results
    """
    # 1. Get browser from execution
    # 2. Create Agent
    # 3. Execute instruction
    # 4. Capture XPaths
    # 5. Return XPaths and actions
    pass

@bp_excel_execution.route('/api/excel-execution/<execution_id>/generate-excel', methods=['POST'])
def generate_excel_from_execution(execution_id):
    """
    Generate Excel from execution
    - Combine Excel steps + instruction steps
    - Include XPaths
    - Return Excel file
    """
    # 1. Get all steps (Excel + instruction)
    # 2. Generate Excel
    # 3. Return file path
    pass
```

---

## Key Differences from Current Flow

### Current Instructions Flow:
- Excel login (steps 1-12) → Agent executes → Generate Excel
- All in one request
- Uses async/event loop

### New Excel-Driven Flow:
- Excel steps (all steps) → Wait → UI instruction → Execute → Generate Excel
- Multiple requests (start, execute, generate)
- Excel steps: Sequential (no iterations)
- Instruction: Agent-based (with iterations)

---

## Execution Flow

```
1. User clicks "Start Excel Execution"
   ↓
2. Backend reads Excel file
   ↓
3. Execute Excel steps sequentially:
   for row in excel_rows:
       if action == 'navigate': page.goto(url)
       elif action == 'click': element.click()
       elif action == 'fill': element.fill()
   ↓
4. Browser stays open, wait for instruction
   ↓
5. User enters instruction in UI: "Click Program dropdown"
   ↓
6. Backend receives instruction
   ↓
7. Use Agent to execute:
   - Agent interprets instruction
   - Finds elements
   - Executes actions
   - Captures XPaths automatically
   ↓
8. Combine Excel steps + instruction steps
   ↓
9. Generate Excel with XPaths
   ↓
10. User downloads Excel
```

---

## XPath Capture Strategy

### During Excel Execution:
- XPaths already in Excel → Use those

### During Instruction Execution:
- Use DiscoveryTracker to capture XPaths
- Extract from actions_taken
- Match to discoveries
- Store in execution state

### Excel Generation:
- Excel steps: Use XPaths from Excel
- Instruction steps: Use captured XPaths
- Combine into single Excel file

---

## UI Flow

### Page 1: Start Excel Execution
```
[Excel File Upload] or [Use test_case.xlsx]
[Max Steps: ___] (optional, null = all steps)
[Start Execution] button
```

### Page 2: Execution Running
```
Status: Running Excel steps...
Progress: Step 5/15
[Browser visible]
```

### Page 3: Waiting for Instruction
```
Status: Waiting for instruction...
[Instruction Input Box]
[Execute Instruction] button
```

### Page 4: Instruction Executing
```
Status: Executing instruction...
[Show captured XPaths in real-time]
```

### Page 5: Results
```
[Download Excel] button
[View XPaths] table
[View Screenshots]
```

---

## Benefits

✅ **Excel-driven**: Uses Excel steps (deterministic)
✅ **UI instructions**: User provides instructions via web
✅ **XPath capture**: Automatically captures XPaths
✅ **Excel generation**: Combines both into Excel
✅ **No iterations for Excel**: Fast, sequential execution
✅ **Iterations only for instructions**: Agent adapts to find elements

---

## Implementation Steps

1. **Create new blueprint**: `excel_execution_routes.py`
2. **Excel execution function**: Sequential step execution
3. **State management**: Store browser/execution state
4. **Instruction execution**: Use Agent (with iterations)
5. **XPath capture**: Extract from discoveries
6. **Excel generation**: Combine steps
7. **UI pages**: Create web interface
8. **Testing**: Test full flow

---

## Questions to Answer

1. **Excel file source**: Upload or use `test_case.xlsx`?
2. **Wait point**: After which step? (e.g., after step 12, or all steps?)
3. **Multiple instructions**: Can user provide multiple instructions?
4. **Browser management**: Keep browser open between requests?
5. **Session management**: How to handle browser sessions?

---

## Next Steps

1. Create `excel_execution_routes.py`
2. Implement Excel sequential execution
3. Add instruction execution endpoint
4. Add XPath capture logic
5. Add Excel generation
6. Create UI pages
7. Test end-to-end

