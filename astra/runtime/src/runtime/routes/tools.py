"""Tool definition routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from framework.storage.client import StorageClient
from framework.storage.stores.tool_definition import ToolDefinitionStore
from pydantic import BaseModel


router = APIRouter(prefix="/tools", tags=["tools"])


class ToolUpdateRequest(BaseModel):
    """Request body for updating a tool definition."""

    name: str | None = None
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    is_active: bool | None = None


class ToolResponse(BaseModel):
    """Tool definition response."""

    id: str
    slug: str
    name: str
    source: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    required_fields: list[str] | None = None
    version: str | None = None
    is_active: bool = True
    hash: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ToolListResponse(BaseModel):
    """Response for listing tools."""

    tools: list[ToolResponse]
    total: int
    page: int
    page_size: int


def _get_storage() -> StorageClient | None:
    """Get storage client from registry."""
    from runtime.registry import storage_registry

    return storage_registry.get_default()


def _tool_to_response(tool) -> ToolResponse:
    """Convert ToolDefinition to response."""
    return ToolResponse(
        id=str(tool.id) if tool.id else "",
        slug=tool.slug,
        name=tool.name,
        source=tool.source,
        description=tool.description,
        input_schema=tool.input_schema,
        output_schema=tool.output_schema,
        required_fields=tool.required_fields,
        version=tool.version,
        is_active=tool.is_active,
        hash=tool.hash,
        created_at=tool.created_at.isoformat() if tool.created_at else None,
        updated_at=tool.updated_at.isoformat() if tool.updated_at else None,
    )


@router.get("/")
async def list_tools(
    request: Request,
    search: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ToolListResponse:
    """
    List all tool definitions.

    Query params:
    - search: Filter by name/description
    - source: Filter by source (e.g., "local", "mcp:filesystem")
    - page: Page number (1-indexed)
    - page_size: Items per page
    """
    storage = _get_storage()
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not configured")

    store = ToolDefinitionStore(storage.storage)

    # Get all tools (we'll filter in memory for now, can optimize with DB query later)
    if source:
        tools = await store.get_by_source(source)
    else:
        tools = await store.get_all(limit=1000)

    # Apply search filter
    if search:
        search_lower = search.lower()
        tools = [
            t
            for t in tools
            if search_lower in t.name.lower()
            or (t.description and search_lower in t.description.lower())
            or search_lower in t.slug.lower()
        ]

    # Pagination
    total = len(tools)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = tools[start:end]

    return ToolListResponse(
        tools=[_tool_to_response(t) for t in paginated],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}")
async def get_tool(request: Request, slug: str) -> ToolResponse:
    """Get a single tool definition by slug."""
    storage = _get_storage()
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not configured")

    store = ToolDefinitionStore(storage.storage)
    tool = await store.get_by_name(slug)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{slug}' not found")

    return _tool_to_response(tool)


@router.put("/{slug}")
async def update_tool(request: Request, slug: str, body: ToolUpdateRequest) -> ToolResponse:
    """Update a tool definition."""
    storage = _get_storage()
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not configured")

    store = ToolDefinitionStore(storage.storage)
    tool = await store.get_by_name(slug)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{slug}' not found")

    # Build update fields
    update_fields = {}
    if body.name is not None:
        update_fields["name"] = body.name
    if body.description is not None:
        update_fields["description"] = body.description
    if body.input_schema is not None:
        update_fields["input_schema"] = body.input_schema
    if body.output_schema is not None:
        update_fields["output_schema"] = body.output_schema
    if body.is_active is not None:
        update_fields["is_active"] = body.is_active

    if not update_fields:
        return _tool_to_response(tool)

    updated = await store.update(tool.id, **update_fields)  # type: ignore
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update tool")

    from runtime.sync.tool_cache import invalidate_agent_cache, invalidate_team_cache

    # Tool definitions feed prompt-time tool schema; clear in-process caches immediately.
    invalidate_agent_cache()
    invalidate_team_cache()

    return _tool_to_response(updated)


@router.delete("/{slug}")
async def delete_tool(request: Request, slug: str) -> dict[str, str]:
    """Delete a tool definition."""
    storage = _get_storage()
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not configured")

    store = ToolDefinitionStore(storage.storage)
    tool = await store.get_by_name(slug)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{slug}' not found")

    await store.delete(tool.id)  # type: ignore

    from runtime.sync.tool_cache import invalidate_agent_cache, invalidate_team_cache

    invalidate_agent_cache()
    invalidate_team_cache()

    return {"message": f"Tool '{slug}' deleted"}


@router.post("/sync")
async def sync_tools(request: Request) -> dict[str, Any]:
    """Trigger manual re-sync of tools. Returns sync report."""
    runtime = getattr(request.app.state, "astra_server", None)
    if not runtime:
        raise HTTPException(status_code=503, detail="Runtime not available")

    storage = _get_storage()
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not configured")

    startup_sync_config = getattr(request.app.state, "startup_sync_config", None)

    # Sync tools to DB
    report = await runtime.sync_tools(
        mcp_list_timeout_seconds=float(getattr(startup_sync_config, "mcp_list_timeout_seconds", 10.0)),
        mcp_retries=int(getattr(startup_sync_config, "mcp_retries", 2)),
        mcp_retry_backoff_seconds=float(
            getattr(startup_sync_config, "mcp_retry_backoff_seconds", 0.5)
        ),
    )

    from runtime.sync.tool_cache import invalidate_agent_cache, invalidate_team_cache

    invalidate_agent_cache()
    invalidate_team_cache()

    return {
        "message": "Tools synced",
        "report": report,
    }
