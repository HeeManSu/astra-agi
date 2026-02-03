"""
Tool Sync for Astra Runtime.

Syncs tools to DB at server startup:
1. Introspect local tools
2. Connect to MCP servers, list/describe tools
3. Normalize to ToolDefinition
4. Hash and upsert with versioning
5. Disconnect MCP discovery connections
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

    for tool in tools:
        # Extract required fields from parameters schema
        required_fields = []
        if tool.parameters and isinstance(tool.parameters, dict):
            required_fields = tool.parameters.get("required", [])

        tool_slug = f"{source}-{tool.name}".lower().replace("_", "-")

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
        existing = await definition_storage.get_by_name(tool_slug)

        if existing and existing.hash == content_hash:
            unchanged += 1
            continue

        if existing:
            new_version = bump_version(existing.version)
            definition = ToolDefinition(
                **definition_dict, hash=content_hash, version=new_version, is_active=True
            )
        else:
            definition = ToolDefinition(
                **definition_dict, hash=content_hash, version="1.0.0", is_active=True
            )

        await definition_storage.save(definition)
        synced += 1

    return synced, unchanged


async def sync_mcp_tools(
    storage: StorageClient,
    mcp_tools: list[MCPToolkit],
    source: str = "mcp",
) -> dict[str, tuple[int, int]]:
    """
    Connect to MCP server, discover tools, sync to DB.

    Args:
        storage: Storage client
        mcp_tools: List of MCPToolkit instances to sync
        source: Source identifier (default: "mcp")

    Returns:
        Dict of {server_name: (synced_count, unchanged_count)}
    """
    from framework.storage.stores.tool_definition import ToolDefinitionStore

    definition_storage = ToolDefinitionStore(storage.storage)
    results: dict[str, tuple[int, int]] = {}

    for mcp in mcp_tools:
        mcp_source = f"{source}:{mcp.name}"
        synced = 0
        unchanged = 0

        try:
            await mcp.connect()
            tools = await mcp.list_tools()

            for tool_info in tools:
                # Extract required fields from MCP inputSchema
                input_schema = tool_info.get("inputSchema", {})
                required_fields = (
                    input_schema.get("required", []) if isinstance(input_schema, dict) else []
                )

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
                existing = await definition_storage.get_by_name(tool_slug)

                if existing and existing.hash == content_hash:
                    unchanged += 1
                    continue

                if existing:
                    new_version = bump_version(existing.version)
                    definition = ToolDefinition(
                        **definition_dict, hash=content_hash, version=new_version, is_active=True
                    )
                else:
                    definition = ToolDefinition(
                        **definition_dict, hash=content_hash, version="1.0.0", is_active=True
                    )

                await definition_storage.save(definition)
                synced += 1
        finally:
            await mcp.close()

        results[mcp.name] = (synced, unchanged)

    return results
