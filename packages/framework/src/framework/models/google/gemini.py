"""
Google Gemini model implementations for Astra Framework.

Supports:
- gemini-1.5-flash
- gemini-1.5-pro
"""
import time
from typing import Any, AsyncIterator, Dict, List, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerateContentResponse
except ImportError:
    raise ImportError(
        "google-generativeai not installed. "
        "Install with: pip install google-generativeai"
    )

from ..base import Model, ModelResponse


class GeminiModel(Model):
    """
    Base class for Gemini models.
    
    Handles common Gemini API functionality.
    """
    
    # Gemini pricing (per 1M tokens) - as of 2024
    PRICING = {
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-pro": {"input": 0.50, "output": 1.50},
    }
    
    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Initialize Gemini model.
        
        Args:
            model_id: Model identifier (e.g., 'gemini-1.5-flash')
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            **kwargs: Additional parameters
        """
        super().__init__(model_id=model_id, api_key=api_key, **kwargs)
        
        # Configure API key
        if api_key:
            genai.configure(api_key=api_key)
        elif not genai.api_key:
            # Try to get from environment
            import os
            env_key = os.getenv("GOOGLE_API_KEY")
            if env_key:
                genai.configure(api_key=env_key)
            else:
                raise ValueError(
                    "Google API key required. "
                    "Provide via api_key parameter or set GOOGLE_API_KEY environment variable."
                )
        
        # Initialize model - try different model name formats
        # Google Generative AI uses specific model names
        # Note: Some model names may create the object but fail on actual API calls
        model_alternatives = {
            "gemini-pro": ["gemini-1.0-pro"],  # gemini-pro often doesn't work, use 1.0-pro
            "gemini-1.5-flash": ["gemini-1.5-flash", "gemini-1.5-flash-001"],
            "gemini-1.5-pro": ["gemini-1.5-pro", "gemini-1.5-pro-001"],
            "gemini-2.5-flash": ["gemini-2.5-flash"],
        }
        
        # Get alternatives for this model_id
        # If model_id is in alternatives map, use those alternatives
        # Otherwise, try the model_id as-is first
        if model_id in model_alternatives:
            alternatives = model_alternatives[model_id]
        else:
            alternatives = [model_id]
        
        last_error = None
        for alt_model in alternatives:
            try:
                self._model = genai.GenerativeModel(alt_model)
                # Update model_id to the working one
                self.model_id = alt_model
                break
            except Exception as e:
                last_error = e
                continue
        else:
            # If all alternatives fail, raise error with helpful message
            raise ValueError(
                f"Could not initialize model '{model_id}'. "
                f"Tried alternatives: {alternatives}. "
                f"Last error: {str(last_error)[:200]}. "
                f"Please check if the model name is correct and your API key has access."
            )
    
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> ModelResponse:
        """
        Invoke Gemini model and return complete response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            ModelResponse: Complete model response
        """
        start_time = time.perf_counter()
        
        # Convert messages to Gemini format
        gemini_messages = self._convert_messages(messages)
        
        # Prepare generation config
        generation_config = {
            "temperature": temperature,
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        # Convert tools to Gemini format if provided
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)
        
        # Call model (synchronous API, but we're in async context)
        # Note: google-generativeai doesn't have native async, so we run in executor
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._model.generate_content(
                gemini_messages,
                tools=gemini_tools,
                generation_config=generation_config,
                **kwargs
            )
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Parse response - handle both text and function calls
        try:
            content = response.text if response.text else ""
        except ValueError:
            # Response contains function calls, not text
            content = ""
        
        tool_calls = self._extract_tool_calls(response)
        
        # Calculate usage
        usage = self._calculate_usage(response, messages)
        
        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            metadata={
                "latency_ms": latency_ms,
                "model_id": self.model_id,
            }
        )
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncIterator[ModelResponse]:
        """
        Stream responses from Gemini model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Yields:
            ModelResponse: Streaming response chunks
        """
        # Convert messages to Gemini format
        gemini_messages = self._convert_messages(messages)
        
        # Prepare generation config
        generation_config = {
            "temperature": temperature,
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        # Convert tools to Gemini format if provided
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)
        
        # Stream response (synchronous API in executor)
        import asyncio
        loop = asyncio.get_event_loop()
        response_stream = await loop.run_in_executor(
            None,
            lambda: self._model.generate_content(
                gemini_messages,
                tools=gemini_tools,
                generation_config=generation_config,
                stream=True,
                **kwargs
            )
        )
        
        # Yield chunks
        for chunk in response_stream:
            # Handle both text and function calls
            try:
                content = chunk.text if chunk.text else ""
            except ValueError:
                # Response contains function calls, not text
                content = ""
            
            tool_calls = self._extract_tool_calls(chunk) if hasattr(chunk, 'candidates') else []
            
            yield ModelResponse(
                content=content,
                tool_calls=tool_calls,
                usage={},
                metadata={
                    "model_id": self.model_id,
                    "is_streaming": True,
                }
            )
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Convert framework messages to Gemini format.
        
        Gemini uses 'user' and 'model' roles, and 'system' is prepended to first user message.
        """
        gemini_messages = []
        system_content = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_content = content
            elif role == "user":
                # Prepend system message if exists
                user_content = content
                if system_content:
                    user_content = f"{system_content}\n\n{content}"
                    system_content = None  # Only prepend once
                
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": user_content}]
                })
            elif role == "assistant" or role == "model":
                gemini_messages.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        return gemini_messages
    
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert framework tools to Gemini format.
        
        Framework tools format:
        {
            "name": "tool_name",
            "description": "Tool description",
            "parameters": {...}  # JSON schema
        }
        
        Gemini format:
        {
            "function_declarations": [{
                "name": "tool_name",
                "description": "Tool description",
                "parameters": {...}
            }]
        }
        """
        gemini_tools = []
        for tool in tools:
            # Handle both direct tool dict and nested function dict
            if "function" in tool:
                func = tool["function"]
            else:
                func = tool
            
            gemini_tools.append({
                "function_declarations": [{
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {})
                }]
            })
        
        return gemini_tools
    
    def _extract_tool_calls(self, response: GenerateContentResponse) -> List[Dict[str, Any]]:
        """Extract tool calls from Gemini response."""
        tool_calls = []
        
        if not response.candidates:
            return tool_calls
        
        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not candidate.content:
            return tool_calls
        
        parts = candidate.content.parts
        for part in parts:
            if hasattr(part, 'function_call') and part.function_call:
                tool_calls.append({
                    "name": part.function_call.name,
                    "arguments": dict(part.function_call.args) if hasattr(part.function_call, 'args') else {}
                })
        
        return tool_calls
    
    def _calculate_usage(self, response: GenerateContentResponse, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Calculate token usage and cost.
        
        Note: Gemini API provides usage metadata, but we estimate if not available.
        """
        # Try to get usage from response
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage_meta = response.usage_metadata
            input_tokens = getattr(usage_meta, 'prompt_token_count', 0)
            output_tokens = getattr(usage_meta, 'candidates_token_count', 0)
        else:
            # Estimate tokens (rough: 1 token ≈ 4 characters)
            input_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
            input_tokens = input_chars // 4
            
            output_chars = len(response.text) if response.text else 0
            output_tokens = output_chars // 4
        
        # Calculate cost
        pricing = self.PRICING.get(self.model_id, self.PRICING["gemini-1.5-flash"])
        cost_usd = (
            (input_tokens / 1_000_000 * pricing["input"]) +
            (output_tokens / 1_000_000 * pricing["output"])
        )
        
        return {
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
        }


# Convenience classes for specific Gemini models
class GeminiFlash(GeminiModel):
    """Gemini Flash model - fast and efficient (supports 1.5-flash, 2.5-flash, etc.)."""
    
    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None, **kwargs: Any):
        # Use provided model_id or default to 1.5-flash
        model_name = model_id or "gemini-1.5-flash"
        super().__init__(model_id=model_name, api_key=api_key, **kwargs)


class GeminiPro(GeminiModel):
    """Gemini Pro model - more capable."""
    
    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None, **kwargs: Any):
        # Use gemini-pro as default (more widely available), but allow override
        model_name = model_id or "gemini-pro"
        super().__init__(model_id=model_name, api_key=api_key, **kwargs)

