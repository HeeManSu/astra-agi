"""
Agent Settings
--------------

Shared instances used across all agents: paths and URLs.
Import from here — never recreate these.
"""

from datetime import datetime
from os import getenv


def datetime_context() -> str:
    """Returns current date/time string — matches Agno's add_datetime_to_context=True."""
    return f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y %H:%M %Z')}\n\n"


# Exa MCP URL for web search (free tier available at exa.ai)
EXA_API_KEY = getenv("EXA_API_KEY", "")
EXA_MCP_URL = (
    f"https://mcp.exa.ai/mcp?exaApiKey={EXA_API_KEY}&tools=web_search_exa" if EXA_API_KEY else ""
)
