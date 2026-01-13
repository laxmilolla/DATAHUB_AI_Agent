"""
Multi-Provider LLM Client
Supports: AWS Bedrock, OpenAI, Anthropic Direct API
"""
import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        """Make LLM conversation call with tool support"""
        pass
    
    @abstractmethod
    async def call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        """Simple LLM call for disambiguation"""
        pass


class BedrockClient(LLMClient):
    """AWS Bedrock Client (Claude via Bedrock)"""
    
    def __init__(self, region: str = 'us-east-1', model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"):
        import boto3
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
    
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        response = self.bedrock.converse(
            modelId=self.model_id,
            messages=messages,
            system=[{"text": system_prompt}],
            toolConfig={"tools": tools},
            inferenceConfig={"maxTokens": 4096, "temperature": 0.0}
        )
        
        stop_reason = response['stopReason']
        tool_uses = []
        if stop_reason == 'tool_use':
            tool_uses = [
                block['toolUse']
                for block in response['output']['message']['content']
                if 'toolUse' in block
            ]
        
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
            logger.error(f"Bedrock LLM call failed: {e}")
            return ""


class OpenAIClient(LLMClient):
    """OpenAI Client (GPT-4, GPT-4 Turbo)"""
    
    def __init__(self, model: str = "gpt-4-turbo-preview", api_key: Optional[str] = None):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
            self.model = model
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
    
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        # Convert messages format
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', [])
            if isinstance(content, list):
                text_content = next((c.get('text', '') for c in content if 'text' in c), '')
            else:
                text_content = str(content)
            openai_messages.append({"role": role, "content": text_content})
        
        # Convert tools format
        openai_tools = []
        for tool in tools:
            tool_spec = tool.get('toolSpec', {})
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool_spec.get('name', ''),
                    "description": tool_spec.get('description', ''),
                    "parameters": tool_spec.get('inputSchema', {}).get('json', {})
                }
            })
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
            max_tokens=4096,
            temperature=0.0
        )
        
        message = response.choices[0].message
        stop_reason = response.choices[0].finish_reason
        
        tool_uses = []
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_uses.append({
                    "toolUseId": tool_call.id,
                    "name": tool_call.function.name,
                    "input": eval(tool_call.function.arguments) if tool_call.function.arguments else {}
                })
        
        return {
            "stop_reason": "tool_use" if tool_uses else "end_turn",
            "tool_uses": tool_uses,
            "response_text": message.content or "",
            "output": {"message": {"content": [{"text": message.content}]}}
        }
    
    async def call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.0
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI LLM call failed: {e}")
            return ""


class AnthropicClient(LLMClient):
    """Anthropic Direct API Client (Claude)"""
    
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
            self.model = model
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
    
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        # Convert messages format
        anthropic_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', [])
            if isinstance(content, list):
                text_content = next((c.get('text', '') for c in content if 'text' in c), '')
            else:
                text_content = str(content)
            anthropic_messages.append({"role": role, "content": text_content})
        
        # Convert tools format
        anthropic_tools = []
        for tool in tools:
            tool_spec = tool.get('toolSpec', {})
            input_schema = tool_spec.get('inputSchema', {}).get('json', {})
            anthropic_tools.append({
                "name": tool_spec.get('name', ''),
                "description": tool_spec.get('description', ''),
                "input_schema": {
                    "type": input_schema.get('type', 'object'),
                    "properties": input_schema.get('properties', {}),
                    "required": input_schema.get('required', [])
                }
            })
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=anthropic_messages,
            tools=anthropic_tools if anthropic_tools else None,
            temperature=0.0
        )
        
        stop_reason = response.stop_reason
        tool_uses = []
        
        if response.content:
            for block in response.content:
                if block.type == 'tool_use':
                    tool_uses.append({
                        "toolUseId": block.id,
                        "name": block.name,
                        "input": block.input
                    })
        
        response_text = ""
        if response.content:
            for block in response.content:
                if block.type == 'text':
                    response_text += block.text
        
        return {
            "stop_reason": "tool_use" if tool_uses else "end_turn",
            "tool_uses": tool_uses,
            "response_text": response_text,
            "output": {"message": {"content": [{"text": response_text}]}}
        }
    
    async def call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            if response.content:
                return response.content[0].text
            return ""
        except Exception as e:
            logger.error(f"Anthropic LLM call failed: {e}")
            return ""


class GroqClient(LLMClient):
    """Groq Client - FREE cloud API (very fast, no local resources)"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant"):
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key or os.getenv('GROQ_API_KEY'))
            self.model = model
        except ImportError:
            raise ImportError("groq package required. Install with: pip install groq")
    
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        import asyncio
        import json
        
        # Convert messages format (Groq uses standard OpenAI format)
        groq_messages = []
        # Add system prompt as first message (Groq doesn't have separate system parameter)
        if system_prompt:
            groq_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', [])
            
            # Handle different content formats
            if isinstance(content, list):
                # Extract text from content blocks
                text_parts = []
                
                for c in content:
                    if isinstance(c, dict):
                        # Handle Bedrock tool result format - convert to text
                        if 'toolResult' in c:
                            tool_result = c['toolResult']
                            result_content = tool_result.get('content', [])
                            # Extract text from result content
                            result_text = ''
                            if isinstance(result_content, list):
                                for rc in result_content:
                                    if isinstance(rc, dict) and 'text' in rc:
                                        result_text = rc.get('text', '')
                                    elif isinstance(rc, str):
                                        result_text = rc
                            elif isinstance(result_content, str):
                                result_text = result_content
                            if result_text:
                                text_parts.append(str(result_text))
                        elif 'text' in c:
                            text_val = c.get('text')
                            if text_val is not None:
                                text_parts.append(str(text_val))
                        elif 'tool_use' in c or 'toolUse' in c:
                            # Tool use blocks - Groq handles these automatically, skip
                            continue
                    elif isinstance(c, str):
                        text_parts.append(c)
                
                # Filter out None values and join
                text_parts = [str(t) for t in text_parts if t is not None]
                text_content = ' '.join(text_parts).strip()
            else:
                text_content = str(content).strip() if content else ''
            
            # Groq requires non-empty content - skip empty messages
            if text_content:
                groq_messages.append({"role": role, "content": text_content})
        
        # Convert tools format for Groq (OpenAI-compatible format)
        groq_tools = []
        for tool in tools:
            tool_spec = tool.get('toolSpec', {})
            input_schema = tool_spec.get('inputSchema', {}).get('json', {})
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": tool_spec.get('name', ''),
                    "description": tool_spec.get('description', ''),
                    "parameters": input_schema  # Groq expects the full schema object
                }
            })
        
        # Groq client is synchronous, so run in executor
        def _call_groq():
            return self.client.chat.completions.create(
                model=self.model,
                messages=groq_messages,
                tools=groq_tools if groq_tools else None,
                tool_choice="auto",  # Let model decide when to use tools
                max_tokens=4096,
                temperature=0.0
            )
        
        # Run synchronous Groq call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _call_groq)
        
        message = response.choices[0].message
        stop_reason = response.choices[0].finish_reason
        
        tool_uses = []
        if message.tool_calls:
            for tool_call in message.tool_calls:
                try:
                    # Parse arguments (Groq returns as string or dict)
                    if isinstance(tool_call.function.arguments, str):
                        args = json.loads(tool_call.function.arguments)
                    else:
                        args = tool_call.function.arguments or {}
                    
                    tool_uses.append({
                        "toolUseId": tool_call.id,
                        "name": tool_call.function.name,
                        "input": args
                    })
                except Exception as e:
                    logger.warning(f"  ⚠️ Failed to parse Groq tool call arguments: {e}")
                    # Fallback: try to extract what we can
                    tool_uses.append({
                        "toolUseId": tool_call.id,
                        "name": tool_call.function.name,
                        "input": {}
                    })
        
        return {
            "stop_reason": "tool_use" if tool_uses else "end_turn",
            "tool_uses": tool_uses,
            "response_text": message.content or "",
            "output": {"message": {"content": [{"text": message.content}]}}
        }
    
    async def call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        import asyncio
        try:
            def _call_groq():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.0
                )
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call_groq)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Groq LLM call failed: {e}")
            return ""


class OllamaClient(LLMClient):
    """Ollama Client - FREE local models (runs on your machine)"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        import aiohttp
        self.base_url = base_url
        self.model = model
        self.session = None
    
    async def _get_session(self):
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def converse(self, messages: List[Dict], tools: List[Dict], system_prompt: str) -> Dict[str, Any]:
        session = await self._get_session()
        
        # Convert messages format for Ollama
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', [])
            if isinstance(content, list):
                text_content = next((c.get('text', '') for c in content if 'text' in c), '')
            else:
                text_content = str(content)
            ollama_messages.append({"role": role, "content": text_content})
        
        # Ollama doesn't support tools natively, so we'll use JSON mode and prompt engineering
        # Add tool definitions to system prompt
        tools_prompt = ""
        if tools:
            tools_prompt = "\n\nAvailable tools:\n"
            for tool in tools:
                tool_spec = tool.get('toolSpec', {})
                tools_prompt += f"- {tool_spec.get('name', '')}: {tool_spec.get('description', '')}\n"
            tools_prompt += "\nRespond with JSON format: {\"tool\": \"tool_name\", \"input\": {...}}"
        
        full_system = system_prompt + tools_prompt
        
        try:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": ollama_messages,
                    "system": full_system,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 4096
                    },
                    "format": "json" if tools else None
                }
            ) as response:
                result = await response.json()
                
                response_text = result.get('message', {}).get('content', '')
                
                # Try to parse tool calls from JSON response
                tool_uses = []
                if tools and response_text:
                    try:
                        import json
                        parsed = json.loads(response_text)
                        if isinstance(parsed, dict) and 'tool' in parsed:
                            tool_uses.append({
                                "name": parsed.get('tool', ''),
                                "input": parsed.get('input', {})
                            })
                    except:
                        pass  # Not JSON, treat as text response
                
                return {
                    "stop_reason": "tool_use" if tool_uses else "end_turn",
                    "tool_uses": tool_uses,
                    "response_text": response_text,
                    "output": {"message": {"content": [{"text": response_text}]}}
                }
        except Exception as e:
            logger.error(f"Ollama LLM call failed: {e}")
            raise
    
    async def call_llm_simple(self, prompt: str, max_tokens: int = 100) -> str:
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": max_tokens
                    }
                }
            ) as response:
                result = await response.json()
                return result.get('response', '')
        except Exception as e:
            logger.error(f"Ollama simple call failed: {e}")
            return ""


def create_llm_client() -> LLMClient:
    """
    Create LLM client based on environment variables
    Priority: LLM_PROVIDER env var, then auto-detect from available credentials
    FREE option: Use Ollama (local, no API costs)
    """
    provider = os.getenv('LLM_PROVIDER', '').lower()
    
    # Auto-detect if not specified - prioritize free options
    if not provider:
        # Check Groq first (FREE cloud, no local resources)
        if os.getenv('GROQ_API_KEY'):
            provider = 'groq'
            logger.info("✅ Groq detected - using FREE cloud API (fast, no local resources)")
        # Check Ollama (free/local but uses resources)
        else:
            ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            try:
                import aiohttp
                import asyncio
                async def check_ollama():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{ollama_url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                            return resp.status == 200
                if asyncio.run(check_ollama()):
                    provider = 'ollama'
                    logger.info("✅ Ollama detected - using FREE local model (uses CPU/RAM)")
            except:
                pass
        
        # Fall back to paid APIs if free options not available
        if not provider:
            if os.getenv('OPENAI_API_KEY'):
                provider = 'openai'
            elif os.getenv('ANTHROPIC_API_KEY'):
                provider = 'anthropic'
            elif os.getenv('AWS_ACCESS_KEY_ID'):
                provider = 'bedrock'
            else:
                logger.warning("No LLM provider found. Options:")
                logger.warning("  1. Groq (FREE cloud): Get API key from https://console.groq.com")
                logger.warning("  2. Ollama (FREE local): Install from https://ollama.ai")
                raise ValueError("No LLM provider available. Use Groq (free cloud) or Ollama (free local).")
    
    logger.info(f"Using LLM provider: {provider}")
    
    if provider == 'groq':
        model = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')  # FREE, very fast
        api_key = os.getenv('GROQ_API_KEY')
        return GroqClient(api_key=api_key, model=model)
    
    elif provider == 'ollama':
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = os.getenv('OLLAMA_MODEL', 'llama3.2')  # Free, fast model
        return OllamaClient(base_url=base_url, model=model)
    
    elif provider == 'openai':
        model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        return OpenAIClient(model=model)
    
    elif provider == 'anthropic':
        model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        return AnthropicClient(model=model)
    
    elif provider == 'bedrock':
        region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        model_id = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
        return BedrockClient(region=region, model_id=model_id)
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'groq' (FREE cloud), 'ollama' (FREE local), 'openai', 'anthropic', or 'bedrock'")

