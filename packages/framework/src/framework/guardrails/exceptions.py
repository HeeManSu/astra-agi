"""
Guardrail exceptions.
"""


class GuardrailError(Exception):
    """Base exception for guardrail violations."""
    pass


class InputGuardrailError(GuardrailError):
    """Raised when input validation fails."""
    pass


class OutputGuardrailError(GuardrailError):
    """Raised when output validation fails."""
    pass


class SchemaValidationError(GuardrailError):
    """Raised when output doesn't match expected schema."""
    pass
