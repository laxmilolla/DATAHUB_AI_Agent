# Manual Preconditions Setup Solution

## Problem
You want to manually set up preconditions (login, TOTP) before running test instructions.

## Solution Options

### Option 1: Include Login/TOTP in Instructions (Simplest)
Just include login steps in your instructions:
```
Go to https://hub-stage.datacommons.cancer.gov/
Click on Login link
Enter username: Laxmi_AI_test@yahoo.com
Enter password: Testnci123456789!
Click Submit
Enter TOTP code (system will auto-generate)
Click Submit
Wait 5 seconds
[Then your actual test steps]
Go to Data Submissions page
Click Create Data Submission
...
```

**Pros:**
- Simple - everything in one instruction set
- Fully automated
- Can be re-run anytime

**Cons:**
- TOTP needs to be handled automatically (we already do this)

### Option 2: Pause for Manual Setup (Better UX)
Add a special instruction that pauses execution:
```
[PAUSE FOR MANUAL SETUP]
Go to https://hub-stage.datacommons.cancer.gov/
[System pauses here - you manually login and enter TOTP]
[Click "Continue" button]
[Then your actual test steps]
Go to Data Submissions page
...
```

**Pros:**
- You control the login/TOTP manually
- Browser stays open and visible
- Can verify you're logged in before continuing

**Cons:**
- Requires UI changes
- More complex implementation

### Option 3: Two-Step Process (Recommended)
1. **Precondition Setup Mode**: Browser opens, you manually login/TOTP, system records the state
2. **Test Execution Mode**: System continues from authenticated state

**Implementation:**
- Add checkbox: "Set up preconditions manually first"
- When checked: Browser opens → You login → Click "Ready" → Then instructions execute

## Recommended: Option 1 + Option 3 Hybrid

### Simple Mode (Default):
Include login in instructions - system handles everything automatically.

### Manual Mode:
1. Check "Set up preconditions manually"
2. Browser opens (visible)
3. You manually login and enter TOTP
4. Click "Ready to Continue"
5. Enter your test instructions
6. System executes from authenticated state

## Implementation Plan

### Step 1: Add Manual Precondition Mode to Instructions Page
- Add checkbox: "Set up preconditions manually"
- When checked:
  - Browser opens first (before instructions)
  - Shows "Set up your preconditions (login, TOTP), then click Continue"
  - User clicks "Continue" → Instructions execute

### Step 2: Modify Instructions Route
- If manual mode: Start browser first, wait for "continue" signal
- Then execute instructions from current browser state

### Step 3: UI Updates
- Add precondition setup section
- Show browser status
- "Continue" button after manual setup

