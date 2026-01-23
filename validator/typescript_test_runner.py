"""
TypeScript Test Runner
Executes generated Playwright TypeScript tests and captures results
"""

import subprocess
import time
import json
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class TypeScriptTestRunner:
    """Run generated Playwright TypeScript tests and capture results"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.excel_tests_dir = self.project_root / 'storage' / 'excel_tests'
    
    def run(self, test_file: str, execution_id: str = None) -> Dict[str, Any]:
        """
        Run a generated Playwright TypeScript test
        
        Args:
            test_file: Name of test file (e.g., 'test_excel_xxx.spec.ts') or full path
            execution_id: Original execution ID (for comparison)
            
        Returns:
            Dict with test results
        """
        # Handle both relative and absolute paths
        if Path(test_file).is_absolute():
            test_path = Path(test_file)
        else:
            test_path = self.excel_tests_dir / test_file
        
        if not test_path.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")
        
        print(f"🚀 Running TypeScript test: {test_path.name}")
        
        start_time = time.time()
        
        # Check if Node.js and Playwright are available
        node_executable = shutil.which('node')
        npx_executable = shutil.which('npx')
        
        if not node_executable:
            raise RuntimeError("Node.js not found. Please install Node.js to run TypeScript tests.")
        
        if not npx_executable:
            raise RuntimeError("npx not found. Please install npm to run TypeScript tests.")
        
        # Get the directory containing the test file
        test_dir = test_path.parent
        
        # Check if package.json exists in test directory, if not, create one
        package_json = test_dir / 'package.json'
        if not package_json.exists():
            # Create minimal package.json for Playwright
            package_json_content = {
                "name": "playwright-test",
                "version": "1.0.0",
                "scripts": {
                    "test": "playwright test"
                },
                "dependencies": {
                    "@playwright/test": "^1.40.0",
                    "dotenv": "^16.0.0",
                    "otplib": "^12.0.0"
                }
            }
            with open(package_json, 'w') as f:
                json.dump(package_json_content, f, indent=2)
            print(f"✅ Created package.json in {test_dir}")
        
        # Check if node_modules exists, if not, install dependencies
        node_modules = test_dir / 'node_modules'
        if not node_modules.exists():
            print(f"📦 Installing dependencies in {test_dir}...")
            install_result = subprocess.run(
                [npx_executable, 'npm', 'install'],
                cwd=str(test_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for npm install
            )
            if install_result.returncode != 0:
                print(f"⚠️  npm install failed: {install_result.stderr}")
                # Continue anyway, Playwright might still work
        
        # Install Playwright browsers if needed
        playwright_install_result = subprocess.run(
            [npx_executable, 'playwright', 'install', 'chromium'],
            cwd=str(test_dir),
            capture_output=True,
            text=True,
            timeout=300
        )
        # Don't fail if browser install fails, might already be installed
        
        try:
            # Run the test using npx playwright test
            result = subprocess.run(
                [npx_executable, 'playwright', 'test', test_path.name, '--reporter=list'],
                cwd=str(test_dir),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout (test has 5 min timeout, allow extra for setup/teardown)
                env={**dict(os.environ), 'CI': 'true'}  # Set CI mode for headless
            )
            
            duration = time.time() - start_time
            
            # Parse results
            passed = result.returncode == 0
            stdout = result.stdout
            stderr = result.stderr
            
            # Count assertions from console output
            assertions_passed = stdout.count('✅') + stdout.count('passed')
            assertions_failed = stdout.count('❌') + stdout.count('failed')
            
            # Extract Playwright screenshots from disk (same as Python runner)
            screenshots = self._collect_screenshots(start_time, duration, execution_id)
            
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
                'test_file': str(test_path.relative_to(self.project_root)),
                'execution_id': execution_id
            }
            
            if passed:
                print(f"✅ TypeScript test PASSED in {duration:.2f}s")
                print(f"   Assertions: {assertions_passed} passed")
            else:
                print(f"❌ TypeScript test FAILED in {duration:.2f}s")
                print(f"   Assertions: {assertions_passed} passed, {assertions_failed} failed")
                if stderr:
                    print(f"   Error: {stderr[:200]}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            # Collect screenshots even on timeout (test may have generated some before timing out)
            screenshots = self._collect_screenshots(start_time, duration, execution_id)
            return {
                'status': 'timeout',
                'exit_code': -1,
                'duration': round(duration, 2),
                'stdout': '',
                'stderr': 'Test execution timeout (600s exceeded)',
                'assertions_passed': 0,
                'assertions_failed': 0,
                'screenshots': screenshots,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'test_file': str(test_path.relative_to(self.project_root)),
                'execution_id': execution_id
            }
        
        except Exception as e:
            # Collect screenshots even on error (test may have generated some before error)
            screenshots = self._collect_screenshots(start_time, 0, execution_id)
            return {
                'status': 'error',
                'exit_code': -1,
                'duration': 0,
                'stdout': '',
                'stderr': str(e),
                'assertions_passed': 0,
                'assertions_failed': 0,
                'screenshots': screenshots,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'test_file': str(test_path.relative_to(self.project_root)),
                'execution_id': execution_id
            }
    
    def _collect_screenshots(self, start_time: float, duration: float, execution_id: str = None) -> list:
        """
        Collect screenshots from disk that were created during test execution
        
        Args:
            start_time: Test start time (when runner started)
            duration: Test duration in seconds (0 if unknown)
            execution_id: Execution ID to filter screenshots (optional, for logging)
            
        Returns:
            List of screenshot dictionaries
        """
        screenshots = []
        
        # Use tight time window: only screenshots created during THIS test execution
        # start_time is when the test runner started, so screenshots should be between
        # start_time and start_time + duration + small buffer
        test_start_time = start_time
        test_end_time = start_time + duration + 30 if duration > 0 else start_time + 600  # 30s buffer, or 10min if duration unknown
        
        # Check main screenshots directory
        screenshots_dir = self.project_root / 'storage' / 'screenshots'
        if screenshots_dir.exists():
            for screenshot_file in screenshots_dir.glob('pw_*.png'):
                try:
                    # Check if file was modified during test execution window
                    file_mtime = screenshot_file.stat().st_mtime
                    # Only include files created/modified during THIS test execution
                    if test_start_time <= file_mtime <= test_end_time:
                        screenshot_name = screenshot_file.name
                        screenshot_path = f"storage/screenshots/{screenshot_name}"
                        
                        screenshots.append({
                            'filename': screenshot_name,
                            'path': screenshot_path,
                            'full_path': str(screenshot_file),
                            'source': 'disk'
                        })
                except Exception as e:
                    # Skip files that can't be accessed
                    continue
        
        # Also check test directory's screenshots folder (some tests save there)
        test_screenshots_dir = self.excel_tests_dir / 'storage' / 'screenshots'
        if test_screenshots_dir.exists():
            for screenshot_file in test_screenshots_dir.glob('pw_*.png'):
                try:
                    file_mtime = screenshot_file.stat().st_mtime
                    # Only include files created/modified during THIS test execution
                    if test_start_time <= file_mtime <= test_end_time:
                        screenshot_name = screenshot_file.name
                        # Use relative path from project root
                        screenshot_path = f"storage/excel_tests/storage/screenshots/{screenshot_name}"
                        
                        screenshots.append({
                            'filename': screenshot_name,
                            'path': screenshot_path,
                            'full_path': str(screenshot_file),
                            'source': 'disk'
                        })
                except Exception as e:
                    continue
        
        # Sort by filename to maintain step order (pw_step1_*, pw_step2_*, etc.)
        screenshots.sort(key=lambda x: x['filename'])
        
        if execution_id:
            print(f"📸 Collected {len(screenshots)} screenshots for execution {execution_id} (time window: {test_start_time:.0f} to {test_end_time:.0f})")
        
        return screenshots


# Example usage
if __name__ == '__main__':
    import os
    runner = TypeScriptTestRunner()
    result = runner.run('test_excel_xxx.spec.ts', execution_id='exec_xxx')
    
    print("\n📊 Test Results:")
    print(json.dumps(result, indent=2))

