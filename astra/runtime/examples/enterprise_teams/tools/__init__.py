"""Shared local and MCP tools for the enterprise_teams example.

MCP toolkit instances are created once and imported by every agent.
This prevents duplicate-tool registration issues at startup.
"""

import os

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.tool.mcp import presets


brave_mcp = presets.brave_search(os.getenv("BRAVE_API_KEY", ""))
duckduckgo_mcp = presets.duckduckgo()
github_mcp = presets.github(os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", ""))
notion_mcp = presets.notion(os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY", ""))


__all__ = [
    "brave_mcp",
    "duckduckgo_mcp",
    "github_mcp",
    "notion_mcp",
]
