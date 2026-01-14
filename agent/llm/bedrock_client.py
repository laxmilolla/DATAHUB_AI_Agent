"""
Bedrock Client - Bedrock LLM API client
Extracted from bedrock_playwright_agent.py lines 34-36, 3290-3310, 867-887
"""
import boto3
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class BedrockClient:
    """Bedrock LLM API client"""
    
    def __init__(self, region: str = 'us-east-1', model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"):
        """
        Initialize Bedrock client
        Args:
            region: AWS region
            model_id: Bedrock model ID
        """
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
    
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        """
        Make LLM conversation call
        Args:
            messages: Conversation messages
            tools: Tool definitions
            system_prompt: System prompt
        Returns: {stop_reason, tool_uses, response_text}
        """
        response = self.bedrock.converse(
            modelId=self.model_id,
            messages=messages,
            system=[{"text": system_prompt}],
            toolConfig={
                "tools": tools,
                "toolChoice": "any"  # Allow Claude to use tools (prevents text-only responses)
            },
            inferenceConfig={"maxTokens": 4096, "temperature": 0.0}
        )
        
        stop_reason = response['stopReason']
        
        # Extract tool uses
        tool_uses = []
        if stop_reason == 'tool_use':
            tool_uses = [
                block['toolUse']
                for block in response['output']['message']['content']
                if 'toolUse' in block
            ]
        
        # Extract response text
        response_text = ""
        if response['output']['message']['content']:
            for block in response['output']['message']['content']:
                if 'text' in block:
                    response_text += block['text']
        
        return {
            "stop_reason": stop_reason,
            "tool_uses": tool_uses,
            "response_text": response_text,
            "output": response['output']
        }
    
    async def call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        """
        Simple LLM call for disambiguation
        Args:
            prompt: Prompt text
            max_tokens: Maximum tokens
        Returns: Response text
        """
        try:
            response = self.bedrock.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0}
            )
            
            if response['output']['message']['content']:
                return response['output']['message']['content'][0].get('text', '')
            return ""
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""





