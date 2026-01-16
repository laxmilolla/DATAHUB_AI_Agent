# Pulling from BACKUP - Quick Reference

All existing codebase is in `BACKUP/` folder. Pull methodically from there.

## Quick Reference Map

| What You Need | Pull From BACKUP | Destination in REFACTOR |
|---------------|------------------|-------------------------|
| API patterns | `BACKUP/api/routes.py` | `REFACTOR/api/` (new files) |
| Test runner | `BACKUP/validator/test_runner.py` | Reference for enhancement |
| UI patterns | `BACKUP/web/templates/results.html` | `REFACTOR/web/templates/` |
| JS patterns | `BACKUP/web/static/js/app.js` | `REFACTOR/web/static/js/` |
| Generator patterns | `BACKUP/generator/playwright_generator.py` | Reference for patterns |
| Validation patterns | `BACKUP/generator/pw_codegen/` | `REFACTOR/generator/excel_validator.py` |

## Pull Order

1. **Study** the file in BACKUP
2. **Understand** the pattern
3. **Adapt** for Excel use case
4. **Create** in REFACTOR
5. **Test** before moving to next

## Example: Pulling API Pattern

```bash
# Step 1: Study BACKUP file
cat BACKUP/api/routes.py | grep -A 20 "def generate_and_validate"

# Step 2: Understand pattern
# - How endpoint is structured
# - How errors are handled
# - How responses are formatted

# Step 3: Adapt for Excel
# - Change endpoint name
# - Change input (Excel file instead of execution_id)
# - Keep same error handling pattern
# - Keep same response format

# Step 4: Create in REFACTOR
# Create REFACTOR/api/excel_routes.py with adapted code

# Step 5: Test
# Test the new endpoint
```

## Files Already Copied

- ✅ `REFACTOR/generator/excel_generator.py` - From BACKUP (working)
- ✅ `REFACTOR/tests/test_excel_generator.py` - From BACKUP

## Files to Pull Next

1. **Excel Validator** - Reference `BACKUP/generator/pw_codegen/step_generators.py`
2. **API Endpoints** - Reference `BACKUP/api/routes.py`
3. **Test Runner** - Reference `BACKUP/validator/test_runner.py`
4. **UI Components** - Reference `BACKUP/web/templates/results.html`

