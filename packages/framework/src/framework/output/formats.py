"""
Base output format classes.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel
    from .builtin.text import PlainTextFormat, MarkdownFormat
    from .builtin.json import JSONSchemaFormat
    from .builtin.pydantic import PydanticFormat


class OutputFormat(ABC):
    """
    Base class for output formats.
    
    Defines how the agent should format its response.
    
    Example:
        ```python
        agent = Agent(
            model=Gemini("1.5-flash"),
            output_format=OutputFormat.JSON(schema={...})
        )
        ```
    """
    
    @abstractmethod
    def get_instructions(self) -> str:
        """
        Get instructions to add to system prompt.
        
        Returns:
            Instructions string to append to agent instructions
        """
        pass
    
    @abstractmethod
    def get_response_format(self) -> Optional[Dict[str, Any]]:
        """
        Get response_format parameter for model.
        
        Returns:
            Dict for model's response_format parameter, or None
        """
        pass
    
    @abstractmethod
    async def validate(self, output: str) -> bool:
        """
        Validate output matches expected format.
        
        Args:
            output: Model output string
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def parse(self, output: str) -> Any:
        """
        Parse output into expected type.
        
        Args:
            output: Model output string
            
        Returns:
            Parsed output (str, dict, Pydantic model, etc.)
        """
        pass
    
    # Convenience class methods for creating formats
    @classmethod
    def PLAIN_TEXT(cls) -> 'PlainTextFormat':
        """Create plain text format (default)."""
        from .builtin.text import PlainTextFormat
        return PlainTextFormat()
    
    @classmethod
    def MARKDOWN(cls) -> 'MarkdownFormat':
        """Create markdown format."""
        from .builtin.text import MarkdownFormat
        return MarkdownFormat()
    
    @classmethod
    def JSON(cls, schema: Dict[str, Any]) -> 'JSONSchemaFormat':
        """Create JSON format with schema validation."""
        from .builtin.json import JSONSchemaFormat
        return JSONSchemaFormat(schema=schema)
    
    @classmethod
    def PYDANTIC(cls, model: type['BaseModel']) -> 'PydanticFormat':
        """Create Pydantic model format."""
        from .builtin.pydantic import PydanticFormat
        return PydanticFormat(model=model)
