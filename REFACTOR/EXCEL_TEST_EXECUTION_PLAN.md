# Excel Test Execution Plan

## Goal
After Excel test generation, automatically run the test, capture screenshots, and display results like the existing system.

## What Needs to Be Done

### 1. Create Execution ID for Excel Tests
- Generate a unique execution_id (e.g., `excel_exec_<timestamp>_<id>`)
- Link Excel ID to execution ID
- Store execution metadata similar to existing system

### 2. Auto-Run Test After Generation
- After test generation completes, automatically run it in background thread
- Use TestRunner (from BACKUP/validator/test_runner.py)
- Capture screenshots during execution
- Save results to execution JSON file

### 3. Save Results Format
- Save to `storage/executions/<execution_id>.json`
- Include screenshots array
- Include test execution metadata
- Include Excel metadata link

### 4. Return Execution ID
- Return execution_id in generate response
- Frontend can redirect to `/results/<execution_id>`
- Results page will display screenshots and execution details

## Implementation Steps

### Step 1: Modify Excel Generate Endpoint
- Create execution_id after generation
- Run test automatically in background thread
- Save results to execution JSON

### Step 2: Create Execution JSON Structure
- Similar to existing execution format
- Include Excel metadata
- Include test results and screenshots

### Step 3: Update Frontend
- Show "Test is running..." message
- Redirect to results page when complete
- Poll for execution status

## Code Changes Needed

1. **REFACTOR/api/excel_routes.py** - Modify `generate_from_excel()`:
   - Create execution_id
   - Run test in background thread
   - Save results

2. **TestRunner Integration** - Use existing TestRunner from BACKUP
   - Import TestRunner
   - Run test with execution_id
   - Capture screenshots

3. **Results Page** - Should already work (uses execution_id)

