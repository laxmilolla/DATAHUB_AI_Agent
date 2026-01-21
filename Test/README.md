# Playwright Test Package

This package contains a Playwright TypeScript test generated from Excel.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Install Playwright browsers:
   ```bash
   npx playwright install chromium
   ```

3. Create a `.env` file with your TOTP secret key:
   ```bash
   TOTP_SECRET_KEY=your_secret_key_here
   ```

## Running the Test

Run in headed mode (see browser):
```bash
npm test
```

Or run headless:
```bash
npm run test:headless
```

## Test File

- `test_case_experiment.spec.ts` - Main test file generated from Excel

## Registry Files

The `element_maps/` directory contains JSON registry files that map element IDs to XPaths.
These are used by the test to locate elements dynamically without hard-coded XPaths.

## Notes

- The test uses registry-based element lookup (no hard-coded XPaths)
- TOTP codes are generated automatically using `otplib`
- The test includes auto-navigation if on wrong page
- Screenshots are saved to `storage/screenshots/` directory
