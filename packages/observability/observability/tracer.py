"""
OpenTelemetry-based distributed tracing for Astra.

This module provides a clean interface for creating and managing distributed traces
across agent runs, tool calls, and model interactions. It uses OpenTelemetry SDK
with console exporter for MVP (easily switchable to OTLP later).

Responsibilities:
- Create spans for every logical operation (agent.run(), model.call(), tool.call(), etc.)
- Propagate trace context across async operations
- Record span attributes, events, and errors
- Export traces to console (MVP) or OTLP endpoint
"""


from functools import wraps
import time
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.status import Status, StatusCode

Func = TypeVar("Func", bound=Callable[..., Awaitable[Any]])
# Func is a type variable that is bound to a callable that returns an awaitable of any type. This is a generic type that can be used to create a callable that returns an awaitable of any type.

class Tracer:
    """
    OpenTelemetry-based tracer for distributed tracing in Astra.
    
    Provides a simple interface for creating spans, recording events, and managing trace context across async operations.
    """
    
    def __init__(self, service_name: str = "astra", environment: str = "dev"):
        """
        Initialize the tracer with OpenTelemetry SDK.
        
        Args: 
            service_name: Name of the service (e.g., "astra")
        """
        
        self.service_name = service_name
        
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "0.1.0",  # TODO: Get from package version
        })
        
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            ConsoleSpanExporter(),  # TODO: Switch to OTLP exporter for production
            max_export_batch_size=100,
            export_timeout_millis=30000,
        )
        
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self._trace = trace.get_tracer(service_name)
        
    def get_tracer(self) -> trace.Tracer:
        """ Get the underlying OpenTelemetry tracer instance."""
        return self._trace
    
    def start_span(
        self, 
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[Any] = None
    ) -> trace.Span:
        """
        Start a new span with optional attributes.
        
        Args:
            name: Span name (e.g., "astra.framework.agent.run")
            attributes: Key-value pairs to attach to the span
            parent_context: Parent span context (optional)
            
        Returns:
            Started span instance
        """
        
        span = self._trace.start_span(name, context=parent_context)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
                
        return span
    
    def trace_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Callable[[Func], Func]:
        """
        Decorator to trace a function with a span.
        
        Args:
            name: Span name (e.g., "astra.framework.agent.run")
            attributes: Key-value pairs to attach to the span
            
        Returns:
            Decorator function
        """
        
        def decorator(func: Func) -> Func:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                with self._trace.start_as_current_span(name) as span:
                    # Add static attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                            
                            # Record start time for duration calculation
                    start_time = time.perf_counter()
                        
                    try:
                        
                        # Execute the wrapped function
                        result = await func(*args, **kwargs)
                        
                        # Mark span as successful
                        span.set_status(StatusCode.OK)
                        
                        return result
                            
                    except Exception as e:
                        
                        # Record exception details
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, f"{type(e).__name__}:{str(e)}")
                        )
                        raise   
                    finally:
                        # Record duration
                        duration_ms = int((time.perf_counter() - start_time) * 1000)
                        span.set_attribute("duration_ms", duration_ms)
                        
            return wrapper # type: ignore
        return decorator
    
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        
        """
        Add an event to the current active span.
        
        Args:
            name: Event name (e.g., "model.request_sent")
            attributes: Event attributes
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.add_event(name, attributes or {})
            
            
    def set_attribute(self, key: str, value: Any) -> None:
        """
        Set an attribute on the current active span.
        
        Args:
            key: Attribute key
            value: Attribute value
        """
        
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute(key, value)
            
    def record_exception(self, exception: Exception) -> None:
        """
        Record an exception on the current active span.
        
        Args:
            exception: Exception to record
        """
        current_span = trace.get_current_span()
        
        if current_span and current_span.is_recording():
            current_span.record_exception(exception)
            
    def get_trace_id(self) -> Optional[str]:
        """
        Get the current trace ID as a hex string.
        
        Returns:
            Trace ID or None if no active span
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            return f"{ctx.trace_id:032x}"              # It returns the trace ID as a hex string with 32 digits. 
        return None
        
        
    def get_span_id(self) -> Optional[str]:
        """
        Get the current span ID as a hex string.
        
        Returns:
            Span ID or None if no active span
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            return f"{ctx.span_id:016x}"
        return None
    
    def shutdown(self) -> None:
        """
        Shutdown the tracer and flush any pending spans.
        
        Should be called during application shutdown.
        """
        
        provider  = trace.get_tracer_provider()
        if hasattr(provider, 'shutdown'):
            provider.shutdown()  # type: ignore[attr-defined]