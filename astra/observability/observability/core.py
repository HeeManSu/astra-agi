"""
Main Observability facade for Astra.

This module provides a minimal facade using composition pattern.
Components (tracer, metrics, logger) are exposed directly for clean API.

Responsibilities:
- Initialize and configure all observability components
- Provide singleton pattern for convenience
- Manage component lifecycle and shutdown
- Expose components directly (composition over delegation)
"""

from threading import Lock
from typing import Optional

from .tracer import Tracer
from .metrics import MetricsRecorder
from .logger import Logger


class Observability:
    """
    Minimal observability facade using composition pattern.
    
    Components are exposed directly (obs.tracer, obs.metrics, obs.logger)
    rather than wrapping every method. This keeps the facade simple and
    maintainable while providing a single initialization point.
    
    Supports both singleton pattern (for convenience) and dependency injection
    (for testing and flexibility).
    """
    
    _instance: Optional["Observability"] = None
    _lock = Lock()
    
    def __init__(
        self, 
        service_name: str = "astra",
        log_level: str = "INFO",
        enable_json_logs: bool = True,
        log_file: Optional[str] = None
    ):
        """
        Initialize observability components.
        
        Args:
            service_name: Service name for all components
            log_level: Minimum log level (INFO, ERROR)
            enable_json_logs: Whether to use JSON formatting for logs
            log_file: Optional file path for log output
        """
        self.service_name = service_name
        
        # Initialize components - exposed directly via composition
        self.tracer = Tracer(
            service_name=service_name,
        )
        
        self.metrics = MetricsRecorder(
            service_name=service_name
        )
        
        self.logger = Logger(
            service_name=service_name,
            log_level=log_level,
            enable_json=enable_json_logs,
            log_file=log_file
        )
        
        # Log initialization
        self.logger.info(
            "Observability initialized",
            service=service_name,
            components=["tracer", "metrics", "logger"]
        )
    
    @classmethod
    def init(
        cls, 
        service_name: str = "astra",
        log_level: str = "INFO",
        enable_json_logs: bool = True,
        log_file: Optional[str] = None
    ) -> "Observability":
        """
        Initialize the singleton instance.
        
        Args:
            service_name: Service name for all components
            log_level: Minimum log level
            enable_json_logs: Whether to use JSON formatting
            log_file: Optional file path for log output
            
        Returns:
            Singleton observability instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    service_name=service_name,
                    log_level=log_level,
                    enable_json_logs=enable_json_logs,
                    log_file=log_file
                )
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "Observability":
        """
        Get the singleton instance.
        
        Returns:
            Singleton observability instance
            
        Raises:
            RuntimeError: If not initialized
        """
        if cls._instance is None:
            raise RuntimeError(
                "Observability not initialized. Call Observability.init() first."
            )
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance (useful for testing).
        """
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown()
                cls._instance = None
    
    # Convenience methods for common cross-cutting patterns
    # These are the only wrapper methods - everything else uses direct component access
    
    def trace_agent_run(self, agent_id: str):
        """
        Convenience decorator for tracing agent runs with standard attributes.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Decorator function
            
        Example:
            @obs.trace_agent_run("my-agent")
            async def run():
                pass
        """
        return self.tracer.trace_span(
            "astra.framework.agent.run",
            {"agent_id": agent_id, "component": "agent"}
        )
    
    def trace_model_call(self, model_name: str, provider: str):
        """
        Convenience decorator for tracing model calls.
        
        Args:
            model_name: Model name
            provider: Model provider
            
        Returns:
            Decorator function
            
        Example:
            @obs.trace_model_call("gpt-4", "openai")
            async def call_model():
                pass
        """
        return self.tracer.trace_span(
            "astra.framework.model.call",
            {"model_name": model_name, "provider": provider, "component": "model"}
        )
    
    def trace_tool_call(self, tool_name: str):
        """
        Convenience decorator for tracing tool calls.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Decorator function
            
        Example:
            @obs.trace_tool_call("web_search")
            async def call_tool():
                pass
        """
        return self.tracer.trace_span(
            "astra.framework.tool.call",
            {"tool_name": tool_name, "component": "tool"}
        )
    
    def shutdown(self) -> None:
        """
        Shutdown all observability components.
        
        Should be called during application shutdown to ensure
        all traces, metrics, and logs are properly flushed.
        """
        self.logger.info("Shutting down observability components")
        
        try:
            self.tracer.shutdown()
        except Exception as e:
            self.logger.error("Error shutting down tracer", exception=e)
        
        try:
            self.logger.shutdown()
        except Exception as e:
            # Can't log this since logger is shutting down
            print(f"Error shutting down logger: {e}")