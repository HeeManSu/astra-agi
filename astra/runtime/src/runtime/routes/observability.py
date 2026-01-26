"""
Observability API routes for Astra Runtime.

These routes provide HTTP endpoints for querying observability data.
They depend on the observability package (which is framework-agnostic).
"""

from fastapi import APIRouter, HTTPException, Request
from observability import Log, Span, Trace, get_trace_with_spans, list_traces
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


router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/traces", response_model=TraceListResponse)
async def api_list_traces(
    request: Request,
    limit: int = 50,
    offset: int = 0,
) -> TraceListResponse:
    """
    List traces with pagination.

    Args:
        limit: Maximum number of traces to return (default 50)
        offset: Number of traces to skip (default 0)

    Returns:
        List of traces ordered by start_time DESC
    """
    obs = getattr(request.app.state, "observability", None)
    if obs is None:
        raise HTTPException(status_code=503, detail="Observability not initialized")

    traces = await list_traces(obs.storage, limit=limit, offset=offset)
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
