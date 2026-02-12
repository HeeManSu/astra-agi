"""
Tool Sync for Astra Runtime.

Syncs tools to DB at server startup:
1. Introspect local tools
2. Use already-connected MCP servers to list/describe tools
3. Normalize to ToolDefinition
4. Hash and upsert with versioning
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import sys
from typing import TYPE_CHECKING, Any

from framework.storage.models import ToolDefinition
from framework.tool.mcp.toolkit import MCPToolkit


if TYPE_CHECKING:
    from framework.storage.client import StorageClient
    from framework.tool import Tool


@dataclass
class SyncReport:
    """Report of tools synced to DB."""

    local_synced: int = 0
    local_unchanged: int = 0
    mcp_synced: dict[str, int] = field(default_factory=dict)
    mcp_unchanged: dict[str, int] = field(default_factory=dict)
    mcp_failed: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        mcp_servers = sorted(set(self.mcp_synced) | set(self.mcp_unchanged) | set(self.mcp_failed))
        return {
            "local": {
                "synced": self.local_synced,
                "unchanged": self.local_unchanged,
            },
            "mcp": {
                server: {
                    "synced": self.mcp_synced.get(server, 0),
                    "unchanged": self.mcp_unchanged.get(server, 0),
                    "status": "failed" if server in self.mcp_failed else "ok",
                    "error": self.mcp_failed.get(server),
                }
                for server in mcp_servers
            },
            "total_synced": self.local_synced + sum(self.mcp_synced.values()),
            "total_unchanged": self.local_unchanged + sum(self.mcp_unchanged.values()),
            "total_failed_mcp_servers": len(self.mcp_failed),
        }


@dataclass
class MCPSyncResult:
    """Per-server MCP sync result."""

    server: str
    synced: int = 0
    unchanged: int = 0
    error: str | None = None


def compute_tool_hash(definition: dict[str, Any]) -> str:
    """Compute a deterministic hash of tool schema for change detection."""
    hashable = {
        "name": definition.get("name"),
        "slug": definition.get("slug"),
        "source": definition.get("source"),
        "description": definition.get("description"),
        "input_schema": definition.get("input_schema"),
        "output_schema": definition.get("output_schema"),
        "required_fields": definition.get("required_fields"),
        "example": definition.get("example"),
    }
    canonical = json.dumps(hashable, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


def bump_version(version: str) -> str:
    """Bump the patch version (1.0.0 -> 1.0.1)."""
    parts = version.split(".")
    if len(parts) != 3:
        return "1.0.1"
    major, minor, patch = parts
    return f"{major}.{minor}.{int(patch) + 1}"


async def sync_local_tools(
    storage: StorageClient,
    tools: list[Tool],
    source: str = "local",
) -> tuple[int, int]:
    """
    Introspect and sync local Python tools to DB.

    Args:
        storage: Storage client
        tools: List of Tool instances to sync
        source: Source identifier (default: "local")

    Returns:
        Tuple of (synced_count, unchanged_count)
    """
    from framework.storage.stores.tool_definition import ToolDefinitionStore

    definition_storage = ToolDefinitionStore(storage.storage)
    synced = 0
    unchanged = 0
    to_save: list[ToolDefinition] = []

    # Batch get existing tool hashes
    tool_slugs: list[str] = []
    seen_local_slugs: dict[str, int] = {}
    for tool in tools:
        raw_tool_slug = getattr(tool, "slug", None)
        if not isinstance(raw_tool_slug, str) or not raw_tool_slug.strip():
            raise ValueError("Local tool is missing slug during sync. Ensure tool.slug is set.")
        tool_slug = f"{source}-{raw_tool_slug.strip()}".lower().replace("_", "-")
        existing_obj_id = seen_local_slugs.get(tool_slug)
        if existing_obj_id is not None and existing_obj_id != id(tool):
            raise ValueError(f"Duplicate local tool slug '{tool_slug}' detected during sync.")
        seen_local_slugs[tool_slug] = id(tool)
        tool_slugs.append(tool_slug)

    existing_hashes = await definition_storage.get_hashes_by_slugs(tool_slugs)
    existing_tools = await definition_storage.get_by_slugs(tool_slugs)

    for tool, tool_slug in zip(tools, tool_slugs, strict=False):
        required_fields = list(tool.parameters.get("required", [])) if tool.parameters else []

        definition_dict = {
            "slug": tool_slug,
            "name": tool.name,
            "source": source,
            "description": tool.description or "",
            "input_schema": tool.parameters,
            "output_schema": tool.output_schema.model_json_schema() if tool.output_schema else None,
            "required_fields": required_fields,
            "example": tool.example,
        }

        content_hash = compute_tool_hash(definition_dict)
        existing_hash = existing_hashes.get(tool_slug)

        if existing_hash == content_hash:
            unchanged += 1
            continue

        existing = existing_tools.get(tool_slug)

        if existing:
            new_version = bump_version(existing.version)
            definition = ToolDefinition(
                **definition_dict, hash=content_hash, version=new_version, is_active=True
            )
        else:
            definition = ToolDefinition(
                **definition_dict, hash=content_hash, version="1.0.0", is_active=True
            )

        to_save.append(definition)
        synced += 1

    # Bulk save
    if to_save:
        await definition_storage.save_many(to_save)

    return synced, unchanged


async def _sync_single_mcp(
    mcp: MCPToolkit,
    definition_storage: Any,
    source: str = "mcp",
    *,
    list_timeout_seconds: float = 10.0,
    retries: int = 2,
    retry_backoff_seconds: float = 0.5,
) -> MCPSyncResult:
    """
    Sync a single MCP server.

    NOTE: MCP must already be connected (long-lived connections from lifespan).

    Returns: (name, synced, unchanged)
    """
    raw_mcp_slug = getattr(mcp, "slug", None)
    if not isinstance(raw_mcp_slug, str) or not raw_mcp_slug.strip():
        return MCPSyncResult(server=mcp.name, error="MCP toolkit missing slug")
    mcp_source = f"{source}:{raw_mcp_slug.strip()}"
    synced = 0
    unchanged = 0
    to_save: list[ToolDefinition] = []

    # Use existing connection (already connected in lifespan), with bounded retries.
    attempts = max(retries, 0) + 1
    tools: list[dict[str, Any]] | None = None
    for attempt in range(attempts):
        try:
            tools = await asyncio.wait_for(mcp.list_tools(), timeout=list_timeout_seconds)
            break
        except Exception as e:  # noqa: PERF203
            if attempt < attempts - 1:
                await asyncio.sleep(retry_backoff_seconds * (2**attempt))
                continue
            return MCPSyncResult(
                server=mcp.name,
                error=f"list_tools failed after {attempts} attempts: {e}",
            )

    if tools is None:
        return MCPSyncResult(server=mcp.name, error="list_tools returned no tools")

    # Batch get existing tool hashes
    tool_slugs = [f"{mcp_source}-{t['name']}".lower().replace("_", "-") for t in tools]
    if len(tool_slugs) != len(set(tool_slugs)):
        return MCPSyncResult(server=mcp.name, error="MCP list_tools returned duplicate tool names")
    existing_hashes = await definition_storage.get_hashes_by_slugs(tool_slugs)
    existing_tools = await definition_storage.get_by_slugs(tool_slugs)

    for tool_info in tools:
        input_schema = tool_info.get("inputSchema", {})
        required_fields = input_schema.get("required", []) if isinstance(input_schema, dict) else []

        tool_slug = f"{mcp_source}-{tool_info['name']}".lower().replace("_", "-")

        definition_dict = {
            "slug": tool_slug,
            "name": tool_info["name"],
            "source": mcp_source,
            "description": tool_info.get("description", ""),
            "input_schema": input_schema,
            "output_schema": tool_info.get("outputSchema"),
            "required_fields": required_fields,
            "example": None,
        }

        content_hash = compute_tool_hash(definition_dict)
        existing_hash = existing_hashes.get(tool_slug)

        if existing_hash == content_hash:
            unchanged += 1
            continue

        existing = existing_tools.get(tool_slug)

        if existing:
            new_version = bump_version(existing.version)
            definition = ToolDefinition(
                **definition_dict, hash=content_hash, version=new_version, is_active=True
            )
        else:
            definition = ToolDefinition(
                **definition_dict, hash=content_hash, version="1.0.0", is_active=True
            )

        to_save.append(definition)
        synced += 1

    if to_save:
        await definition_storage.save_many(to_save)

    return MCPSyncResult(server=mcp.name, synced=synced, unchanged=unchanged)


async def sync_mcp_tools(
    storage: StorageClient,
    mcp_tools: list[MCPToolkit],
    source: str = "mcp",
    *,
    list_timeout_seconds: float = 10.0,
    retries: int = 2,
    retry_backoff_seconds: float = 0.5,
) -> list[MCPSyncResult]:
    """
    Sync MCP tools to DB using already-connected servers.

    NOTE: MCP servers must already be connected (long-lived connections from lifespan).

    Args:
        storage: Storage client
        mcp_tools: List of MCPToolkit instances (already connected)
        source: Source identifier (default: "mcp")

    Returns:
        List of per-server MCP sync results.
    """
    from framework.storage.stores.tool_definition import ToolDefinitionStore

    definition_storage = ToolDefinitionStore(storage.storage)

    # Only sync connected MCP toolkits
    connected_mcps = [mcp for mcp in mcp_tools if mcp._session is not None]

    tasks = [
        _sync_single_mcp(
            mcp,
            definition_storage,
            source,
            list_timeout_seconds=list_timeout_seconds,
            retries=retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        for mcp in connected_mcps
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[MCPSyncResult] = []
    for mcp, raw_result in zip(connected_mcps, raw_results, strict=False):
        if isinstance(raw_result, BaseException):
            err = f"sync failed unexpectedly: {raw_result}"
            sys.stdout.write(f"MCP sync error ({mcp.name}): {err}\n")
            results.append(MCPSyncResult(server=mcp.name, error=err))
            continue
        results.append(raw_result)

    return results
