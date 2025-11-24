"""
Output format exceptions.
"""


class OutputFormatError(Exception):
    """Base exception for output format errors."""
    pass


class OutputValidationError(OutputFormatError):
    """Raised when output validation fails."""
    pass


class OutputRepairError(OutputFormatError):
    """Raised when output repair fails after retries."""
    pass
