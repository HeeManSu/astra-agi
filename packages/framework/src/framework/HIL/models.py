"""
HIL data models.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class PauseReason(str, Enum):
    """Reason for pausing execution."""
    APPROVAL = "approval"
    SUSPENSION = "suspension"
    EXTERNAL = "external"


class RunStatus(str, Enum):
    """Status of a run."""
    RUNNING = "running"
    PAUSED_APPROVAL = "paused_approval"
    PAUSED_SUSPENSION = "paused_suspension"
    PAUSED_EXTERNAL = "paused_external"
    COMPLETED = "completed"
    FAILED = "failed"


class ResumeData(BaseModel):
    """Data for resuming a paused run."""
    decision: Optional[str] = None  # "approve" or "decline" for approval
    data: Optional[Dict[str, Any]] = None  # Input data for suspension
    result: Optional[Dict[str, Any]] = None  # Tool result for external execution


class PauseResult(BaseModel):
    """Result of a pause operation."""
    paused: bool
    run_id: str
    reason: PauseReason
    message: Optional[str] = None
    pause_data: Optional[Dict[str, Any]] = None


class ResumeResult(BaseModel):
    """Result of a resume operation."""
    resumed: bool
    run_id: str
    result: Optional[Dict[str, Any]] = None
