"""
Error exception classes for AWS Bedrock model implementation.
This file contains ONLY exception class definitions and error parsing logic.
"""

from typing import Any


class BedrockError(Exception):
    """Base exception class for all Bedrock-related errors."""

    def __init__(
        self, message: str, status_code: int | None = None, details: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class BedrockAuthenticationError(BedrockError):
    """Raised when authentication fails (invalid credentials, missing credentials, etc.)."""


class BedrockValidationError(BedrockError):
    """Raised when request validation fails (invalid parameters, malformed request, etc.)."""


class BedrockThrottlingError(BedrockError):
    """Raised when rate limiting/throttling occurs."""


class BedrockModelError(BedrockError):
    """Raised when model-specific errors occur."""


class BedrockAPIError(BedrockError):
    """Raised for general API errors."""


def parse_bedrock_error(response: dict[str, Any]) -> BedrockError:
    """
    Parse error response from Bedrock API and return appropriate exception.

    Bedrock API returns errors in different formats depending on the error type.
    This function handles all known error formats and returns the appropriate
    exception class.

    Args:
        response: Error response dictionary from Bedrock API

    Returns:
        Appropriate BedrockError subclass based on error type
    """
    # Extract error message and type
    error_message = "Unknown error"
    error_type = response.get("__type", "")
    status_code = response.get("statusCode")

    # Try to extract message from different possible fields
    if "message" in response:
        error_message = response["message"]
    elif "Message" in response:
        error_message = response["Message"]
    elif "error" in response:
        error_message = str(response["error"])

    # Determine error type and create appropriate exception
    error_type_lower = error_type.lower()

    if "throttling" in error_type_lower or "throttled" in error_type_lower:
        return BedrockThrottlingError(
            message=error_message,
            status_code=status_code,
            details=response,
        )

    if "validation" in error_type_lower or "invalid" in error_type_lower:
        return BedrockValidationError(
            message=error_message,
            status_code=status_code,
            details=response,
        )

    if (
        "authentication" in error_type_lower
        or "credential" in error_type_lower
        or "unauthorized" in error_type_lower
    ):
        return BedrockAuthenticationError(
            message=error_message,
            status_code=status_code,
            details=response,
        )

    if "model" in error_type_lower or "modelerror" in error_type_lower:
        return BedrockModelError(
            message=error_message,
            status_code=status_code,
            details=response,
        )

    # Default to general API error
    return BedrockAPIError(
        message=error_message,
        status_code=status_code,
        details=response,
    )
