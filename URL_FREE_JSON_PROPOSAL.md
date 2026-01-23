# URL-Free JSON Registry Structure Proposal

## Current JSON Structure (with URL)

```json
{
  "page": "data-submissions",
  "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
  "version": "1.0",
  "timestamp": "2026-01-15T19:37:44.427275Z",
  "elements": {
    "organization_filter": {
      "xpath": "//input[@id=\"organization-filter\"]",
      "selector": "//input[@id=\"organization-filter\"]",
      "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
      "element_id": "ID_org_filter_001",
      "usage_count": 0,
      "last_used": null,
      "source": "manual",
      "object_type": "input",
      "action": "fill",
      "discovered_at": "2026-01-22T18:00:00.000000Z",
      "last_updated": "2026-01-22T18:00:00.000000Z"
    },
    "submission_name_input": {
      "xpath": "//input[@data-testid=\"submission-name-input\"]",
      "selector": "//input[@data-testid=\"submission-name-input\"]",
      "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
      "element_id": "ID_sub_name_001",
      "usage_count": 0,
      "last_used": null,
      "source": "manual",
      "object_type": "input",
      "action": "fill",
      "discovered_at": "2026-01-22T18:00:00.000000Z",
      "last_updated": "2026-01-22T18:00:00.000000Z"
    },
    "generic_table": {
      "xpath": "//table[@data-testid=\"generic-table\"]",
      "selector": "//table[@data-testid=\"generic-table\"]",
      "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
      "element_id": "ID_generic_table_001",
      "usage_count": 0,
      "last_used": null,
      "source": "manual",
      "object_type": "table",
      "action": "verify",
      "discovered_at": "2026-01-23T13:10:00.000000Z",
      "last_updated": "2026-01-23T13:10:00.000000Z"
    }
  },
  "id_index": {
    "ID_org_filter_001": "organization_filter",
    "ID_sub_name_001": "submission_name_input",
    "ID_generic_table_001": "generic_table"
  },
  "statistics": {
    "total_elements": 3,
    "parsed_elements": 0,
    "discovered_elements": 0
  },
  "last_updated": "2026-01-23T13:10:00.000000Z"
}
```

---

## Proposed URL-Free JSON Structure

### Minimal Version (Only Required Fields)

```json
{
  "elements": {
    "organization_filter": {
      "element_id": "ID_org_filter_001",
      "xpath": "//input[@id=\"organization-filter\"]"
    },
    "submission_name_input": {
      "element_id": "ID_sub_name_001",
      "xpath": "//input[@data-testid=\"submission-name-input\"]"
    },
    "generic_table": {
      "element_id": "ID_generic_table_001",
      "xpath": "//table[@data-testid=\"generic-table\"]"
    }
  },
  "id_index": {
    "ID_org_filter_001": "organization_filter",
    "ID_sub_name_001": "submission_name_input",
    "ID_generic_table_001": "generic_table"
  }
}
```

### Recommended Version (With Useful Metadata)

```json
{
  "page": "data-submissions",
  "version": "1.0",
  "elements": {
    "organization_filter": {
      "element_id": "ID_org_filter_001",
      "xpath": "//input[@id=\"organization-filter\"]",
      "selector": "//input[@id=\"organization-filter\"]",
      "object_type": "input",
      "action": "fill",
      "source": "manual",
      "discovered_at": "2026-01-22T18:00:00.000000Z"
    },
    "submission_name_input": {
      "element_id": "ID_sub_name_001",
      "xpath": "//input[@data-testid=\"submission-name-input\"]",
      "selector": "//input[@data-testid=\"submission-name-input\"]",
      "object_type": "input",
      "action": "fill",
      "source": "manual",
      "discovered_at": "2026-01-22T18:00:00.000000Z"
    },
    "generic_table": {
      "element_id": "ID_generic_table_001",
      "xpath": "//table[@data-testid=\"generic-table\"]",
      "selector": "//table[@data-testid=\"generic-table\"]",
      "object_type": "table",
      "action": "verify",
      "source": "manual",
      "discovered_at": "2026-01-23T13:10:00.000000Z"
    }
  },
  "id_index": {
    "ID_org_filter_001": "organization_filter",
    "ID_sub_name_001": "submission_name_input",
    "ID_generic_table_001": "generic_table"
  },
  "statistics": {
    "total_elements": 3
  },
  "last_updated": "2026-01-23T13:10:00.000000Z"
}
```

---

## Field Comparison

### ✅ REQUIRED Fields (for lookup to work)

| Field | Location | Purpose |
|-------|----------|---------|
| `element_id` | `elements[key].element_id` | Unique identifier for lookup |
| `xpath` | `elements[key].xpath` | XPath selector to locate element |
| `id_index` | Top-level | Maps `element_id` → element key |

### 📝 OPTIONAL but Recommended Fields

| Field | Location | Purpose |
|-------|----------|---------|
| `page` | Top-level | Organization/documentation (which page this registry is for) |
| `selector` | `elements[key].selector` | CSS selector fallback |
| `object_type` | `elements[key].object_type` | Element type (input, button, table) |
| `action` | `elements[key].action` | Common action (click, fill, verify) |
| `source` | `elements[key].source` | How element was discovered (manual, ai_discovery) |
| `discovered_at` | `elements[key].discovered_at` | Timestamp for tracking |
| `version` | Top-level | Registry version |
| `statistics` | Top-level | Metadata about registry |
| `last_updated` | Top-level | Last modification time |

### ❌ REMOVED Fields (URL-free approach)

| Field | Location | Why Removed |
|-------|----------|-------------|
| `url` | Top-level | Not needed for lookup |
| `url` | `elements[key].url` | Not needed for lookup |
| `usage_count` | `elements[key].usage_count` | Optional metadata |
| `last_used` | `elements[key].last_used` | Optional metadata |

---

## Excel Structure (URL-Free)

### Current Excel (with URL)

| Step | URL | XPath | Action | Text Value | Functions | Wait Time |
|------|-----|-------|--------|------------|-----------|-----------|
| 1 | https://hub-stage.../data-submissions | //input[@id="org-filter"] | fill | ALL | | 2000 |
| 2 | https://hub-stage.../data-submissions | //input[@data-testid="submission-name-input"] | fill | Spandana | | 2000 |
| 3 | https://hub-stage.../data-submissions | //table[@data-testid="generic-table"] | verify | Submission Name=spandana | TABLE | |

### Proposed Excel (URL-Free)

| Step | XPath | Action | Text Value | Functions | Wait Time |
|------|-------|--------|------------|-----------|-----------|
| 1 | //input[@id="org-filter"] | fill | ALL | | 2000 |
| 2 | //input[@data-testid="submission-name-input"] | fill | Spandana | | 2000 |
| 3 | //table[@data-testid="generic-table"] | verify | Submission Name=spandana | TABLE | |

**Note:** URL column becomes **optional** - only needed for `navigate` action.

---

## Lookup Flow (URL-Free)

### Current Flow (with URL)
```
1. getXpathById(elementId, pageUrl)
2. Extract domain/page from pageUrl
3. Find matching registry file
4. Search registry by element_id
5. Fallback: Search all domain registries
6. Fallback: Search all registries
```

### Proposed Flow (URL-Free)
```
1. getXpathById(elementId)
2. Search ALL registries by element_id
3. Return xpath when found
```

**Much simpler!**

---

## Example: Dynamic URL Scenario

### Scenario
- Step 1: Navigate to base URL
- Step 2: Click submission → navigates to `.../data-submission/{uuid}/upload-activity`
- Step 3: Fill form on dynamic URL page

### Excel (URL-Free)
| Step | XPath | Action | Text Value |
|------|-------|--------|------------|
| 1 | N/A | navigate | https://hub-stage.datacommons.cancer.gov/data-submissions |
| 2 | //a[contains(text(), "My Submission")] | click | |
| 3 | //input[@id="upload-file"] | fill | file.pdf |

### JSON Registry (URL-Free)
```json
{
  "elements": {
    "submission_link": {
      "element_id": "ID_sub_link_001",
      "xpath": "//a[contains(text(), \"My Submission\")]"
    },
    "upload_file_input": {
      "element_id": "ID_upload_file_001",
      "xpath": "//input[@id=\"upload-file\"]"
    }
  },
  "id_index": {
    "ID_sub_link_001": "submission_link",
    "ID_upload_file_001": "upload_file_input"
  }
}
```

**Works perfectly!** No URL matching needed - just element_id lookup.

---

## Benefits Summary

1. **Simpler JSON**: Only essential fields
2. **Simpler Excel**: No URL column needed (except for navigate)
3. **Dynamic URLs**: Works with any URL structure
4. **Faster Lookup**: Direct element_id search (no URL parsing)
5. **Cross-Page**: Elements work across pages/domains
6. **Easier Maintenance**: Less fields to manage

---

## Migration Path

### Backward Compatibility
- Keep reading `url` fields if present (ignore them)
- Generate `element_id` if missing
- Support both old and new JSON formats during transition

### Migration Steps
1. Update generator to ignore URL fields
2. Update lookup to use element_id only
3. Optionally remove URL fields from existing registries
4. Update Excel template to make URL optional

---

## Final Minimal JSON Example

```json
{
  "elements": {
    "my_button": {
      "element_id": "ID_abc123",
      "xpath": "//button[@id=\"submit\"]"
    }
  },
  "id_index": {
    "ID_abc123": "my_button"
  }
}
```

**That's it!** Just 3 required fields per element:
- `element_id` (unique identifier)
- `xpath` (selector)
- Entry in `id_index` (for reverse lookup)
