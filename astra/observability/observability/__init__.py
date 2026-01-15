"""
Astra Observability Package

This package provides comprehensive observability for the Astra AI platform,
including distributed tracing, metrics collection, and structured logging.

Main Components:
- Observability: Unified facade for all observability features
- Tracer: OpenTelemetry-based distributed tracing
- MetricsRecorder: Prometheus-based metrics collection
- Logger: Loguru-based structured logging with trace correlation

Usage:
    # Initialize observability (singleton pattern)
    from observability import Observability
    
    obs = Observability.init(
        service_name="astra",
        environment="dev",
        log_level="INFO"
    )
    
    # Use in agent code - components exposed directly (composition pattern)
    @obs.trace_agent_run("my-agent")
    async def run_agent():
        obs.logger.info("Agent started", agent_id="my-agent")
        # ... agent logic ...
        obs.metrics.record_agent_run("my-agent", duration_seconds=1.5, status="success")
        obs.tracer.add_event("processing.completed")

    # Or use components directly (without facade)
    from observability import Tracer, MetricsRecorder, Logger
    
    tracer = Tracer("astra", "dev")
    metrics = MetricsRecorder("astra")
    logger = Logger("astra", "dev")
"""

from .core import Observability
from .tracer import Tracer
from .metrics import MetricsRecorder, MetricsTimer
from .logger import Logger

# Version info
__version__ = "0.1.0"
__author__ = "Himanshu Sharma"
__email__ = "himanshu.kumarr07@gmail.com"

# Main exports
__all__ = [
    # Main facade
    "Observability",
    
    # Individual components
    "Tracer",
    "MetricsRecorder", 
    "MetricsTimer",
    "Logger",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]

# Convenience function for quick initialization
def init_observability(
    service_name: str = "astra",
    log_level: str = "INFO",
    enable_json_logs: bool = True,
    log_file: str = None
) -> Observability:
    """
    Initialize observability with common defaults.
    
    Args:
        service_name: Service name for all components
        environment: Deployment environment (dev, staging, prod)
        log_level: Minimum log level (INFO, ERROR)
        enable_json_logs: Whether to use JSON formatting for logs
        log_file: Optional file path for log output
        
    Returns:
        Initialized Observability instance
        
    Example:
        from observability import init_observability
        
        obs = init_observability(
            service_name="astra",
            environment="prod",
            log_level="INFO"
        )
        
        @obs.trace_agent_run("my-agent")
        async def my_agent():
            obs.info("Agent running")
    """
    return Observability.init(
        service_name=service_name,
        log_level=log_level,
        enable_json_logs=enable_json_logs,
        log_file=log_file
    )

# Add convenience function to exports
__all__.append("init_observability")
