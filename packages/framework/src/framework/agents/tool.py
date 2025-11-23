"""
Tool decorator for Astra Framework.

This module provides the @tool decorator to convert Python functions into Tool objects
that can be used by agents. It handles:
- Automatic JSON Schema generation from type hints
- Sync and async function support
- Error handling and wrapping
- Parameter filtering (removes framework-injected params)

Example:
    @tool
    def add(a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        return a + b
"""
import inspect
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union, get_args, get_origin, get_type_hints


def _type_to_json_schema_type(python_type: Any) -> Dict[str, Any]:
    """
    Convert Python type to JSON Schema type.
    
    Handles:
    - Basic types (int, str, float, bool)
    - Collections (List[T], Dict[K, V])
    - Optional/Union types
    - Unknown types (defaults to string)
    
    Args:
        python_type: Python type (int, str, float, bool, List[T], etc.)
    
    Returns:
        JSON Schema type definition
    """
    # Handle None type
    if python_type is type(None):
        return {"type": "null"}
    
    # Handle Union types (including Optional which is Union[X, None])
    origin = get_origin(python_type) if hasattr(python_type, "__origin__") else None
    if origin is Union:
        args = get_args(python_type)
        # For Optional types (Union[X, None]), extract the non-None type
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            # Use the first non-None type
            return _type_to_json_schema_type(non_none_args[0])
        # If all args are None, default to string
        return {"type": "string"}
    
    # Handle List/Tuple/Set types
    if origin in (list, tuple, set):
        args = get_args(python_type)
        items_schema = _type_to_json_schema_type(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": items_schema}
    
    # Handle Dict types
    if origin is dict:
        args = get_args(python_type)
        # For Dict[K, V], use object type (Gemini doesn't support additionalProperties in function schemas)
        # We'll use a generic object type
        return {"type": "object"}
    
    # Basic type mapping
    type_mapping = {
        int: {"type": "integer"},
        float: {"type": "number"},
        str: {"type": "string"},
        bool: {"type": "boolean"},
    }
    
    # Check direct mapping
    if python_type in type_mapping:
        return type_mapping[python_type]
    
    # Handle type objects (when type is passed as a class, not instance)
    if isinstance(python_type, type):
        type_name = python_type.__name__
        if type_name in ("int", "float", "complex", "Decimal"):
            return {"type": "number"}
        elif type_name in ("str", "string"):
            return {"type": "string"}
        elif type_name in ("bool", "boolean"):
            return {"type": "boolean"}
        elif type_name in ("list", "tuple", "set", "frozenset"):
            return {"type": "array", "items": {"type": "string"}}
        elif type_name in ("dict", "mapping"):
            return {"type": "object"}
    
    # Default to string for unknown types
    return {"type": "string"}


def _get_function_schema(func: Callable) -> Dict[str, Any]:
    """
    Extract JSON Schema from function signature using type hints.
    
    Filters out framework-injected parameters:
    - self, cls
    - agent, team, run_context, session_state, dependencies
    - images, videos, audios, files (media parameters)
    
    Args:
        func: Function to extract schema from
    
    Returns:
        JSON Schema dict with properties and required fields
    """
    sig = inspect.signature(func)
    
    # Get type hints, handling cases where function might not have them
    try:
        type_hints = get_type_hints(func)
    except (NameError, TypeError):
        # If type hints can't be resolved (e.g., forward references), use empty dict
        type_hints = {}
    
    # Framework-injected parameters to skip
    SKIP_PARAMS = {
        "self", "cls",
        "agent", "team", "run_context", "session_state", "dependencies",
        "images", "videos", "audios", "files"
    }
    
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Skip framework-injected parameters
        if param_name in SKIP_PARAMS:
            continue
        
        # Get type hint (default to str if not available)
        param_type = type_hints.get(param_name, str)
        
        # Convert to JSON schema
        param_schema = _type_to_json_schema_type(param_type)
        
        # Add description from docstring if available
        # (Basic implementation - could be enhanced with docstring parsing)
        
        properties[param_name] = param_schema
        
        # Add to required if no default value
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


class Tool:
    """
    Tool object that wraps a function for use by agents.
    
    Attributes:
        name: Tool name (from function name)
        description: Tool description (from docstring)
        parameters: JSON Schema parameters definition
        invoke: The actual function to call
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        invoke: Callable
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.invoke = invoke
    
    def __call__(self, *args, **kwargs):
        """Allow tool to be called directly."""
        return self.invoke(*args, **kwargs)


def tool(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> Any:
    """
    Decorator to convert a function into a Tool that can be used by an agent.
    
    Usage:
        @tool
        def add(a: int, b: int) -> int:
            \"\"\"Add two numbers.\"\"\"
            return a + b
        
        @tool(name="custom_name", description="Custom description")
        def multiply(a: int, b: int) -> int:
            \"\"\"Multiply two numbers.\"\"\"
            return a * b
        
        @tool
        async def async_tool(text: str) -> str:
            \"\"\"Async tool example.\"\"\"
            return text.upper()
    
    Args:
        func: Function to decorate (when used as @tool)
        name: Optional override for tool name
        description: Optional override for tool description
    
    Returns:
        Tool object that can be passed to agents
    
    Note:
        Framework-injected parameters are automatically filtered:
        - self, cls
        - agent, team, run_context, session_state, dependencies
        - images, videos, audios, files
    """
    def decorator(f: Callable) -> Tool:
        """Inner decorator that creates the Tool object."""
        
        # Wrap function to preserve metadata and handle errors
        @wraps(f)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Re-raise with context
                raise RuntimeError(f"Error in tool '{f.__name__}': {e}") from e
        
        @wraps(f)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                # Re-raise with context
                raise RuntimeError(f"Error in async tool '{f.__name__}': {e}") from e
        
        # Choose appropriate wrapper based on function type
        if inspect.iscoroutinefunction(f):
            wrapper = async_wrapper
        else:
            wrapper = sync_wrapper
        
        # Get tool name
        tool_name = name or f.__name__
        
        # Get description from docstring or use provided
        if description:
            tool_description = description
        else:
            tool_description = inspect.getdoc(f) or ""
            # Use first line of docstring as description
            if tool_description:
                tool_description = tool_description.split('\n')[0].strip()
        
        # Extract parameters schema from function signature
        parameters_schema = _get_function_schema(f)
        
        # Create and return Tool object
        return Tool(
            name=tool_name,
            description=tool_description,
            parameters=parameters_schema,
            invoke=wrapper  # Use wrapped function for better error handling
        )
    
    # Handle both @tool and @tool() cases
    if func is not None:
        return decorator(func)
    return decorator

