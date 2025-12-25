"""
Bedrock Agent with MCP Browser Tools
Architecture 2: LLM-driven autonomous test execution
"""
import boto3
import json
import subprocess
import uuid
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedrockAgentQA:
    """
    Autonomous QA agent powered by Bedrock + MCP
    
    The LLM makes real-time decisions and controls the browser directly.
    """
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize Bedrock agent
        
        Args:
            region: AWS region for Bedrock
        """
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.mcp_process: Optional[subprocess.Popen] = None
        self.execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
    def start_mcp_server(self):
        """Start MCP Playwright server as subprocess"""
        logger.info("Starting MCP server...")
        
        mcp_server_path = Path(__file__).parent.parent / "mcp-server" / "server.js"
        
        self.mcp_process = subprocess.Popen(
            ['node', str(mcp_server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0  # Unbuffered
        )
        
        time.sleep(2)  # Give server time to start
        logger.info("MCP server started")
    
    def execute_story(self, user_story: str, max_iterations: int = 50) -> Dict[str, Any]:
        """
        Execute test scenario autonomously
        
        The LLM agent will:
        1. Read the user story
        2. Decide what actions to take
        3. Use browser tools to execute
        4. Adapt based on results
        5. Report success/failure
        
        Args:
            user_story: Natural language test scenario
            max_iterations: Maximum agent loops (safety limit)
            
        Returns:
            Execution results with actions, screenshots, status
        """
        logger.info(f"Execution {self.execution_id}: Starting story execution")
        logger.info(f"Story: {user_story[:100]}...")
        
        # System prompt - defines agent behavior
        system_prompt = self._get_system_prompt()
        
        # Initialize conversation
        messages = [
            {
                "role": "user",
                "content": [{
                    "text": f"""Execute this test scenario:

{user_story}

Use the browser tools to complete this task. Think step by step:
1. What page do I need to visit?
2. What elements do I need to interact with?
3. How do I validate success?

Take screenshots at important steps for documentation."""
                }]
            }
        ]
        
        # Results tracking
        results = {
            "execution_id": self.execution_id,
            "story": user_story,
            "actions_taken": [],
            "screenshots": [],
            "status": "running",
            "error": None,
            "summary": None,
            "started_at": time.time()
        }
        
        # Agentic loop - LLM makes decisions
        for iteration in range(1, max_iterations + 1):
            logger.info(f"Iteration {iteration}/{max_iterations}")
            
            try:
                # Call Bedrock with tool definitions
                response = self.bedrock.converse(
                    modelId=self.model_id,
                    messages=messages,
                    system=[{"text": system_prompt}],
                    toolConfig={
                        "tools": self._get_tool_definitions()
                    },
                    inferenceConfig={
                        "maxTokens": 4096,
                        "temperature": 0.0  # Deterministic
                    }
                )
                
                stop_reason = response['stopReason']
                logger.info(f"LLM stop reason: {stop_reason}")
                
                # Check if LLM wants to use tools
                if stop_reason == 'tool_use':
                    # Extract tool requests
                    tool_requests = [
                        block for block in response['output']['message']['content']
                        if 'toolUse' in block
                    ]
                    
                    logger.info(f"LLM requested {len(tool_requests)} tool calls")
                    
                    # Execute each tool
                    tool_results = []
                    for tool_request in tool_requests:
                        tool_name = tool_request['toolUse']['name']
                        tool_input = tool_request['toolUse']['input']
                        tool_use_id = tool_request['toolUse']['toolUseId']
                        
                        logger.info(f"Calling tool: {tool_name}")
                        logger.debug(f"Tool input: {tool_input}")
                        
                        # Call MCP tool
                        tool_result = self._call_mcp_tool(tool_name, tool_input)
                        
                        # Log action
                        action_record = {
                            "iteration": iteration,
                            "tool": tool_name,
                            "input": tool_input,
                            "result": tool_result,
                            "timestamp": time.time()
                        }
                        results["actions_taken"].append(action_record)
                        
                        # Track screenshots
                        if tool_name == "browser_screenshot":
                            screenshot_path = tool_result.get("path")
                            if screenshot_path:
                                results["screenshots"].append(screenshot_path)
                        
                        # Prepare tool result for LLM
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"text": json.dumps(tool_result)}]
                        })
                    
                    # Add assistant message (with tool use)
                    messages.append(response['output']['message'])
                    
                    # Add tool results as user message
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                elif stop_reason == 'end_turn':
                    # LLM finished the task
                    final_message = response['output']['message']['content'][0]['text']
                    logger.info(f"Agent completed: {final_message[:200]}")
                    
                    results["status"] = "completed"
                    results["summary"] = final_message
                    results["completed_at"] = time.time()
                    results["duration"] = results["completed_at"] - results["started_at"]
                    break
                    
                elif stop_reason == 'max_tokens':
                    # Response too long - continue conversation
                    messages.append(response['output']['message'])
                    messages.append({
                        "role": "user",
                        "content": [{"text": "Continue from where you left off."}]
                    })
                    
                else:
                    # Unexpected stop reason
                    logger.error(f"Unexpected stop reason: {stop_reason}")
                    results["status"] = "error"
                    results["error"] = f"Unexpected stop reason: {stop_reason}"
                    break
                    
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}", exc_info=True)
                results["status"] = "error"
                results["error"] = str(e)
                break
        
        else:
            # Max iterations reached
            logger.warning(f"Max iterations ({max_iterations}) reached")
            results["status"] = "timeout"
            results["error"] = f"Agent did not complete within {max_iterations} iterations"
        
        logger.info(f"Execution {self.execution_id} finished: {results['status']}")
        return results
    
    def _call_mcp_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call MCP tool via stdio
        
        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            
        Returns:
            Tool result
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_input
            }
        }
        
        # Send request to MCP server
        request_json = json.dumps(request) + '\n'
        self.mcp_process.stdin.write(request_json.encode())
        self.mcp_process.stdin.flush()
        
        # Read response
        response_line = self.mcp_process.stdout.readline()
        response = json.loads(response_line)
        
        if 'error' in response:
            logger.error(f"MCP tool error: {response['error']}")
            return {"success": False, "error": response['error']}
        
        result = response.get('result', {})
        
        # Extract text from MCP content format
        if 'content' in result and isinstance(result['content'], list):
            content_text = ' '.join([
                item.get('text', '') 
                for item in result['content'] 
                if item.get('type') == 'text'
            ])
            return {"success": True, "result": content_text}
        
        return {"success": True, "result": result}
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the agent"""
        return """You are an expert QA automation agent. Your job is to execute test scenarios using browser tools.

Available Tools:
- browser_navigate(url): Navigate to a URL
- browser_snapshot(): Get current page HTML/DOM
- browser_click(selector): Click an element (CSS selector or text="Button Text")
- browser_fill(selector, text): Fill an input field
- browser_screenshot(name): Take a screenshot
- browser_evaluate(code): Run JavaScript to inspect or interact with the page

Strategy for Success:
1. **After navigating, always take a snapshot** to see what's on the page
2. **Use browser_evaluate()** to find the right selectors when needed
   Example: browser_evaluate("document.querySelector('#searchBox') ? '#searchBox' : 'input[type=search]'")
3. **Take screenshots at key steps** (after navigation, after important actions, before validation)
4. **Validate each action** - check that it succeeded before moving on
5. **If something fails, adapt** - try alternative selectors or approaches
6. **Think step by step** - break complex tasks into simple actions

Selector Tips:
- Prefer IDs: #elementId
- Use CSS selectors: .className, input[type="text"]
- Use text selectors: text="Button Text"
- Check the DOM with browser_snapshot() or browser_evaluate() first

Error Handling:
- If a selector doesn't work, examine the DOM to find the right one
- If a page doesn't load, wait and retry
- If an unexpected element appears (popup, dialog), handle it

Reporting:
- At the end, summarize what you did
- Report success or failure clearly
- List any issues encountered"""
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Define browser tools for Bedrock"""
        return [
            {
                "toolSpec": {
                    "name": "browser_navigate",
                    "description": "Navigate browser to a URL. Always do this first before other actions.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "Full URL to navigate to (include https://)"
                                }
                            },
                            "required": ["url"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_snapshot",
                    "description": "Get current page HTML/DOM. Use this after navigating to see what elements are available. Returns the full page HTML.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_click",
                    "description": "Click an element on the page. Use CSS selectors (#id, .class) or text selectors (text='Button').",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "selector": {
                                    "type": "string",
                                    "description": "CSS selector (e.g., '#id', '.class', 'button') or text selector (e.g., 'text=Search')"
                                }
                            },
                            "required": ["selector"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_fill",
                    "description": "Fill an input field with text. Use CSS selector to target the field.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "selector": {
                                    "type": "string",
                                    "description": "CSS selector for the input field (e.g., '#searchBox', 'input[name=\"q\"]')"
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Text to fill into the field"
                                }
                            },
                            "required": ["selector", "text"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_screenshot",
                    "description": "Take a screenshot of the current page. Always take screenshots at important steps for documentation.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Descriptive filename for the screenshot (e.g., 'search_results', 'product_page')"
                                }
                            },
                            "required": ["name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "browser_evaluate",
                    "description": "Execute JavaScript on the page to get information or interact with elements. Useful for finding selectors, reading values, or complex interactions.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "string",
                                    "description": "JavaScript code to execute. Can access DOM (document.querySelector, etc). Return a value."
                                }
                            },
                            "required": ["code"]
                        }
                    }
                }
            }
        ]
    
    def close(self):
        """Cleanup - close MCP server"""
        logger.info("Closing agent...")
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process.wait(timeout=5)
        logger.info("Agent closed")

