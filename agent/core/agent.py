"""
Agent - Main orchestrator for QA automation
Wires all components together and executes stories
"""
import re
import logging
import time
from pathlib import Path
from typing import Dict, Any

from agent.utils.story_parser import StoryParser
from agent.utils.totp_handler import TOTPHandler
from agent.utils.llm_helper import LLMHelper
from agent.utils.step_matcher import StepMatcher
from agent.browser.playwright_manager import PlaywrightManager
from agent.browser.screenshot_manager import ScreenshotManager
from agent.browser.element_locator import ElementLocator
from agent.browser.action_executor import ActionExecutor
from agent.discovery.xpath_generator import XPathGenerator
from agent.discovery.discovery_tracker import DiscoveryTracker
from agent.discovery.registry_manager import RegistryManager
from agent.llm.bedrock_client import BedrockClient
from agent.llm.prompt_builder import PromptBuilder
from agent.llm.tool_definitions import ToolDefinitions
from agent.tools.browser_navigate import BrowserNavigateTool
from agent.tools.browser_click import BrowserClickTool
from agent.tools.browser_fill import BrowserFillTool
from agent.tools.browser_evaluate import BrowserEvaluateTool
from agent.tools.browser_verify import BrowserVerifyTool
from agent.core.execution_context import ExecutionContext

from utils.element_registry import ElementRegistry

logger = logging.getLogger(__name__)


class Agent:
    """Main agent orchestrator"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize agent with all components
        Args:
            region: AWS region for Bedrock
        """
        # Core components
        self.context = ExecutionContext(f"exec_{time.time():.0f}")
        
        # Utilities
        self.story_parser = StoryParser()
        self.totp_handler = TOTPHandler()
        
        # Browser components
        self.playwright_manager = PlaywrightManager()
        self.screenshots_dir = Path(__file__).parent.parent.parent / 'storage' / 'screenshots'
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_manager = ScreenshotManager(self.screenshots_dir)
        
        # Element registry - use project root path (not relative to api/)
        project_root = Path(__file__).parent.parent.parent
        element_maps_dir = project_root / 'element_maps'
        self.element_registry = ElementRegistry(str(element_maps_dir))
        
        # Element locator (needs page, will be set after browser starts)
        self.element_locator = None
        
        # Discovery components
        self.xpath_generator = None  # Needs page, will be set after browser starts
        self.discovery_tracker = None  # Needs page, will be set after browser starts
        self.registry_manager = RegistryManager(self.element_registry, self.context.execution_id)
        
        # LLM components
        self.bedrock_client = BedrockClient(region)
        self.prompt_builder = PromptBuilder(self.story_parser)
        self.tool_definitions = ToolDefinitions()
        self.llm_helper = None  # Needs bedrock_client and story, will be set during execution
        
        # Action executor (needs page, will be set after browser starts)
        self.action_executor = None
        
        # Tool handlers (will be initialized after browser starts)
        self.navigate_tool = None
        self.click_tool = None
        self.fill_tool = None
        self.evaluate_tool = None
        self.verify_tool = None
    
    async def execute_story(self, story: str, max_iterations: int = 50) -> Dict[str, Any]:
        """
        Execute story using agentic loop
        Args:
            story: Story text to execute
            max_iterations: Maximum iterations for agentic loop
        Returns: Results dict
        """
        try:
            # Parse story
            parsed_steps = self.story_parser.parse(story)
            self.context.set_story(story)
            self.context.set_parsed_steps(parsed_steps)
            
            # Initialize step matcher for content-based matching
            self.step_matcher = StepMatcher(parsed_steps, story)
            
            # Initialize LLM helper with story
            self.llm_helper = LLMHelper(self.bedrock_client, story)
            
            # Start browser
            await self.playwright_manager.start(headless=True)
            page = self.playwright_manager.get_page()
            
            # Initialize components that need page
            self.xpath_generator = XPathGenerator(page)
            self.action_executor = ActionExecutor(page, self.screenshot_manager)
            
            # Get current URL for discovery tracker
            current_url = page.url
            self.discovery_tracker = DiscoveryTracker(
                page, self.xpath_generator, self.element_registry, current_url, self.context
            )
            
            # Initialize element locator
            self.element_locator = ElementLocator(
                page, self.element_registry, parsed_steps, self.context.current_step_number
            )
            
            # Initialize tool handlers
            self.navigate_tool = BrowserNavigateTool(self.playwright_manager, self.context, self.discovery_tracker)
            self.click_tool = BrowserClickTool(
                page, self.element_locator, self.action_executor, self.discovery_tracker,
                self.registry_manager, self.xpath_generator, self.llm_helper, self.totp_handler,
                self.screenshot_manager, self.context, parsed_steps, story
            )
            self.fill_tool = BrowserFillTool(
                page, self.element_locator, self.action_executor, self.totp_handler,
                self.discovery_tracker, self.context, parsed_steps, story
            )
            self.evaluate_tool = BrowserEvaluateTool(self.playwright_manager)
            self.verify_tool = BrowserVerifyTool(
                self.playwright_manager, self.discovery_tracker, self.screenshot_manager
            )
            
            # Build prompts
            formatted_story = self.prompt_builder.build_story_prompt(story, parsed_steps)
            system_prompt = self.prompt_builder.get_system_prompt()
            
            # Initialize messages
            messages = [{
                "role": "user",
                "content": [{"text": f"Execute this test scenario:\n\n{formatted_story}\n\nFollow the [ACTION] hints for each step."}]
            }]
            
            # Agentic loop
            logger.info("🔄 Starting agentic loop...")
            for iteration in range(1, max_iterations + 1):
                self.context.increment_step()
                logger.info(f"\n{'='*60}")
                logger.info(f"Iteration {iteration}/{max_iterations}")
                logger.info(f"{'='*60}")
                
                # Call LLM
                response = await self.bedrock_client.converse(
                    messages=messages,
                    tools=self.tool_definitions.get_tools(),
                    system_prompt=system_prompt
                )
                
                stop_reason = response['stop_reason']
                
                if stop_reason == 'tool_use':
                    # Execute tools
                    tool_uses = response['tool_uses']
                    logger.info(f"LLM requested {len(tool_uses)} tools")
                    
                    tool_results = []
                    for tool_use in tool_uses:
                        tool_name = tool_use['name']
                        tool_input = tool_use['input']
                        
                        # Execute tool
                        result_text = await self._execute_tool(tool_name, tool_input)
                        
                        # Match action to story step by content
                        step_identifier = self.step_matcher.match_action_to_step(
                            tool_name, tool_input, result_text
                        )
                        
                        # If no match found, use sequential fallback (next unmatched step)
                        if not step_identifier:
                            # Find next unmatched step identifier
                            all_step_ids = sorted(self.step_matcher.step_texts.keys(), 
                                                 key=lambda x: (int(re.match(r'(\d+)', x).group(1)), x))
                            completed = self.step_matcher.get_completed_steps()
                            for step_id in all_step_ids:
                                if step_id not in completed:
                                    step_identifier = step_id
                                    logger.info(f"  ⚠️  Using sequential fallback: Step {step_identifier}")
                                    self.step_matcher.completed_step_identifiers.add(step_identifier)
                                    break
                        
                        # Update context with matched step identifier
                        if step_identifier:
                            self.context.current_step_identifier = step_identifier
                            # Extract step number for backward compatibility
                            step_num_match = re.match(r'(\d+)', step_identifier)
                            if step_num_match:
                                self.context.current_step_number = int(step_num_match.group(1))
                            
                            # CRITICAL FIX: Update last discovery's step_identifier if discovery was tracked
                            # Discoveries are tracked during tool execution (before step_identifier is known),
                            # so we need to update it after we determine the correct step_identifier
                            if self.discovery_tracker and tool_name in ['browser_click', 'browser_fill']:
                                self.discovery_tracker.update_last_discovery_step_identifier(
                                    step_identifier, self.context.current_step_number
                                )
                        
                        # Add to actions
                        self.context.add_action({
                            "iteration": iteration,
                            "step_number": self.context.current_step_number,  # Keep for backward compatibility
                            "step_identifier": step_identifier,  # NEW: Story step identifier ("1", "1a", "2", etc.)
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result_text
                        })
                        
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use['toolUseId'],
                                "content": [{"text": result_text}]
                            }
                        })
                    
                    messages.append(response['output']['message'])
                    messages.append({"role": "user", "content": tool_results})
                
                elif stop_reason == 'end_turn':
                    final_text = response['response_text']
                    self.context.mark_completed(final_text)
                    logger.info(f"✅ Story completed: {final_text}")
                    break
                
                elif stop_reason == 'max_tokens':
                    messages.append(response['output']['message'])
                    messages.append({"role": "user", "content": [{"text": "Continue."}]})
                
                else:
                    self.context.mark_error(f"Unexpected stop: {stop_reason}")
                    break
            
            # Save discoveries to registry
            discoveries = self.discovery_tracker.get_discoveries()
            if discoveries:
                current_url = page.url
                await self.registry_manager.save_discoveries(discoveries, current_url, preserve_manual=True)
                # Store discoveries in execution context so they're included in results
                self.context.discoveries = discoveries
            
            # Save step_number mapping (HYBRID APPROACH: execution-specific step mapping)
            if discoveries and self.context.actions_taken:
                self.registry_manager.save_step_mapping(
                    story=self.context.story,
                    actions_taken=self.context.actions_taken,
                    discoveries=discoveries,
                    parsed_steps=self.context.parsed_steps
                )
            
            # Get results
            results = self.context.get_results()
            
            return results
        
        except Exception as e:
            logger.error(f"Error executing story: {e}", exc_info=True)
            self.context.mark_error(str(e))
            return self.context.get_results()
        
        finally:
            # Cleanup
            await self.playwright_manager.close()
    
    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Route tool execution to appropriate handler
        Args:
            tool_name: Name of tool to execute
            tool_input: Tool input parameters
        Returns: Result message
        """
        try:
            if tool_name == "browser_navigate":
                return await self.navigate_tool.execute(tool_input['url'])
            
            elif tool_name == "browser_snapshot":
                # Simple snapshot - return page info
                page = self.playwright_manager.get_page()
                title = await page.title()
                url = page.url
                buttons = await page.locator("button").count()
                links = await page.locator("a").count()
                inputs = await page.locator("input").count()
                return f"Page Snapshot: {title} | {url} | {buttons} buttons, {links} links, {inputs} inputs"
            
            elif tool_name == "browser_click":
                selector = tool_input['selector']
                element_description = selector.replace("text=", "").replace("_", " ")
                return await self.click_tool.execute(selector, element_description)
            
            elif tool_name == "browser_fill":
                return await self.fill_tool.execute(tool_input['selector'], tool_input['text'])
            
            elif tool_name == "browser_screenshot":
                name = tool_input.get('name', 'screenshot')
                result = await self.screenshot_manager.capture(self.playwright_manager.get_page(), name)
                size = Path(result['path']).stat().st_size if Path(result['path']).exists() else 0
                # Add screenshot to execution context
                self.context.add_screenshot(result['filename'])
                return f"✅ Screenshot saved: {result['filename']} ({size} bytes)"
            
            elif tool_name == "browser_evaluate":
                return await self.evaluate_tool.execute(tool_input['code'])
            
            elif tool_name == "browser_verify_table":
                return await self.verify_tool.execute(
                    tool_input.get('table_selector', 'visible_table'),
                    tool_input['column_name'],
                    tool_input['expected_value']
                )
            
            else:
                return f"Unknown tool: {tool_name}"
        
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return f"❌ Tool execution FAILED: {str(e)}"

