"""
Playground Agent Routes.

Provides /api/agents/* endpoints for playground UI.
"""

from collections.abc import AsyncIterator
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class PlaygroundChatRequest(BaseModel):
    """Request body for playground chat."""

    message: str = Field(..., description="The message to send to the agent")
    thread_id: str | None = Field(None, description="Thread ID for conversation continuity")


class PlaygroundAgentResponse(BaseModel):
    """Agent info for playground."""

    id: str
    name: str
    description: str | None = None
    model: dict[str, Any] | None = None
    tools: list[str] = []
    instructions: str | None = None


# ============================================================================
# Router Factory
# ============================================================================


def create_agents_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for agent-related playground endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter for /agents endpoints
    """
    router = APIRouter(tags=["Playground - Agents"])

    @router.get("/agents", response_model=list[PlaygroundAgentResponse])
    async def list_agents() -> list[PlaygroundAgentResponse]:
        """List all agents for playground."""
        agents = []

        for name, agent in registry.agents.items():
            # Get tool names
            tool_names = []
            if hasattr(agent, "tools") and agent.tools:
                for tool in agent.tools:
                    if hasattr(tool, "name"):
                        tool_names.append(tool.name)
                    elif hasattr(tool, "__name__"):
                        tool_names.append(tool.__name__)

            # Get model info
            model_info = None
            if hasattr(agent, "model") and agent.model:
                model = agent.model
                model_info = {
                    "provider": getattr(model, "provider", type(model).__name__),
                    "model_id": getattr(model, "model", getattr(model, "model_id", "unknown")),
                }

            agents.append(
                PlaygroundAgentResponse(
                    id=getattr(agent, "id", None) or name,
                    name=name,
                    description=getattr(agent, "description", None),
                    model=model_info,
                    tools=tool_names,
                    instructions=getattr(agent, "instructions", None),
                )
            )

        return agents

    @router.get("/agents/{agent_id}", response_model=PlaygroundAgentResponse)
    async def get_agent(agent_id: str) -> PlaygroundAgentResponse:
        """Get agent details for playground."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        tool_names = []
        if hasattr(agent, "tools") and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, "name"):
                    tool_names.append(tool.name)
                elif hasattr(tool, "__name__"):
                    tool_names.append(tool.__name__)

        model_info = None
        if hasattr(agent, "model") and agent.model:
            model = agent.model
            model_info = {
                "provider": getattr(model, "provider", type(model).__name__),
                "model_id": getattr(model, "model", getattr(model, "model_id", "unknown")),
            }

        return PlaygroundAgentResponse(
            id=getattr(agent, "id", None) or agent_id,
            name=agent_id,
            description=getattr(agent, "description", None),
            model=model_info,
            tools=tool_names,
            instructions=getattr(agent, "instructions", None),
        )

    @router.post("/agents/{agent_id}/stream")
    async def stream_chat(
        agent_id: str,
        request: PlaygroundChatRequest,
    ) -> StreamingResponse:
        """Stream agent response for playground chat."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events."""
            try:
                invoke_kwargs: dict[str, Any] = {}
                if request.thread_id:
                    invoke_kwargs["thread_id"] = request.thread_id

                # Check if agent supports streaming
                if hasattr(agent, "stream"):
                    async for chunk in agent.stream(request.message, **invoke_kwargs):
                        data = {"content": str(chunk)}
                        yield f"data: {json.dumps(data)}\n\n"
                else:
                    # Fallback: invoke and send as single chunk
                    response = await agent.invoke(request.message, **invoke_kwargs)
                    data = {"content": str(response)}
                    yield f"data: {json.dumps(data)}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/agents/{agent_id}/chat")
    async def chat(
        agent_id: str,
        request: PlaygroundChatRequest,
    ) -> dict[str, Any]:
        """Non-streaming chat for playground."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        try:
            invoke_kwargs: dict[str, Any] = {}
            if request.thread_id:
                invoke_kwargs["thread_id"] = request.thread_id

            response = await agent.invoke(request.message, **invoke_kwargs)

            return {
                "id": "msg_" + str(hash(str(response)))[:8],
                "thread_id": request.thread_id,
                "role": "assistant",
                "content": str(response),
                "created_at": "",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return router
