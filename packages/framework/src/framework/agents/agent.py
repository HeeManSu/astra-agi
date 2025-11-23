"""
Agent class for Astra Framework.

The Agent class is the core abstraction for creating AI agents. It supports:
- Standalone mode: Agent creates its own infrastructure (AstraContext)
- Managed mode: Agent shares infrastructure from Astra orchestrator
- Lazy initialization: Resources initialized only when needed
- Model abstraction: Supports multiple LLM providers via factory pattern
- Tool execution: Automatic tool calling and result handling
- Observability: Built-in tracing, metrics, and logging

Initialization Scenarios:
1. Standalone: Agent(name="...", instructions="...", model="...")
   - Creates own AstraContext with observability
   - Suitable for single-agent applications
   
2. Managed: Astra.add_agent(Agent(...))
   - Shares AstraContext from Astra orchestrator
   - Suitable for multi-agent systems
   - Avoids resource duplication

Example:
    # Standalone agent
    agent = Agent(
        name="Assistant",
        instructions="You are helpful",
        model="google/gemini-1.5-flash",
        tools=[calculator]
    )
    response = await agent.invoke("What is 2+2?")
"""
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Union, TYPE_CHECKING

from ..astra import AstraContext
from .types import ModelConfig
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
        name: str = "Agent",
        instructions: str = "You are a helpful assistant.",
        model: Union[ModelConfig, Dict[str, Any], str, 'Model'] = "google/gemini-1.5-flash",
        id: Optional[str] = None,
        description: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        storage: Optional[Any] = None,
        knowledge: Optional[Any] = None,
        max_retries: int = 0,
    ):
        """
        Initialize an Agent with the provided configuration.
        
        **Initialization Patterns**:
        
        1. **Explicit Model Class** (Recommended):
           ```python
           from framework.models import Gemini
           agent = Agent(name="Bot", model=Gemini("1.5-flash"))
           ```
           
        2. **String Configuration** (Alternative):
           ```python
           agent = Agent(name="Bot", model="google/gemini-1.5-flash")
           ```
        
        Args:
            name: Agent name (required)
            instructions: Agent instructions (required)
            model: Model instance (e.g., Gemini(...)) or config string/dict
            id: Optional agent ID (auto-generated if not provided)
            description: Optional agent description
            tools: Optional list of tools
            storage: Optional storage backend (e.g., PostgresStorage)
            knowledge: Optional knowledge base (e.g., PDFKnowledgeBase)
            max_retries: Maximum retry attempts (default: 0)
        """
        # Context will be injected by Astra or lazily initialized
        self._context: Optional[AstraContext] = None
        self._astra: Optional['Astra'] = None
        self._initialized = False
        
        # Set required properties
        self.name: str = name
        # Generate unique id if not provided to ensure uniqueness across all agents
        self.id: str = id or f"agent-{uuid.uuid4().hex[:8]}"
        self.instructions: str = instructions
        
        # Optional properties
        self.description: Optional[str] = description
        self.max_retries: int = max_retries
        
        # Dynamic resources
        self.tools: List[Any] = tools or []
        self.storage: Optional[Any] = storage
        self.knowledge: Optional[Any] = knowledge
        
        # Handle model configuration
        from ..models.base import Model
        
        if isinstance(model, Model):
            self._model_instance = model
            self.model = {'provider': 'custom', 'model': getattr(model, 'model_id', 'unknown')}
        elif isinstance(model, str):
            # Simple string format: "provider/model" or just "model"
            parts = model.split('/', 1)
            if len(parts) == 2:
                self.model = {'provider': parts[0], 'model': parts[1]}
            else:
                self.model = {'provider': 'openai', 'model': parts[0]}
            self._model_instance = None
        elif isinstance(model, dict):
            self.model = model
            self._model_instance = None
        else:
            raise ValueError(
                f"Invalid model configuration for agent '{self.name}'. "
                f"Expected Model instance, string, or dict, got {type(model)}"
            )
        
        # Logger will be initialized lazily when first accessed
        self._logger: Optional[Any] = None
        
        # Initialize memory if storage is provided
        self.memory = None
        if self.storage:
            self.set_storage(self.storage)
    
    @property
    def context(self) -> 'AstraContext':
        """
        Get agent context (infrastructure).
        
        Lazily initializes a default context if one hasn't been injected.
        This ensures the agent works in standalone mode.
        """
        if self._context is None:
            # Standalone mode: create default context
            self._context = AstraContext()
        return self._context

    def add_tool(self, tool: Any) -> None:
        """
        Add a tool to the agent dynamically.
        
        Args:
            tool: Tool function or object
        """
        self.tools.append(tool)
        
    def set_storage(self, storage: Any) -> None:
        """
        Set storage backend dynamically.
        
        Args:
            storage: Storage backend instance
        """
        self.storage = storage
        # Initialize memory facade
        from ..storage.memory import AgentMemory
        from ..storage.base import StorageBackend
        
        if isinstance(storage, StorageBackend):
            self.memory = AgentMemory(storage)
        else:
            self.memory = None
        
    def set_knowledge(self, knowledge: Any) -> None:
        """
        Set knowledge base dynamically.
        
        Args:
            knowledge: Knowledge base instance
        """
        self.knowledge = knowledge

    def set_context(self, context: 'AstraContext') -> None:
        """
        Inject context (called by Astra).
        
        Args:
            context: AstraContext instance
        """
        self._context = context

    async def startup(self) -> None:
        """
        Initialize agent components.
        
        Ensures context is ready.
        """
        if self._initialized:
            return
        
        # Accessing context property triggers lazy initialization if needed
        _ = self.context
        
        # Start memory system (queue worker)
        if self.memory:
            await self.memory.start()
        
        self._initialized = True
    
    async def shutdown(self) -> None:
        """
        Cleanup agent components.
        
        If the agent is registered with Astra, observability shutdown is handled by Astra.
        Only standalone agents need to shutdown their own observability.
        """
        if self.memory:
            await self.memory.stop()
            
        # Only shutdown context if we own it (standalone) or if explicitly requested
        # In managed mode, Astra handles shutdown
        if not self._astra and self._context:
            self._context.shutdown()
        
        self._initialized = False
    
    def get_astra_instance(self) -> Optional['Astra']:
        """Get the Astra instance this agent is registered with."""
        return self._astra
    
    def _register_astra(self, astra_instance: 'Astra') -> None:
        """
        Register this agent with an Astra instance.
        Called internally by Astra when agent is added.
        """
        self._astra = astra_instance
        # Context injection is now handled by set_context called by Astra
    
    @property
    def logger(self) -> Any:
        """Get logger instance (lazy initialization)."""
        if self._logger is None:
            # Get logger from context
            self._logger = self.context.logger
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
        from ..models import get_model
        
        # Get model config
        if not isinstance(self.model, dict):
            raise ValueError(f"Invalid model configuration for agent '{self.name}'")
        
        provider = self.model.get('provider', '').lower()
        model_id = self.model.get('model', '')
        api_key = self.model.get('api_key')
        
        # Use the model factory to create the appropriate model instance
        try:
            self._model_instance = get_model(provider, model_id, api_key)
        except Exception as e:
            raise ValueError(
                f"Failed to create model instance for provider '{provider}' with model '{model_id}': {e}"
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
        start_time = time.perf_counter()
        
        # Ensure observability is initialized
        await self.startup()
        obs = self.context.observability
        
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
        obs = self.context.observability
        
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
            
            # 5. Save interaction to storage if enabled
            if self.memory:
                # Ensure storage is connected
                await self.storage.connect()
                
                # Use agent ID as thread ID for now (or generate a session ID)
                thread_id = self.id
                
                # Save user message (first message)
                user_content = messages_list[0]['content'] if messages_list else ""
                await self.memory.add_message(
                    thread_id=thread_id,
                    role="user",
                    content=user_content
                )
                
                # Save assistant response
                await self.memory.add_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=final_response.content or ""
                )
            
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
        obs = self.context.observability
        
            
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
            
            # 5. Save interaction to storage if enabled
            if self.memory:
                print(f"DEBUG: Saving to memory for thread {self.id}")
                # Ensure storage is connected
                await self.storage.connect()
                
                # Use agent ID as thread ID for now (or generate a session ID)
                thread_id = self.id
                
                # Save user message (assuming the initial messages_list contains the user's input)
                # This part needs careful consideration as 'message' and 'response.text' are not directly available here.
                # For debugging persistence, we'll use a placeholder or the initial input.
                # For now, let's assume the first message in messages_list is the user's initial query.
                initial_user_message = messages_list[0]['content'] if messages_list else "No initial user message"
                await self.memory.add_message(
                    thread_id=thread_id,
                    role="user",
                    content=initial_user_message
                )
                print("DEBUG: Saved initial user message")
                
                # Save assistant response (this would typically be the final response content)
                # For streaming, the final_response.content would be the accumulated content.
                # If this block is meant for the invoke method, 'response.text' would be appropriate.
                # Here, we'll use a placeholder or the accumulated content from the stream.
                # This part of the debug code seems more suited for the invoke method's final response.
                # For stream, we'd save the final accumulated content.
                # Let's assume final_response.content holds the full response after tool execution.
                if final_response and final_response.content:
                    await self.memory.add_message(
                        thread_id=thread_id,
                        role="assistant",
                        content=final_response.content
                    )
                    print("DEBUG: Saved assistant message after tool execution")
                else:
                    print("DEBUG: No final assistant content to save after tool execution.")

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

