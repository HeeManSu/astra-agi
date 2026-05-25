"""
Observability API routes for Astra Runtime.

These routes provide HTTP endpoints for querying observability data.
They depend on the observability package (which is framework-agnostic).
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from observability import Log, Span, Trace, get_trace_with_spans, list_traces
from observability.query.metrics import compute_metrics
from observability.query.traces import get_logs_for_trace
from pydantic import BaseModel


# Response models
class TraceListResponse(BaseModel):
    """Response for listing traces."""

    traces: list[Trace]
    count: int


class TraceDetailResponse(BaseModel):
    """Response for trace detail with spans."""

    trace: Trace
    spans: list[Span]


class LogListResponse(BaseModel):
    """Response for listing logs."""

    logs: list[Log]
    count: int


class TopItemResponse(BaseModel):
    name: str
    count: int
    extra: dict[str, Any] = {}


class MetricsResponse(BaseModel):
    """Aggregated metrics over a recent time window."""

    window_start: str
    window_end: str
    trace_sample_size: int
    truncated: bool

    request_count: int
    success_count: int
    error_count: int
    running_count: int
    success_rate: float
    error_rate: float

    latency_p50_ms: float | None
    latency_p95_ms: float | None
    latency_p99_ms: float | None
    latency_avg_ms: float | None

    total_tokens: int
    input_tokens: int
    output_tokens: int
    thoughts_tokens: int
    avg_tokens_per_request: float

    avg_ttft_ms: float | None
    generation_p50_ms: float | None
    generation_p95_ms: float | None

    top_models: list[TopItemResponse]
    top_tools: list[TopItemResponse]
    top_agents: list[TopItemResponse]
    top_teams: list[TopItemResponse]

    tool_call_count: int
    tool_error_count: int
    tool_error_rate: float


router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/traces", response_model=TraceListResponse)
async def api_list_traces(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    include_system: bool = False,
) -> TraceListResponse:
    """
    List traces with pagination.

    Args:
        limit: Maximum number of traces to return (default 50)
        offset: Number of traces to skip (default 0)
        include_system: If True, include operational traces (e.g. ``server.startup``).
            Default False so the dashboard only shows user-request traces.

    Returns:
        List of traces ordered by start_time DESC
    """
    obs = getattr(request.app.state, "observability", None)
    if obs is None:
        raise HTTPException(status_code=503, detail="Observability not initialized")

    traces = await list_traces(
        obs.storage,
        limit=limit,
        offset=offset,
        include_system=include_system,
    )
    return TraceListResponse(traces=traces, count=len(traces))


@router.get("/traces/{trace_id}", response_model=TraceDetailResponse)
async def api_get_trace_detail(
    request: Request,
    trace_id: str,
) -> TraceDetailResponse:
    """
    Get a trace with all its spans.

    Args:
        trace_id: ID of the trace to retrieve

    Returns:
        Trace with all associated spans (trace includes token metrics)
    """
    obs = getattr(request.app.state, "observability", None)
    if obs is None:
        raise HTTPException(status_code=503, detail="Observability not initialized")

    result = await get_trace_with_spans(obs.storage, trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    return TraceDetailResponse(trace=result.trace, spans=result.spans)


@router.get("/traces/{trace_id}/logs", response_model=LogListResponse)
async def api_get_trace_logs(
    request: Request,
    trace_id: str,
    limit: int = 500,
) -> LogListResponse:
    """
    Get all logs for a trace.

    Args:
        trace_id: ID of the trace
        limit: Maximum number of logs to return (default 500)

    Returns:
        List of logs ordered by timestamp
    """
    obs = getattr(request.app.state, "observability", None)
    if obs is None:
        raise HTTPException(status_code=503, detail="Observability not initialized")

    logs = await get_logs_for_trace(obs.storage, trace_id, limit=limit)
    return LogListResponse(logs=logs, count=len(logs))


@router.get("/metrics", response_model=MetricsResponse)
async def api_get_metrics(
    request: Request,
    hours: float = 24,
    max_traces: int = 500,
    include_system: bool = False,
) -> MetricsResponse:
    """Aggregated dashboard metrics over a recent time window.

    Args:
        hours: window size in hours (default 24)
        max_traces: hard cap on traces to scan (default 500)
        include_system: include operational traces like ``server.startup``
    """
    obs = getattr(request.app.state, "observability", None)
    if obs is None:
        raise HTTPException(status_code=503, detail="Observability not initialized")

    snap = await compute_metrics(
        obs.storage,
        hours=hours,
        max_traces=max_traces,
        include_system=include_system,
    )

    def _items(seq) -> list[TopItemResponse]:
        return [TopItemResponse(name=i.name, count=i.count, extra=i.extra) for i in seq]

    return MetricsResponse(
        window_start=snap.window_start.isoformat(),
        window_end=snap.window_end.isoformat(),
        trace_sample_size=snap.trace_sample_size,
        truncated=snap.truncated,
        request_count=snap.request_count,
        success_count=snap.success_count,
        error_count=snap.error_count,
        running_count=snap.running_count,
        success_rate=snap.success_rate,
        error_rate=snap.error_rate,
        latency_p50_ms=snap.latency_p50_ms,
        latency_p95_ms=snap.latency_p95_ms,
        latency_p99_ms=snap.latency_p99_ms,
        latency_avg_ms=snap.latency_avg_ms,
        total_tokens=snap.total_tokens,
        input_tokens=snap.input_tokens,
        output_tokens=snap.output_tokens,
        thoughts_tokens=snap.thoughts_tokens,
        avg_tokens_per_request=snap.avg_tokens_per_request,
        avg_ttft_ms=snap.avg_ttft_ms,
        generation_p50_ms=snap.generation_p50_ms,
        generation_p95_ms=snap.generation_p95_ms,
        top_models=_items(snap.top_models),
        top_tools=_items(snap.top_tools),
        top_agents=_items(snap.top_agents),
        top_teams=_items(snap.top_teams),
        tool_call_count=snap.tool_call_count,
        tool_error_count=snap.tool_error_count,
        tool_error_rate=snap.tool_error_rate,
    )
