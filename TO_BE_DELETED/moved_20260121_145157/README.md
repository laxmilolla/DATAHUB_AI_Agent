# Dead Code Moved Here

**Date**: 2026-01-21 14:51:57

## Purpose
This folder contains code that was identified as dead/unused and moved here for safe testing.
After verifying the application still works, these files can be permanently deleted.

## Items Moved

- **Experimented/**: Moved features - no longer used
- **experiment_extended_test.py**: Test script - not part of main app
- **extract_all_elements.py**: Extraction script - not part of main app
- **extract_datasubmissions_elements.py**: Extraction script - not part of main app
- **extract_input_fields.py**: Extraction script - not part of main app
- **test_add_steps.py**: Test script - not part of main app
- **test_cdp_connection.py**: Test script - not part of main app
- **utils/capture_filters_graphql.py**: GraphQL capture - not imported
- **utils/capture_graphql.py**: GraphQL capture - not imported
- **utils/check_api_calls.py**: API call checker - not imported
- **utils/compare_maps.py**: Map comparison - not imported
- **utils/create_element_map.py**: Element map creation - not imported
- **utils/fetch_and_parse_html.py**: HTML fetcher - not imported
- **utils/html_parser.py**: HTML parser - not imported in main code
- **utils/playwright_tree_parser.py**: Tree parser - not imported
- **utils/test_element_matching.py**: Test matching - not imported
- **utils/xpath_builder.py**: XPath builder - not imported

## Testing Checklist

Before deleting this folder, verify:

- [ ] Excel upload works
- [ ] Excel test generation works (Python)
- [ ] Excel test generation works (TypeScript)
- [ ] Excel test execution works
- [ ] Registry lookups work
- [ ] TOTP generation works
- [ ] Screenshots are captured
- [ ] Results page displays correctly

## Safe to Delete?

Once all tests pass, this folder can be safely deleted.

**DO NOT DELETE** until:
1. Application runs without errors
2. All Excel features work
3. No import errors in logs
4. At least 1 successful test run completed
