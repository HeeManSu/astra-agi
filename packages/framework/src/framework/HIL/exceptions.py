"""
HIL exceptions for execution control.
"""

class HILError(Exception):
    """Base exception for HIL errors."""
    pass


class SuspendExecution(HILError):
    """
    Exception raised to suspend tool execution.
    
    This exception is raised by the suspend() function to pause
    tool execution and wait for human input.
    
    Attributes:
        message: Message to display to human
        schema: Schema for expected input data
        run_id: Run ID of the paused execution
        tool_call_id: Tool call ID that was suspended
    """
    
    def __init__(
        self, 
        message: str, 
        schema: dict = None,
        run_id: str = None,
        tool_call_id: str = None
    ):
        self.message = message
        self.schema = schema or {}
        self.run_id = run_id
        self.tool_call_id = tool_call_id
        super().__init__(message)


class HILNotEnabledError(HILError):
    """Raised when HIL feature is used but not enabled (no storage)."""
    pass


class InvalidResumeDataError(HILError):
    """Raised when resume data doesn't match expected format."""
    pass


class RunNotFoundError(HILError):
    """Raised when trying to resume a non-existent run."""
    pass


class RunNotPausedError(HILError):
    """Raised when trying to resume a run that isn't paused."""
    pass
