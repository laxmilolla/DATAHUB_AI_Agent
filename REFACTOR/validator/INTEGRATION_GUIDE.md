# Test Runner Integration Guide

This guide shows how to integrate Excel support into the existing TestRunner when it's pulled from BACKUP.

## Current TestRunner Structure

The existing `TestRunner` class (from `BACKUP/validator/test_runner.py`) has:
- `run(test_file, execution_id)` method
- Screenshot capture
- Result reporting
- Execution metadata structure

## Enhancement Strategy

Instead of modifying the existing TestRunner directly, we create a wrapper that:
1. Uses the existing TestRunner
2. Adds Excel metadata support
3. Links Excel files to test executions
4. Saves results back to Excel metadata

## Integration Steps

### Step 1: Copy TestRunner from BACKUP

```python
# Copy BACKUP/validator/test_runner.py to validator/test_runner.py
# Keep existing functionality intact
```

### Step 2: Enhance TestRunner.run() Method

Add `excel_id` parameter to the `run()` method:

```python
# In validator/test_runner.py
def run(self, test_file: str, execution_id: str = None, 
        excel_id: str = None) -> Dict[str, Any]:
    """
    Run a generated Playwright test
    
    Args:
        test_file: Name of test file
        execution_id: Original execution ID (for comparison)
        excel_id: Optional Excel file ID (for Excel-generated tests)
        
    Returns:
        Dict with test results
    """
    # Existing test execution logic...
    test_result = {
        'status': 'passed' if passed else 'failed',
        # ... existing fields ...
    }
    
    # Add Excel metadata if provided
    if excel_id:
        excel_metadata = self._load_excel_metadata(excel_id)
        if excel_metadata:
            test_result['excel_id'] = excel_id
            test_result['excel_metadata'] = {
                'excel_id': excel_id,
                'filename': excel_metadata.get('filename'),
                'uploaded_at': excel_metadata.get('uploaded_at')
            }
            test_result['source'] = 'excel'
    
    return test_result
```

### Step 3: Add Helper Methods

Add methods to load and save Excel metadata:

```python
# In validator/test_runner.py
def _load_excel_metadata(self, excel_id: str) -> Optional[Dict]:
    """Load Excel file metadata"""
    metadata_file = self.project_root / 'storage' / 'excel_files' / 'metadata' / f"{excel_id}.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None

def _save_excel_test_result(self, excel_id: str, test_result: Dict):
    """Save test result back to Excel metadata"""
    metadata_file = self.project_root / 'storage' / 'excel_files' / 'metadata' / f"{excel_id}.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        if 'test_executions' not in metadata:
            metadata['test_executions'] = []
        
        metadata['test_executions'].append({
            'execution_id': test_result.get('execution_id'),
            'test_file': test_result.get('test_file'),
            'status': test_result.get('status'),
            'executed_at': test_result.get('timestamp')
        })
        
        metadata['last_execution'] = metadata['test_executions'][-1]
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
```

### Step 4: Update API Endpoints

Update Excel API endpoints to use enhanced TestRunner:

```python
# In REFACTOR/api/excel_routes.py
from validator.test_runner import TestRunner

@bp_excel.route('/api/excel/<excel_id>/run-test', methods=['POST'])
def run_excel_test(excel_id):
    """Run test generated from Excel"""
    # Load metadata
    metadata = load_excel_metadata(excel_id)
    
    if 'generated_test' not in metadata:
        return jsonify({'error': 'Test not generated yet'}), 404
    
    test_file = metadata['generated_test']['test_file']
    
    # Run test with Excel ID
    runner = TestRunner(project_root)
    result = runner.run(test_file, excel_id=excel_id)
    
    return jsonify(result), 200
```

## Alternative: Use Wrapper Class

If you prefer not to modify the existing TestRunner, use the wrapper:

```python
# Use ExcelTestRunner wrapper
from REFACTOR.validator.excel_test_runner import run_test_with_excel
from validator.test_runner import TestRunner

runner = TestRunner(project_root)
result = run_test_with_excel(runner, test_file, excel_id=excel_id)
```

## Benefits

1. **Backward Compatible**: Existing code continues to work
2. **Optional Enhancement**: Excel support is opt-in via `excel_id` parameter
3. **Metadata Tracking**: Excel files linked to test executions
4. **Result Linking**: Test results saved back to Excel metadata

## Testing

After integration, test with:

```python
# Test with Excel ID
runner = TestRunner(project_root)
result = runner.run('test_excel_abc123.py', excel_id='excel_20240115_120000_abc123')

# Verify Excel metadata in result
assert 'excel_id' in result
assert 'excel_metadata' in result
```

## Notes

- Excel support is optional - existing functionality unchanged
- Excel metadata is loaded only when `excel_id` is provided
- Test results are saved back to Excel metadata automatically
- All changes are generic - no hard-coding

