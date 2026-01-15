# Results Page Enhancement Guide

This guide shows how to enhance the existing results page (`BACKUP/web/templates/results.html`) to display Excel metadata.

## Enhancement Strategy

Add Excel metadata display to the results page when a test was generated from an Excel file.

## Integration Steps

### Step 1: Add Excel Metadata Section

Add this section to the results page HTML (after the status banner):

```html
<!-- Excel Metadata Section (if test was generated from Excel) -->
<div id="excel-metadata-section" class="card" style="display: none; margin-bottom: 20px;">
    <h3>📊 Excel Test Case</h3>
    <div id="excel-metadata-content"></div>
</div>
```

### Step 2: Add JavaScript to Display Excel Metadata

Add this JavaScript function to `results.html` or create a separate file:

```javascript
function displayExcelMetadata(results) {
    const excelSection = document.getElementById('excel-metadata-section');
    const excelContent = document.getElementById('excel-metadata-content');
    
    // Check if results have Excel metadata
    if (!results.excel_id && !results.excel_metadata) {
        excelSection.style.display = 'none';
        return;
    }
    
    const excelId = results.excel_id || results.excel_metadata?.excel_id;
    const metadata = results.excel_metadata || {};
    
    if (!excelId) {
        excelSection.style.display = 'none';
        return;
    }
    
    // Show section
    excelSection.style.display = 'block';
    
    // Build HTML content
    let html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <div>
                <strong>Excel File:</strong><br>
                <span>${metadata.filename || 'N/A'}</span>
            </div>
            <div>
                <strong>Uploaded:</strong><br>
                <span>${metadata.uploaded_at ? new Date(metadata.uploaded_at).toLocaleString() : 'N/A'}</span>
            </div>
            <div>
                <strong>Validation:</strong><br>
                <span style="color: ${metadata.validation?.valid ? '#28a745' : '#dc3545'};">
                    ${metadata.validation?.valid ? '✅ Valid' : '❌ Invalid'}
                </span>
            </div>
        </div>
        
        <div style="margin-top: 20px;">
            <button class="btn btn-secondary" onclick="downloadExcelFile('${excelId}')">
                Download Excel File
            </button>
            <button class="btn btn-secondary" onclick="viewExcelStatus('${excelId}')">
                View Excel Status
            </button>
        </div>
    `;
    
    excelContent.innerHTML = html;
}

function downloadExcelFile(excelId) {
    window.location.href = `/api/excel/${excelId}/download`;
}

async function viewExcelStatus(excelId) {
    try {
        const response = await fetch(`/api/excel/${excelId}/status`);
        const data = await response.json();
        
        if (response.ok) {
            alert(`Excel Status:\n\n` +
                  `File: ${data.filename}\n` +
                  `Uploaded: ${data.uploaded_at}\n` +
                  `Generation Status: ${data.generation_status}\n` +
                  `Validation: ${data.validation?.valid ? 'Valid' : 'Invalid'}`);
        } else {
            alert('Error: ' + (data.error || 'Failed to get status'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}
```

### Step 3: Call Display Function

In the results page JavaScript, call `displayExcelMetadata()` when loading results:

```javascript
// When loading execution results
async function loadExecutionResults(executionId) {
    try {
        const response = await fetch(`/api/executions/${executionId}/results`);
        const data = await response.json();
        
        // ... existing result display code ...
        
        // Display Excel metadata if present
        displayExcelMetadata(data);
        
    } catch (error) {
        console.error('Error loading results:', error);
    }
}
```

### Step 4: Check for Excel Metadata in Results

The results JSON should include Excel metadata when a test was generated from Excel:

```json
{
  "execution_id": "exec_123",
  "status": "completed",
  "excel_id": "excel_20240115_120000_abc123",
  "excel_metadata": {
    "excel_id": "excel_20240115_120000_abc123",
    "filename": "test_case.xlsx",
    "uploaded_at": "2024-01-15T12:00:00",
    "validation": {
      "valid": true,
      "row_count": 10
    }
  }
}
```

## CSS Styling

Add these styles to match the existing results page:

```css
#excel-metadata-section {
    background: white;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    border-left: 5px solid #667eea;
}

#excel-metadata-section h3 {
    margin-top: 0;
    color: #2c3e50;
    font-size: 1.5em;
}
```

## Integration Points

1. **Results Loading**: Add Excel metadata display when results are loaded
2. **Status Display**: Show Excel file info in status section
3. **Download Links**: Add links to download Excel file and generated test
4. **Metadata Display**: Show validation results and upload info

## Notes

- Excel metadata is optional - only shown when present
- All display is generic - no hard-coding
- Follows existing results page patterns
- Backward compatible with existing results

