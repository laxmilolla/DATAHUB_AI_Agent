"""
Test Runner
Executes generated Playwright tests and captures results
"""

import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class TestRunner:
    """Run generated Playwright tests and capture results"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.generated_tests_dir = self.project_root / 'tests' / 'generated'
    
    def run(self, test_file: str, execution_id: str = None) -> Dict[str, Any]:
        """
        Run a generated Playwright test
        
        Args:
            test_file: Name of test file (e.g., 'test_samples.py')
            execution_id: Original execution ID (for comparison)
            
        Returns:
            Dict with test results
        """
        test_path = self.generated_tests_dir / test_file
        
        if not test_path.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")
        
        print(f"🚀 Running generated test: {test_file}")
        
        start_time = time.time()
        
        # Run the test as a subprocess
        try:
            result = subprocess.run(
                ['python', str(test_path)],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=str(self.project_root)
            )
            
            duration = time.time() - start_time
            
            # Parse results
            passed = result.returncode == 0
            stdout = result.stdout
            stderr = result.stderr
            
            # Count assertions
            assertions_passed = stdout.count('✅')
            assertions_failed = stdout.count('❌')
            
            test_result = {
                'status': 'passed' if passed else 'failed',
                'exit_code': result.returncode,
                'duration': round(duration, 2),
                'stdout': stdout,
                'stderr': stderr,
                'assertions_passed': assertions_passed,
                'assertions_failed': assertions_failed,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'test_file': test_file,
                'execution_id': execution_id
            }
            
            if passed:
                print(f"✅ Test PASSED in {duration:.2f}s")
                print(f"   Assertions: {assertions_passed} passed")
            else:
                print(f"❌ Test FAILED in {duration:.2f}s")
                print(f"   Assertions: {assertions_passed} passed, {assertions_failed} failed")
                if stderr:
                    print(f"   Error: {stderr[:200]}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'status': 'timeout',
                'exit_code': -1,
                'duration': round(duration, 2),
                'stdout': '',
                'stderr': 'Test execution timeout (120s exceeded)',
                'assertions_passed': 0,
                'assertions_failed': 0,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'test_file': test_file,
                'execution_id': execution_id
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'exit_code': -1,
                'duration': 0,
                'stdout': '',
                'stderr': str(e),
                'assertions_passed': 0,
                'assertions_failed': 0,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'test_file': test_file,
                'execution_id': execution_id
            }
    
    def run_from_code(self, code: str, test_name: str = 'temp_test') -> Dict[str, Any]:
        """
        Run Playwright test from code string (temporary file)
        
        Args:
            code: Python Playwright code
            test_name: Name for temporary test file
            
        Returns:
            Dict with test results
        """
        # Write to temporary file
        temp_file = self.generated_tests_dir / f'{test_name}.py'
        with open(temp_file, 'w') as f:
            f.write(code)
        
        # Run the test
        result = self.run(f'{test_name}.py')
        
        return result


# Example usage
if __name__ == '__main__':
    runner = TestRunner()
    result = runner.run('test_samples.py', execution_id='exec_172351d5')
    
    print("\n📊 Test Results:")
    print(json.dumps(result, indent=2))

