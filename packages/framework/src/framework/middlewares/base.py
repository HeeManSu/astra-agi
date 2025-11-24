"""
Base classes for middlewares.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .context import MiddlewareContext


class InputMiddleware(ABC):
    """
    Base class for input middlewares.
    
    Input middlewares run before the LLM is called and can:
    - Validate input
    - Transform messages
    - Add context
    - Enforce rules
    - Abort execution
    
    Example:
        ```python
        class PIIRedactionMiddleware(InputMiddleware):
            async def process(self, messages, context):
                for msg in messages:
                    msg['content'] = redact_pii(msg['content'])
                return messages
        ```
    """
    
    @abstractmethod
    async def process(
        self,
        messages: List[Dict[str, str]],
        context: MiddlewareContext
    ) -> List[Dict[str, str]]:
        """
        Process input messages before LLM call.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            context: Middleware context with run metadata
            
        Returns:
            Modified messages list
            
        Raises:
            InputValidationError: If validation fails
            MiddlewareAbortError: To abort execution
        """
        pass


class OutputMiddleware(ABC):
    """
    Base class for output middlewares.
    
    Output middlewares run after the LLM generates output and can:
    - Validate output
    - Apply guardrails
    - Moderate content
    - Format output
    - Abort execution
    
    Example:
        ```python
        class ContentModerationMiddleware(OutputMiddleware):
            async def process(self, output, context):
                if contains_unsafe_content(output):
                    raise MiddlewareAbortError("Unsafe content")
                return output
        ```
    """
    
    @abstractmethod
    async def process(
        self,
        output: str,
        context: MiddlewareContext
    ) -> str:
        """
        Process final output after LLM call.
        
        Args:
            output: LLM output text
            context: Middleware context with run metadata
            
        Returns:
            Modified output text
            
        Raises:
            OutputValidationError: If validation fails
            MiddlewareAbortError: To abort execution
        """
        pass


class StreamingOutputMiddleware(ABC):
    """
    Base class for streaming output middlewares.
    
    Streaming middlewares can process chunks as they arrive and maintain
    internal state across chunks.
    
    Example:
        ```python
        class StreamingModerationMiddleware(StreamingOutputMiddleware):
            def __init__(self):
                self.buffer = ""
            
            async def on_chunk(self, chunk, context):
                self.buffer += chunk
                if is_unsafe(self.buffer):
                    raise MiddlewareAbortError("Unsafe content")
                return chunk
            
            async def on_complete(self, context):
                self.buffer = ""  # Reset state
                return None
        ```
    """
    
    @abstractmethod
    async def on_chunk(
        self,
        chunk: str,
        context: MiddlewareContext
    ) -> Optional[str]:
        """
        Process each streaming chunk.
        
        Args:
            chunk: Text chunk from LLM
            context: Middleware context
            
        Returns:
            Modified chunk or None to skip this chunk
            
        Raises:
            MiddlewareAbortError: To abort streaming
        """
        pass
    
    @abstractmethod
    async def on_complete(
        self,
        context: MiddlewareContext
    ) -> Optional[str]:
        """
        Called when streaming completes.
        
        Can return a final chunk to append or None.
        
        Args:
            context: Middleware context
            
        Returns:
            Optional final chunk to append
        """
        pass
