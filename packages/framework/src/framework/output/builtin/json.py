"""
JSON output format with schema validation.
"""
import json
from typing import Any, Dict, Optional

try:
    import jsonschema  # type: ignore[import-untyped]
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from ..formats import OutputFormat
from ..exceptions import OutputValidationError


class JSONSchemaFormat(OutputFormat):
    """
    JSON output with schema validation.
    
    Validates output against JSON Schema and provides native structured
    output support for compatible models.
    
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
            model=Gemini("1.5-flash"),
            output_format=OutputFormat.JSON(schema=schema)
        )
        ```
    """
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize with JSON schema.
        
        Args:
            schema: JSON Schema dict
            
        Raises:
            ImportError: If jsonschema library not installed
        """
        if not HAS_JSONSCHEMA:
            raise ImportError(
                "jsonschema library required for JSONSchemaFormat. "
                "Install with: pip install jsonschema"
            )
        
        self.schema = schema
    
    def get_instructions(self) -> str:
        """Instruct model to return JSON matching schema."""
        return f"Respond with valid JSON matching this schema: {json.dumps(self.schema, indent=2)}"
    
    def get_response_format(self) -> Optional[Dict[str, Any]]:
        """
        Get response_format for native structured outputs.
        
        For models that support it (Gemini, OpenAI), this enables
        native JSON mode with schema validation.
        """
        return {
            "type": "json_schema",
            "json_schema": self.schema
        }
    
    async def validate(self, output: str) -> bool:
        """
        Validate output is valid JSON matching schema.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            data = json.loads(output)
            jsonschema.validate(data, self.schema)
            return True
        except (json.JSONDecodeError, jsonschema.ValidationError):
            return False
    
    async def parse(self, output: str) -> Dict[str, Any]:
        """
        Parse JSON output.
        
        Args:
            output: JSON string
            
        Returns:
            Parsed dict
            
        Raises:
            OutputValidationError: If output is not valid JSON
        """
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise OutputValidationError(f"Invalid JSON: {e}")
