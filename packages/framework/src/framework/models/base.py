"""
Base model class for Astra Framework.

Provides abstract base class for all model providers.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class ModelResponse:
    """
    Standardized model response format.
    
    All model implementations should return this format for consistency.
    """
    
    def __init__(
        self,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize model response.
        
        Args:
            content: Generated text content
            tool_calls: List of tool calls if any
            usage: Token usage information
            metadata: Additional metadata from provider
        """
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage = usage or {}
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "usage": self.usage,
            "metadata": self.metadata,
        }


class Model(ABC):
    """
    Abstract base class for all model providers.
    
    All model implementations must inherit from this class and implement
    the `invoke` and `stream` methods.
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs: Any):
        """
        Initialize model.
        
        Args:
            model_id: Model identifier (e.g., 'gemini-1.5-flash')
            api_key: API key for the provider
            **kwargs: Additional provider-specific parameters
        """
        
        self.model_id = model_id
        self.api_key = api_key
        self._config = kwargs
        
    @property
    def provider(self) -> str:
        """Get provider name (e.g., 'google', 'openai')."""
        return self.__class__.__module__.split('.')[-1] if '.' in self.__class__.__module__ else 'unknown'    
    
    @abstractmethod
    async def invoke(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, temperature: float = 0.7, max_tokens: Optional[int] = None, **kwargs: Any) -> ModelResponse:
        """
        Invoke the model with messages and return complete response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ModelResponse: Complete model response
            
        Example:
            ```python
            messages = [{"role": "user", "content": "Hello!"}]
            response = await model.invoke(messages)
            print(response.content)
            ```
        """
        pass
    
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncIterator[ModelResponse]:
        """
        Stream responses from the model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        
        Yields:
            ModelResponse: Streaming response chunks
        
        Example:
            ```python
            messages = [{"role": "user", "content": "Tell me a story"}]
            async for chunk in model.stream(messages):
                print(chunk.content, end='', flush=True)
            ```
        """
        pass
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(model_id='{self.model_id}', provider='{self.provider}')"