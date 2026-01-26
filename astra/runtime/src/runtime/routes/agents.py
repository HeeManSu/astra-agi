"""Agent routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from runtime.registry import agent_registry


router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    """Request body for running an agent."""

    message: str
    thread_id: str | None = None
    context: dict[str, Any] | None = None


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
    import time

    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    start_time = time.time()
    print(f"[TIMING] Agent '{agent_id}' invoke started at {time.strftime('%H:%M:%S')}")

    # Run the agent with optional thread_id for message persistence
    response = await agent.invoke(
        request.message, thread_id=request.thread_id, context=request.context
    )

    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    print(f"[TIMING] Agent '{agent_id}' invoke completed at {time.strftime('%H:%M:%S')}")
    print(
        f"[TIMING] Agent '{agent_id}' total time: {duration_ms:.2f}ms ({duration_ms / 1000:.2f}s)"
    )

    return {"response": response, "timing_ms": round(duration_ms, 2)}


@router.post("/{agent_id}/stream")
async def stream_agent(agent_id: str, request: AgentRunRequest, http_request: Request):
    """Stream an agent response using SSE."""
    import time

    from fastapi.responses import StreamingResponse
    from observability import LogLevel, log, span, trace

    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    async def generate():
        start_time = time.time()
        print(f"[TIMING] Agent '{agent_id}' stream started at {time.strftime('%H:%M:%S')}")

        # Use ContextVar-based trace (works even if observability not initialized)
        async with trace(
            f"agent.{agent_id}.stream",
            attributes={
                "agent_id": agent_id,
                "agent_name": agent.name,
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
            async for event in agent.stream(
                request.message,
                thread_id=request.thread_id,
                context=request.context,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        print(f"[TIMING] Agent '{agent_id}' stream completed at {time.strftime('%H:%M:%S')}")
        print(
            f"[TIMING] Agent '{agent_id}' total time: {duration_ms:.2f}ms ({duration_ms / 1000:.2f}s)"
        )

        yield f'data: {{"timing_ms": {round(duration_ms, 2)}}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
