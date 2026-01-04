"""
Agent Routes for Astra Server.

Provides /v1/agents endpoints for listing, generating, streaming, and ingesting.
"""

from collections.abc import AsyncIterator
import json
import logging
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class GenerateRequest(BaseModel):
    """Request body for agent generation."""

    message: str = Field(..., description="The message to send to the agent")
    thread_id: str | None = Field(None, description="Thread ID for conversation continuity")
    context: dict[str, Any] | None = Field(None, description="User-provided context")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(None, gt=0, description="Maximum tokens to generate")


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GenerateResponse(BaseModel):
    """Response from agent generation."""

    content: str
    thread_id: str | None = None
    usage: UsageInfo | None = None
    tool_calls: list[dict[str, Any]] | None = None


class IngestRequest(BaseModel):
    """Request body for RAG ingestion."""

    text: str | None = Field(None, description="Text content to ingest")
    url: str | None = Field(None, description="URL to ingest content from")
    path: str | None = Field(None, description="File path to ingest")
    name: str | None = Field(None, description="Name for the content")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class IngestResponse(BaseModel):
    """Response from RAG ingestion."""

    success: bool
    content_id: str | None = None
    message: str


class AgentDetailResponse(BaseModel):
    """Detailed agent information."""

    name: str
    id: str | None = None
    description: str | None = None
    instructions: str | None = None
    tools: list[str] = []
    has_memory: bool = False
    has_rag: bool = False


# ============================================================================
# Router Factory
# ============================================================================


def create_agent_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for agent endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter
    """
    router = APIRouter(prefix="/v1/agents", tags=["Agents"])

    @router.get(
        "",
        response_model=list[AgentDetailResponse],
        summary="List all agents",
        description="Returns a list of all available agents with their configuration",
    )
    async def list_agents() -> list[AgentDetailResponse]:
        """List all registered agents."""
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

            agents.append(
                AgentDetailResponse(
                    name=name,
                    id=getattr(agent, "id", None) or name,
                    description=getattr(agent, "description", None),
                    instructions=_get_truncated_instructions(agent),
                    tools=tool_names,
                    has_memory=bool(getattr(agent, "storage", None)),
                    has_rag=bool(getattr(agent, "rag_pipeline", None)),
                )
            )

        return agents

    @router.get(
        "/{agent_name}",
        response_model=AgentDetailResponse,
        summary="Get agent details",
        description="Returns detailed information about a specific agent",
    )
    async def get_agent(agent_name: str) -> AgentDetailResponse:
        """Get details for a specific agent."""
        agent = registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        tool_names = []
        if hasattr(agent, "tools") and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, "name"):
                    tool_names.append(tool.name)
                elif hasattr(tool, "__name__"):
                    tool_names.append(tool.__name__)

        return AgentDetailResponse(
            name=agent_name,
            id=getattr(agent, "id", None) or agent_name,
            description=getattr(agent, "description", None),
            instructions=_get_truncated_instructions(agent),
            tools=tool_names,
            has_memory=bool(getattr(agent, "storage", None)),
            has_rag=bool(getattr(agent, "rag_pipeline", None)),
        )

    @router.post(
        "/{agent_name}/generate",
        response_model=GenerateResponse,
        summary="Generate agent response",
        description="Invoke agent with a message and get a complete response",
    )
    async def generate(
        agent_name: str,
        request: GenerateRequest,
    ) -> GenerateResponse:
        """Generate a response from the agent."""
        agent = registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Build invoke kwargs
        invoke_kwargs: dict[str, Any] = {}
        if request.thread_id:
            invoke_kwargs["thread_id"] = request.thread_id
        if request.context:
            invoke_kwargs["context"] = request.context
        if request.temperature is not None:
            invoke_kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            invoke_kwargs["max_tokens"] = request.max_tokens

        try:
            # Generate request ID for logging
            request_id = str(uuid.uuid4())[:8]
            logger.info(f"[{request_id}] Generating response from '{agent_name}'")

            # Invoke agent
            response = await agent.invoke(request.message, **invoke_kwargs)

            # Extract usage if available
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = UsageInfo(
                    prompt_tokens=getattr(response.usage, "prompt_tokens", 0),
                    completion_tokens=getattr(response.usage, "completion_tokens", 0),
                    total_tokens=getattr(response.usage, "total_tokens", 0),
                )

            # Extract tool calls if available
            tool_calls = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = response.tool_calls

            logger.info(f"[{request_id}] Response generated successfully")

            return GenerateResponse(
                content=str(response),
                thread_id=request.thread_id,
                usage=usage,
                tool_calls=tool_calls,
            )

        except (ValidationError, ValueError) as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        except Exception as err:
            logger.error(f"Error in generate: {err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {err}") from err

    @router.post(
        "/{agent_name}/stream",
        summary="Stream agent response",
        description="Invoke agent and stream the response via Server-Sent Events",
    )
    async def stream(
        agent_name: str,
        request: GenerateRequest,
    ) -> StreamingResponse:
        """Stream a response from the agent using SSE."""
        agent = registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events."""
            try:
                # Build invoke kwargs
                invoke_kwargs: dict[str, Any] = {"stream": True}
                if request.thread_id:
                    invoke_kwargs["thread_id"] = request.thread_id
                if request.context:
                    invoke_kwargs["context"] = request.context
                if request.temperature is not None:
                    invoke_kwargs["temperature"] = request.temperature
                if request.max_tokens is not None:
                    invoke_kwargs["max_tokens"] = request.max_tokens

                # Check if agent supports streaming
                if hasattr(agent, "stream"):
                    # Use native stream method
                    async for chunk in agent.stream(request.message, **invoke_kwargs):
                        data = {"content": str(chunk)}
                        yield f"event: token\ndata: {json.dumps(data)}\n\n"
                else:
                    # Fallback: invoke and send as single chunk
                    response = await agent.invoke(request.message, **invoke_kwargs)
                    data = {"content": str(response)}
                    yield f"event: token\ndata: {json.dumps(data)}\n\n"

                # Send done event
                yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

            except Exception as e:
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

    @router.post(
        "/{agent_name}/ingest",
        response_model=IngestResponse,
        summary="Ingest content to agent's RAG",
        description="Ingest content into the agent's knowledge base",
    )
    async def ingest(
        agent_name: str,
        request: IngestRequest,
    ) -> IngestResponse:
        """Ingest content into agent's RAG pipeline."""
        agent = registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Check if agent has RAG
        if not hasattr(agent, "rag_pipeline") or agent.rag_pipeline is None:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{agent_name}' does not have RAG configured",
            )

        # Validate request
        if not any([request.text, request.url, request.path]):
            raise HTTPException(
                status_code=400,
                detail="At least one of 'text', 'url', or 'path' must be provided",
            )

        try:
            # Ingest via agent's rag_pipeline
            content_id = await agent.ingest(
                text=request.text,
                url=request.url,
                path=request.path,
                name=request.name,
                metadata=request.metadata,
            )

            return IngestResponse(
                success=True,
                content_id=content_id,
                message="Content ingested successfully",
            )

        except Exception as e:
            logger.error(f"Ingestion error for '{agent_name}': {e}")
            return IngestResponse(
                success=False,
                content_id=None,
                message=f"Ingestion failed: {e!s}",
            )

    return router


def _get_truncated_instructions(agent: Any, max_length: int = 200) -> str | None:
    """Get truncated instructions from agent."""
    instructions = getattr(agent, "instructions", None)
    if not instructions:
        return None

    if len(instructions) > max_length:
        return instructions[:max_length] + "..."

    return instructions
