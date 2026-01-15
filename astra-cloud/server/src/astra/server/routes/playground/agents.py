"""
Playground Agent Routes.

Provides /api/v1/agents/* endpoints for SDK and playground UI.
"""

from collections.abc import AsyncIterator
import json
import logging
from typing import Any
import uuid

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


def create_agents_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for agent-related endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter for /api/v1/agents endpoints (playground routes)
    """

    router = APIRouter(prefix="/agents", tags=["Agents"])

    @router.get(
        "",
        response_model=list[dict[str, Any]],
        summary="List all agents",
        description="Returns a list of all available agents",
    )
    async def list_agents() -> list[dict[str, Any]]:
        """List all agents."""
        agents = []
        for agent_id_key, agent in registry.agents.items():
            model = agent.model
            tools = getattr(agent, "tools", None) or []
            tools_length = len(tools)
            actual_agent_id = getattr(agent, "id", None) or agent_id_key
            # Safely get model_id - handle models without model_id attribute
            model_id = (
                getattr(model, "model_id", None)
                or getattr(model, "model", None)
                or str(type(model).__name__)
            )
            agents.append(
                {
                    "id": actual_agent_id,
                    "name": getattr(agent, "name", None) or agent_id_key,
                    "description": getattr(agent, "description", None),
                    "model": model_id,
                    "tools": tools_length,
                }
            )
        return agents

    @router.get(
        "/{agent_id}",
        response_model=dict[str, Any],
        summary="Get agent by ID",
        description="Returns details for a specific agent",
    )
    async def get_agent(agent_id: str) -> dict[str, Any]:
        """Get a specific agent by ID."""
        agent = registry.get_agent(agent_id)
        if not agent:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        model = agent.model
        tools = getattr(agent, "tools", None) or []
        tools_length = len(tools)
        actual_agent_id = getattr(agent, "id", None) or agent_id

        return {
            "id": actual_agent_id,
            "name": getattr(agent, "name", None) or agent_id,
            "description": getattr(agent, "description", None),
            "model": model.model_id,
            "tools": tools_length,
            "instructions": getattr(agent, "instructions", None),
        }

    @router.post(
        "/{agent_id}/generate",
        summary="Generate agent response",
        description="Invoke agent with a message and get a complete response",
    )
    async def generate_agent_response(
        agent_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a response from the agent."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        # Extract message (required)
        message = request.get("message")
        if not message:
            raise HTTPException(status_code=400, detail="Missing required field: message")

        # Build invoke kwargs
        invoke_kwargs: dict[str, Any] = {}
        thread_id = request.get("thread_id")
        if thread_id:
            invoke_kwargs["thread_id"] = thread_id
        if "temperature" in request:
            invoke_kwargs["temperature"] = request["temperature"]
        if "max_tokens" in request:
            invoke_kwargs["max_tokens"] = request["max_tokens"]

        try:
            request_id = str(uuid.uuid4())[:8]
            logger.info(f"[{request_id}] Generating response from '{agent_id}'")

            # Invoke agent
            response = await agent.invoke(message, **invoke_kwargs)

            logger.info(f"[{request_id}] Response generated successfully")

            return {
                "content": str(response),
                "thread_id": thread_id,
            }

        except Exception as err:
            logger.error(f"Error in generate: {err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {err}") from err

    @router.post(
        "/{agent_id}/stream",
        summary="Stream agent response",
        description="Invoke agent and stream the response via Server-Sent Events",
    )
    async def stream_agent_response(
        agent_id: str,
        request: dict[str, Any],
    ) -> StreamingResponse:
        """Stream a response from the agent using SSE."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events with tool call support."""
            try:
                # Extract message
                message = request.get("message")
                if not message:
                    raise ValueError("Missing required field: message")

                # Build invoke kwargs
                invoke_kwargs: dict[str, Any] = {"stream": True}
                thread_id = request.get("thread_id")
                if thread_id:
                    invoke_kwargs["thread_id"] = thread_id
                if "temperature" in request:
                    invoke_kwargs["temperature"] = request["temperature"]
                if "max_tokens" in request:
                    invoke_kwargs["max_tokens"] = request["max_tokens"]

                # Send thinking event
                yield f"event: thinking\ndata: {json.dumps({'status': 'thinking'})}\n\n"

                # Check if agent supports streaming
                if hasattr(agent, "stream"):
                    # Use native stream method
                    async for chunk in agent.stream(message, **invoke_kwargs):
                        chunk_str = str(chunk)

                        # Check if this is a StreamEvent (tool-related)
                        if hasattr(chunk, "event_type"):
                            event_type = chunk.event_type
                            if event_type == "tool_start":
                                data = {
                                    "tool_name": chunk.tool_name,
                                    "tool_id": chunk.tool_id,
                                    "arguments": chunk.arguments,
                                }
                                yield f"event: tool_start\ndata: {json.dumps(data)}\n\n"
                            elif event_type == "tool_result":
                                data = {
                                    "tool_name": chunk.tool_name,
                                    "tool_id": chunk.tool_id,
                                    "result": chunk.result,
                                    "success": chunk.success,
                                }
                                yield f"event: tool_result\ndata: {json.dumps(data)}\n\n"
                            continue

                        # Regular content token
                        if chunk_str:
                            data = {"content": chunk_str}
                            yield f"event: token\ndata: {json.dumps(data)}\n\n"

                    # Ensure messages are flushed to storage after streaming completes
                    if thread_id and hasattr(agent, "storage") and agent.storage:
                        if hasattr(agent.storage, "queue"):
                            await agent.storage.queue.flush()
                else:
                    # Fallback: invoke and send as single chunk
                    response = await agent.invoke(message, **invoke_kwargs)
                    data = {"content": str(response)}
                    yield f"event: token\ndata: {json.dumps(data)}\n\n"

                    # Ensure messages are flushed for non-streaming too
                    if thread_id and hasattr(agent, "storage") and agent.storage:
                        if hasattr(agent.storage, "queue"):
                            await agent.storage.queue.flush()

                # Send done event
                yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

            except Exception as e:
                logger.error(f"Error in stream: {e}", exc_info=True)
                error_data = {"error": str(e)}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
