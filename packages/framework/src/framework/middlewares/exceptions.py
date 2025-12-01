"""
Middleware exceptions.
"""


class MiddlewareError(Exception):
    """Base exception for middleware errors."""


class InputValidationError(MiddlewareError):
    """Raised when input validation fails."""


class OutputValidationError(MiddlewareError):
    """Raised when output validation fails."""


class MiddlewareAbortError(MiddlewareError):
    """
    Raised to abort execution.

    When raised, the agent stops processing and returns an error to the user.
    """
