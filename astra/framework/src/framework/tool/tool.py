"""
Tool implementation for Astra Framework.

This module provides the core Tool class and bind_tool decorator for creating
tools that agents can use. Tools are functions with validated Pydantic schemas
that enable agents to perform specific actions.

Key concepts:
- Tool: A callable wrapper around a function with input/output schemas
- ToolSpec: A declarative specification defining what a tool does
- bind_tool: A decorator that connects a ToolSpec to its implementation

The ToolSpec architecture separates "what" (specification) from "how"
(implementation), making tools reusable and easy to validate.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import inspect
import re
from typing import Any, get_type_hints

from pydantic import BaseModel


class Tool:
    """
    Runtime wrapper for tool functions.

    A Tool encapsulates:
    1. A callable function that performs the actual work
    2. Pydantic schemas that define input and output structure
    3. Metadata like name, description, and examples

    Agents use Tool instances to understand what actions they can perform
    and how to call them correctly.

    Example:
        # After binding with @bind_tool, you get a Tool instance
        tool = get_stock_price  # This is a Tool instance

        # Call it like a function
        result = await tool(GetStockPriceInput(symbol="AAPL"))

        # Access metadata
        print(tool.name)         # "get_stock_price"
        print(tool.description)  # "Get current stock price..."
        print(tool.parameters)   # JSON schema for input
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        input_schema: type[BaseModel],
        output_schema: type[BaseModel],
        example: dict | None = None,
        source: str = "local",
        slug: str | None = None,
    ):
        """
        Initialize a Tool.

        Args:
            name: Tool identifier (e.g., "get_stock_price")
            description: Human-readable description for LLM
            func: The actual Python function to execute
            input_schema: Pydantic model defining expected input
            output_schema: Pydantic model defining expected output
            example: Optional example showing input/output pair
            source: Tool source (default: "local")
            slug: Optional tool slug (derived from name if not provided)
        """
        provided_slug = str(slug).strip() if slug is not None else ""
        if provided_slug:
            # Normalize custom slugs the same way auto-generated ones are,
            # so semantic layer and sandbox tool map keys always agree.
            normalized = re.sub(r"[^a-z0-9]+", "-", provided_slug.lower())
            normalized = re.sub(r"-+", "-", normalized).strip("-")
            self.slug = normalized or "unknown"
        else:
            normalized_name = re.sub(r"[^a-z0-9]+", "-", name.lower())
            normalized_name = re.sub(r"-+", "-", normalized_name).strip("-")
            if not normalized_name:
                normalized_name = "unknown"
            self.slug = normalized_name
        self.name = name
        self.description = description
        self.func = func
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.example = example
        self.source = source

    @property
    def parameters(self) -> dict[str, Any]:
        """
        Get JSON schema representation of input parameters.

        Used by LLMs, validation systems, and documentation generators.
        """
        return self.input_schema.model_json_schema()

    def __call__(self, *args, **kwargs):
        """
        Make the Tool callable like a regular function.

        This allows you to use tool instances naturally:
            result = await my_tool(input_data)

        Instead of:
            result = await my_tool.func(input_data)
        """
        return self.func(*args, **kwargs)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Tool(name='{self.name}', input={self.input_schema.__name__}, output={self.output_schema.__name__})"


def bind_tool(spec):
    """
    Decorator that binds a ToolSpec to its implementation function.

    This is the bridge between declarative specification and actual code.
    It performs three key jobs:

    1. **Validation**: Ensures the function signature matches the spec
       - Checks parameter types
       - Checks return type
       - Provides clear error messages if anything doesn't match

    2. **Error Handling**: Wraps the function to provide better error context
       - Catches exceptions from the tool
       - Re-raises with tool name for easier debugging

    3. **Tool Creation**: Builds a runtime Tool instance
       - Packages everything agents need to use the tool
       - Includes metadata from spec and implementation

    Why separate spec from implementation?
    - Specs can be shared across multiple implementations
    - Specs can be validated independently
    - Specs provide rich context for LLM code generation
    - Implementation stays clean and focused

    Args:
        spec: ToolSpec instance defining the tool's interface

    Returns:
        A decorator function that takes your implementation and returns a Tool

    Raises:
        TypeError: If spec is not a ToolSpec, or if parameter/return types don't match
        ValueError: If function signature is invalid (not exactly one parameter)

    Example usage:
        # Step 1: Define ToolSpec
        GET_PRICE_SPEC = ToolSpec(
            name="get_price",
            description="Get stock price for a symbol",
            input_schema=PriceInput,
            output_schema=PriceOutput,
            examples=[{"input": {"symbol": "AAPL"}, "output": {...}}]
        )

        # Step 2: Bind implementation
        @bind_tool(GET_PRICE_SPEC)
        async def get_price(input: PriceInput) -> PriceOutput:
            '''Fetch and return stock price'''
            # ... implementation ...
            return PriceOutput(...)

        # Result: get_price is now a Tool instance
        # You can call it: await get_price(PriceInput(symbol="AAPL"))
    """
    # Import ToolSpec here to avoid circular import issues
    # (tool.py and tool_spec.py can't import each other at module level)
    from framework.tool.tool_spec import ToolSpec

    # Validate input is actually a ToolSpec
    # This catches mistakes like @bind_tool("wrong") early
    if not isinstance(spec, ToolSpec):
        raise TypeError(f"bind_tool requires a ToolSpec, got {type(spec)}")

    def decorator(func: Callable) -> Tool:
        """
        The actual decorator that processes the implementation function.

        Args:
            func: The implementation function to bind to the spec

        Returns:
            Tool instance ready for use by agents
        """

        # === STEP 1: Extract type information ===
        # We need to know what types the function expects/returns
        # to validate they match the spec
        try:
            hints = get_type_hints(func)
        except Exception:
            # If type hints can't be extracted (rare), continue with empty dict
            # Validation will fail later with clear error
            hints = {}

        # === STEP 2: Get function parameters ===
        # inspect.signature gives us parameter information
        sig = inspect.signature(func)

        # Filter out 'self' and 'cls' because:
        # - If this is a method, self/cls are implicit
        # - Tools should only have one explicit parameter (the input model)
        params = [p for p in sig.parameters.values() if p.name not in ("self", "cls")]

        # === STEP 3: Validate parameter count ===
        # Tools must have exactly one parameter for consistency
        # This makes it easy for LLMs to generate tool calls:
        #   tool_name(InputModel(...))
        # Instead of:
        #   tool_name(arg1, arg2, arg3, ...)
        if len(params) != 1:
            raise ValueError(
                f"Tool '{spec.name}' must have exactly one parameter. "
                f"Got {len(params)}: {[p.name for p in params]}\n"
                f"Expected signature: def {func.__name__}(input: {spec.input_schema.__name__}) -> {spec.output_schema.__name__}"
            )

        # === STEP 4: Validate parameter type ===
        # The parameter must be the exact Pydantic model from the spec
        param = params[0]
        param_type = hints.get(param.name)

        if param_type != spec.input_schema:
            raise TypeError(
                f"Tool '{spec.name}' parameter type mismatch.\n"
                f"Expected: {spec.input_schema.__name__}\n"
                f"Got: {param_type.__name__ if param_type else 'missing type hint'}\n"
                f"Fix: Add type hint: def {func.__name__}(input: {spec.input_schema.__name__})"
            )

        # === STEP 5: Validate return type ===
        # The return type must match the spec's output model
        return_type = hints.get("return")

        if return_type != spec.output_schema:
            raise TypeError(
                f"Tool '{spec.name}' return type mismatch.\n"
                f"Expected: {spec.output_schema.__name__}\n"
                f"Got: {return_type.__name__ if return_type else 'missing type hint'}\n"
                f"Fix: Add return type: def {func.__name__}(...) -> {spec.output_schema.__name__}"
            )

        # === STEP 6: Create error-handling wrappers ===
        # We wrap the function to catch errors and add tool context
        # This makes debugging much easier: instead of generic errors,
        # you see "Error in tool 'get_stock_price': ..."

        @wraps(func)  # Preserves original function's name, docstring, etc.
        def sync_wrapper(*args, **kwargs):
            """Wrapper for synchronous tools."""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Re-raise with tool context
                raise RuntimeError(f"Error in tool '{spec.name}': {e}") from e

        @wraps(func)  # Preserves original function's metadata
        async def async_wrapper(*args, **kwargs):
            """Wrapper for asynchronous tools."""
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Re-raise with tool context
                raise RuntimeError(f"Error in async tool '{spec.name}': {e}") from e

        # Choose the right wrapper based on whether the function is async
        # inspect.iscoroutinefunction returns True for async functions
        wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

        # === STEP 7: Create and return Tool instance ===
        # Now that everything is validated, create the runtime Tool
        # This is what agents will actually use
        return Tool(
            name=spec.name,
            description=spec.description,
            func=wrapper,  # Use wrapped version for error handling
            input_schema=spec.input_schema,
            output_schema=spec.output_schema,
            example=spec.examples[0] if spec.examples else None,
        )

    return decorator
