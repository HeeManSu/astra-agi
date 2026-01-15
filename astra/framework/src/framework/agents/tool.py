"""
Tool decorator for Astra Framework.

This module provides the @tool decorator to convert Python functions into Tool objects
that can be used by agents. It uses Pydantic models for input/output schemas.

Example:
    from pydantic import BaseModel, Field

    class AddInput(BaseModel):
        a: int = Field(description="First number")
        b: int = Field(description="Second number")

    class AddOutput(BaseModel):
        result: int = Field(description="Sum of a and b")

    @tool(description="Add two numbers")
    def add(input: AddInput) -> AddOutput:
        return AddOutput(result=input.a + input.b)
"""

from collections.abc import Callable
from functools import wraps
import inspect
from typing import Any, get_type_hints

from pydantic import BaseModel


def _is_pydantic_model(cls: Any) -> bool:
    """Check if a class is a Pydantic BaseModel subclass."""
    try:
        return isinstance(cls, type) and issubclass(cls, BaseModel)
    except TypeError:
        return False


def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize JSON schema by removing unsupported fields like $schema.
    This ensures compatibility with model providers like Gemini.
    """
    if not schema:
        return {}

    # Fields to remove for model compatibility
    remove_keys = {"$schema", "$defs", "definitions"}
    sanitized = {k: v for k, v in schema.items() if k not in remove_keys}

    # Recursively sanitize nested schemas in properties
    if "properties" in sanitized and isinstance(sanitized["properties"], dict):
        sanitized["properties"] = {
            key: _sanitize_schema(value) if isinstance(value, dict) else value
            for key, value in sanitized["properties"].items()
        }

    # Recursively sanitize items in arrays
    if "items" in sanitized and isinstance(sanitized["items"], dict):
        sanitized["items"] = _sanitize_schema(sanitized["items"])

    return sanitized


class Tool:
    """
    Tool wrapper with Pydantic schema support.

    Tools require Pydantic models for input and output schemas to enable
    accurate code generation and validation.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        input_schema: type[BaseModel],
        output_schema: type[BaseModel],
        example: dict | None = None,
    ):
        """
        Initialize a Tool.

        Args:
            name: Tool name
            description: Tool description
            func: Wrapped function
            input_schema: Pydantic model for input validation
            output_schema: Pydantic model for output
            example: Optional example with input/output
        """
        self.name = name
        self.description = description
        self.func = func
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.example = example
        self._schema_cache: dict[str, Any] | None = None

    @property
    def parameters(self) -> dict[str, Any]:
        """Get JSON schema from input_schema.

        Returns sanitized schema compatible with model providers.
        """
        if self._schema_cache is None:
            raw_schema = self.input_schema.model_json_schema()
            self._schema_cache = _sanitize_schema(raw_schema)
        return self._schema_cache

    def __call__(self, *args, **kwargs):
        """Call the tool function."""
        return self.func(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Tool(name='{self.name}', input={self.input_schema.__name__}, output={self.output_schema.__name__})"


def tool(
    *,
    description: str,
    example: dict | None = None,
):
    """
    Decorator to convert a function with Pydantic schemas into a Tool.

    The function must:
    - Have a single parameter that is a Pydantic BaseModel
    - Have a return type that is a Pydantic BaseModel

    Args:
        description: Tool description (required)
        example: Optional example dict with 'input' and 'output' keys

    Example:
        from pydantic import BaseModel, Field

        class CalculateInput(BaseModel):
            x: int = Field(description="First number")
            y: int = Field(description="Second number")

        class CalculateOutput(BaseModel):
            result: int = Field(description="Calculation result")

        @tool(
            description="Multiply two numbers",
            example={"input": {"x": 5, "y": 3}, "output": {"result": 15}},
        )
        async def multiply(input: CalculateInput) -> CalculateOutput:
            return CalculateOutput(result=input.x * input.y)
    """

    def decorator(func: Callable) -> Tool:
        # Get type hints
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}

        # Extract input schema from parameters
        input_schema: type[BaseModel] | None = None
        sig = inspect.signature(func)
        for param_name in sig.parameters:
            if param_name in ("self", "cls"):
                continue
            param_type = hints.get(param_name)
            if _is_pydantic_model(param_type):
                input_schema = param_type
                break

        # Extract output schema from return type
        output_schema = hints.get("return")

        # Validate schemas
        if input_schema is None:
            raise ValueError(
                f"Tool '{func.__name__}' must have a Pydantic BaseModel as input parameter. "
                f"Example: def {func.__name__}(input: MyInputModel) -> MyOutputModel"
            )

        if not _is_pydantic_model(output_schema):
            raise ValueError(
                f"Tool '{func.__name__}' must return a Pydantic BaseModel. "
                f"Example: def {func.__name__}(input: MyInputModel) -> MyOutputModel"
            )

        # Create sync/async wrapper with error handling
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise RuntimeError(f"Error in tool '{func.__name__}': {e}") from e

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise RuntimeError(f"Error in async tool '{func.__name__}': {e}") from e

        wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

        return Tool(
            name=func.__name__,
            description=description,
            func=wrapper,
            input_schema=input_schema,
            output_schema=output_schema,  # type: ignore[arg-type]  # Validated above
            example=example,
        )

    return decorator
