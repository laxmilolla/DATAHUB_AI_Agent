"""
Browser Evaluate Tool - Handle browser_evaluate tool
Extracted from bedrock_playwright_agent.py lines 3086-3110
"""
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BrowserEvaluateTool:
    """Handle browser_evaluate tool"""
    
    def __init__(self, playwright_manager):
        """
        Initialize evaluate tool
        Args:
            playwright_manager: PlaywrightManager instance
        """
        self.playwright_manager = playwright_manager
    
    async def execute(self, code: str) -> str:
        """
        Execute JavaScript code
        Args:
            code: JavaScript code to execute
        Returns: Result message
        """
        logger.info("Evaluating JS")
        
        page = self.playwright_manager.get_page()
        
        # Auto-wrap code in function if needed
        # Check if code contains await - if so, use async wrapper
        has_await = 'await' in code
        if 'return' in code and not code.strip().startswith('(') and not code.strip().startswith('function'):
            if has_await:
                wrapped_code = f"(async () => {{ {code} }})()"
            else:
                wrapped_code = f"(() => {{ {code} }})()"
        elif has_await and not code.strip().startswith('async'):
            # Code has await but isn't wrapped - wrap in async function
            wrapped_code = f"(async () => {{ {code} }})()"
        else:
            wrapped_code = code
        
        # Execute with error handling
        try:
            result = await page.evaluate(wrapped_code)
            
            # Verify execution
            if result is None:
                logger.info(f"  ✅ JS executed, returned null/undefined")
                return f"✅ JS executed successfully - Result: null"
            else:
                logger.info(f"  ✅ JS executed, returned {type(result).__name__}")
                return f"✅ JS executed successfully - Result: {json.dumps(result, indent=2)}"
        except Exception as js_error:
            logger.error(f"  ❌ JS execution failed: {str(js_error)}")
            return f"❌ JS execution FAILED: {str(js_error)}"

