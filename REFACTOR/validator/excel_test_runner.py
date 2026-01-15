"""
Excel-Enhanced Test Runner
Wrapper around TestRunner that adds Excel metadata support.
This can be integrated with the existing test runner when pulled from BACKUP.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ExcelTestRunner:
    """
    Enhanced Test Runner with Excel metadata support.
    
    This wraps the existing TestRunner and adds Excel-specific functionality.
    When the main TestRunner is pulled from BACKUP, this can be integrated.
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.excel_metadata_dir = self.project_root / 'storage' / 'excel_files' / 'metadata'
    
    def load_excel_metadata(self, excel_id: str) -> Optional[Dict]:
        """
        Load Excel file metadata.
        
        Args:
            excel_id: Excel file ID
            
        Returns:
            Excel metadata dict or None if not found
        """
        metadata_file = self.excel_metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Excel metadata: {e}")
            return None
    
    def enhance_test_result_with_excel(
        self, 
        test_result: Dict[str, Any], 
        excel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhance test result with Excel metadata.
        
        Args:
            test_result: Test result from TestRunner.run()
            excel_id: Optional Excel file ID
            
        Returns:
            Enhanced test result with Excel metadata
        """
        if not excel_id:
            return test_result
        
        # Load Excel metadata
        excel_metadata = self.load_excel_metadata(excel_id)
        
        if excel_metadata:
            # Add Excel metadata to test result
            test_result['excel_id'] = excel_id
            test_result['excel_metadata'] = {
                'excel_id': excel_id,
                'filename': excel_metadata.get('filename'),
                'uploaded_at': excel_metadata.get('uploaded_at'),
                'validation': excel_metadata.get('validation', {}),
                'generated_test': excel_metadata.get('generated_test', {})
            }
            
            # Link Excel file to test execution
            test_result['source'] = 'excel'
            test_result['source_file'] = excel_metadata.get('file_path')
        
        return test_result
    
    def save_excel_test_result(
        self, 
        excel_id: str, 
        test_result: Dict[str, Any]
    ) -> bool:
        """
        Save test result back to Excel metadata file.
        
        Args:
            excel_id: Excel file ID
            test_result: Test result from TestRunner.run()
            
        Returns:
            True if saved successfully, False otherwise
        """
        metadata_file = self.excel_metadata_dir / f"{excel_id}.json"
        
        if not metadata_file.exists():
            print(f"Excel metadata file not found: {metadata_file}")
            return False
        
        try:
            # Load existing metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Add test execution results
            if 'test_executions' not in metadata:
                metadata['test_executions'] = []
            
            execution_record = {
                'execution_id': test_result.get('execution_id'),
                'test_file': test_result.get('test_file'),
                'status': test_result.get('status'),
                'duration': test_result.get('duration'),
                'assertions_passed': test_result.get('assertions_passed', 0),
                'assertions_failed': test_result.get('assertions_failed', 0),
                'screenshots_count': len(test_result.get('screenshots', [])),
                'executed_at': test_result.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                'exit_code': test_result.get('exit_code', 0)
            }
            
            metadata['test_executions'].append(execution_record)
            
            # Update last execution info
            metadata['last_execution'] = execution_record
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving Excel test result: {e}")
            return False


def run_test_with_excel(
    test_runner,
    test_file: str,
    excel_id: Optional[str] = None,
    execution_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run test with Excel metadata support.
    
    This is a helper function that can be used to enhance the existing
    TestRunner.run() method with Excel support.
    
    Args:
        test_runner: TestRunner instance
        test_file: Test file name
        excel_id: Optional Excel file ID
        execution_id: Optional execution ID
        
    Returns:
        Enhanced test result with Excel metadata
    """
    # Run test using existing TestRunner
    test_result = test_runner.run(test_file, execution_id=execution_id)
    
    # Enhance with Excel metadata if provided
    if excel_id:
        excel_runner = ExcelTestRunner(test_runner.project_root)
        test_result = excel_runner.enhance_test_result_with_excel(test_result, excel_id)
        
        # Save result back to Excel metadata
        excel_runner.save_excel_test_result(excel_id, test_result)
    
    return test_result

