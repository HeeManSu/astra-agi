"""
Tool decorator for Astra Framework.

This module provides the @tool decorator to convert Python functions into Tool objects
that can be used by agents. It handles:
- Automatic JSON Schema generation from type hints
- Sync and async function support
- Error handling and wrapping

Example:
    @tool
    def add(a: int, b: int) -> int:
        return a + b
"""

from collections.abc import Callable
from functools import wraps
import inspect
from typing import Any, Union, get_args, get_origin, get_type_hints


_JSON_BASIC_TYPES = {
    int: {"type": "integer"},
    float: {"type": "number"},
    str: {"type": "string"},
    bool: {"type": "boolean"},
}


def _type_to_json_schema_type(python_type: Any) -> dict[str, Any]:
    """Convert python type into JSON schema"""

    if python_type is type(None):
        return {"type": "null"}

    origin = get_origin(python_type)

    # Optional / Union types -> take first non-None type
    if origin is Union:
        non_none = [t for t in get_args(python_type) if t is not type(None)]
        return _type_to_json_schema_type(non_none[0] if non_none else str)

    # Collections
    if origin in (list, tuple, set):
        args = get_args(python_type)
        return {"type": "array", "items": _type_to_json_schema_type(args[0] if args else str)}

    if origin is dict:
        return {"type": "object"}

    # Fast mapping
    if python_type in _JSON_BASIC_TYPES:
        return _JSON_BASIC_TYPES[python_type].copy()

    # Default fallback
    return {"type": "string"}


def _get_function_schema(func: Callable) -> dict[str, Any]:
    """Extract JSON schema from function."""
    sig = inspect.signature(func)
    try:
        type_hints = get_type_hints(func)
    except Exception:
        type_hints = {}

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        p_type = type_hints.get(param_name, str)
        properties[param_name] = _type_to_json_schema_type(p_type)

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize JSON schema by removing unsupported fields like $schema.
    This ensures compatibility with model providers like Gemini.
    """
    if not schema:
        return {}

    # Create a copy to avoid mutating the original
    sanitized = {k: v for k, v in schema.items() if k != "$schema"}

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
    Tool wrapper that can be used by agents.
    """

    def __init__(self, name: str, description: str, func: Callable, module: str | None = None):
        self.name = name
        self.description = description
        self.func = func
        self.module = module  # Explicit module override (optional)
        self._schema_cache: dict[str, Any] | None = None

    @property
    def parameters(self) -> dict[str, Any]:
        """Get parameters for the tool and cache

        Example:
        @tool(module="utils")
        def process_data(data: dict, count: int, name: str = "default") -> list:
         # Process data with various parameters.
          return []

        # When you access: process_data.parameters
        # Returns:
        {
          "type": "object",
          "properties": {
            "data": {"type": "object"},
            "count": {"type": "integer"},
            "name": {"type": "string"}
          },
          "required": ["data", "count"]
        """
        if self._schema_cache is None:
            self._schema_cache = _get_function_schema(self.func)
        return self._schema_cache

    def __call__(self, *args, **kwargs):
        """Call the tool function"""
        return self.func(*args, **kwargs)


def tool(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    module: str | None = None,
):
    """
    Decorator to convert normal function → Tool with lazy metadata.

    Args:
        func: Function to decorate (if used as @tool)
        name: Explicit tool name (defaults to function name)
        description: Explicit tool description (defaults to first line of docstring)
        module: Explicit module/namespace for code mode (defaults to inference from name)

    Example:
        @tool
        def add(a: int, b: int) -> int:
            return a + b

        @tool(module="math")
        def multiply(a: int, b: int) -> int:
            return a * b

        @tool(name="crm.get_user", module="crm")
        def get_user(user_id: int) -> dict:
            return {"id": user_id}
    """

    def decorator(f: Callable) -> Tool:
        # Wrap sync vs async separately
        @wraps(f)
        def sync_wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                raise RuntimeError(f"Error in tool '{f.__name__}': {e}") from e

        @wraps(f)
        async def async_wrapper(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                raise RuntimeError(f"Error in async tool '{f.__name__}': {e}") from e

        wrapper = async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper

        # Minimal init params → fast initialization
        return Tool(
            name=name or f.__name__,
            description=description or (inspect.getdoc(f) or "").split("\n")[0].strip(),
            func=wrapper,
            module=module,
        )

    return decorator(func) if func else decorator
