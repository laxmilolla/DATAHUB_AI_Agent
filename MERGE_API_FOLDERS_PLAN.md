# Merge API Folders Plan

## Why Merge?

**Benefits:**
- ✅ Single source of truth for all API routes
- ✅ Easier to maintain and find routes
- ✅ Simpler import structure
- ✅ No need to register two blueprints

**Drawbacks:**
- ⚠️ Large file (~3000 lines)
- ⚠️ Mixes Excel-specific with general routes
- ⚠️ Breaks REFACTOR folder organization (but helper can stay)

---

## Merge Strategy

### Step 1: Move Excel Routes to `api/routes.py`
1. Copy all route functions from `REFACTOR/api/excel_routes.py` to `api/routes.py`
2. Change `@bp_excel.route` → `@bp.route` (use same blueprint)
3. Change `bp_excel` → `bp` in all decorators
4. Keep `active_excel_generations` dict (can coexist with `active_executions`)

### Step 2: Update Imports
1. Add Excel generator imports to `api/routes.py`:
   ```python
   from REFACTOR.generator.excel_generator_ts import generate_playwright_ts_from_excel
   from REFACTOR.generator.excel_validator import validate_excel_file, get_validation_summary
   from REFACTOR.generator.excel_template import generate_excel_template, get_template_path
   from REFACTOR.generator.excel_registry_helper import extract_elements_from_excel, compare_with_registry
   ```

2. Update `api/app.py`:
   - Remove: `from REFACTOR.api.excel_routes import bp_excel`
   - Remove: Excel blueprint registration
   - Keep: Only `api.routes` blueprint

### Step 3: Handle `manual_registry_helper.py`
**Option A**: Keep in `REFACTOR/api/` (recommended)
- Already imported by `api/routes.py`
- No changes needed

**Option B**: Move to `api/` folder
- Update import in `api/routes.py`
- More consistent location

### Step 4: Delete `REFACTOR/api/excel_routes.py`
- After routes are moved and tested
- Keep `manual_registry_helper.py` in REFACTOR

---

## Technical Details

### Blueprint Changes
**Before:**
```python
# REFACTOR/api/excel_routes.py
bp_excel = Blueprint('excel_api', __name__)
@bp_excel.route('/api/excel/upload', ...)
```

**After:**
```python
# api/routes.py
bp = Blueprint('api', __name__)  # Already exists
@bp.route('/api/excel/upload', ...)  # Changed from bp_excel
```

### Global Variables
Both can coexist:
```python
active_executions = {}  # For story-based executions
active_excel_generations = {}  # For Excel generations
```

### Route Prefixes
- Excel routes already have `/api/excel` prefix
- General routes have `/api` prefix (from blueprint registration)
- No conflicts - different paths

---

## Files to Modify

1. ✅ `api/routes.py` - Add Excel routes (change bp_excel → bp)
2. ✅ `api/app.py` - Remove Excel blueprint import/registration
3. ✅ `REFACTOR/api/excel_routes.py` - Delete after merge
4. ⚠️ `REFACTOR/api/__init__.py` - Update or delete (exports bp_excel)
5. ⚠️ `REFACTOR/api/README.md` - Update or move to docs/

---

## Testing Checklist

After merge:
- [ ] Excel upload works (`/api/excel/upload`)
- [ ] Excel generation works (`/api/excel/generate-ts`)
- [ ] Story execution works (`/api/execute`)
- [ ] Execution status works (`/api/executions/<id>/status`)
- [ ] All Excel routes respond correctly
- [ ] No import errors
- [ ] Flask app starts without errors

---

## Estimated Impact

- **Lines added to api/routes.py**: ~1215 lines
- **Final file size**: ~2977 lines
- **Files deleted**: 1 (`REFACTOR/api/excel_routes.py`)
- **Files modified**: 2 (`api/routes.py`, `api/app.py`)
- **Risk level**: Medium (need to test all routes)

---

## Recommendation

**✅ YES, merge is feasible and beneficial**

The merge will:
- Simplify the codebase structure
- Make all routes easier to find
- Reduce confusion about where routes are
- Keep code organized in one place

The only downside is a larger file, but 3000 lines is manageable for a routes file.

