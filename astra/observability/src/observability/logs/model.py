"""
Log model for Astra Observability.

A Log represents a structured event that occurred within a Span or Trace.
"""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Severity level of the log."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class Log(BaseModel):
    """
    Represents a single structured log entry.

    Attributes:
        id: Unique identifier for the log
        trace_id: ID of the trace this log belongs to
        span_id: ID of the span this log belongs to (optional)
        level: Severity level
        message: Human-readable message
        attributes: Structured data associated with the log
        timestamp: When the log occurred
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    span_id: str | None = None
    level: LogLevel
    message: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
