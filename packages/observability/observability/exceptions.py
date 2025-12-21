"""
Observability Exception Hierarchy

This module defines all custom exceptions and warnings used throughout the Observability SDK.
All exceptions inherit from a base ObservabilityException for easy catching and handling.

Exception Hierarchy:
    ObservabilityException (base)
    ├── InitializationError - Raised when tracer/exporter fails to initialize
    ├── ConfigurationError - Raised when configuration is missing or invalid (env vars, settings)
    ├── ExporterError - Raised when sending data to collector fails
    └── ShutdownError - Raised when SDK fails to shutdown/flush remaining data

Warning Classes:
    TracingDisabledWarning - Warning when tracing is disabled but operations are attempted

Usage:
    from observability.exceptions import ConfigurationError
    
    if not api_key:
        raise ConfigurationError(
            "ASTRAOPS_API_KEY environment variable is required",
            cause=None
        )
    
    try:
        # SDK operations
        pass
    except ObservabilityException as e:
        print(f"Observability error: {e}")
        if e.cause:
            print(f"Caused by: {e.cause}")
"""

from typing import Optional


class ObservabilityException(Exception):
    """Base exception class for all Observability SDK errors."""
    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} | Caused by: {type(self.cause).__name__}: {str(self.cause)}"
        return self.message


class InitializationError(ObservabilityException):    
    def __init__(self, message: str = "Failed to initialize Observability SDK", cause: Optional[Exception] = None):
        super().__init__(message, cause)


class ConfigurationError(ObservabilityException):    
    def __init__(self, message: str = "Invalid or missing configuration", cause: Optional[Exception] = None):
        super().__init__(message, cause)


class ExporterError(ObservabilityException):    
    def __init__(self, message: str = "Failed to export telemetry data", cause: Optional[Exception] = None):
        super().__init__(message, cause)


class ShutdownError(ObservabilityException):    
    def __init__(self, message: str = "Failed to shutdown SDK gracefully", cause: Optional[Exception] = None):
        super().__init__(message, cause)


class TracingDisabledWarning(Warning):
    pass


class InstrumentationError(ObservabilityException):
    def __init__(self, message: str = "Instrumentation error", cause: Optional[Exception] = None):
        super().__init__(message, cause)


class ParseError(ObservabilityException):
    def __init__(self, message: str = "Failed to parse provider payload", cause: Optional[Exception] = None):
        super().__init__(message, cause)


class WrapperError(ObservabilityException):
    def __init__(self, message: str = "Wrapper execution error", cause: Optional[Exception] = None):
        super().__init__(message, cause)
