"""
Pydantic model output format.
"""
import json
from typing import Any, Dict, Optional, Type

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel as PydanticBaseModel, ValidationError as PydanticValidationError

try:
    from pydantic import BaseModel, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = None  # type: ignore[assignment]
    ValidationError = None  # type: ignore[assignment]

from ..formats import OutputFormat
from ..exceptions import OutputValidationError


class PydanticFormat(OutputFormat):
    """
    Pydantic model output format.
    
    Validates output against Pydantic model and returns typed instance.
    Internally converts Pydantic to JSON Schema (following Agno pattern).
    
    Example:
        ```python
        from pydantic import BaseModel
        
        class UserProfile(BaseModel):
            name: str
            age: int
            email: str
        
        agent = Agent(
            model=Gemini("1.5-flash"),
            output_format=OutputFormat.PYDANTIC(model=UserProfile)
        )
        
        response = await agent.invoke("Create user: Alice, 30, alice@example.com")
        user = response['parsed']  # UserProfile instance
        print(user.name)  # "Alice"
        ```
    """
    
    def __init__(self, model: 'Type[PydanticBaseModel]'):  # type: ignore[valid-type]
        """
        Initialize with Pydantic model.
        
        Args:
            model: Pydantic model class
            
        Raises:
            ImportError: If pydantic library not installed
        """
        if not HAS_PYDANTIC:
            raise ImportError(
                "pydantic library required for PydanticFormat. "
                "Install with: pip install pydantic"
            )
        
        self.model = model
        # Convert Pydantic to JSON Schema (Agno pattern)
        self.schema = model.model_json_schema()
    
    def get_instructions(self) -> str:
        """Instruct model to return JSON matching Pydantic model."""
        return f"Respond with valid JSON matching this structure: {json.dumps(self.schema, indent=2)}"
    
    def get_response_format(self) -> Optional[Dict[str, Any]]:
        """
        Get response_format using JSON Schema.
        
        Pydantic models are converted to JSON Schema internally.
        """
        return {
            "type": "json_schema",
            "json_schema": self.schema
        }
    
    async def validate(self, output: str) -> bool:
        """
        Validate output matches Pydantic model.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            data = json.loads(output)
            self.model(**data)  # type: ignore[misc]
            return True
        except json.JSONDecodeError:
            return False
        except Exception as e:  # type: ignore[misc]
            # Catch ValidationError if pydantic is available
            if HAS_PYDANTIC and ValidationError and isinstance(e, ValidationError):
                return False
            # Re-raise if it's not a validation error
            raise
    
    async def parse(self, output: str) -> Any:  # type: ignore[return]
        """
        Parse output into Pydantic model instance.
        
        Args:
            output: JSON string
            
        Returns:
            Pydantic model instance
            
        Raises:
            OutputValidationError: If output doesn't match model
        """
        try:
            data = json.loads(output)
            return self.model(**data)  # type: ignore[misc]
        except json.JSONDecodeError as e:
            raise OutputValidationError(f"Invalid JSON: {e}")
        except Exception as e:  # type: ignore[misc]
            if HAS_PYDANTIC and ValidationError and isinstance(e, ValidationError):
                raise OutputValidationError(f"Pydantic validation failed: {e}")
            raise OutputValidationError(f"Validation failed: {e}")
