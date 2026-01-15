"""
Playground Team Routes.

Provides /api/v1/teams/* endpoints for SDK and playground UI.
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


def create_teams_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for team-related endpoints.

    Args:
        registry: AgentRegistry with all teams

    Returns:
        FastAPI APIRouter for /api/v1/teams endpoints (playground routes)
    """

    router = APIRouter(prefix="/teams", tags=["Teams"])

    @router.get(
        "",
        response_model=list[dict[str, Any]],
        summary="List all teams",
        description="Returns a list of all available teams",
    )
    async def list_teams() -> list[dict[str, Any]]:
        """List all teams."""
        teams = []
        for team_id_key, team in registry.teams.items():
            model = team.model
            # Team.members is list[TeamMember], not dict
            members = getattr(team, "members", [])
            member_count = len(members) if isinstance(members, list) else 0
            actual_team_id = getattr(team, "id", None) or team_id_key
            # Safely get model_id - handle models without model_id attribute
            model_id = (
                getattr(model, "model_id", None)
                or getattr(model, "model", None)
                or str(type(model).__name__)
            )
            teams.append(
                {
                    "id": actual_team_id,
                    "name": getattr(team, "name", None) or team_id_key,
                    "description": getattr(team, "description", None),
                    "member_count": member_count,
                    "model": model_id,
                }
            )
        return teams

    @router.get(
        "/{team_id}",
        response_model=dict[str, Any],
        summary="Get team by ID",
        description="Returns detailed information for a specific team",
    )
    async def get_team(team_id: str) -> dict[str, Any]:
        """Get a specific team by ID."""
        team = registry.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

        model = team.model
        # Team.members is list[TeamMember], each has .agent property
        members = getattr(team, "members", [])
        actual_team_id = getattr(team, "id", None) or team_id

        # Format members list - each member is a TeamMember with .agent property
        members_list = []
        if isinstance(members, list):
            for member in members:
                # TeamMember has .agent which is the actual Agent/Team
                agent = getattr(member, "agent", member)
                # Get id from TeamMember or from the wrapped agent
                member_id = getattr(member, "id", None) or getattr(agent, "id", None) or "unknown"
                member_name = (
                    getattr(member, "name", None) or getattr(agent, "name", None) or member_id
                )
                member_desc = getattr(member, "description", None) or getattr(
                    agent, "description", ""
                )
                members_list.append(
                    {
                        "id": member_id,
                        "name": member_name,
                        "description": member_desc,
                        "enabled": getattr(member, "enabled", True),
                    }
                )

        # Get model information
        model_id = (
            getattr(model, "model_id", None)
            or getattr(model, "model", None)
            or str(type(model).__name__)
        )

        return {
            "id": actual_team_id,
            "name": getattr(team, "name", None) or team_id,
            "description": getattr(team, "description", None),
            "member_count": len(members_list),
            "model": model_id,
            "members": members_list,
            "configuration": {
                "timeout": getattr(team, "timeout", 300.0),
                "max_retries": getattr(team, "max_retries", 2),
            },
        }

    @router.post(
        "/{team_id}/generate",
        summary="Generate team response",
        description="Invoke team with a message and get a complete response",
    )
    async def generate_team_response(
        team_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a response from the team."""
        team = registry.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

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
            logger.info(f"[{request_id}] Generating response from team '{team_id}'")

            # Invoke team
            response = await team.invoke(message, **invoke_kwargs)

            logger.info(f"[{request_id}] Response generated successfully")

            return {
                "content": str(response),
                "thread_id": thread_id,
            }

        except Exception as err:
            logger.error(f"Error in generate: {err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {err}") from err

    @router.post(
        "/{team_id}/stream",
        summary="Stream team response",
        description="Invoke team and stream the response via Server-Sent Events",
    )
    async def stream_team_response(
        team_id: str,
        request: dict[str, Any],
    ) -> StreamingResponse:
        """Stream a response from the team using SSE."""
        team = registry.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events with team execution support."""
            try:
                # Extract message
                message = request.get("message")
                if not message:
                    raise ValueError("Missing required field: message")

                # Build invoke kwargs (no stream flag needed - we're calling team.stream() directly)
                invoke_kwargs: dict[str, Any] = {}
                thread_id = request.get("thread_id")
                if thread_id:
                    invoke_kwargs["thread_id"] = thread_id
                if "temperature" in request:
                    invoke_kwargs["temperature"] = request["temperature"]
                if "max_tokens" in request:
                    invoke_kwargs["max_tokens"] = request["max_tokens"]

                # Send thinking event
                yield f"event: thinking\ndata: {json.dumps({'status': 'thinking'})}\n\n"

                # Check if team supports streaming
                if hasattr(team, "stream"):
                    # Use native stream method
                    async for chunk in team.stream(message, **invoke_kwargs):
                        # Check if this is a StreamEvent
                        if hasattr(chunk, "event_type") and hasattr(chunk, "data"):
                            event_type = chunk.event_type
                            event_data = chunk.data  # StreamEvent.data is already a dict

                            if event_type == "status":
                                yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
                            elif event_type == "code_generated":
                                yield f"event: code_generated\ndata: {json.dumps(event_data)}\n\n"
                            elif event_type == "tool_call":
                                yield f"event: tool_call\ndata: {json.dumps(event_data)}\n\n"
                            elif event_type == "tool_result":
                                yield f"event: tool_result\ndata: {json.dumps(event_data)}\n\n"
                            elif event_type == "content":
                                # Content event has "text" key - convert to "content" for frontend
                                text = event_data.get("text", "")
                                yield f"event: token\ndata: {json.dumps({'content': text})}\n\n"
                            elif event_type == "error":
                                yield f"event: error\ndata: {json.dumps(event_data)}\n\n"
                            elif event_type == "done":
                                # Don't yield done here, we'll yield it after the loop
                                pass
                            else:
                                # Unknown event type - pass through as-is
                                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                        else:
                            # Regular string content
                            chunk_str = str(chunk)
                            if chunk_str:
                                yield f"event: token\ndata: {json.dumps({'content': chunk_str})}\n\n"

                    # Ensure messages are flushed to storage after streaming completes
                    if thread_id and hasattr(team, "storage") and team.storage:
                        if hasattr(team.storage, "queue"):
                            await team.storage.queue.flush()
                else:
                    # Fallback: invoke and send as single chunk
                    response = await team.invoke(message, **invoke_kwargs)
                    data = {"content": str(response)}
                    yield f"event: token\ndata: {json.dumps(data)}\n\n"

                    # Ensure messages are flushed for non-streaming too
                    if thread_id and hasattr(team, "storage") and team.storage:
                        if hasattr(team.storage, "queue"):
                            await team.storage.queue.flush()

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
