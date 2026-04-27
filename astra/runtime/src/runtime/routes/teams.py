"""Team routes."""

import sys
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
            id=team.id,
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
        id=team.id,
        name=team.name,
        description=team.description,
    )


async def _build_team_context(team_id: str, user_context: dict[str, Any] | None) -> dict[str, Any]:
    """Build context with tool_definitions for team execution."""
    from runtime.sync.tool_cache import get_team_tool_definitions

    tool_definitions = await get_team_tool_definitions(team_id)
    context = dict(user_context or {})
    context["tool_definitions"] = tool_definitions

    return context


@router.post("/{team_id}/invoke")
async def run_team(team_id: str, request: TeamRunRequest):
    """Run a team synchronously."""
    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    start_time = time.time()
    sys.stdout.write(f"[TIMING] Team '{team_id}' invoke started\n")

    context = await _build_team_context(team_id, request.context)

    response = await team.invoke(request.message, thread_id=request.thread_id, context=context)

    duration_ms = (time.time() - start_time) * 1000
    sys.stdout.write(f"[TIMING] Team '{team_id}' invoke completed in {duration_ms:.2f}ms\n")

    return {"response": response, "timing_ms": round(duration_ms, 2)}


@router.post("/{team_id}/stream")
async def stream_team(team_id: str, request: TeamRunRequest):
    """Stream a team response using SSE."""
    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    context = await _build_team_context(team_id, request.context)

    async def generate():
        start_time = time.time()
        sys.stdout.write(f"[TIMING] Team '{team_id}' stream started\n")

        async for event in team.stream(
            request.message,
            thread_id=request.thread_id,
            context=context,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

        duration_ms = (time.time() - start_time) * 1000
        sys.stdout.write(f"[TIMING] Team '{team_id}' stream completed in {duration_ms:.2f}ms\n")

        yield f'data: {{"timing_ms": {round(duration_ms, 2)}}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
