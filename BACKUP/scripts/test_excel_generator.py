"""
Test script for Excel generator
Creates a sample Excel file and generates Playwright code
"""
from pathlib import Path
import pandas as pd
from generator.excel_generator import generate_playwright_from_excel

# Create sample Excel file
excel_data = {
    'Step': [1, '1a', 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, '16b', 17, '17b', 18, 19],
    'URL': [
        'https://hub-stage.datacommons.cancer.gov/',
        'https://hub-stage.datacommons.cancer.gov/',
        'https://hub-stage.datacommons.cancer.gov/',
        'https://hub-stage.datacommons.cancer.gov/',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://secure.login.gov',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
        'https://hub-stage.datacommons.cancer.gov/data-submissions',
    ],
    'XPath': [
        'N/A',
        'N/A',
        "//div[@data-testid='system-use-warning-dialog']//button[contains(., 'Continue')]",
        "(//a[@id='header-navbar-login-button'])[1]",
        "(//*[normalize-space(.)='Login.gov'])[1]",
        "//input[@type='email']",
        "//input[@type='password']",
        "(//*[normalize-space(.)='Submit'])[1]",
        "//input[@class='one-time-code-input__input']",
        'N/A',
        "(//*[normalize-space(.)='Submit'])[1]",
        'N/A',
        "//input[@name='action']",
        "//div[@id='navbar-dropdown-data-submissions' and @role='button']",
        "//button[normalize-space(.)='Create a Data Submission']",
        "//div[@id=\"mui-component-select-dataCommons\" and @role=\"button\"]",
        "//ul[@role=\"listbox\"]//li[@role=\"option\" and normalize-space(.)=\"GC\"]",
        "//div[@id=\"mui-component-select-studyID\" and @role=\"button\"]",
        "//ul[@role=\"listbox\"]//li[@role=\"option\" and normalize-space(.)=\"NewTestSpn_laxmi\"]",
        "(//*[@data-testid=\"create-submission-dialog\"])//input[@name='name']",
        "(//*[@data-testid=\"create-submission-dialog\"])//button[@data-testid='create-data-submission-dialog-create-button']",
    ],
    'Object Type': [
        'page', 'page', 'button', 'link', 'button', 'input', 'input', 'button', 'input', 'page', 'button',
        'page', 'button', 'button', 'button', 'dropdown', 'option', 'dropdown', 'option', 'input', 'button'
    ],
    'Action': [
        'navigate', 'wait', 'click', 'click', 'click', 'fill', 'fill', 'click', 'fill', 'wait', 'click',
        'wait', 'click', 'click', 'click', 'click', 'click', 'click', 'click', 'fill', 'click'
    ],
    'Functions': [
        '', '', '', '', '', '', '', '', 'TOTP', '', '',
        '', '', '', '', '', '', '', '', '', ''
    ],
    'Text Value': [
        '', '', '', '', '', 'Laxmi_AI_test@yahoo.com', 'Testnci123456789!', '', '${TOTP_CODE}', '', '',
        '', '', '', '', '', '', '', '', '${TIMESTAMP}', ''
    ],
    'Wait Time': [
        '', 3000, '', '', '', '', '', '', '', 5000, '',
        2000, '', '', '', '', '', '', '', '', ''
    ],
    'Optional': [
        False, False, True, False, False, False, False, False, False, False, False,
        True, True, False, False, False, False, False, False, False, False
    ]
}

# Create Excel file
excel_file = Path('test_case.xlsx')
df = pd.DataFrame(excel_data)
df.to_excel(excel_file, index=False)
print(f"✅ Created sample Excel file: {excel_file}")

# Generate Playwright script
output_file = Path('tests/generated/test_excel_generated.py')
result = generate_playwright_from_excel(excel_file, output_file)

print("\n" + "=" * 80)
print("EXCEL GENERATOR RESULTS")
print("=" * 80)
print(f"Success: {result['success']}")
print(f"Rows processed: {result['rows_processed']}")
print(f"Output file: {result['output_file']}")

if result.get('errors'):
    print(f"\n⚠️  Errors:")
    for error in result['errors']:
        print(f"  - {error}")
else:
    print("\n✅ No errors!")

print(f"\n📝 Generated script: {output_file}")

