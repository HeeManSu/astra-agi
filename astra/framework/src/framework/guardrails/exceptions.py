"""
Guardrail exceptions.
"""


class GuardrailError(Exception):
    """Base exception for guardrail violations."""


class InputGuardrailError(GuardrailError):
    """Raised when input validation fails."""


class OutputGuardrailError(GuardrailError):
    """Raised when output validation fails."""


class SchemaValidationError(GuardrailError):
    """Raised when output doesn't match expected schema."""
