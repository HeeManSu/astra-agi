"""
Astra Cloud exceptions.
"""


class AstraCloudError(Exception):
    """Base exception for Astra Cloud errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(AstraCloudError):
    """Raised when authentication fails."""


class NotFoundError(AstraCloudError):
    """Raised when a resource is not found."""


class ConnectionError(AstraCloudError):
    """Raised when connection to Astra Cloud fails."""


class ValidationError(AstraCloudError):
    """Raised when validation fails."""
