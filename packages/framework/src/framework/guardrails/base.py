"""
Base classes for guardrails.

Guardrails extend middlewares with safety-focused validation.
"""
from abc import abstractmethod
from typing import Any, Dict, List

from ..middlewares import InputMiddleware, OutputMiddleware, MiddlewareContext
from .exceptions import InputGuardrailError, OutputGuardrailError, SchemaValidationError


class InputGuardrail(InputMiddleware):
    """
    Base class for input guardrails.
    
    Input guardrails validate user input before the agent processes it.
    They act as a safety layer to prevent harmful, invalid, or malicious input.
    
    Example:
        ```python
        class PromptInjectionGuardrail(InputGuardrail):
            async def validate(self, messages, context):
                for msg in messages:
                    if self._is_injection_attempt(msg['content']):
                        raise InputGuardrailError("Prompt injection detected")
                return True
        ```
    """
    
    @abstractmethod
    async def validate(
        self,
        messages: List[Dict[str, str]],
        context: MiddlewareContext
    ) -> bool:
        """
        Validate input messages.
        
        Args:
            messages: Input messages
            context: Middleware context
            
        Returns:
            True if valid
            
        Raises:
            InputGuardrailError: If validation fails
        """
        pass
    
    async def process(
        self,
        messages: List[Dict[str, str]],
        context: MiddlewareContext
    ) -> List[Dict[str, str]]:
        """Process messages (calls validate internally)."""
        await self.validate(messages, context)
        return messages


class OutputGuardrail(OutputMiddleware):
    """
    Base class for output guardrails.
    
    Output guardrails validate agent output before returning to the user.
    They ensure the output is safe, appropriate, and meets quality standards.
    
    Example:
        ```python
        class ToxicityGuardrail(OutputGuardrail):
            async def validate(self, output, context):
                if self._is_toxic(output):
                    raise OutputGuardrailError("Toxic content detected")
                return True
        ```
    """
    
    @abstractmethod
    async def validate(
        self,
        output: str,
        context: MiddlewareContext
    ) -> bool:
        """
        Validate output.
        
        Args:
            output: Agent output
            context: Middleware context
            
        Returns:
            True if valid
            
        Raises:
            OutputGuardrailError: If validation fails
        """
        pass
    
    async def process(
        self,
        output: str,
        context: MiddlewareContext
    ) -> str:
        """Process output (calls validate internally)."""
        await self.validate(output, context)
        return output


class SchemaGuardrail(OutputMiddleware):
    """
    Base class for schema validation guardrails.
    
    Schema guardrails validate that output matches an expected structure/format.
    This ensures the agent returns data in the correct format.
    
    Example:
        ```python
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        agent = Agent(
            name="StructuredAgent",
            model=Gemini("1.5-flash"),
            output_middlewares=[JSONSchemaGuardrail(schema=schema)]
        )
        ```
    """
    
    def __init__(self, schema: Any):
        """
        Initialize with expected schema.
        
        Args:
            schema: Schema definition (JSON schema dict or Pydantic model)
        """
        self.schema = schema
    
    @abstractmethod
    async def validate_schema(
        self,
        output: str,
        schema: Any,
        context: MiddlewareContext
    ) -> bool:
        """
        Validate output against schema.
        
        Args:
            output: Agent output
            schema: Expected schema
            context: Middleware context
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        pass
    
    async def process(
        self,
        output: str,
        context: MiddlewareContext
    ) -> str:
        """Process output (validates schema)."""
        await self.validate_schema(output, self.schema, context)
        return output
