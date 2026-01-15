# TODO: Selector Validation Utilities

## Reminder: Implement Selector Validation Tools

**Date Created:** 2026-01-14
**Context:** After debugging Study dropdown and discovering selector issues (modal vs main page, wrong element types)

## What to Build

### 1. `utils/test_element.py` - Interactive Element Tester
- Generalize `test_study_dropdown.py` into a reusable utility
- Test any element type (dropdown, input, button)
- Support both modal and main page contexts
- Connect to existing browser via CDP (port 9222)

**Usage:**
```bash
python utils/test_element.py --url <url> --element "Study" --type dropdown --modal
python utils/test_element.py --url <url> --element "Submission Name" --type input --modal
```

### 2. `utils/selector_validator.py` - Pre-Execution Validator
- Validate all selectors in registry files before test execution
- Check visibility, accessibility, correct context (modal vs main)
- Generate validation report
- Can be integrated into CI/CD

**Usage:**
```bash
python utils/selector_validator.py --page data-submissions
python utils/selector_validator.py --page data-submissions --modal
```

## Reference Documents
- `SELECTOR_VALIDATION_OPTIONS.md` - Full analysis of all options
- `test_study_dropdown.py` - Working template for element testing

## Key Findings from Testing
- Study dropdown: `#mui-component-select-studyID` (modal-scoped)
- Datacommons dropdown: `#mui-component-select-dataCommons` (modal-scoped)
- Submission Name input: `input[name="name"]` (modal-scoped, NOT `submissionName`)

## Why This Is Important
- Prevents selector mismatches (main page vs modal)
- Catches wrong element types (label vs button)
- Validates selectors before they cause test failures
- Saves debugging time

