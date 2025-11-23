"""
HIL (Human-in-the-Loop) - Execution control layer for Astra.

Provides three patterns for human intervention:
1. Tool Approval - Require approval before tool execution
2. Tool Suspension - Pause mid-execution for human input
3. External Execution - Delegate tool execution to external systems

Example:
    # Tool approval
    @tool(requires_approval=True)
    def delete_file(path: str):
        os.remove(path)
    
    # Tool suspension
    @tool(suspend_schema={"otp": str})
    def verify_payment(amount: float):
        otp = suspend("Enter OTP")
        verify(otp)
    
    # External execution
    @tool(external_execution=True)
    def run_shell(command: str):
        # Executed externally, not by agent
        pass
"""

from .manager import HILManager
from .models import RunStatus, PauseReason, ResumeData, PauseResult
from .state import RunState, RunStateStorage
from .events import HILEvent, HILEventBus
from .exceptions import SuspendExecution, HILError

__all__ = [
    "HILManager",
    "RunStatus",
    "PauseReason",
    "ResumeData",
    "PauseResult",
    "RunState",
    "RunStateStorage",
    "HILEvent",
    "HILEventBus",
    "SuspendExecution",
    "HILError",
]
