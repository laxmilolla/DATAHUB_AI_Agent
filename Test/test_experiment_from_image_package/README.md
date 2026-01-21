# Playwright TypeScript Test - Experiment

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
   npx playwright test test_experiment_from_image.spec.ts
   ```

## Files Included
- `test_experiment_from_image.spec.ts` - Main test file
- `package.json` - Dependencies
- `playwright.config.ts` - Playwright configuration
- `element_maps/` - Registry JSON files with element XPath mappings

## Test Steps
1. Navigate to hub-stage.datacommons.cancer.gov
2. Click Continue (optional dialog)
3. Click Login button
4. Click Login.gov button
5. Fill email
6. Fill password
7. Click Submit
8. Fill TOTP code
10. Click Submit (after TOTP)
13. Click Data Submissions dropdown
14. Click Create a Data Submission
15. Click Organization filter
16. Fill Submission name with timestamp

## Important
- **`.env` file is NOT included** for security reasons. You must create your own `.env` file with your TOTP_SECRET_KEY.
- Test runs in **headed mode** (headless: false) so you can see the browser
- Screenshots are saved to `storage/screenshots/` directory

## Notes
- The test uses registry-based XPath lookups (no hard-coding)
- TOTP code is automatically generated from TOTP_SECRET_KEY
- Test timeout is set to 5 minutes to allow for all steps
