# Excel API Routes

API endpoints for Excel file upload, test generation, and template download.

## Endpoints

### 1. Upload Excel File
**POST** `/api/excel/upload`

Upload and validate an Excel file.

**Request:**
- Form data with `file` field (Excel file)

**Response:**
```json
{
  "success": true,
  "excel_id": "excel_20240115_120000_abc123",
  "filename": "test_case.xlsx",
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "uploaded_at": "2024-01-15T12:00:00"
}
```

### 2. Generate Test from Excel
**POST** `/api/excel/generate`

Generate Playwright test from uploaded Excel file.

**Request:**
```json
{
  "excel_id": "excel_20240115_120000_abc123",
  "test_name": "optional_test_name"
}
```

**Response:**
```json
{
  "success": true,
  "excel_id": "excel_20240115_120000_abc123",
  "test_name": "test_excel_abc123",
  "test_file": "storage/excel_tests/test_excel_abc123.py",
  "rows_processed": 10,
  "generated_at": "2024-01-15T12:00:00"
}
```

### 3. Get Excel Status
**GET** `/api/excel/<excel_id>/status`

Get status and metadata for an Excel file.

**Response:**
```json
{
  "excel_id": "excel_20240115_120000_abc123",
  "filename": "test_case.xlsx",
  "uploaded_at": "2024-01-15T12:00:00",
  "validation": {...},
  "generation_status": "completed",
  "generated_test": {...}
}
```

### 4. Download Template
**GET** `/api/excel/template?include_examples=true`

Download Excel template file.

**Query Parameters:**
- `include_examples`: true/false (default: true)

**Response:**
- Excel file download

### 5. Get Excel Metadata
**GET** `/api/excel/<excel_id>/metadata`

Get full metadata for an Excel file.

**Response:**
```json
{
  "excel_id": "excel_20240115_120000_abc123",
  "filename": "test_case.xlsx",
  "uploaded_at": "2024-01-15T12:00:00",
  "validation": {...},
  "generated_test": {...}
}
```

### 6. Download Excel File
**GET** `/api/excel/<excel_id>/download`

Download the uploaded Excel file.

**Response:**
- Excel file download

### 7. Download Generated Test
**GET** `/api/excel/<excel_id>/test`

Download the generated Playwright test file.

**Response:**
- Python file download

## Integration

To use these endpoints in a Flask app:

```python
from REFACTOR.api.excel_routes import bp_excel

app.register_blueprint(bp_excel)
```

## Storage Structure

Excel files are stored in:
- `storage/excel_files/` - Uploaded Excel files
- `storage/excel_files/metadata/` - Excel metadata JSON files
- `storage/excel_tests/` - Generated Playwright test files

## Error Handling

All endpoints follow consistent error handling:
- 400: Bad request (missing/invalid parameters)
- 404: Resource not found
- 500: Server error

Error responses:
```json
{
  "error": "Error message"
}
```

## Notes

- All endpoints are generic - no application-specific hard-coding
- File uploads are validated before saving
- Test generation happens synchronously (can be enhanced with background threads)
- Metadata is stored in JSON format for easy access

