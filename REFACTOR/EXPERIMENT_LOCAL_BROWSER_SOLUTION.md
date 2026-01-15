# Experiment Area - Local Browser Solution

## Problem
When Flask runs on server, browser runs on server (invisible). User cannot manually set up preconditions (login, navigate).

## Solution Options

### Option 1: Use User's Browser via Browser Extension (Recommended)
- Create browser extension that injects into user's browser
- Extension connects to Flask server via WebSocket
- Flask sends commands → Extension executes in user's browser
- User can manually set up preconditions, then run tests

### Option 2: Playwright Connect Over CDP (Chrome DevTools Protocol)
- User starts Chrome with remote debugging: `chrome --remote-debugging-port=9222`
- Flask connects to user's Chrome via CDP
- User can interact with browser, Flask can control it
- Works for localhost access

### Option 3: Run Everything Locally (Simplest)
- User runs Flask locally: `python api/app.py`
- Browser runs locally (visible)
- User can interact directly
- Best for development/testing

### Option 4: Hybrid Approach (Best UX)
- Detect if localhost → Use local browser
- If server → Provide instructions to:
  1. Run Flask locally, OR
  2. Use browser extension, OR
  3. Use CDP connection

## Recommended: Option 2 (CDP) + Option 3 (Local)

### Implementation Plan

#### For Localhost Access:
1. User runs Flask locally
2. Browser runs locally (visible)
3. User can interact directly

#### For Server Access:
1. User starts Chrome with CDP:
   ```bash
   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```
2. Flask connects to user's Chrome via CDP
3. User can see and interact with browser
4. Flask can control it programmatically

## Code Changes Needed

### 1. Detect Browser Location
```python
def get_browser_mode(request):
    """Determine browser mode based on request"""
    host = request.headers.get('Host', '')
    is_local = 'localhost' in host or '127.0.0.1' in host
    
    if is_local:
        return 'local'  # Browser runs on user's machine
    else:
        return 'cdp'  # Connect to user's browser via CDP
```

### 2. CDP Connection Mode
```python
from playwright.async_api import async_playwright

async def connect_to_user_browser(cdp_url='http://localhost:9222'):
    """Connect to user's Chrome browser via CDP"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.connect_over_cdp(cdp_url)
    page = browser.pages[0] if browser.pages else await browser.new_page()
    return browser, page
```

### 3. Update Experiment Runner
```python
async def start_browser(self, mode='local', cdp_url=None):
    """Start browser in different modes"""
    if mode == 'local':
        # Standard local browser
        await self.playwright_manager.start(headless=False)
    elif mode == 'cdp':
        # Connect to user's browser
        browser, page = await connect_to_user_browser(cdp_url)
        self.playwright_manager.browser = browser
        self.playwright_manager.page = page
```

## User Instructions for Server Access

### Step 1: Start Chrome with CDP
```bash
# On user's machine
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
# Or on Mac:
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

### Step 2: Access Experiment Area
- Open: http://13.222.91.163:5000/experiment
- Click "Start Browser"
- System connects to your Chrome browser
- You can interact with it directly
- Flask can control it programmatically

## Benefits
✅ User can see browser (their own Chrome)
✅ User can manually set up preconditions
✅ Flask can control browser programmatically
✅ Works for server deployment
✅ No browser extension needed

## Implementation Priority
1. ✅ Local mode (already works when Flask runs locally)
2. 🔄 Add CDP mode for server access
3. 🔄 Add UI instructions for CDP setup
4. 🔄 Auto-detect CDP connection

