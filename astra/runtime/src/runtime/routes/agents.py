"""Agent routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from runtime.registry import agent_registry


router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    """Request body for running an agent."""

    message: str
    thread_id: str | None = None


class AgentResponse(BaseModel):
    """Agent details response."""

    id: str
    name: str
    description: str | None = None


@router.get("/")
async def list_agents() -> list[AgentResponse]:
    """List all registered agents."""
    agents = agent_registry.list_all()
    return [
        AgentResponse(
            id=agent.id or agent.name,
            name=agent.name,
            description=agent.description,
        )
        for agent in agents
    ]


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> AgentResponse:
    """Get agent details by ID."""
    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return AgentResponse(
        id=agent.id or agent.name,
        name=agent.name,
        description=agent.description,
    )


@router.post("/{agent_id}/invoke")
async def run_agent(agent_id: str, request: AgentRunRequest):
    """Run an agent synchronously."""
    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    # Run the agent
    response = await agent.invoke(request.message)
    return {"response": response}


@router.post("/{agent_id}/stream")
async def stream_agent(agent_id: str, request: AgentRunRequest):
    """Stream an agent response using SSE."""
    from fastapi.responses import StreamingResponse

    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    async def generate():
        async for event in agent.stream(request.message):
            yield f"data: {event.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
