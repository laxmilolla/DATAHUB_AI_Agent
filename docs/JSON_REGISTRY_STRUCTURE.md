# JSON Element Registry Structure - Complete Attribute Reference

## Overview
This document describes the complete structure of JSON element registries used in the AI Agent QA system. It includes all attributes captured for each element, their meanings, data types, and examples.

---

## Table of Contents
1. [Registry File Structure](#registry-file-structure)
2. [Top-Level Attributes](#top-level-attributes)
3. [Element Attributes](#element-attributes)
4. [Source Types](#source-types)
5. [Complete Examples](#complete-examples)
6. [ID Index Structure](#id-index-structure)
7. [Statistics Section](#statistics-section)
8. [Attribute Reference Table](#attribute-reference-table)

---

## Registry File Structure

### File Location Pattern
```
element_maps/{domain}/{page}_page.json
```

**Example**:
```
element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json
```

### Complete JSON Structure
```json
{
  "page": "string",
  "url": "string",
  "version": "string",
  "timestamp": "ISO8601 datetime",
  "elements": {
    "element_name": {
      // Element attributes (see below)
    }
  },
  "id_index": {
    "element_id": "element_name"
  },
  "statistics": {
    "total_elements": number,
    "parsed_elements": number,
    "discovered_elements": number
  },
  "last_updated": "ISO8601 datetime"
}
```

---

## Top-Level Attributes

### `page` (string, required)
- **Description**: Page identifier extracted from URL
- **Example**: `"data-submissions"`
- **Source**: Extracted from URL path

### `url` (string, required)
- **Description**: Full URL where elements were discovered
- **Example**: `"https://hub-stage.datacommons.cancer.gov/data-submissions"`
- **Source**: From Excel URL column or discovery URL

### `version` (string, optional)
- **Description**: Registry version number
- **Example**: `"1.0"`
- **Default**: `"1.0"`

### `timestamp` (string, ISO8601, optional)
- **Description**: When registry file was created
- **Example**: `"2026-01-15T19:37:44.427275Z"`
- **Format**: ISO8601 with Z suffix (UTC)

### `last_updated` (string, ISO8601, optional)
- **Description**: Last time registry was updated
- **Example**: `"2026-01-20T22:00:31.858502Z"`
- **Format**: ISO8601 with Z suffix (UTC)

---

## Element Attributes

Each element in the `elements` object contains the following attributes:

### Core Identification Attributes

#### `element_id` (string, required)
- **Description**: Unique identifier for the element (8-character hex)
- **Format**: `ID_{8 hex characters}`
- **Example**: `"ID_70bc9e6a"`
- **Uniqueness**: Globally unique across all registries
- **Usage**: Used for registry lookup in generated tests

#### `xpath` (string, required)
- **Description**: XPath selector for locating the element
- **Example**: `"//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]"`
- **Special Cases**:
  - Modal elements: Scoped to modal container
  - Main page elements: Direct XPath
- **Source**: Generated or from Excel

#### `selector` (string, optional)
- **Description**: Alternative selector (usually same as XPath)
- **Example**: `"//div[@id=\"mui-component-select-dataCommons\"]"`
- **Note**: Often duplicates `xpath` field

### Source & Discovery Attributes

#### `source` (string, required)
- **Description**: Origin of the element entry
- **Possible Values**:
  - `"excel"` - From Excel file upload
  - `"ai_discovery"` - Discovered by AI agent during test execution
  - `"manual"` - Manually added
- **Example**: `"excel"`

#### `discovery_method` (string, optional)
- **Description**: Method used to discover the element (for AI discoveries)
- **Possible Values**:
  - `"direct"` - Direct element match
  - `"llm_prediction"` - LLM predicted the element
  - `"xpath_generation"` - XPath was generated
- **Example**: `"llm_prediction"`
- **Note**: Only present for `source: "ai_discovery"`

#### `discovered_at` (string, ISO8601, optional)
- **Description**: When element was first discovered/added
- **Example**: `"2026-01-20T12:08:32.002019Z"`
- **Format**: ISO8601 with Z suffix (UTC)
- **Note**: Present for Excel and AI discoveries

#### `discovery_url` (string, optional)
- **Description**: URL where element was discovered (may differ from page URL)
- **Example**: `"https://hub-stage.datacommons.cancer.gov/data-submissions"`
- **Note**: Important for modal elements discovered on different pages

### Element Type & Action Attributes

#### `type` (string, optional)
- **Description**: HTML element type
- **Possible Values**: `"input"`, `"button"`, `"div"`, `"a"`, `"select"`, etc.
- **Example**: `"input"`
- **Note**: Present for AI discoveries

#### `object_type` (string, optional)
- **Description**: Element type from Excel/Object Type column
- **Possible Values**: `"button"`, `"input"`, `"dropdown"`, `"option"`, `"link"`, etc.
- **Example**: `"dropdown"`
- **Note**: Present for Excel-sourced elements

#### `action` (string, optional)
- **Description**: Action performed on element
- **Possible Values**: `"click"`, `"fill"`, `"verify"`, `"navigate"`
- **Example**: `"click"`
- **Note**: Present for Excel-sourced elements

### Location & Context Attributes

#### `url` (string, optional)
- **Description**: URL where element is used
- **Example**: `"https://hub-stage.datacommons.cancer.gov/data-submissions"`
- **Note**: May differ from `discovery_url` for modal elements

#### `context` (string, optional)
- **Description**: Element context (modal vs main page)
- **Possible Values**:
  - `"main-page"` - Element on main page
  - `"modal"` - Element inside modal dialog
- **Example**: `"modal"`
- **Default**: `"main-page"`

### Uniqueness & Matching Attributes

#### `uniqueness_method` (string, optional)
- **Description**: Method used to ensure element uniqueness
- **Possible Values**:
  - `"xpath"` - XPath-based uniqueness
  - `"id"` - ID-based uniqueness
  - `"positional"` - Position-based uniqueness
  - `"clicked_xpath"` - XPath from clicked element
- **Example**: `"xpath"`

#### `unique_attributes` (object, optional)
- **Description**: Key attributes that make element unique
- **Structure**: Key-value pairs of HTML attributes
- **Example**:
```json
{
  "id": "mui-component-select-dataCommons",
  "role": "button",
  "aria-labelledby": "dataCommons",
  "name": "dataCommons"
}
```
- **Common Attributes Captured**:
  - `id` - Element ID
  - `name` - Input/select name
  - `role` - ARIA role
  - `data-testid` - Test ID attribute
  - `aria-label` - ARIA label
  - `aria-labelledby` - ARIA labelled-by reference
  - `class` - CSS classes
  - `type` - Input type
  - `placeholder` - Input placeholder
  - `text` - Element text content

### Usage Tracking Attributes

#### `usage_count` (number, optional)
- **Description**: Number of times element has been used
- **Example**: `1`
- **Default**: `0` or `1` (depending on source)

#### `last_used` (string, ISO8601, optional)
- **Description**: Last time element was used
- **Example**: `"2026-01-20T17:00:31.858426Z"`
- **Format**: ISO8601 with Z suffix (UTC)
- **Note**: `null` if never used

#### `last_updated` (string, ISO8601, optional)
- **Description**: Last time element was updated
- **Example**: `"2026-01-20T17:00:31.858426Z"`
- **Format**: ISO8601 with Z suffix (UTC)

### Metadata Attributes

#### `description` (string, optional)
- **Description**: Human-readable description of element
- **Example**: `"Discovered by AI in test exec_1768523816"`
- **Format**: Free text

#### `name` (string, optional)
- **Description**: Element name (used as key in elements object)
- **Example**: `"dropdown_16"`
- **Note**: This is the key, not stored as attribute

#### `alternatives` (array, optional)
- **Description**: Alternative selectors/XPaths for element
- **Example**: `[]`
- **Type**: Array of strings
- **Note**: Usually empty, reserved for future use

### Step Tracking Attributes (AI Discoveries)

#### `step_number` (number, optional)
- **Description**: Step number when element was discovered
- **Example**: `13`
- **Note**: Only present for AI discoveries with execution context

#### `step_identifier` (string, optional)
- **Description**: Step identifier (may include letters like "13a", "13b")
- **Example**: `"13"` or `"13a"`
- **Note**: Only present for AI discoveries with execution context

---

## Source Types

### 1. Excel-Sourced Elements (`source: "excel"`)

**Attributes Present**:
- `element_id` ✅
- `xpath` ✅
- `selector` ✅
- `url` ✅
- `source: "excel"` ✅
- `object_type` ✅
- `action` ✅
- `discovered_at` ✅
- `usage_count` ✅
- `last_used` ✅ (may be null)
- `last_updated` ✅ (optional)

**Example**:
```json
{
  "dropdown_16": {
    "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
    "selector": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
    "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
    "element_id": "ID_70bc9e6a",
    "usage_count": 0,
    "last_used": null,
    "source": "excel",
    "object_type": "dropdown",
    "action": "click",
    "discovered_at": "2026-01-20T12:08:32.002019Z"
  }
}
```

### 2. AI-Discovered Elements (`source: "ai_discovery"`)

**Attributes Present**:
- `element_id` ✅
- `xpath` ✅
- `selector` ✅
- `source: "ai_discovery"` ✅
- `discovery_method` ✅
- `type` ✅
- `description` ✅
- `discovery_url` ✅
- `unique_attributes` ✅ (optional)
- `context` ✅
- `uniqueness_method` ✅
- `usage_count` ✅
- `alternatives` ✅
- `step_number` ✅ (optional)
- `step_identifier` ✅ (optional)

**Example**:
```json
{
  "text": {
    "selector": "input[type=\"text\"]",
    "xpath": "(//*)[1]",
    "uniqueness_method": "positional",
    "type": "input",
    "description": "Discovered by AI in test exec_1768523816",
    "source": "ai_discovery",
    "discovery_method": "direct",
    "usage_count": 1,
    "alternatives": [],
    "discovery_url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
    "unique_attributes": null,
    "context": "main-page",
    "element_id": "ID_d4e1aae2"
  }
}
```

### 3. Manually Added Elements (`source: "manual"`)

**Attributes Present**:
- `element_id` ✅
- `xpath` ✅
- `selector` ✅
- `source: "manual"` ✅
- Other attributes as needed

---

## Complete Examples

### Example 1: Excel-Sourced Dropdown (Modal Element)

```json
{
  "dropdown_16": {
    "xpath": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
    "selector": "//div[@data-testid=\"create-data-submission-dialog-data-commons-input\"]//div[@id=\"mui-component-select-dataCommons\"]",
    "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
    "element_id": "ID_70bc9e6a",
    "usage_count": 0,
    "last_used": null,
    "source": "excel",
    "object_type": "dropdown",
    "action": "click",
    "discovered_at": "2026-01-20T12:08:32.002019Z"
  }
}
```

**Key Points**:
- XPath is scoped to modal container (`create-data-submission-dialog-data-commons-input`)
- `object_type` indicates it's a dropdown
- `action` indicates it's clicked
- `source` is `"excel"`

### Example 2: Excel-Sourced Option (Modal Element)

```json
{
  "option_16b": {
    "xpath": "(//*[@data-testid=\"create-submission-dialog\"])//ul[@role=\"listbox\"]//li[@role=\"option\" and normalize-space(.)=\"GC\"]",
    "selector": "(//*[@data-testid=\"create-submission-dialog\"])//ul[@role=\"listbox\"]//li[@role=\"option\" and normalize-space(.)=\"GC\"]",
    "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
    "element_id": "ID_0aad039e",
    "usage_count": 0,
    "last_used": null,
    "source": "excel",
    "object_type": "option",
    "action": "click",
    "discovered_at": "2026-01-20T12:08:32.002044Z"
  }
}
```

**Key Points**:
- XPath includes text content (`normalize-space(.)="GC"`)
- Scoped to modal dialog
- `object_type` is `"option"`

### Example 3: Excel-Sourced Input (Fill Action)

```json
{
  "input_18": {
    "xpath": "(//*[@data-testid=\"create-submission-dialog\"])//input[@name='name']",
    "selector": "(//*[@data-testid=\"create-submission-dialog\"])//input[@name='name']",
    "url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
    "element_id": "ID_d8cd705a",
    "usage_count": 0,
    "last_used": null,
    "source": "excel",
    "object_type": "input",
    "action": "fill",
    "discovered_at": "2026-01-20T12:08:32.002115Z"
  }
}
```

**Key Points**:
- Uses `name` attribute for XPath
- `action` is `"fill"` (not `"click"`)
- Scoped to modal

### Example 4: AI-Discovered Element (With Unique Attributes)

```json
{
  "input_18": {
    "selector": "//input[@name='name']",
    "xpath": "(//*[@data-testid=\"create-submission-dialog\"])//input[@name='name']",
    "uniqueness_method": "xpath",
    "type": "input",
    "description": "Discovered by AI in test exec_1768523816",
    "source": "ai_discovery",
    "discovery_method": "llm_prediction",
    "usage_count": 1,
    "alternatives": [],
    "discovery_url": "https://hub-stage.datacommons.cancer.gov/data-submissions",
    "unique_attributes": {
      "name": "name",
      "placeholder": "25 characters allowed",
      "maxlength": "25",
      "aria-labelledby": "submissionName",
      "class": "MuiInputBase-input MuiOutlinedInput-input css-1x5jdmq"
    },
    "context": "main-page",
    "element_id": "ID_d8cd705a"
  }
}
```

**Key Points**:
- `unique_attributes` contains detailed HTML attributes
- `discovery_method` is `"llm_prediction"`
- `context` is stored (though XPath is modal-scoped)

---

## ID Index Structure

### Purpose
Maps `element_id` to element name for quick lookup.

### Structure
```json
{
  "id_index": {
    "ID_70bc9e6a": "dropdown_16",
    "ID_0aad039e": "option_16b",
    "ID_d2542a0d": "dropdown_17"
  }
}
```

### Rules
- **Key**: `element_id` (e.g., `"ID_70bc9e6a"`)
- **Value**: Element name/key in `elements` object (e.g., `"dropdown_16"`)
- **Uniqueness**: Each `element_id` maps to exactly one element name
- **Note**: One `element_id` can map to multiple entries if element appears in multiple registries

---

## Statistics Section

### Structure
```json
{
  "statistics": {
    "total_elements": 11,
    "parsed_elements": 0,
    "discovered_elements": 0
  }
}
```

### Attributes

#### `total_elements` (number)
- **Description**: Total number of elements in registry
- **Example**: `11`
- **Calculation**: Count of keys in `elements` object

#### `parsed_elements` (number)
- **Description**: Number of elements parsed from HTML (legacy, usually 0)
- **Example**: `0`
- **Note**: Not actively used

#### `discovered_elements` (number)
- **Description**: Number of elements discovered by AI (legacy, usually 0)
- **Example**: `0`
- **Note**: Not actively used

---

## Attribute Reference Table

| Attribute | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `element_id` | string | ✅ | All | Unique identifier (ID_xxxxx) |
| `xpath` | string | ✅ | All | XPath selector |
| `selector` | string | ⚠️ | All | Alternative selector |
| `source` | string | ✅ | All | "excel", "ai_discovery", "manual" |
| `url` | string | ⚠️ | Excel | URL where element is used |
| `discovery_url` | string | ⚠️ | AI | URL where element was discovered |
| `object_type` | string | ⚠️ | Excel | Element type from Excel |
| `action` | string | ⚠️ | Excel | Action performed ("click", "fill") |
| `type` | string | ⚠️ | AI | HTML element type |
| `discovery_method` | string | ⚠️ | AI | "direct", "llm_prediction", etc. |
| `discovered_at` | ISO8601 | ⚠️ | Excel/AI | When element was discovered |
| `last_updated` | ISO8601 | ⚠️ | All | Last update timestamp |
| `last_used` | ISO8601/null | ⚠️ | All | Last usage timestamp |
| `usage_count` | number | ⚠️ | All | Number of times used |
| `context` | string | ⚠️ | AI | "main-page" or "modal" |
| `unique_attributes` | object | ⚠️ | AI | Key HTML attributes |
| `uniqueness_method` | string | ⚠️ | AI | Uniqueness strategy |
| `description` | string | ⚠️ | AI | Human-readable description |
| `alternatives` | array | ⚠️ | AI | Alternative selectors |
| `step_number` | number | ⚠️ | AI | Step number when discovered |
| `step_identifier` | string | ⚠️ | AI | Step identifier ("13", "13a") |

**Legend**:
- ✅ = Always present
- ⚠️ = Conditionally present (depends on source or context)

---

## Element Naming Conventions

### Excel-Sourced Elements
- **Pattern**: `{object_type}_{step_number}` or `{object_type}_{step_number}{suffix}`
- **Examples**:
  - `button_14` - Button from Step 14
  - `dropdown_16` - Dropdown from Step 16
  - `option_16b` - Option from Step 16 (second option, hence "b")
  - `input_18` - Input from Step 18

### AI-Discovered Elements
- **Pattern**: Descriptive name based on element characteristics
- **Examples**:
  - `text` - Generic text input
  - `submit_button` - Submit button
  - `login_email` - Email input field

---

## Modal vs Main-Page Elements

### Main-Page Elements
- **XPath**: Direct XPath without modal scoping
- **Example**: `//div[@id="mui-component-select-dataCommons"]`
- **Context**: `"main-page"` (or not specified)

### Modal Elements
- **XPath**: Scoped to modal container
- **Example**: `//div[@data-testid="create-data-submission-dialog-data-commons-input"]//div[@id="mui-component-select-dataCommons"]`
- **Context**: `"modal"`
- **Note**: XPath includes modal container to ensure correct element is found

---

## Data Types Reference

### String Types
- **ISO8601 DateTime**: `"2026-01-20T12:08:32.002019Z"` (UTC timezone)
- **URL**: Full URL string
- **XPath**: Valid XPath expression
- **Element ID**: `"ID_{8 hex characters}"`

### Number Types
- **usage_count**: Integer (0 or positive)
- **step_number**: Integer (positive)

### Object Types
- **unique_attributes**: Object with string keys and string/null values
- **elements**: Object with element names as keys

### Array Types
- **alternatives**: Array of strings (usually empty)

### Null Values
- **last_used**: Can be `null` if never used
- **unique_attributes**: Can be `null` if no unique attributes found

---

## Validation Rules

### Required Fields (All Sources)
- `element_id` - Must be unique format: `ID_{8 hex}`
- `xpath` - Must be valid XPath expression
- `source` - Must be one of: `"excel"`, `"ai_discovery"`, `"manual"`

### Excel Source Requirements
- `object_type` - Must be present
- `action` - Must be present
- `url` - Should match page URL
- `discovered_at` - Should be present

### AI Discovery Requirements
- `discovery_method` - Must be present
- `type` - Should be present
- `description` - Should be present
- `discovery_url` - Should be present

### XPath Validation
- Must be valid XPath syntax
- Modal elements must include modal container in XPath
- Should not contain invalid characters or triple slashes (`///`)

---

## Common Patterns

### Pattern 1: Dropdown Button
```json
{
  "xpath": "//div[@id=\"mui-component-select-dataCommons\"]",
  "object_type": "dropdown",
  "action": "click"
}
```

### Pattern 2: Dropdown Option
```json
{
  "xpath": "//li[@role=\"option\" and normalize-space(.)=\"GC\"]",
  "object_type": "option",
  "action": "click"
}
```

### Pattern 3: Input Field
```json
{
  "xpath": "//input[@name='name']",
  "object_type": "input",
  "action": "fill"
}
```

### Pattern 4: Button
```json
{
  "xpath": "//button[@data-testid='create-data-submission-dialog-create-button']",
  "object_type": "button",
  "action": "click"
}
```

---

## Summary

### Key Attributes for Independent Tasks

**Minimum Required** (for any element):
- `element_id` - Unique identifier
- `xpath` - XPath selector
- `source` - Origin of element

**Excel Elements** (additional):
- `object_type` - Element type
- `action` - Action to perform
- `url` - Page URL

**AI Discovered Elements** (additional):
- `discovery_method` - How it was discovered
- `type` - HTML element type
- `unique_attributes` - Key attributes
- `context` - Modal or main-page

**All Elements** (optional but useful):
- `discovered_at` - Timestamp
- `usage_count` - Usage tracking
- `last_updated` - Update timestamp

This structure allows independent developers to:
1. Understand what data is stored
2. Create/update JSON registries correctly
3. Query elements by various attributes
4. Maintain element metadata properly

