# Playwright TypeScript Test Setup

This zip contains a Playwright test written in TypeScript (`.spec.ts` format).

## Prerequisites

1. **Node.js** (v16 or higher)
   - Download from: https://nodejs.org/
   - Verify installation: `node --version`

2. **npm** (comes with Node.js)
   - Verify installation: `npm --version`

## Setup Instructions

### Step 1: Extract the zip file
Extract all files to a directory of your choice.

### Step 2: Install dependencies
Open a terminal in the extracted directory and run:
```bash
npm install
```

This will install:
- `@playwright/test` - Playwright test framework
- `dotenv` - For loading `.env` file
- `otplib` - For TOTP code generation

### Step 3: Install Playwright browsers
```bash
npx playwright install chromium
```

### Step 4: Set up environment variables
Ensure the `.env` file is in the same directory as the test file, or in one of these locations:
- Same directory as test file
- Parent directory
- Home directory (`~/.env`)
- 3 levels up from test file

The `.env` file should contain:
```
TOTP_SECRET_KEY=your_actual_secret_key_value
```

### Step 5: Verify JSON registry files
Ensure all JSON registry files are present in the correct directory structure:
- `LoginMFA.aspx_page.json`
- `hub-stage.datacommons.cancer.gov/data-submissions_page.json`
- `hub-stage.datacommons.cancer.gov/home_page.json`
- `secure.login.gov/authenticator_page.json`
- `secure.login.gov/home_page.json`
- `sts.nih.gov/consent_page.json`

## Running the Test

### Run in headless mode (default):
```bash
npx playwright test test_step_https_stage.spec.ts
```

### Run with visible browser:
```bash
npx playwright test test_step_https_stage.spec.ts --headed
```

### Run with UI mode (interactive):
```bash
npx playwright test test_step_https_stage.spec.ts --ui
```

## Test Structure

The test includes:
- **15 steps** - Complete login and navigation flow
- **XPath lookups** - Reads from JSON registry files
- **TOTP generation** - Automatic 2FA code generation
- **Screenshots** - Captured at each step (saved to `storage/screenshots/`)

## Troubleshooting

### "Module not found" errors
Run `npm install` again to ensure all dependencies are installed.

### "TOTP_SECRET_KEY not found"
Check that your `.env` file exists and contains `TOTP_SECRET_KEY=your_key`.

### "Registry file not found"
Ensure all JSON registry files are in the correct directory structure as listed above.

### "Playwright browsers not installed"
Run: `npx playwright install chromium`

## Files Included

- `test_step_https_stage.spec.ts` - Main test file
- `.env` - Environment variables (TOTP_SECRET_KEY)
- `package.json` - Node.js dependencies
- JSON registry files - Element XPath mappings

## Notes

- Screenshots are saved to `storage/screenshots/` directory (created automatically)
- The test uses the same XPaths and logic as the Python version
- All steps are preserved in the same order
- Critical failures are tracked and reported at the end


