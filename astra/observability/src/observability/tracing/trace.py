"""
Trace model for Astra Observability.

A Trace represents a single user request flowing through the system.
It contains multiple Spans representing individual operations.
"""

from datetime import datetime, timezone


def _now_utc() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    Using a tz-aware value ensures the JSON serialization includes an offset
    (`+00:00`), so browsers parse it as UTC instead of local time.
    """
    return datetime.now(timezone.utc)


from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field, computed_field


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

        # Token metrics (aggregated from spans when trace ends)
        total_tokens: Total tokens used across all LLM calls
        input_tokens: Input/prompt tokens
        output_tokens: Output/completion tokens
        thoughts_tokens: Thinking process tokens (e.g., Gemini thoughts)

        # Model info
        model: Primary LLM model used (if single model) or "multiple"
    """

    model_config = {"from_attributes": True}

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: TraceStatus = TraceStatus.RUNNING
    start_time: datetime = Field(default_factory=_now_utc)
    end_time: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    # Token metrics (aggregated when trace ends)
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    thoughts_tokens: int = 0

    # Model info
    model: str | None = None

    @computed_field
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
        self.end_time = _now_utc()

    def add_token_usage(
        self,
        total: int = 0,
        input_: int = 0,
        output: int = 0,
        thoughts: int = 0,
        model_name: str | None = None,
    ) -> None:
        """Add token usage from a span."""
        self.total_tokens += total
        self.input_tokens += input_
        self.output_tokens += output
        self.thoughts_tokens += thoughts

        # Track model - set if first model, or "multiple" if different
        if model_name:
            if self.model is None:
                self.model = model_name
            elif self.model != model_name and self.model != "multiple":
                self.model = "multiple"
