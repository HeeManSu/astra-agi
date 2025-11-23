"""
Agent execution steps for Astra Framework.

This module contains the execution pipeline for agent invocations:
1. prepare_memory_step: Adds system instructions to messages
2. prepare_tools_step: Converts tools to model-compatible format
3. invoke_step: Calls the model and returns response
4. stream_step: Streams model responses
5. map_results_step: Executes tool calls and collects results
6. execute_tool: Executes a single tool by name

The ExecutionContext object is passed between steps to maintain state.
"""
from typing import Any, AsyncIterator, Dict, List, Optional, TYPE_CHECKING

from ..models.base import Model, ModelResponse

if TYPE_CHECKING:
    from observability import Observability


class ExecutionContext:
    """
    Context passed between execution steps.
    
    This object maintains the state of an agent invocation as it flows through
    the execution pipeline. It contains messages, tools, model parameters, and
    intermediate results.
    
    Attributes:
        messages: List of message dicts with 'role' and 'content'
        tools: List of Tool objects available to the agent
        temperature: Sampling temperature for model (0.0-1.0)
        max_tokens: Maximum tokens to generate
        converted_tools: Tools converted to model-compatible JSON schema format
        model_response: Last response from the model
        tool_results: Results from executed tool calls
    """
    
    def __init__(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        # Input parameters
        self.messages = messages
        self.tools = tools or []
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Intermediate state
        self.converted_tools: Optional[List[Dict[str, Any]]] = None
        self.model_response: Optional[ModelResponse] = None
        self.tool_results: List[Dict[str, Any]] = []


async def prepare_tools_step(
    context: ExecutionContext,
    agent_tools: List[Any],
    obs: Optional['Observability'] = None
) -> ExecutionContext:
    """
    Prepare tools for model execution.
    
    Converts agent tools list to model-compatible format.
    
    Args:
        context: Execution context
        agent_tools: Agent's tools list (e.g., [PythonTool(), HttpTool()])
    
    Returns:
        Updated execution context with converted_tools
    """
    if not agent_tools:
        context.converted_tools = None
        return context
    
    # Convert tools to model format
    # Format: [{"name": "...", "description": "...", "parameters": {...}}]
    converted_tools = []
    
    for tool_def in agent_tools:
        if isinstance(tool_def, dict):
            # Tool is already a dict with name, description, parameters
            tool_dict = {
                "name": tool_def.get("name", ""),
                "description": tool_def.get("description", ""),
                "parameters": tool_def.get("parameters", {})
            }
        else:
            # Tool is an object (e.g., PythonTool(), HttpTool())
            # Extract name, description, parameters from object attributes
            tool_dict = {
                "name": getattr(tool_def, "name", ""),
                "description": getattr(tool_def, "description", ""),
                "parameters": getattr(tool_def, "parameters", {})
            }
        
        # Only add if tool has a name
        if tool_dict["name"]:
            converted_tools.append(tool_dict)
    
    context.converted_tools = converted_tools if converted_tools else None
    return context


async def prepare_memory_step(
    context: ExecutionContext,
    instructions: str,
    obs: Optional['Observability'] = None
) -> ExecutionContext:
    """
    Prepare memory and instructions.
    
    For MVP, we just prepend instructions to messages.
    Memory will be implemented later.
    
    Args:
        context: Execution context
        instructions: Agent instructions
    
    Returns:
        Updated execution context with instructions prepended
    """
    # Prepend instructions as system message if not already present
    if context.messages and context.messages[0].get("role") != "system":
        context.messages = [
            {"role": "system", "content": instructions}
        ] + context.messages
    elif not context.messages:
        context.messages = [
            {"role": "system", "content": instructions}
        ]
    
    return context


async def stream_step(
    context: ExecutionContext,
    model: Model
) -> AsyncIterator[ModelResponse]:
    """
    Stream responses from the model.
    
    Args:
        context: Execution context
        model: Model instance
    
    Yields:
        ModelResponse chunks
    """
    async for chunk in model.stream(
        messages=context.messages,
        tools=context.converted_tools,
        temperature=context.temperature,
        max_tokens=context.max_tokens
    ):
        yield chunk


async def invoke_step(
    context: ExecutionContext,
    model: Model,
    obs: Optional['Observability'] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None
) -> ModelResponse:
    """
    Invoke model and get complete response with tracing and metrics.
    
    Args:
        context: Execution context
        model: Model instance
        obs: Optional observability instance
        model_name: Model name for tracing
        provider: Model provider for tracing
    
    Returns:
        Complete ModelResponse
    """
    import time
    
    if obs and model_name and provider:
        # Use decorator properly - define function first, then decorate
        async def _invoke_with_trace():
            start_time = time.perf_counter()
            response = await model.invoke(
                messages=context.messages,
                tools=context.converted_tools,
                temperature=context.temperature,
                max_tokens=context.max_tokens
            )
            duration = time.perf_counter() - start_time
            
            # Record model usage metrics
            usage = response.usage or {}
            tokens_input = usage.get('tokens_in', 0)
            tokens_output = usage.get('tokens_out', 0)
            cost = usage.get('cost_usd', 0)
            
            obs.metrics.record_model_usage(
                model_name=model_name,
                provider=provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost,
                ttft_seconds=duration,
                status="success"
            )
            
            obs.logger.log_model_call(
                model_name=model_name,
                provider=provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost,
                duration_ms=int(duration * 1000)
            )
            
            return response
        
        # Apply decorator and call
        traced_func = obs.trace_model_call(model_name, provider)(_invoke_with_trace)
        return await traced_func()
    else:
        # No observability, just call model
        return await model.invoke(
            messages=context.messages,
            tools=context.converted_tools,
            temperature=context.temperature,
            max_tokens=context.max_tokens
        )


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    agent_tools: List[Any],
    obs: Optional['Observability'] = None
) -> Any:
    """
    Execute a tool call with tracing and metrics.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        agent_tools: Agent's tools list (e.g., [PythonTool(), HttpTool()])
        obs: Optional observability instance
    
    Returns:
        Tool execution result
    
    Raises:
        ValueError: If tool not found
    """
    import inspect
    import time
    
    # Find tool by name in the list
    tool_def = None
    for tool in agent_tools:
        # Check if tool is a dict with name key
        if isinstance(tool, dict):
            if tool.get("name") == tool_name:
                tool_def = tool
                break
        # Check if tool is a Tool object or has name attribute
        elif hasattr(tool, "name") and getattr(tool, "name") == tool_name:
            tool_def = tool
            break
    
    if tool_def is None:
        available_tools = []
        for tool in agent_tools:
            if isinstance(tool, dict):
                available_tools.append(tool.get("name", "unknown"))
            elif hasattr(tool, "name"):
                available_tools.append(getattr(tool, "name"))
        raise ValueError(
            f"Tool '{tool_name}' not found in agent tools. "
            f"Available tools: {available_tools}"
        )
    
    async def _execute_internal():
        # Handle Tool object (from @tool decorator)
        if hasattr(tool_def, "invoke") and callable(tool_def.invoke):
            invoke_func = tool_def.invoke
            if inspect.iscoroutinefunction(invoke_func):
                return await invoke_func(**arguments)
            else:
                return invoke_func(**arguments)
        
        # Handle tool dict structure: {"name": "...", "invoke": callable}
        if isinstance(tool_def, dict):
            # Check if tool has invoke function
            if "invoke" in tool_def:
                invoke_func = tool_def["invoke"]
                if inspect.iscoroutinefunction(invoke_func):
                    return await invoke_func(**arguments)
                else:
                    return invoke_func(**arguments)
            else:
                raise ValueError(f"Tool '{tool_name}' dict must have 'invoke' key")
        
        # Handle direct callable
        if callable(tool_def):
            if inspect.iscoroutinefunction(tool_def):
                return await tool_def(**arguments)
            else:
                return tool_def(**arguments)
        
        raise ValueError(f"Tool '{tool_name}' is not callable or doesn't have invoke method")
    
    # Trace tool call if observability is available
    if obs:
        @obs.trace_tool_call(tool_name)
        async def _execute_with_trace():
            start_time = time.perf_counter()
            try:
                result = await _execute_internal()
                duration = time.perf_counter() - start_time
                
                # Record metrics
                obs.metrics.record_tool_call(
                    tool_name=tool_name,
                    duration_seconds=duration,
                    status="success"
                )
                
                obs.logger.log_tool_call(
                    tool_name=tool_name,
                    duration_ms=int(duration * 1000),
                    status="success"
                )
                
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                obs.metrics.record_tool_call(
                    tool_name=tool_name,
                    duration_seconds=duration,
                    status="error"
                )
                obs.logger.error(f"Tool call failed: {tool_name}", exception=e)
                raise
        
        return await _execute_with_trace()
    else:
        return await _execute_internal()


async def map_results_step(
    context: ExecutionContext,
    response: ModelResponse,
    agent_tools: List[Any],
    obs: Optional['Observability'] = None,
    max_tool_iterations: int = 3
) -> ModelResponse:
    """
    Map model results and handle tool calls if any.
    
    For MVP, we handle tool calls in a simple loop.
    
    Args:
        context: Execution context
        response: Model response
        agent_tools: Agent's tools dictionary
        max_tool_iterations: Maximum tool call iterations
    
    Returns:
        Final ModelResponse after tool execution
    """
    # If no tool calls, return response as-is
    if not response.tool_calls:
        return response
    
    # Handle tool calls (simple loop for MVP)
    iterations = 0
    current_response = response
    
    while current_response.tool_calls and iterations < max_tool_iterations:
        iterations += 1
        
        # Execute all tool calls
        tool_results = []
        for tool_call in current_response.tool_calls:
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("arguments", {})
            
            try:
                result = await execute_tool(tool_name, arguments, agent_tools, obs)
                tool_results.append({
                    "tool": tool_name,
                    "result": result
                })
            except Exception as e:
                tool_results.append({
                    "tool": tool_name,
                    "error": str(e)
                })
        
        # Add tool results to messages
        tool_message = {
            "role": "user",
            "content": f"Tool execution results: {tool_results}"
        }
        context.messages.append(tool_message)
        
        # Call model again with tool results
        from ..models.base import Model
        # We need the model instance - this will be passed from agent
        # For now, return response with tool calls
        # The agent will handle the loop
        
        context.tool_results.extend(tool_results)
        break  # For MVP, we do one iteration
    
    return current_response

