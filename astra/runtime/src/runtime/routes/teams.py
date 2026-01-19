"""Team routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from runtime.registry import team_registry


router = APIRouter(prefix="/teams", tags=["teams"])


class TeamRunRequest(BaseModel):
    """Request body for running a team."""

    message: str
    thread_id: str | None = None


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
    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    # Run the team with optional thread_id for message persistence
    response = await team.invoke(request.message, thread_id=request.thread_id)
    return {"response": response}


@router.post("/{team_id}/stream")
async def stream_team(team_id: str, request: TeamRunRequest):
    """Stream a team response using SSE."""
    from fastapi.responses import StreamingResponse

    team = team_registry.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    async def generate():
        async for event in team.stream(request.message, thread_id=request.thread_id):
            yield f"data: {event.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
