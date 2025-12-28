"""
Comparator
Compares AI discovery results with Playwright test results
"""

import json
from pathlib import Path
from typing import Dict, Any, List


class Comparator:
    """Compare AI discovery results with generated test results"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.executions_dir = self.project_root / 'storage' / 'executions'
    
    def compare(self, execution_id: str, playwright_result: Dict) -> Dict[str, Any]:
        """
        Compare AI execution with Playwright test execution
        
        Args:
            execution_id: Original AI execution ID
            playwright_result: Results from TestRunner
            
        Returns:
            Dict with comparison results
        """
        # Load AI execution results
        ai_result = self._load_execution(execution_id)
        
        # Compare status
        ai_passed = ai_result.get('status') == 'completed'
        pw_passed = playwright_result.get('status') == 'passed'
        status_match = ai_passed == pw_passed
        
        # Compare screenshots count (rough check)
        ai_screenshots = len(ai_result.get('screenshots', []))
        pw_assertions = playwright_result.get('assertions_passed', 0)
        
        # Build comparison result
        comparison = {
            'execution_id': execution_id,
            'match': status_match and pw_passed,
            'ai_result': {
                'status': ai_result.get('status'),
                'passed': ai_passed,
                'screenshots': ai_screenshots,
                'error': ai_result.get('error')
            },
            'playwright_result': {
                'status': playwright_result.get('status'),
                'passed': pw_passed,
                'duration': playwright_result.get('duration'),
                'assertions_passed': pw_assertions,
                'assertions_failed': playwright_result.get('assertions_failed', 0)
            },
            'differences': self._find_differences(ai_result, playwright_result),
            'recommendation': self._get_recommendation(status_match, ai_passed, pw_passed)
        }
        
        return comparison
    
    def _load_execution(self, execution_id: str) -> Dict:
        """Load AI execution results"""
        file_path = self.executions_dir / f'{execution_id}.json'
        if not file_path.exists():
            raise FileNotFoundError(f"Execution {execution_id} not found")
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _find_differences(self, ai_result: Dict, pw_result: Dict) -> List[str]:
        """Find key differences between AI and Playwright results"""
        differences = []
        
        ai_status = ai_result.get('status')
        pw_status = pw_result.get('status')
        
        if ai_status == 'completed' and pw_status == 'failed':
            differences.append("AI succeeded but Playwright failed - selectors may be outdated")
        elif ai_status == 'error' and pw_status == 'passed':
            differences.append("AI failed but Playwright passed - possible timing or retry differences")
        elif ai_status != 'completed' and pw_status != 'passed':
            differences.append("Both failed - manual review needed")
        
        # Check assertion counts
        pw_failed = pw_result.get('assertions_failed', 0)
        if pw_failed > 0:
            differences.append(f"{pw_failed} Playwright assertions failed")
        
        # Check if AI had errors
        if ai_result.get('error'):
            differences.append(f"AI error: {ai_result['error'][:100]}")
        
        # Check if Playwright had errors
        if pw_result.get('stderr') and pw_result['status'] == 'failed':
            stderr_preview = pw_result['stderr'][:100]
            differences.append(f"Playwright error: {stderr_preview}")
        
        return differences
    
    def _get_recommendation(self, status_match: bool, ai_passed: bool, pw_passed: bool) -> str:
        """Get recommendation based on comparison"""
        if status_match and ai_passed and pw_passed:
            return "✅ APPROVE: Both AI and Playwright passed. Ready for CI/CD."
        
        if ai_passed and not pw_passed:
            return "⚠️  REVIEW: AI passed but Playwright failed. Check selectors and timing."
        
        if not ai_passed and pw_passed:
            return "⚠️  REVIEW: Playwright passed but AI failed. Unexpected - verify results."
        
        return "❌ REJECT: Both failed. Fix issues before deploying."


# Example usage
if __name__ == '__main__':
    comparator = Comparator()
    
    # Mock Playwright result
    pw_result = {
        'status': 'passed',
        'duration': 12.5,
        'assertions_passed': 5,
        'assertions_failed': 0
    }
    
    comparison = comparator.compare('exec_172351d5', pw_result)
    
    print("📊 Comparison Results:")
    print(json.dumps(comparison, indent=2))

