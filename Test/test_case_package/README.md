# Playwright TypeScript Test - test_case

## Prerequisites
- Node.js (v16 or higher)
- npm

## Setup Instructions

1. Extract all files from the zip
2. Create a `.env` file in the same directory with:
   ```
   TOTP_SECRET_KEY=your_secret_key_here
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Install Playwright browsers:
   ```bash
   npx playwright install chromium
   ```
5. Run the test:
   ```bash
   npx playwright test test_case.spec.ts
   ```

## Files Included
- `test_case.spec.ts` - Main test file
- `package.json` - Dependencies
- `playwright.config.ts` - Playwright configuration
- `element_maps/` - Registry JSON files with element XPath mappings

## Important
- **`.env` file is NOT included** for security reasons. You must create your own `.env` file with your TOTP_SECRET_KEY.
- Test runs in **headed mode** (headless: false) so you can see the browser
- Screenshots are saved to `storage/screenshots/` directory

## Notes
- The test uses registry-based XPath lookups (no hard-coding)
- TOTP code is automatically generated from TOTP_SECRET_KEY
- Test timeout is set to 5 minutes to allow for all steps
- **OTP Fix Applied**: Steps 8 and 10 no longer navigate away from the TOTP page
