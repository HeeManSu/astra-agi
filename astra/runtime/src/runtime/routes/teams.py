"""Team routes."""

import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from runtime.registry import team_registry


router = APIRouter(prefix="/teams", tags=["teams"])


class TeamRunRequest(BaseModel):
    """Request body for running a team."""

    message: str
    thread_id: str | None = None
    context: dict[str, Any] | None = None


class TeamResponse(BaseModel):
    """Team details response."""

    id: str
    name: str
    description: str | None = None


@router.get("/")
async def list_teams() -> list[TeamResponse]:
    """List all registered teams."""
    teams = team_registry.list_all()
    return [
        TeamResponse(
            id=team.id or team.name,
            name=team.name,
            description=team.description,
        )
        for team in teams
    ]


@router.get("/{team_id}")
async def get_team(team_id: str) -> TeamResponse:
    """Get team details by ID."""
    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return TeamResponse(
        id=team.id or team.name,
        name=team.name,
        description=team.description,
    )


@router.post("/{team_id}/invoke")
async def run_team(team_id: str, request: TeamRunRequest):
    """Run a team synchronously."""
    import time

    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    start_time = time.time()
    sys.stdout.write(f"[TIMING] Team '{team_id}' invoke started at {time.strftime('%H:%M:%S')}")

    # Run the team with optional thread_id for message persistence
    response = await team.invoke(
        request.message, thread_id=request.thread_id, context=request.context
    )

    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    sys.stdout.write(f"[TIMING] Team '{team_id}' invoke completed at {time.strftime('%H:%M:%S')}")
    sys.stdout.write(
        f"[TIMING] Team '{team_id}' total time: {duration_ms:.2f}ms ({duration_ms / 1000:.2f}s)"
    )

    return {"response": response, "timing_ms": round(duration_ms, 2)}


@router.post("/{team_id}/stream")
async def stream_team(team_id: str, request: TeamRunRequest, http_request: Request):
    """Stream a team response using SSE."""
    import time

    from fastapi.responses import StreamingResponse
    from observability import LogLevel, log, span, trace

    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    async def generate():
        start_time = time.time()
        sys.stdout.write(f"[TIMING] Team '{team_id}' stream started at {time.strftime('%H:%M:%S')}")

        # Use ContextVar-based trace (works even if observability not initialized)
        async with trace(
            f"team.{team_id}.stream",
            attributes={
                "team_id": team_id,
                "team_name": team.name,
                "thread_id": request.thread_id or "new",
                "user_query": request.message[:100] if request.message else "",
                "operation": "stream",
                **(request.context or {}),
            },
        ):
            # Log trace-level events
            async with span("request.init"):
                await log(LogLevel.INFO, "Stream started")
                if request.context:
                    await log(LogLevel.INFO, f"Request received with context: {request.context}")

            # Execute the streaming logic
            async for event in team.stream(
                request.message,
                thread_id=request.thread_id,
                context=request.context,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        sys.stdout.write(
            f"[TIMING] Team '{team_id}' stream completed at {time.strftime('%H:%M:%S')}"
        )
        sys.stdout.write(
            f"[TIMING] Team '{team_id}' total time: {duration_ms:.2f}ms ({duration_ms / 1000:.2f}s)"
        )

        yield f'data: {{"timing_ms": {round(duration_ms, 2)}}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
