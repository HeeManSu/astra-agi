"""StreamAccumulator: gathers TTFT, chunk counts, and token usage for a streaming LLM call.

Used inside a model's `stream()` method:

    async with span("generation.gemini.stream", kind=SpanKind.GENERATION, attributes={...}):
        acc = StreamAccumulator()
        async for chunk in upstream_stream:
            acc.observe_chunk(chunk)
            yield chunk
        update_span(acc.finalize(usage=last_usage))
"""

from __future__ import annotations

import time
from typing import Any


PREVIEW_DEFAULT = 200


def preview(value: Any, n: int = PREVIEW_DEFAULT) -> str:
    """Truncate any value to a short, log-safe preview string."""
    if value is None:
        return ""
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return "<unrepr>"
    if len(value) <= n:
        return value
    return value[:n] + f"...[+{len(value) - n} chars]"


class StreamAccumulator:
    """Accumulate metrics across the lifetime of a streaming LLM call.

    Tracks first-token latency, per-event chunk counts, content vs tool-call
    chunks, and reasoning vs generation phase durations. Returns a flat dict
    of attributes from .finalize() that can be passed straight to update_span().
    """

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._first_content_at: float | None = None
        self._first_tool_at: float | None = None
        self._last_event_at: float | None = None
        self._reasoning_started_at: float | None = None
        self._reasoning_ended_at: float | None = None
        self.chunk_count = 0
        self.content_chunks = 0
        self.tool_call_chunks = 0
        self.reasoning_chunks = 0
        self.content_chars = 0
        self.reasoning_chars = 0
        self._sample_chunks: list[str] = []  # debug-only: first few chunks raw

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe_chunk(self, chunk: Any) -> None:
        """Record a single streamed chunk.

        Accepts ModelResponse-shaped objects (with .content / .tool_calls /
        .metadata) or plain dicts. Anything else is counted but otherwise ignored.
        """
        now = time.perf_counter()
        self.chunk_count += 1
        self._last_event_at = now

        content = _get(chunk, "content", "")
        tool_calls = _get(chunk, "tool_calls", None)
        metadata = _get(chunk, "metadata", {}) or {}

        is_reasoning = bool(metadata.get("reasoning")) or bool(metadata.get("is_reasoning"))

        if is_reasoning and content:
            self.reasoning_chunks += 1
            self.reasoning_chars += len(content)
            if self._reasoning_started_at is None:
                self._reasoning_started_at = now
            self._reasoning_ended_at = now
        elif content:
            self.content_chunks += 1
            self.content_chars += len(content)
            if self._first_content_at is None:
                self._first_content_at = now

        if tool_calls:
            self.tool_call_chunks += 1
            if self._first_tool_at is None:
                self._first_tool_at = now

        if len(self._sample_chunks) < 5:
            sample = {
                "content": preview(content, 120),
                "tool_calls": preview(tool_calls, 120) if tool_calls else None,
                "metadata": metadata,
            }
            self._sample_chunks.append(preview(sample, 240))

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def finalize(
        self,
        usage: dict[str, Any] | None = None,
        model: str | None = None,
        provider: str | None = None,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Return a flat attribute dict for update_span().

        Token keys (`input_tokens`, `output_tokens`, `thoughts_tokens`,
        `total_tokens`, `model`) match the names ObservabilityEngine.end_span
        already aggregates onto the parent trace.
        """
        now = time.perf_counter()
        total_ms = round((now - self._start) * 1000, 2)

        first_token_at = (
            min(t for t in (self._first_content_at, self._first_tool_at) if t is not None)
            if (self._first_content_at or self._first_tool_at)
            else None
        )
        ttft_ms = round((first_token_at - self._start) * 1000, 2) if first_token_at else None

        reasoning_ms = (
            round((self._reasoning_ended_at - self._reasoning_started_at) * 1000, 2)
            if self._reasoning_started_at and self._reasoning_ended_at
            else 0.0
        )
        generation_ms = (
            round((now - self._first_content_at) * 1000, 2) if self._first_content_at else 0.0
        )

        attrs: dict[str, Any] = {
            "ttft_ms": ttft_ms,
            "total_duration_ms": total_ms,
            "reasoning_duration_ms": reasoning_ms,
            "generation_duration_ms": generation_ms,
            "chunk_count": self.chunk_count,
            "content_chunks": self.content_chunks,
            "tool_call_chunks": self.tool_call_chunks,
            "reasoning_chunks": self.reasoning_chunks,
            "content_chars": self.content_chars,
            "reasoning_chars": self.reasoning_chars,
        }

        if model is not None:
            attrs["model"] = model
        if provider is not None:
            attrs["provider"] = provider

        if usage:
            for key in ("input_tokens", "output_tokens", "thoughts_tokens", "total_tokens"):
                if key in usage and usage[key] is not None:
                    attrs[key] = usage[key]

        if include_raw and self._sample_chunks:
            attrs["chunks_raw_preview"] = self._sample_chunks

        return attrs


def _get(obj: Any, attr: str, default: Any) -> Any:
    """Read attribute from an object or key from a dict, with a default."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
