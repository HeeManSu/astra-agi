"""Shared tool instances for the finance team.

MCP toolkit instances MUST be shared across agents to avoid duplicate slug errors.
Each call to `presets.brave_search()` / `presets.notion()` creates a new Python object.
The runtime's `sync_tools()` dedup uses `id(obj)`, so different objects with the same
slug will crash at startup.  Creating them once here and importing everywhere solves this.
"""

import os

from dotenv import load_dotenv


# Load .env from project root
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.tool.mcp import presets


# --- Shared MCP toolkit instances (create ONCE, import everywhere) ---
brave_mcp = presets.brave_search(os.getenv("BRAVE_API_KEY", ""))

# Accept either NOTION_TOKEN or NOTION_API_KEY
_notion_token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY", "")
notion_mcp = presets.notion(_notion_token)

__all__ = ["brave_mcp", "notion_mcp"]
