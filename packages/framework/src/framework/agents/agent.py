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
from typing import Any, AsyncIterator, Dict, List, Optional, Union, TYPE_CHECKING, Callable

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
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        context_window_size: int = 10,
        enable_summary: bool = False,
        input_middlewares: Optional[Union[List[Any], 'Callable']] = None,
        output_middlewares: Optional[Union[List[Any], 'Callable']] = None,
        guardrails: Optional[Dict[str, Any]] = None,
        output_format: Optional[Any] = None,
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
            storage: Optional storage backend (e.g., SQLiteStorage)
            knowledge: Optional knowledge base (e.g., PDFKnowledgeBase)
            max_retries: Maximum retry attempts for failed requests (default: 3)
            temperature: Sampling temperature for model responses (default: 0.7, range: 0.0-2.0)
            max_tokens: Maximum tokens to generate per response (default: 4096)
            stream: Whether to stream responses by default (default: False)
            context_window_size: Number of recent messages to keep in context (default: 10)
                                 Higher = more context but more tokens
            enable_summary: Whether to summarize old messages instead of dropping them (default: False)
                           When True, messages beyond context_window_size are summarized
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
        self.temperature: float = temperature
        self.max_tokens: int = max_tokens
        self.streaming_enabled: bool = stream
        self.context_window_size: int = context_window_size
        self.enable_summary: bool = enable_summary
        
        # Conversation manager for short-term memory (context window management)
        from .conversation import ConversationManager
        self.conversation = ConversationManager(
            max_messages=self.context_window_size,
            enable_summary=self.enable_summary
        )
        
        # Dynamic resources
        self.tools: List[Any] = tools or []
        self.storage: Optional[Any] = storage
        self.knowledge: Optional[Any] = knowledge
        
        # Process guardrails (convenience API)
        # Guardrails can be specified via 'guardrails' dict OR 'input_middlewares'/'output_middlewares'
        if guardrails:
            input_guards = guardrails.get('input', [])
            output_guards = guardrails.get('output', [])
            schema_guard = guardrails.get('schema')
            
            # Combine with existing middlewares
            input_list = input_middlewares if isinstance(input_middlewares, list) else (input_middlewares or [])
            output_list = output_middlewares if isinstance(output_middlewares, list) else (output_middlewares or [])
            
            # Add guardrails to middleware lists
            if isinstance(input_guards, list):
                input_list = input_guards + (input_list if isinstance(input_list, list) else [])
            if isinstance(output_guards, list):
                output_list = output_guards + (output_list if isinstance(output_list, list) else [])
            if schema_guard:
                output_list = (output_list if isinstance(output_list, list) else []) + [schema_guard]
            
            self._input_middlewares = input_list if input_list else input_middlewares
            self._output_middlewares = output_list if output_list else output_middlewares
        else:
            # Middlewares (can be static list or callable for dynamic resolution)
            self._input_middlewares = input_middlewares
            self._output_middlewares = output_middlewares
        
        # Output format for structured outputs
        self.output_format: Optional[Any] = output_format
        
        # HIL (Human-in-the-Loop) manager - initialized lazily
        self._hil: Optional[Any] = None
        self._hil_initialized: bool = False
        
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
    
    @property
    def hil(self) -> Optional[Any]:
        """
        Get HIL manager (lazy initialization).
        
        HIL is only available if storage is configured.
        """
        if not self._hil_initialized:
            self._hil_initialized = True
            if self.storage:
                try:
                    from ..HIL import HILManager, RunStateStorage  # type: ignore[import-untyped]
                    self._hil = HILManager(RunStateStorage(self.storage))
                except ImportError:
                    # HIL module not available
                    self._hil = None
            else:
                self._hil = None
        return self._hil

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
        
        # Initialize MCP tools if present
        # We iterate through tools to find MCPTools instances
        # and replace them with the actual tools they provide
        new_tools = []
        mcp_initialized = False
        
        for tool in self.tools:
            # Check if it's an MCPTools instance (using class name check to avoid import if possible, or import inside)
            if hasattr(tool, 'initialize') and hasattr(tool, '_detect_collisions'):
                # It's likely MCPTools
                try:
                    # Get existing tool names for collision detection
                    existing_names = [t.name for t in new_tools if hasattr(t, 'name')]
                    
                    # Initialize and get tools
                    mcp_tools = await tool.initialize(existing_names)
                    new_tools.extend(mcp_tools)
                    mcp_initialized = True
                except Exception as e:
                    self.logger.error(f"Failed to initialize MCP tool: {e}")
                    # Keep the original object if initialization fails? Or skip?
                    # Skipping prevents broken tools from blocking agent
                    pass
            else:
                new_tools.append(tool)
        
        if mcp_initialized:
            self.tools = new_tools
            
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
    
    def _resolve_middlewares(
        self,
        middlewares: Optional[Union[List[Any], Callable]],
        context: Any
    ) -> List[Any]:
        """
        Resolve middlewares (supports static list or callable).
        
        Args:
            middlewares: Static list or callable that returns list
            context: Middleware context for dynamic resolution
            
        Returns:
            List of middleware instances
        """
        if middlewares is None:
            return []
        
        # If callable, call it with context to get dynamic list
        if callable(middlewares):
            return middlewares(context)
        
        # Otherwise return static list
        return middlewares
    
    async def _run_input_middlewares(
        self,
        messages: List[Dict[str, str]],
        context: Any
    ) -> List[Dict[str, str]]:
        """
        Run input middlewares sequentially.
        
        Args:
            messages: Input messages
            context: Middleware context
            
        Returns:
            Modified messages
            
        Raises:
            InputValidationError: If validation fails
            MiddlewareAbortError: If middleware aborts
        """
        from ..middlewares import InputMiddleware
        from ..middlewares.exceptions import MiddlewareError
        
        middlewares = self._resolve_middlewares(self._input_middlewares, context)
        current_messages = messages
        
        for middleware in middlewares:
            if not isinstance(middleware, InputMiddleware):
                self.logger.warning(
                    f"Skipping non-InputMiddleware: {type(middleware).__name__}"
                )
                continue
            
            try:
                current_messages = await middleware.process(current_messages, context)
            except MiddlewareError as e:
                # Check if this is a guardrail violation (special logging)
                from ..guardrails.exceptions import GuardrailError
                
                if isinstance(e, GuardrailError):
                    self.logger.error(
                        f"🛡️ GUARDRAIL VIOLATION: {type(middleware).__name__}",
                        error=str(e),
                        middleware=type(middleware).__name__,
                        guardrail_type="input",
                        violation_type=type(e).__name__
                    )
                else:
                    # Log regular middleware errors
                    self.logger.error(
                        f"Input middleware {type(middleware).__name__} failed",
                        error=str(e),
                        middleware=type(middleware).__name__
                    )
                raise
            except Exception as e:
                # Log unexpected errors
                self.logger.error(
                    f"Unexpected error in input middleware {type(middleware).__name__}",
                    error=str(e),
                    middleware=type(middleware).__name__
                )
                raise
        
        return current_messages
    
    async def _run_output_middlewares(
        self,
        output: str,
        context: Any
    ) -> str:
        """
        Run output middlewares sequentially.
        
        Args:
            output: LLM output
            context: Middleware context
            
        Returns:
            Modified output
            
        Raises:
            OutputValidationError: If validation fails
            MiddlewareAbortError: If middleware aborts
        """
        from ..middlewares import OutputMiddleware
        from ..middlewares.exceptions import MiddlewareError
        
        middlewares = self._resolve_middlewares(self._output_middlewares, context)
        current_output = output
        
        for middleware in middlewares:
            if not isinstance(middleware, OutputMiddleware):
                self.logger.warning(
                    f"Skipping non-OutputMiddleware: {type(middleware).__name__}"
                )
                continue
            
            try:
                current_output = await middleware.process(current_output, context)
            except MiddlewareError as e:
                # Check if this is a guardrail violation (special logging)
                from ..guardrails.exceptions import GuardrailError
                
                if isinstance(e, GuardrailError):
                    self.logger.error(
                        f"🛡️ GUARDRAIL VIOLATION: {type(middleware).__name__}",
                        error=str(e),
                        middleware=type(middleware).__name__,
                        guardrail_type="output",
                        violation_type=type(e).__name__
                    )
                else:
                    # Log regular middleware errors
                    self.logger.error(
                        f"Output middleware {type(middleware).__name__} failed",
                        error=str(e),
                        middleware=type(middleware).__name__
                    )
                raise
            except Exception as e:
                # Log unexpected errors
                self.logger.error(
                    f"Unexpected error in output middleware {type(middleware).__name__}",
                    error=str(e),
                    middleware=type(middleware).__name__
                )
                raise
        
        return current_output
    
    async def resume(
        self,
        run_id: str,
        decision: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resume a paused run (HIL).
        
        This method continues execution from where it was paused by:
        1. Loading the saved execution context
        2. Processing the resume data (approval decision, suspension data, or external result)
        3. Continuing the agent loop with the tool result
        
        Args:
            run_id: Run ID to resume
            decision: Decision for approval ("approve" or "decline")
            data: Input data for suspension
            result: Tool result for external execution
            
        Returns:
            Response dict with execution result
            
        Example:
            # Resume after approval
            await agent.resume(run_id, decision="approve")
            
            # Resume after suspension with data
            await agent.resume(run_id, data={"otp": "123456"})
            
            # Resume after external execution
            await agent.resume(run_id, result={"stdout": "success"})
        """
        from ..HIL import ResumeData, PauseReason, HILNotEnabledError  # type: ignore[import-untyped]
        
        if not self.hil:
            raise HILNotEnabledError("HIL not enabled (storage required)")
            
        resume_data = ResumeData(
            decision=decision,
            data=data,
            result=result
        )
        
        # Resume the run (updates state to RUNNING)
        resume_result = await self.hil.resume(run_id, resume_data)
        
        # Get run state with execution context
        run_state = await self.hil.storage.get(run_id)
        
        if not run_state or not run_state.execution_context:
            raise ValueError(f"Run {run_id} has no execution context")
        
        # Extract saved context
        ctx = run_state.execution_context
        messages = ctx.get("messages", [])
        pause_reason = run_state.pause_reason
        pause_data = run_state.pause_data or {}
        
        # Handle different pause reasons
        if pause_reason == PauseReason.APPROVAL:
            # Tool approval flow
            if decision == "decline":
                # User declined - skip tool and return
                await self.hil.complete_run(run_id)
                return {
                    "run_id": run_id,
                    "content": "Tool execution declined by user.",
                    "tool_calls": [],
                    "usage": {},
                    "metadata": {"declined": True}
                }
            elif decision == "approve":
                # User approved - execute the tool
                tool_call_data = pause_data.get("tool_call", {})
                # For now, return approval confirmation
                # Full tool execution would happen here
                await self.hil.complete_run(run_id)
                return {
                    "run_id": run_id,
                    "content": f"Tool {tool_call_data.get('name')} approved and would execute here.",
                    "tool_calls": [tool_call_data],
                    "usage": {},
                    "metadata": {"approved": True}
                }
                
        elif pause_reason == PauseReason.SUSPENSION:
            # Tool suspension flow - tool needs data to continue
            if not data:
                raise ValueError("Suspension requires 'data' parameter")
            # Tool would continue with provided data
            await self.hil.complete_run(run_id)
            return {
                "run_id": run_id,
                "content": f"Tool resumed with data: {data}",
                "tool_calls": [],
                "usage": {},
                "metadata": {"suspension_data": data}
            }
            
        elif pause_reason == PauseReason.EXTERNAL:
            # External execution flow - tool was executed externally
            if not result:
                raise ValueError("External execution requires 'result' parameter")
            # Use the external result
            await self.hil.complete_run(run_id)
            return {
                "run_id": run_id,
                "content": f"External tool result: {result}",
                "tool_calls": [],
                "usage": {},
                "metadata": {"external_result": result}
            }
        
        # Fallback
        await self.hil.complete_run(run_id)
        return {
            "run_id": run_id,
            "resumed": True,
            "result": resume_result.result
        }
    
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
        thread_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Invoke agent with tracing and metrics.
        
        This method is automatically traced and metrics are recorded.
        
        Args:
            messages: User message(s) - can be string or list of message dicts
            thread_id: Optional thread ID for conversation continuity
                      If provided, loads recent context from storage
            temperature: Sampling temperature (uses agent default if not provided)
            max_tokens: Maximum tokens to generate (uses agent default if not provided)
            **kwargs: Additional options
        
        Returns:
            Dict with:
            - content: str - Generated response
            - tool_calls: List[Dict] - Tool calls if any
            - usage: Dict - Token usage
            - metadata: Dict - Additional metadata
            
        Example:
            # Stateless (no context)
            response = await agent.invoke("Hello")
            
            # Stateful (with context from previous turns)
            response = await agent.invoke("Hello", thread_id="thread-123")
            response = await agent.invoke("How are you?", thread_id="thread-123")
        """
        # Use instance defaults if not provided
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        start_time = time.perf_counter()
        
        # Ensure observability is initialized
        await self.startup()
        obs = self.context.observability
        
        # Normalize messages to list format
        if isinstance(messages, str):
            current_message = messages
            messages_list = [{"role": "user", "content": messages}]
        else:
            messages_list = messages
            current_message = messages[-1].get("content", "") if messages else ""
            
        # Load conversation context if thread_id provided and storage available
        # KEY OPTIMIZATION: Only load last N messages, not full history!
        if thread_id and self.memory:
            context_messages = await self.conversation.get_context(thread_id, self.memory)
            # Prepend context to current messages
            messages_list = context_messages + messages_list
        
        # Create middleware context
        from ..middlewares import MiddlewareContext
        
        run_id = kwargs.get('run_id', f"run-{uuid.uuid4().hex[:8]}")
        middleware_ctx = MiddlewareContext(
            run_id=run_id,
            agent_id=self.id,
            thread_id=thread_id,
            metadata=kwargs.get('metadata', {}),
            tools=self.tools
        )
        
        # Run input middlewares FIRST (before any execution)
        messages_list = await self._run_input_middlewares(messages_list, middleware_ctx)
        
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
            if self.memory and self.storage:
                # Ensure storage is connected
                await self.storage.connect()
                
                # Use provided thread_id or fallback to agent ID
                save_thread_id = thread_id or self.id
                
                # Save user message
                await self.memory.add_message(
                    thread_id=save_thread_id,
                    role="user",
                    content=current_message
                )
                
                # Save assistant response
                await self.memory.add_message(
                    thread_id=save_thread_id,
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
        
        # Execute internal invoke
        response = await _invoke_internal()
        
        # Run output middlewares LAST (after all execution)
        if response.get("content"):
            response["content"] = await self._run_output_middlewares(
                response["content"],
                middleware_ctx
            )
        
        try:
            result = response # Use the response after middleware processing
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
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent responses with tool call execution support.
        
        Args:
            messages: User message(s) - can be string or list of message dicts
            temperature: Sampling temperature (uses agent default if not provided)
            max_tokens: Maximum tokens to generate (uses agent default if not provided)
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
        # Use instance defaults if not provided
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        # Normalize messages
        if isinstance(messages, str):
            messages_list = [{"role": "user", "content": messages}]
        else:
            messages_list = messages
        
        # Ensure observability is initialized
        await self.startup()
        obs = self.context.observability
        
        # Create middleware context
        from ..middlewares import MiddlewareContext, StreamingOutputMiddleware
        
        run_id = kwargs.get('run_id', f"run-{uuid.uuid4().hex[:8]}")
        middleware_ctx = MiddlewareContext(
            run_id=run_id,
            agent_id=self.id,
            thread_id=kwargs.get('thread_id'),
            metadata=kwargs.get('metadata', {}),
            tools=self.tools
        )
        
        # Run input middlewares FIRST (before streaming)
        messages_list = await self._run_input_middlewares(messages_list, middleware_ctx)
            
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
        
        # Get streaming middlewares
        middlewares = self._resolve_middlewares(self._output_middlewares, middleware_ctx)
        streaming_middlewares = [
            m for m in middlewares
            if isinstance(m, StreamingOutputMiddleware)
        ]
        
        async for chunk in stream_step(context, model):
            # Process chunk through streaming middlewares
            processed_content = chunk.content
            
            for middleware in streaming_middlewares:
                try:
                    processed_content = await middleware.on_chunk(
                        processed_content,
                        middleware_ctx
                    )
                    if processed_content is None:
                        # Middleware wants to skip this chunk
                        break
                except Exception as e:
                    self.logger.error(
                        f"Streaming middleware {type(middleware).__name__} failed",
                        error=str(e)
                    )
                    raise
            
            # Only yield if chunk wasn't filtered out
            if processed_content is not None:
                yield {
                    "content": processed_content,
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
        
        # Call on_complete for streaming middlewares
        for middleware in streaming_middlewares:
            try:
                final_chunk = await middleware.on_complete(middleware_ctx)
                if final_chunk:
                    yield {
                        "content": final_chunk,
                        "tool_calls": [],
                        "usage": {},
                        "metadata": {},
                    }
            except Exception as e:
                self.logger.error(
                    f"Streaming middleware on_complete {type(middleware).__name__} failed",
                    error=str(e)
                )
        
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
            if self.memory and self.storage:
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
