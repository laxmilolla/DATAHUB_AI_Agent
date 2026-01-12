"""
Test Runner
Executes generated Playwright tests and captures results
"""

import subprocess
import time
import json
import sys
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
        # Use venv Python if available, otherwise system Python
        python_executable = sys.executable
        venv_python = self.project_root / 'venv' / 'bin' / 'python3'
        if venv_python.exists():
            python_executable = str(venv_python)
        
        try:
            result = subprocess.run(
                [python_executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout (test includes login flow which can be slow)
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
            
            # Extract Playwright screenshots from output (stdout parsing)
            screenshots_from_stdout = []
            for line in stdout.split('\n'):
                if '📸 Screenshot:' in line:
                    # Extract filename from "📸 Screenshot: storage/screenshots/pw_XXX.png"
                    screenshot_path = line.split('Screenshot:')[1].strip()
                    screenshot_name = screenshot_path.split('/')[-1]  # Get just filename
                    screenshots_from_stdout.append({
                        'filename': screenshot_name,
                        'path': screenshot_path,
                        'full_path': str(self.project_root / screenshot_path)
                    })
            
            # ALSO scan screenshots directory for files created during test execution
            # This captures screenshots even when tests fail before print statements execute
            screenshots_dir = self.project_root / 'storage' / 'screenshots'
            screenshots_from_disk = []
            if screenshots_dir.exists():
                # Get test start time (subtract duration to get start)
                test_start_time = start_time
                
                # Find all pw_step* and pw_* screenshot files created/modified during test
                # Include all variants: regular, _failed, _pre_attempt, _verify, etc.
                for screenshot_file in screenshots_dir.glob('pw_*.png'):
                    try:
                        # Check if file was modified during test execution window
                        file_mtime = screenshot_file.stat().st_mtime
                        # Include files created/modified within 5 minutes of test start (to account for test duration)
                        if file_mtime >= test_start_time - 60:  # 1 minute buffer before test start
                            screenshot_name = screenshot_file.name
                            screenshot_path = f"storage/screenshots/{screenshot_name}"
                            
                            # Only add if not already in stdout screenshots (avoid duplicates)
                            if not any(s['filename'] == screenshot_name for s in screenshots_from_stdout):
                                screenshots_from_disk.append({
                                    'filename': screenshot_name,
                                    'path': screenshot_path,
                                    'full_path': str(screenshot_file),
                                    'source': 'disk'  # Mark as from disk scan
                                })
                    except Exception as e:
                        # Skip files that can't be accessed
                        continue
            
            # Combine screenshots: stdout first (more accurate), then disk (for failed tests)
            screenshots = screenshots_from_stdout + screenshots_from_disk
            
            # Sort by filename to maintain step order (pw_step1_*, pw_step2_*, etc.)
            screenshots.sort(key=lambda x: x['filename'])
            
            test_result = {
                'status': 'passed' if passed else 'failed',
                'exit_code': result.returncode,
                'duration': round(duration, 2),
                'stdout': stdout,
                'stderr': stderr,
                'assertions_passed': assertions_passed,
                'assertions_failed': assertions_failed,
                'screenshots': screenshots,
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

