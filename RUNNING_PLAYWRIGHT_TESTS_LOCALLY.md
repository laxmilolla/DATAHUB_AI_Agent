# Running Playwright Tests Locally

This guide explains how to run generated Playwright tests on your local computer.

## Prerequisites

### 1. Install Python 3.8 or higher
```bash
python3 --version
```

### 2. Install Required Python Packages
Install these packages **once** (they work globally, not per-folder):
```bash
pip3 install playwright python-dotenv pyotp
```

**Important Notes:**
- `playwright` - Required for browser automation
- `python-dotenv` - Required for loading `.env` file with `TOTP_SECRET_KEY`
- `pyotp` - **Required for TOTP code generation** (tests with 2FA/authentication will fail without this)

**These packages cannot be embedded in the test file** - they must be installed on your system. This is standard Python package management.

### 3. Install Playwright Browsers
```bash
playwright install chromium
```

**Note:** You only need to install these once. They will be available from any directory.

---

## Step-by-Step Setup

### Step 1: Download Test Files

1. Download the generated Playwright test file (`.py` file) from the web interface
2. Download all registry JSON files using the "Download Multiple JSONs" feature or individual downloads

### Step 2: Organize Your Test Directory

Create a folder for your tests (e.g., `LocalTest/Datahubtests`) and place all files there.

**Important:** The downloaded JSON files will have `:` (colon) in their names instead of `/` (slash). You need to organize them into a directory structure.

#### Example of downloaded files:
```
auth.nih.gov: LoginMFA.aspx_page.json
hub-stage.datacommons.cancer.gov:data-submissions_page.json
hub-stage.datacommons.cancer.gov:home_page.json
secure.login.gov:authenticator_page.json
secure.login.gov:home_page.json
sts.nih.gov:consent_page.json
test_step_https_stage_new.py
```

#### Required structure (what the test expects):
```
auth.nih.gov/
  └── LoginMFA.aspx_page.json
hub-stage.datacommons.cancer.gov/
  └── data-submissions_page.json
  └── home_page.json
secure.login.gov/
  └── authenticator_page.json
  └── home_page.json
sts.nih.gov/
  └── consent_page.json
consent_page.json  (also in root)
test_step_https_stage_new.py
storage/
  └── screenshots/  (created automatically)
```

### Step 3: Fix File Organization

Run these commands in your test directory:

```bash
# Navigate to your test directory
cd ~/LocalTest/Datahubtests  # or your directory path

# Create directory structure
mkdir -p "auth.nih.gov" "hub-stage.datacommons.cancer.gov" "secure.login.gov" "sts.nih.gov"

# Move files to correct locations (adjust filenames based on your downloads)
mv "auth.nih.gov: LoginMFA.aspx_page.json" "auth.nih.gov/LoginMFA.aspx_page.json"
mv "hub-stage.datacommons.cancer.gov:data-submissions_page.json" "hub-stage.datacommons.cancer.gov/data-submissions_page.json"
mv "hub-stage.datacommons.cancer.gov:home_page.json" "hub-stage.datacommons.cancer.gov/home_page.json"
mv "secure.login.gov:authenticator_page.json" "secure.login.gov/authenticator_page.json"
mv "secure.login.gov:home_page.json" "secure.login.gov/home_page.json"
mv "sts.nih.gov:consent_page.json" "sts.nih.gov/consent_page.json"

# Copy consent_page.json to root (if test expects it there)
cp "sts.nih.gov/consent_page.json" "consent_page.json"
```

**Alternative:** You can also manually create folders and move files using Finder (Mac) or File Explorer (Windows).

### Step 4: Set Up Environment Variables

The test looks for a `.env` file in multiple locations (in order):
1. **Same directory as the test file** (recommended for local testing)
2. Parent directory
3. Home directory (`~/.env`)
4. 3 levels up from test file

**Easiest option:** Create `.env` in the same directory as your test file:

```bash
# Navigate to your test directory
cd ~/LocalTest/Datahubtests  # or your directory path

# Create .env file in the same directory
echo "TOTP_SECRET_KEY=your_secret_key_here" > .env
```

Or manually create `.env` in your test directory with:
```
TOTP_SECRET_KEY=your_actual_secret_key_value
```

**Alternative:** Create `.env` in your home directory:
```bash
echo "TOTP_SECRET_KEY=your_secret_key_here" > ~/.env
```

**Note:** Replace `your_actual_secret_key_value` with your actual TOTP secret key from the server.

### Step 5: Verify Setup

Check that everything is in place:

```bash
cd ~/LocalTest/Datahubtests  # or your test directory

# Verify JSON files exist
ls -R *.json 2>/dev/null || find . -name "*.json" -type f

# Verify .env file location (3 levels up)
python3 -c "from pathlib import Path; print('Test file:', Path('test_step_https_stage_new.py').absolute()); print('Looking for .env at:', Path('test_step_https_stage_new.py').absolute().parent.parent.parent / '.env')"
```

---

## Running the Test

### Basic Command

```bash
cd ~/LocalTest/Datahubtests  # or your test directory
python3 test_step_https_stage_new.py
```

### What to Expect

The test will:
1. Load environment variables from `.env`
2. Load all registry JSON files
3. Start a browser and execute the test steps
4. Save screenshots to `storage/screenshots/`
5. Print progress messages with ✅ (success) or ❌ (failure)

### Example Output

```
✅ Loaded environment variables from /Users/yourname/.env
✅ Loaded registry: 1 elements from LoginMFA.aspx_page.json
✅ Loaded registry: 3 elements from home_page.json
...
📍 Step 1: Navigated to https://hub-stage.datacommons.cancer.gov/
✅ Step 2: Clicked Continue (element_id: ID_9e268d1f)
...
```

---

## Troubleshooting

### Issue: "Registry file not found"

**Problem:** JSON files are not in the expected directory structure.

**Solution:**
1. Check the `REGISTRY_PATHS` list in your test file
2. Ensure files match the exact paths listed
3. Verify directory structure matches what the test expects

### Issue: ".env file not found"

**Problem:** The `.env` file is not 3 levels up from the test file.

**Solution:**
1. Check where the test expects the `.env` file:
   ```bash
   python3 -c "from pathlib import Path; print(Path('test_step_https_stage_new.py').absolute().parent.parent.parent / '.env')"
   ```
2. Create the `.env` file at that location
3. Or modify the test file to point to a different location

### Issue: "python-dotenv not installed"

**Problem:** Missing `python-dotenv` package.

**Solution:**
```bash
pip3 install python-dotenv
```

### Issue: "playwright not installed"

**Problem:** Missing Playwright package or browsers.

**Solution:**
```bash
pip3 install playwright
playwright install chromium
```

### Issue: "pyotp library not installed" or TOTP generation fails

**Problem:** Missing `pyotp` package required for TOTP code generation.

**Solution:**
```bash
pip3 install pyotp
```

**Note:** This is only needed if your test includes TOTP/2FA authentication steps.

### Issue: Files have `:` instead of `/` in names

**Problem:** Downloaded files use colons instead of slashes (browser limitation).

**Solution:** Manually create directories and move files as shown in Step 3.

### Issue: Test fails with "Element not found"

**Problem:** Registry JSON files may have invalid XPaths or the page structure changed.

**Solution:**
1. Check the error message for which element failed
2. Verify the registry JSON file has correct XPath for that element
3. You may need to update the XPath in the registry file manually

---

## Quick Reference

### Directory Structure Template

```
YourTestDirectory/
├── test_step_https_stage_new.py
├── domain1.com/
│   └── page1_page.json
├── domain2.com/
│   ├── page2_page.json
│   └── page3_page.json
├── consent_page.json  (if needed)
└── storage/
    └── screenshots/  (auto-created)
```

### Required Files Checklist

- [ ] Test Python file (`.py`)
- [ ] All registry JSON files organized in directories
- [ ] `.env` file with `TOTP_SECRET_KEY` (3 levels up)
- [ ] `storage/screenshots/` directory (auto-created)

### Common Commands

```bash
# Check Python version
python3 --version

# Check if packages are installed
python3 -c "import playwright; print('✅ playwright')"
python3 -c "import dotenv; print('✅ python-dotenv')"
python3 -c "import pyotp; print('✅ pyotp')"

# Run test
python3 test_step_https_stage_new.py

# Check file structure
find . -name "*.json" -type f
ls -R
```

---

## Notes

- **Global Installation:** Python packages (`playwright`, `python-dotenv`, `pyotp`) are installed globally, so you don't need to install them in each test folder
- **Browser Installation:** Playwright browsers are also global, but you may need to run `playwright install` once
- **Environment Variables:** The test automatically loads `.env` from 3 levels up, but you can modify the test file if needed
- **Screenshots:** All screenshots are saved to `storage/screenshots/` automatically
- **File Organization:** The directory structure is critical - JSON files must match the paths in `REGISTRY_PATHS`

---

## Getting Help

If you encounter issues:
1. Check the error message carefully
2. Verify all files are in the correct locations
3. Ensure `.env` file exists with correct `TOTP_SECRET_KEY`
4. Check that all Python packages are installed
5. Review the troubleshooting section above

For additional support, check the test file comments or contact the development team.

