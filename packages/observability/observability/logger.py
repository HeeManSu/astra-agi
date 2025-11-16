"""
Loguru-based structured logging for Astra.

This module provides structured logging with trace correlation, JSON formatting,
and configurable output destinations. Uses Loguru for clean API and powerful
formatting capabilities.

Responsibilities:
- Structured JSON logging with consistent schema
- Automatic trace/span ID correlation from OpenTelemetry context
- Configurable log levels and output destinations
- Request/session context propagation
- Performance-optimized async logging
"""

import json
import sys
from typing import Any, Dict, Optional
from loguru import logger
from opentelemetry import trace


class Logger:
    """ 
    Loguru-based structured logger with OpenTelemetry trace correlation.
    
    Provides structured JSON logging with automatic trace context injection and configurable output destinations.
    """
    
    def __init__(
        self, 
        service_name: str = "astra", 
        log_level: str = 'INFO', 
        enable_json: bool = True,
        log_file: Optional[str] = None
        ):
        
        """
        Initialize structured logger with Loguru.
        
        Args:
            service_name: Service name for log context
            log_level: Minimum log level (INFO, ERROR)
            enable_json: Whether to use JSON formatting
            log_file: Optional file path for log output
        """
        
        self.service_name = service_name
        self.log_level = log_level
        self.enable_json = enable_json
        self.log_file = log_file
        
        # Remove default logger to avoid duplication
        logger.remove()
        
        # Configure console output
        if enable_json:
            # Use sink function for JSON output
            def json_sink(message):
                record = message.record
                formatted = self._json_formatter(record)
                sys.stdout.write(formatted)
                sys.stdout.flush()
            
            logger.add(
                json_sink,
                level=log_level,
                backtrace=True,
                diagnose=True,
            )
        else:
            logger.add(
                sys.stdout,
                format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level> | "
                "{extra}"
                ),
            level=log_level,
            backtrace=True,
            diagnose=True,
        )
        
        # Configure file output if specified
        if log_file:
            # Ensure directory exists
            from pathlib import Path
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            if enable_json:
                # Use sink function for JSON file output
                # Note: Custom sinks don't support rotation/retention/compression
                # For production, consider using a file path sink with serialize=True
                import threading
                file_lock = threading.Lock()
                
                def json_file_sink(message):
                    record = message.record
                    formatted = self._json_formatter(record)
                    with file_lock:
                        with open(log_file, 'a', encoding='utf-8') as f:
                            f.write(formatted)
                            f.flush()
                
                logger.add(
                    json_file_sink,
                    level=log_level,
                    backtrace=True,
                    diagnose=True,
                )
            else:
                logger.add(
                    log_file,
                    format=(
                        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                        "<level>{level: <8}</level> | "
                        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                        "<level>{message}</level> | "
                        "{extra}"
                    ),
                    level=log_level,
                    backtrace=True,
                    diagnose=True,
                rotation="100 MB",
                retention="7 days",
                compression="gz",
            )
            
        # Bind static context
        self._logger = logger.bind(
            service=service_name,
        )
    
    def _json_formatter(self, record: Any) -> str:
        """
        Custom JSON formatter with trace correlation.
        
        Args:
            record: Loguru log record object (accessed via record["key"])
            
        Returns:
            JSON-formatted log line
        """
        
        # Get current trace context
        current_span = trace.get_current_span()
        trace_id = None
        span_id = None
        
        if current_span and current_span.get_span_context().is_valid:
            span_context = current_span.get_span_context()
            trace_id = format(span_context.trace_id, '032x')
            span_id = format(span_context.span_id, '016x')
        
        # Access Loguru record attributes (record is a dict-like object)
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name.lower(),
            "message": record["message"],
            "service": self.service_name,
            "trace_id": trace_id,
            "span_id": span_id,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        
        # Handle extra fields
        if "extra" in record and record["extra"]:
            extra = dict(record["extra"])
            extra.pop("service", None)
            extra.pop("environment", None)
            if extra:
                log_entry["extra"] = extra
                
        # Handle exceptions
        if "exception" in record and record["exception"]:
            exc_info = record["exception"]
            log_entry["exception"] = {
                "type": exc_info.type.__name__ if exc_info.type else None,
                "value": str(exc_info.value) if exc_info.value else None,
                "traceback": exc_info.traceback.format() if exc_info.traceback else None,
            }
            
        return json.dumps(log_entry, separators=(",", ":"), ensure_ascii=False) + "\n"
    
    
    def _get_context_logger(self, **context) -> Any:
        """
        Get logger with additional context bound.
        
        Args:
            **context: Additional context to bind
            
        Returns:
            Logger with additional context bound
        """
        return self._logger.bind(**context)
    
    def info(
        self, 
        message: str, 
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ) -> None:
        """
        Log info message with optional context.
        
        Args:
            message: Log message
            agent_id: Agent identifier
            session_id: Session identifier
            request_id: Request identifier
            **extra: Additional context fields
        """
        context = self._build_context(agent_id, session_id, request_id, **extra)
        self._get_context_logger(**context).info(message)
    
    def error(
        self, 
        message: str, 
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        **extra
    ) -> None:
        """
        Log error message with optional context and exception.
        
        Args:
            message: Log message
            agent_id: Agent identifier
            session_id: Session identifier
            request_id: Request identifier
            exception: Exception to log
            **extra: Additional context fields
        """
        context = self._build_context(agent_id, session_id, request_id, **extra)
        context_logger = self._get_context_logger(**context)
        
        if exception:
            context_logger.opt(exception=exception).error(message)
        else:
            context_logger.error(message)
    
    def _build_context(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ) -> Dict[str, Any]:
        """
        Build context dictionary for logging.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            request_id: Request identifier
            **extra: Additional context fields
            
        Returns:
            Context dictionary with non-None values
        """
        context = {}
        
        if agent_id:
            context["agent_id"] = agent_id
        if session_id:
            context["session_id"] = session_id
        if request_id:
            context["request_id"] = request_id
        
        # Add extra fields
        context.update(extra)
        
        return context
    
    def log_agent_start(
        self, 
        agent_id: str, 
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ) -> None:
        """
        Log agent execution start.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            request_id: Request identifier
            **extra: Additional context
        """
        self.info(
            "Agent execution started",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id,
            event_type="agent_start",
            **extra
        )
    
    def log_agent_complete(
        self, 
        agent_id: str, 
        duration_ms: int,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ) -> None:
        """
        Log agent execution completion.
        
        Args:
            agent_id: Agent identifier
            duration_ms: Execution duration in milliseconds
            session_id: Session identifier
            request_id: Request identifier
            **extra: Additional context
        """
        self.info(
            "Agent execution completed",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id,
            event_type="agent_complete",
            duration_ms=duration_ms,
            **extra
        )
    
    def log_model_call(
        self,
        model_name: str,
        provider: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        duration_ms: int,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ) -> None:
        """
        Log model API call with usage details.
        
        Args:
            model_name: Name of the model
            provider: Model provider
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            cost_usd: Cost in USD
            duration_ms: Call duration in milliseconds
            agent_id: Agent identifier
            session_id: Session identifier
            request_id: Request identifier
            **extra: Additional context
        """
        self.info(
            f"Model call completed: {model_name}",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id,
            event_type="model_call",
            model_name=model_name,
            provider=provider,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            **extra
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        duration_ms: int,
        status: str = "success",
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra
    ) -> None:
        """
        Log tool execution.
        
        Args:
            tool_name: Name of the tool
            duration_ms: Execution duration in milliseconds
            status: Execution status
            agent_id: Agent identifier
            session_id: Session identifier
            request_id: Request identifier
            **extra: Additional context
        """
        level_func = self.info if status == "success" else self.error
        level_func(
            f"Tool call {status}: {tool_name}",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id,
            event_type="tool_call",
            tool_name=tool_name,
            duration_ms=duration_ms,
            status=status,
            **extra
        )
    
    def set_level(self, level: str) -> None:
        """
        Change the logging level.
        
        Args:
            level: New log level (INFO, ERROR)
        """
        self.log_level = level
        # Note: Loguru doesn't support dynamic level changes easily
        # This would require reconfiguring handlers
    
    def shutdown(self) -> None:
        """
        Shutdown logger and flush any pending logs.
        """
        logger.stop()