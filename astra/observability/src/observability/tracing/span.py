"""
Span model for Astra Observability.

A Span represents a single operation within a Trace.
Spans support parent-child relationships for hierarchical tracing.
"""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class SpanKind(str, Enum):
    """Type of operation the span represents."""

    WORKFLOW = "WORKFLOW"
    STEP = "STEP"
    GENERATION = "GENERATION"
    TOOL = "TOOL"


class SpanStatus(str, Enum):
    """Status of a span."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class Span(BaseModel):
    """
    Represents a single span (one operation within a trace).

    Attributes:
        span_id: Unique identifier for the span
        trace_id: ID of the parent trace
        parent_span_id: ID of the parent span (None for root spans)
        name: Human-readable name
        kind: Type of operation
        status: Current status
        start_time: When the span started
        end_time: When the span ended (None if still running)
        duration_ms: Duration in milliseconds (computed on end)
        attributes: Additional metadata
        error: Error message if status is ERROR
    """

    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    parent_span_id: str | None = None
    name: str
    kind: SpanKind
    status: SpanStatus = SpanStatus.RUNNING
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    duration_ms: int | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    def end(self, status: SpanStatus, error: str | None = None) -> None:
        """Mark the span as ended."""
        self.status = status
        self.end_time = datetime.utcnow()
        self.error = error
        # Calculate duration
        delta = self.end_time - self.start_time
        self.duration_ms = int(delta.total_seconds() * 1000)
