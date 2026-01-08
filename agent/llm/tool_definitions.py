"""
Tool Definitions - Tool schema definitions for LLM
Extracted from bedrock_playwright_agent.py lines 3114-3210
"""
from typing import List, Dict


class ToolDefinitions:
    """Tool schema definitions for Bedrock LLM"""
    
    @staticmethod
    def get_tools() -> List[Dict]:
        """
        Get tool definitions for Bedrock
        Returns: List of tool schemas
        """
        return [
            {
                "toolSpec": {
                    "name": "browser_navigate",
                    "description": "Navigate to a URL",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"url": {"type": "string"}},
                            "required": ["url"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_snapshot",
                    "description": "Get a summary of the current page including title, URL, element counts, and visible text preview",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "browser_click",
                    "description": "Click an element. PREFERRED: Use element descriptions from the page (e.g., 'Study dropdown', 'Continue button', 'Search button'). ALTERNATIVE: Use CSS selectors (e.g., '#id', '.class', 'button') or text selectors (e.g., 'text=Continue'). Do NOT use jQuery syntax like :contains().",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"selector": {"type": "string", "description": "CSS selector or text=Value for Playwright"}},
                            "required": ["selector"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_fill",
                    "description": "Fill input field",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "selector": {"type": "string"},
                                "text": {"type": "string"}
                            },
                            "required": ["selector", "text"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_screenshot",
                    "description": "Take screenshot",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_evaluate",
                    "description": "Execute JavaScript",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"code": {"type": "string"}},
                            "required": ["code"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_verify_table",
                    "description": "Verify that all rows in a table column contain a specific value. Use this for data validation in tables.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "table_selector": {"type": "string", "description": "CSS selector for the table or 'visible_table' to auto-detect"},
                                "column_name": {"type": "string", "description": "Name of the column to verify (will match header text)"},
                                "expected_value": {"type": "string", "description": "Expected value that should appear in all rows"}
                            },
                            "required": ["column_name", "expected_value"]
                        }
                    }
                }
            }
        ]


