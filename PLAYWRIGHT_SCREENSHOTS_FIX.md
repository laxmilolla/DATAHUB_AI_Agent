# Playwright Screenshots UI Display Fix

## Problem
Playwright test screenshots were being generated but **not showing in the UI**.

---

## Root Cause

### The Flow (Before Fix):
1. ✅ Playwright test generates screenshots → Saved to `storage/screenshots/pw_*.png`
2. ✅ TestRunner captures screenshot paths → Stored in `test_result['screenshots']`
3. ✅ `/api/executions/<exec_id>/generate-and-validate` returns `result['playwright_screenshots']`
4. ❌ **But this data was NOT saved to the execution JSON file**
5. ❌ UI loads execution from `/api/executions/<exec_id>/results` → Returns JSON file
6. ❌ JSON file doesn't have `playwright_screenshots` field → UI shows nothing

**The Playwright results were only in the HTTP response, not persisted to disk.**

---

## The Fix

### Code Changes: `api/routes.py` (lines 533-564)

Added code to **persist Playwright results back to the execution JSON file**:

```python
# Step 4: Save Playwright results back to execution file for UI display
results_file = project_root / 'storage' / 'executions' / f'{exec_id}.json'
if results_file.exists():
    with open(results_file, 'r') as f:
        exec_data = json.load(f)
    
    # Add Playwright test results to execution data
    exec_data['playwright_screenshots'] = test_result.get('screenshots', [])
    exec_data['playwright_validation'] = {
        'status': test_result.get('status'),
        'duration': test_result.get('duration'),
        'assertions_passed': test_result.get('assertions_passed'),
        'assertions_failed': test_result.get('assertions_failed'),
        'test_file': test_result.get('test_file'),
        'timestamp': test_result.get('timestamp')
    }
    exec_data['playwright_comparison'] = comparison
    
    # Write back to file
    with open(results_file, 'w') as f:
        json.dump(exec_data, f, indent=2)
```

---

## What This Does

### Now the execution JSON file contains:

```json
{
  "execution_id": "exec_09520f58",
  "status": "completed",
  "screenshots": ["001_pre_click_Continue.png", ...],
  
  "playwright_screenshots": [
    {
      "filename": "pw_Continue.png",
      "path": "storage/screenshots/pw_Continue.png",
      "full_path": "/home/ubuntu/DATAHUB_AI_Agent/storage/screenshots/pw_Continue.png"
    },
    {
      "filename": "pw_DIAGNOSIS.png",
      ...
    }
  ],
  
  "playwright_validation": {
    "status": "failed",
    "duration": 15.65,
    "assertions_passed": 4,
    "assertions_failed": 2,
    ...
  },
  
  "playwright_comparison": {
    "match": false,
    "recommendation": "...",
    ...
  }
}
```

---

## How the UI Displays Screenshots

### The UI (`web/templates/results.html` lines 539-626):

1. Loads execution data from `/api/executions/<exec_id>/results`
2. Extracts screenshots:
   - AI screenshots: Filtered from `results.screenshots` (without `pw_` prefix)
   - Playwright screenshots: From `results.playwright_screenshots` array
3. Renders two separate sections:
   - 🤖 **AI Discovery Screenshots**
   - 🎭 **Playwright Screenshots**

### Screenshot Data Structure:
The `playwright_screenshots` array contains objects:
```json
{
  "filename": "pw_Continue.png",
  "path": "storage/screenshots/pw_Continue.png",
  "full_path": "/full/path/to/pw_Continue.png"
}
```

The UI uses `filename` to display: `/api/screenshots/pw_Continue.png`

---

## Expected Behavior (After Fix)

### When you click "Generate Playwright Test":
1. ✅ Playwright test runs
2. ✅ Screenshots are generated (`pw_*.png`)
3. ✅ TestRunner captures screenshot paths
4. ✅ **Results are saved to execution JSON file** ← NEW!
5. ✅ UI loads execution data
6. ✅ **Playwright screenshots appear in UI** ← FIXED!

### UI Should Show:
```
📸 Test Screenshots

🤖 AI Discovery Screenshots (7)
[Screenshot grid with AI screenshots]

🎭 Playwright Screenshots (4)
[Screenshot grid with Playwright screenshots]
```

---

## Testing

### To verify the fix works:
1. Run an AI test
2. Click "Generate Playwright Test" in the UI
3. Check the "Screenshots" tab in the results
4. Should see **two sections**: AI and Playwright screenshots

### Check the data:
```bash
# View execution JSON
cat storage/executions/exec_<ID>.json | grep -A 10 'playwright_screenshots'
```

Should show the `playwright_screenshots` array with screenshot objects.

---

## Deployment Status
- ✅ Code updated in `api/routes.py`
- ✅ Uploaded to server
- ✅ Flask restarted
- ✅ Ready for testing

---

## Date
December 31, 2025








