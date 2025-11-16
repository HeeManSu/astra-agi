"""
Agent class for Astra Framework.

Supports two initialization scenarios:
1. Independent: Agent(name="...", instructions="...", model={...})
2. Through Astra: Astra({'agents': [Agent(...)]})
"""
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Union, TYPE_CHECKING
from observability import Observability
from ..astra import FrameworkSettings, DependencyContainer
from .types import AgentConfig, ModelConfig
from .execution import (
    ExecutionContext,
    prepare_tools_step,
    prepare_memory_step,
    stream_step,
    invoke_step,
    map_results_step,
    execute_tool
)

if TYPE_CHECKING:
    from ..astra import Astra
    from ..models.base import Model


class Agent:
    """
    The Agent class is the foundation for creating AI agents in Astra.
    
    It provides initialization with basic properties: id, name, description,
    instructions, model, tools, and max_retries.
    
    Example:
        ```python
        agent = Agent(
            id='my-agent',
            name='My Agent',
            instructions='You are a helpful assistant',
            model={'provider': 'google', 'model': 'gemini-2.5-flash'},
            tools=[calculator_tool],
        )
        ```
    """
    
    def __init__(
        self,
        name: str,
        instructions: str,
        model: Union[ModelConfig, Dict[str, Any], str],
        id: Optional[str] = None,
        description: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        max_retries: int = 0,
        astra_instance: Optional['Astra'] = None
    ):
        """
        Initialize an Agent with the provided configuration.
        
        Initialization Flow:
        1. If astra_instance is provided: Share Astra's settings and dependencies (no duplication)
        2. If standalone: Create own settings and dependencies (will initialize observability in startup)
        
        Args:
            name: Agent name (required)
            instructions: Agent instructions (required)
            model: Model configuration - dict with 'provider' and 'model', or string like 'google/gemini-2.5-flash' (required)
            id: Optional agent ID (auto-generated if not provided)
            description: Optional agent description
            tools: Optional list of tools
            max_retries: Maximum retry attempts (default: 0)
            astra_instance: Optional Astra instance (if provided, shares resources to avoid duplication)
        
        Raises:
            ValueError: If model is not provided or invalid
        """
        # Share resources with Astra if provided (avoid duplication)
        # Otherwise, create standalone resources
        if astra_instance:
            # Use Astra's settings and dependencies (shared resources)
            self.settings = astra_instance.settings
            self.dependencies = astra_instance.dependencies
            self._astra = astra_instance
        else:
            # Standalone agent: create own resources
            self.settings = FrameworkSettings()
            self.dependencies = DependencyContainer()
            self._astra = None
        
        self._initialized = False
        
        # Set required properties
        self.name: str = name
        # Generate unique id if not provided to ensure uniqueness across all agents
        # Format: "agent-{uuid4}" for better readability and uniqueness
        self.id: str = id or f"agent-{uuid.uuid4().hex[:8]}"
        self.instructions: str = instructions
        
        # Optional properties
        self.description: Optional[str] = description
        self.max_retries: int = max_retries
        # Tools are stored as a list (e.g., [PythonTool(), HttpTool()])
        self.tools: List[Any] = tools or []
        
        # Normalize model configuration
        if isinstance(model, str):
            # Simple string format: "provider/model" or just "model"
            parts = model.split('/', 1)
            if len(parts) == 2:
                self.model: ModelConfig = {
                    'provider': parts[0],
                    'model': parts[1]
                }
            else:
                # Default provider assumption (can be made configurable)
                self.model: ModelConfig = {
                    'provider': 'openai',  # Default, can be overridden
                    'model': parts[0]
                }
        elif isinstance(model, dict):
            self.model: ModelConfig = model
        else:
            raise ValueError(
                f"Invalid model configuration for agent '{self.name}'. "
                f"Expected string or dict, got {type(model)}"
            )
        
        # Logger will be initialized lazily when first accessed
        self._logger: Optional[Any] = None
        
        # Model instance (will be initialized when needed)
        self._model_instance: Optional['Model'] = None
    
    async def startup(self) -> None:
        """
        Initialize agent components.
        
        Initialization Flow:
        1. If registered with Astra: Observability already initialized, just mark as initialized
        2. If standalone: Initialize own observability (only if not already initialized)
        
        Note: Settings and dependencies are already shared/created in __init__,
        so this method only handles observability initialization for standalone agents.
        """
        if self._initialized:
            return
        
        # If registered with Astra, observability is already initialized by Astra
        # Just ensure dependencies are synced (should already be done in _register_astra)
        if self._astra:
            # Ensure we're using Astra's dependencies (should already be set in _register_astra)
            if self.dependencies is not self._astra.dependencies:
                self.dependencies = self._astra.dependencies
        elif not self.dependencies.observability:
            # Standalone agent: initialize our own observability
            self.dependencies.observability = Observability.init(
                service_name=self.settings.service_name,
                log_level=self.settings.observability_log_level,
                enable_json_logs=True,
                log_file=self.settings.observability_log_file
            )
        
        self._initialized = True
    
    async def shutdown(self) -> None:
        """
        Cleanup agent components.
        
        If the agent is registered with Astra, observability shutdown is handled by Astra.
        Only standalone agents need to shutdown their own observability.
        """
        # Only shutdown observability if this is a standalone agent (not registered with Astra)
        # Agents registered with Astra will have their observability shutdown by Astra.shutdown()
        if not self._astra and self.dependencies.observability:
            self.dependencies.observability.shutdown()
        
        self._initialized = False
    
    def get_astra_instance(self) -> Optional['Astra']:
        """Get the Astra instance this agent is registered with."""
        return self._astra
    
    def _register_astra(self, astra_instance: 'Astra') -> None:
        """
        Register this agent with an Astra instance.
        Called internally by Astra when agent is added.
        
        This method shares Astra's settings and dependencies to avoid duplication.
        If agent was created standalone, it will now use Astra's resources.
        """
        self._astra = astra_instance
        # Share Astra's settings and dependencies (avoid duplication)
        self.settings = astra_instance.settings
        self.dependencies = astra_instance.dependencies
    
    @property
    def logger(self) -> Any:
        """Get logger instance (lazy initialization)."""
        if self._logger is None:
            if self.dependencies.observability:
                # Use observability logger directly (composition pattern)
                self._logger = self.dependencies.observability.logger
            else:
                # Fallback logger if observability not initialized
                import logging
                self._logger = logging.getLogger(f"agent.{self.name}")
        return self._logger
    
    def _get_model_instance(self) -> 'Model':
        """
        Get or create model instance.
        
        Returns:
            Model instance
        
        Raises:
            ValueError: If model provider not supported
        """
        if self._model_instance is not None:
            return self._model_instance
        
        # Import model classes
        from ..models import GeminiFlash, GeminiPro
        
        # Get model config
        if not isinstance(self.model, dict):
            raise ValueError(f"Invalid model configuration for agent '{self.name}'")
        
        provider = self.model.get('provider', '').lower()
        model_id = self.model.get('model', '')
        api_key = self.model.get('api_key')
        
        # Initialize model based on provider
        if provider == 'google':
            if 'flash' in model_id.lower():
                # Use GeminiFlash for all flash models (1.5-flash, 2.5-flash, etc.)
                self._model_instance = GeminiFlash(api_key=api_key, model_id=model_id)
            elif model_id == 'gemini-1.5-pro' or model_id == 'gemini-pro' or 'pro' in model_id.lower():
                # Use GeminiPro - pass model_id to allow it to use the correct one
                self._model_instance = GeminiPro(api_key=api_key, model_id=model_id)
            else:
                # Default to Flash for unknown models
                self._model_instance = GeminiFlash(api_key=api_key, model_id=model_id)
        else:
            raise ValueError(
                f"Unsupported model provider '{provider}' for agent '{self.name}'. "
                f"Supported providers: google"
            )
        
        return self._model_instance
    
    async def invoke(
        self,
        messages: Union[str, List[Dict[str, str]]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Invoke agent with tracing and metrics.
        
        This method is automatically traced and metrics are recorded.
        """
        import time
        start_time = time.perf_counter()
        
        # Ensure observability is initialized
        await self.startup()
        obs = self.dependencies.observability
        
        # Trace agent run
        @obs.trace_agent_run(self.id)
        async def _invoke_internal():
            obs.logger.log_agent_start(
                agent_id=self.id,
                session_id=kwargs.get('session_id'),
                request_id=kwargs.get('request_id')
            )
        """
        Invoke agent and return complete response.
        
        Args:
            messages: User message(s) - can be string or list of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional options
        
        Returns:
            Dict with:
            - content: str - Generated response
            - tool_calls: List[Dict] - Tool calls if any
            - usage: Dict - Token usage
            - metadata: Dict - Additional metadata
        
        Example:
            ```python
            response = await agent.invoke("What is the weather?")
            print(response['content'])
            ```
        """
        # Normalize messages
        if isinstance(messages, str):
            messages_list = [{"role": "user", "content": messages}]
        else:
            messages_list = messages
        
        # Ensure observability is initialized
        await self.startup()
        obs = self.dependencies.observability
        
        # Trace agent run
        @obs.trace_agent_run(self.id)
        async def _invoke_internal():
            obs.logger.log_agent_start(
                agent_id=self.id,
                session_id=kwargs.get('session_id'),
                request_id=kwargs.get('request_id')
            )
            
            # Create execution context
            context = ExecutionContext(
                messages=messages_list,
                tools=self.tools,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Execute steps
            # Step 1: Prepare memory (add instructions)
            context = await prepare_memory_step(context, self.instructions, obs)
            
            # Step 2: Prepare tools
            context = await prepare_tools_step(context, self.tools, obs)
            
            # Step 3: Get model instance
            model = self._get_model_instance()
            model_name = getattr(model, 'model_id', 'unknown')
            provider = 'google'  # Default for now
            
            # Step 4: Invoke model with tracing
            response = await invoke_step(context, model, obs, model_name, provider)
            if response is None:
                raise ValueError("Model invocation returned None")
            
            # Step 5: Handle tool calls if any
            original_tool_calls = response.tool_calls  # Preserve original tool calls
            
            if response.tool_calls:
                # For MVP, handle one iteration of tool calls
                final_response = await map_results_step(
                    context, response, self.tools, obs, max_tool_iterations=1
                )
                
                # If we have tool results, call model again
                if context.tool_results:
                    # Add tool results to messages
                    tool_message = {
                        "role": "user",
                        "content": f"Tool results: {context.tool_results}"
                    }
                    context.messages.append(tool_message)
                    
                    # Call model again with tracing
                    final_response = await invoke_step(context, model, obs, model_name, provider)
            else:
                final_response = response
            
            # Preserve original tool calls in the response (even after execution)
            return {
                "content": final_response.content,
                "tool_calls": original_tool_calls,  # Return original tool calls, not final response's
                "usage": final_response.usage,
                "metadata": final_response.metadata,
            }
        
        try:
            result = await _invoke_internal()
            duration = time.perf_counter() - start_time
            
            # Record metrics
            obs.metrics.record_agent_run(
                agent_id=self.id,
                duration_seconds=duration,
                status="success"
            )
            
            obs.logger.log_agent_complete(
                agent_id=self.id,
                duration_ms=int(duration * 1000),
                session_id=kwargs.get('session_id'),
                request_id=kwargs.get('request_id')
            )
            
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            obs.metrics.record_agent_run(
                agent_id=self.id,
                duration_seconds=duration,
                status="error"
            )
            obs.logger.error("Agent run failed", exception=e, agent_id=self.id)
            raise
    
    async def stream(
        self,
        messages: Union[str, List[Dict[str, str]]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent responses with tool call execution support.
        
        Args:
            messages: User message(s) - can be string or list of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional options
        
        Yields:
            Dict chunks with:
            - content: str - Incremental content
            - tool_calls: List[Dict] - Tool calls if any
            - usage: Dict - Token usage (may be empty during streaming)
            - metadata: Dict - Additional metadata
        
        Example:
            ```python
            async for chunk in agent.stream("Tell me a story"):
                print(chunk['content'], end='', flush=True)
            ```
        """
        # Normalize messages
        if isinstance(messages, str):
            messages_list = [{"role": "user", "content": messages}]
        else:
            messages_list = messages
        
        # Ensure observability is initialized
        await self.startup()
        obs = self.dependencies.observability
        
        # Create execution context
        context = ExecutionContext(
            messages=messages_list,
            tools=self.tools,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Execute steps
        # Step 1: Prepare memory (add instructions)
        context = await prepare_memory_step(context, self.instructions, obs)
        
        # Step 2: Prepare tools
        context = await prepare_tools_step(context, self.tools, obs)
        
        # Step 3: Get model instance
        model = self._get_model_instance()
        model_name = getattr(model, 'model_id', 'unknown')
        provider = 'google'  # Default for now
        
        # Step 4: Stream initial response and detect tool calls
        # We stream chunks as they arrive, but track if tool calls are present
        has_tool_calls = False
        final_response = None
        all_tool_calls = []
        
        async for chunk in stream_step(context, model):
            # Yield chunks immediately for true streaming
            yield {
                "content": chunk.content,
                "tool_calls": chunk.tool_calls,
                "usage": chunk.usage,
                "metadata": chunk.metadata,
            }
            
            # Track tool calls and final response
            if chunk.tool_calls:
                has_tool_calls = True
                # Collect all tool calls (they might be in different chunks)
                all_tool_calls.extend(chunk.tool_calls)
            # Keep track of the last chunk for final response
            final_response = chunk
        
        # Step 5: Handle tool calls if any (similar to invoke method)
        if has_tool_calls and all_tool_calls:
            # Execute tools
            tool_results = []
            for tool_call in all_tool_calls:
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("arguments", {})
                
                try:
                    result = await execute_tool(tool_name, arguments, self.tools, obs)
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
            context.tool_results.extend(tool_results)
            
            # Step 7: Stream final response with tool results
            async for chunk in stream_step(context, model):
                yield {
                    "content": chunk.content,
                    "tool_calls": [],  # No tool calls in final response
                    "usage": chunk.usage,
                    "metadata": chunk.metadata,
                }
    
    def list_tools(self) -> List[Any]:
        """List all tools available to this agent."""
        return self.tools.copy()
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        model_name = self.model.get('model', 'unknown') if isinstance(self.model, dict) else str(self.model)
        return f"Agent(id='{self.id}', name='{self.name}', model={model_name})"

