"""
Tool Sync for Astra Runtime.

Syncs tools to DB at server startup:
1. Introspect local tools
2. Use already-connected MCP servers to list/describe tools
3. Normalize to ToolDefinition
4. Hash and upsert with versioning
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "local": {
                "synced": self.local_synced,
                "unchanged": self.local_unchanged,
            },
            "mcp": {
                server: {"synced": count, "unchanged": self.mcp_unchanged.get(server, 0)}
                for server, count in self.mcp_synced.items()
            },
            "total_synced": self.local_synced + sum(self.mcp_synced.values()),
            "total_unchanged": self.local_unchanged + sum(self.mcp_unchanged.values()),
        }


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
    tool_slugs = [f"{source}-{t.name}".lower().replace("_", "-") for t in tools]
    existing_hashes = await definition_storage.get_hashes_by_slugs(tool_slugs)

    for tool in tools:
        tool_slug = f"{source}-{tool.name}".lower().replace("_", "-")
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

        existing = await definition_storage.get_by_name(tool_slug)

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
) -> tuple[str, int, int]:
    """
    Sync a single MCP server.

    NOTE: MCP must already be connected (long-lived connections from lifespan).

    Returns: (name, synced, unchanged)
    """
    mcp_source = f"{source}:{mcp.name}"
    synced = 0
    unchanged = 0
    to_save: list[ToolDefinition] = []

    # Use existing connection (already connected in lifespan)
    tools = await mcp.list_tools()

    # Batch get existing tool hashes
    tool_slugs = [f"{mcp_source}-{t['name']}".lower().replace("_", "-") for t in tools]
    existing_hashes = await definition_storage.get_hashes_by_slugs(tool_slugs)

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
            "output_schema": None,
            "required_fields": required_fields,
            "example": None,
        }

        content_hash = compute_tool_hash(definition_dict)
        existing_hash = existing_hashes.get(tool_slug)

        if existing_hash == content_hash:
            unchanged += 1
            continue

        existing = await definition_storage.get_by_name(tool_slug)

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

    return (mcp.name, synced, unchanged)


async def sync_mcp_tools(
    storage: StorageClient,
    mcp_tools: list[MCPToolkit],
    source: str = "mcp",
) -> dict[str, tuple[int, int]]:
    """
    Sync MCP tools to DB using already-connected servers.

    NOTE: MCP servers must already be connected (long-lived connections from lifespan).

    Args:
        storage: Storage client
        mcp_tools: List of MCPToolkit instances (already connected)
        source: Source identifier (default: "mcp")

    Returns:
        Dict of {server_name: (synced_count, unchanged_count)}
    """
    import asyncio
    import sys

    from framework.storage.stores.tool_definition import ToolDefinitionStore

    definition_storage = ToolDefinitionStore(storage.storage)

    # Only sync connected MCP toolkits
    connected_mcps = [mcp for mcp in mcp_tools if mcp._session is not None]

    tasks = [_sync_single_mcp(mcp, definition_storage, source) for mcp in connected_mcps]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, tuple[int, int]] = {}
    for result in results_list:
        if isinstance(result, BaseException):
            sys.stdout.write(f"MCP sync error: {result}\n")
            continue
        name, synced, unchanged = result
        results[name] = (synced, unchanged)

    return results
