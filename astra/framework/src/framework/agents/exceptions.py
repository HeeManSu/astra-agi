"""
Custom exceptions for Astra agents.

This module defines the exception hierarchy for agent execution errors.
"""


class AgentError(Exception):
    """Base exception for all agent errors."""


class ValidationError(AgentError):
    """Raised when input validation fails."""


class ModelError(AgentError):
    """Raised when model invocation fails."""


class ToolError(AgentError):
    """Raised when tool execution fails."""


class RetryExhaustedError(AgentError):
    """Raised when max retries are exceeded."""


class TimeoutError(AgentError):
    """Raised when an operation times out."""


class ContextLengthError(AgentError):
    """Raised when context length is exceeded."""
