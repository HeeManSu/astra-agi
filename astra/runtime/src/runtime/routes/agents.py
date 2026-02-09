"""Agent routes."""

import sys
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


async def _build_agent_context(
    agent_id: str, user_context: dict[str, Any] | None
) -> dict[str, Any]:
    """Build context with tool_definitions for agent execution."""
    from runtime.sync.tool_cache import get_agent_tool_definitions

    # Fetch tool definitions (lazy-cached)
    tool_definitions = await get_agent_tool_definitions(agent_id)

    # Merge with user context
    context = dict(user_context or {})
    context["tool_definitions"] = tool_definitions

    return context


@router.post("/{agent_id}/invoke")
async def run_agent(agent_id: str, request: AgentRunRequest):
    """Run an agent synchronously."""
    import time

    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    start_time = time.time()
    sys.stdout.write(f"[TIMING] Agent '{agent_id}' invoke started\n")

    # Build context with tool_definitions
    context = await _build_agent_context(agent_id, request.context)

    response = await agent.invoke(request.message, thread_id=request.thread_id, context=context)

    duration_ms = (time.time() - start_time) * 1000
    sys.stdout.write(f"[TIMING] Agent '{agent_id}' invoke completed in {duration_ms:.2f}ms\n")

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

    # Build context with tool_definitions (before generator to fail fast)
    context = await _build_agent_context(agent_id, request.context)

    async def generate():
        start_time = time.time()
        sys.stdout.write(f"[TIMING] Agent '{agent_id}' stream started\n")

        async with trace(
            f"agent.{agent_id}.stream",
            attributes={
                "agent_id": agent_id,
                "agent_name": agent.name,
                "thread_id": request.thread_id or "new",
                "user_query": request.message[:100] if request.message else "",
                "operation": "stream",
            },
        ):
            async with span("request.init"):
                await log(LogLevel.INFO, "Stream started")
                await log(
                    LogLevel.DEBUG,
                    f"Tool definitions loaded: {len(context.get('tool_definitions', {}))}",
                )

            async for event in agent.stream(
                request.message,
                thread_id=request.thread_id,
                context=context,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

        duration_ms = (time.time() - start_time) * 1000
        sys.stdout.write(f"[TIMING] Agent '{agent_id}' stream completed in {duration_ms:.2f}ms\n")

        yield f'data: {{"timing_ms": {round(duration_ms, 2)}}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
