"""
Trace model for Astra Observability.

A Trace represents a single user request flowing through the system.
It contains multiple Spans representing individual operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class TraceStatus(str, Enum):
    """Status of a trace."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class Trace(BaseModel):
    """
    Represents a single trace (one user request).

    Attributes:
        trace_id: Unique identifier for the trace
        name: Human-readable name (e.g., "workflow:order_processing")
        status: Current status of the trace
        start_time: When the trace started
        end_time: When the trace ended (None if still running)
        attributes: Additional metadata
    """

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: TraceStatus = TraceStatus.RUNNING
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_ms(self) -> int | None:
        """Calculate duration in milliseconds."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() * 1000)

    def end(self, status: TraceStatus) -> None:
        """Mark the trace as ended."""
        self.status = status
        self.end_time = datetime.utcnow()
