"""
Execution layer for the agent.
It contains execution utilities and helpers.

This module contains the execution pipeline for the agents:

"""

import asyncio
from dataclasses import dataclass
import inspect
from typing import Any

from observability.core import Observability


@dataclass
class ExecutionContext:
    """Context for agent execution."""

    agent_id: str
    temperature: float
    max_tokens: int | None
    tools: list[Any] | None
    observability: Observability | None = None

    # Execution state
    attempt: int = 0
    start_time: float = 0.0
    tool_results: list[dict[str, Any]] | None = None

    def __post_init__(self):
        if self.tool_results is None:
            self.tool_results = []


def validate_tool_arguments(tool: Any, arguments: dict[str, Any]) -> None:
    """
    Validate tool arguments against schema.

    Args:
        tool: Tool object
            arguments: Arguments to validate
    """

    # Get parameters schema
    if hasattr(tool, "parameters"):
        schema = tool.parameters
    else:
        return  # No schema to validate against

    required = schema.get("required", [])
    properties = schema.get("properties", {})

    # Check required parameters
    for param in required:
        if param not in arguments:
            raise ValueError(f"Missing required parameter: {param}")

    # Check for unknown parameters
    for param in arguments:
        if param not in properties:
            raise ValueError(f"Unknown parameter: {param}")


async def execute_tool_call(
    tool: Any, tool_name: str, arguments: dict[str, Any], context: ExecutionContext
) -> dict[str, Any]:
    """
    Execute a single tool call.

    Args:
        tool: Tool object
        tool_name: Name of tool
        arguments: Tool arguments
        context: Execution context

    Returns:
        Result dict with tool name and result/error
    """

    try:
        # Validate arguments
        validate_tool_arguments(tool, arguments)

        # Get the invoke function
        if hasattr(tool, "invoke"):
            invoke_func = tool.invoke
        elif hasattr(tool, "func"):
            invoke_func = tool.func
        elif callable(tool):
            invoke_func = tool
        else:
            raise ValueError("Tool must have an invoke method or a func attribute")

        # Execute the tool
        if inspect.iscoroutinefunction(invoke_func):
            result = await invoke_func(**arguments)
        else:
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: invoke_func(**arguments))

        return {
            "tool": tool_name,
            "result": result,
            "success": True,
        }

    except Exception as e:
        return {
            "tool": tool_name,
            "error": str(e),
            "success": False,
        }


async def execute_tool_parallel(
    tool_calls: list[dict[str, Any]], tools: list[Any], context: ExecutionContext
) -> list[Any]:
    """
    Execute multiple tool calls in parallel.

    Args:
        tool_calls: List of tool calls
        tools: List of tools
        context: Execution context

    Returns:
        List of tool results
    """

    # Create tool lookup. This part can be cached so that if there is need of multiple tool call then it won't load al the tools every time.
    tool_map = {}
    for tool in tools:
        name = getattr(tool, "name", None)
        if name:
            tool_map[name] = tool

    # Execute tool calls in parallel
    tasks = []
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        if tool_name not in tool_map:
            # Tool not found - return error
            tasks.append(
                asyncio.create_task(
                    asyncio.sleep(
                        0,
                        result={
                            "tool": tool_name,
                            "error": "Tool not found",
                            "success": False,
                        },
                    )
                )
            )
        else:
            tool = tool_map[tool_name]
            tasks.append(execute_tool_call(tool, tool_name, arguments, context))

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions

    formatted_results = [
        {
            "tool": "Unknown",
            "error": str(result),
            "success": False,
        }
        if isinstance(result, Exception)
        else result
        for result in results
    ]

    return formatted_results
