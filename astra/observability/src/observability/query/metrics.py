"""Aggregated metrics computed on the fly from stored traces and spans.

The trace/span store already holds everything we need (durations, token usage,
tool kinds, status, attributes). For a dashboard, we just scan traces in a
time window and aggregate. This avoids running a parallel metrics pipeline.

Scope is capped at ``max_traces`` per call to keep dashboards responsive.
Numbers beyond that cap should switch to a dedicated metrics store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from observability.storage.base import StorageBackend
from observability.tracing.span import Span, SpanKind, SpanStatus
from observability.tracing.trace import Trace, TraceStatus

from .traces import _is_system_trace


@dataclass
class TopItem:
    name: str
    count: int
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricsSnapshot:
    """A point-in-time aggregation of trace/span data over a time window."""

    window_start: datetime
    window_end: datetime
    trace_sample_size: int  # number of traces actually scanned (may be < total if capped)
    truncated: bool  # True if the cap was hit and older traces were dropped

    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    running_count: int = 0
    success_rate: float = 0.0  # fraction in [0,1] over completed (success+error)
    error_rate: float = 0.0

    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    latency_avg_ms: float | None = None

    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    thoughts_tokens: int = 0
    avg_tokens_per_request: float = 0.0

    avg_ttft_ms: float | None = None
    generation_p50_ms: float | None = None
    generation_p95_ms: float | None = None

    top_models: list[TopItem] = field(default_factory=list)
    top_tools: list[TopItem] = field(default_factory=list)  # extra: error_count, error_rate
    top_agents: list[TopItem] = field(default_factory=list)
    top_teams: list[TopItem] = field(default_factory=list)

    tool_call_count: int = 0
    tool_error_count: int = 0
    tool_error_rate: float = 0.0


def _percentile(values: list[float], pct: float) -> float | None:
    """Return the pct-percentile (0-100) of a numeric list, or None if empty.

    Uses linear interpolation between the two nearest ranks, which is good
    enough for a dashboard with limited samples.
    """
    if not values:
        return None
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_vals) - 1)
    frac = rank - low
    return float(sorted_vals[low] + (sorted_vals[high] - sorted_vals[low]) * frac)


def _string_attr(d: dict[str, Any], key: str) -> str | None:
    v = d.get(key)
    return v if isinstance(v, str) and v else None


def _number_attr(d: dict[str, Any], key: str) -> float | None:
    v = d.get(key)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


async def compute_metrics(
    storage: StorageBackend,
    since: datetime | None = None,
    *,
    hours: float | None = None,
    max_traces: int = 500,
    include_system: bool = False,
    top_n: int = 8,
) -> MetricsSnapshot:
    """Aggregate metrics from traces+spans in a recent time window.

    Args:
        storage: storage backend to query
        since: explicit window start (tz-aware UTC); takes precedence over ``hours``
        hours: relative window in hours (default 24 if ``since`` is None)
        max_traces: hard cap on traces to scan to keep the dashboard responsive
        include_system: whether to include operational traces (``server.*``)
        top_n: how many entries to keep in each "top" list

    Returns:
        MetricsSnapshot
    """
    now = datetime.now(timezone.utc)
    if since is None:
        since = now - timedelta(hours=hours if hours is not None else 24)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)

    # We page through traces newest-first until we cross the window boundary
    # or hit the cap. Storage already returns DESC by start_time, so we can
    # stop early as soon as a trace's start is older than ``since``.
    traces: list[Trace] = []
    truncated = False
    page_size = min(max_traces, 200)
    offset = 0
    while len(traces) < max_traces:
        batch = await storage.list_traces(limit=page_size, offset=offset)
        if not batch:
            break
        stop = False
        for t in batch:
            if not include_system and _is_system_trace(t):
                continue
            start = t.start_time
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if start < since:
                stop = True
                break
            traces.append(t)
            if len(traces) >= max_traces:
                truncated = True
                break
        if stop or len(batch) < page_size:
            break
        offset += page_size

    snapshot = MetricsSnapshot(
        window_start=since,
        window_end=now,
        trace_sample_size=len(traces),
        truncated=truncated,
    )

    if not traces:
        return snapshot

    # ── Trace-level aggregation
    latencies_ms: list[float] = []
    model_counts: dict[str, int] = {}
    model_tokens: dict[str, int] = {}
    agent_counts: dict[str, int] = {}
    team_counts: dict[str, int] = {}

    for t in traces:
        if t.status == TraceStatus.SUCCESS:
            snapshot.success_count += 1
        elif t.status == TraceStatus.ERROR:
            snapshot.error_count += 1
        elif t.status == TraceStatus.RUNNING:
            snapshot.running_count += 1

        if t.duration_ms is not None and t.status != TraceStatus.RUNNING:
            latencies_ms.append(float(t.duration_ms))

        snapshot.total_tokens += t.total_tokens or 0
        snapshot.input_tokens += t.input_tokens or 0
        snapshot.output_tokens += t.output_tokens or 0
        snapshot.thoughts_tokens += t.thoughts_tokens or 0

        if t.model:
            model_counts[t.model] = model_counts.get(t.model, 0) + 1
            model_tokens[t.model] = model_tokens.get(t.model, 0) + (t.total_tokens or 0)

        agent_id = _string_attr(t.attributes or {}, "agent_id")
        if agent_id:
            agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1

        team_id = _string_attr(t.attributes or {}, "team_id")
        if team_id:
            team_counts[team_id] = team_counts.get(team_id, 0) + 1

    snapshot.request_count = len(traces)
    completed = snapshot.success_count + snapshot.error_count
    if completed > 0:
        snapshot.success_rate = snapshot.success_count / completed
        snapshot.error_rate = snapshot.error_count / completed
    if snapshot.request_count > 0:
        snapshot.avg_tokens_per_request = snapshot.total_tokens / snapshot.request_count

    snapshot.latency_p50_ms = _percentile(latencies_ms, 50)
    snapshot.latency_p95_ms = _percentile(latencies_ms, 95)
    snapshot.latency_p99_ms = _percentile(latencies_ms, 99)
    if latencies_ms:
        snapshot.latency_avg_ms = sum(latencies_ms) / len(latencies_ms)

    snapshot.top_models = [
        TopItem(name=m, count=c, extra={"total_tokens": model_tokens.get(m, 0)})
        for m, c in sorted(model_counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    ]
    snapshot.top_agents = [
        TopItem(name=a, count=c)
        for a, c in sorted(agent_counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    ]
    snapshot.top_teams = [
        TopItem(name=tm, count=c)
        for tm, c in sorted(team_counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    ]

    # ── Span-level aggregation (TOOL + GENERATION).
    # N+1 fetch is acceptable here because we already capped trace count.
    tool_total: dict[str, int] = {}
    tool_errors: dict[str, int] = {}
    ttfts: list[float] = []
    generation_durations: list[float] = []

    for t in traces:
        spans: list[Span] = await storage.get_spans_for_trace(t.trace_id)
        for s in spans:
            if s.kind == SpanKind.TOOL:
                tool_name = (
                    _string_attr(s.attributes or {}, "tool_name")
                    or _string_attr(s.attributes or {}, "tool_qualified_name")
                    or s.name
                )
                tool_total[tool_name] = tool_total.get(tool_name, 0) + 1
                snapshot.tool_call_count += 1
                if s.status == SpanStatus.ERROR:
                    tool_errors[tool_name] = tool_errors.get(tool_name, 0) + 1
                    snapshot.tool_error_count += 1
            elif s.kind == SpanKind.GENERATION:
                ttft = _number_attr(s.attributes or {}, "ttft_ms")
                if ttft is not None:
                    ttfts.append(ttft)
                if s.duration_ms is not None and s.status != SpanStatus.RUNNING:
                    generation_durations.append(float(s.duration_ms))

    if snapshot.tool_call_count > 0:
        snapshot.tool_error_rate = snapshot.tool_error_count / snapshot.tool_call_count

    snapshot.top_tools = [
        TopItem(
            name=name,
            count=count,
            extra={
                "error_count": tool_errors.get(name, 0),
                "error_rate": (tool_errors.get(name, 0) / count) if count else 0.0,
            },
        )
        for name, count in sorted(tool_total.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    ]

    if ttfts:
        snapshot.avg_ttft_ms = sum(ttfts) / len(ttfts)
    snapshot.generation_p50_ms = _percentile(generation_durations, 50)
    snapshot.generation_p95_ms = _percentile(generation_durations, 95)

    return snapshot
