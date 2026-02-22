"""
Preset MCP servers for common use cases.

Note: MCP servers are Node.js packages run via npx. The Python mcp SDK
is only the client that connects to these servers via stdio.

Usage:
    from framework.tool.mcp import presets

    async with presets.filesystem(".") as mcp:
        tools = await mcp.list_tools()
"""

from framework.tool.mcp.toolkit import MCPToolkit


def filesystem(path: str = ".") -> MCPToolkit:
    """
    Filesystem MCP server for file operations.
    Free - no API key required.

    Args:
        path: Root directory for file operations
    """
    return MCPToolkit(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", path],
    )


def memory() -> MCPToolkit:
    """
    Memory MCP server for knowledge graph persistence.
    Free - no API key required.
    """
    return MCPToolkit(
        name="memory",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
    )


def brave_search(api_key: str) -> MCPToolkit:
    """
    Brave Search MCP server for web search, news, local search.

    Args:
        api_key: Brave Search API key
    """
    return MCPToolkit(
        name="brave-search",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={"BRAVE_API_KEY": api_key.strip()},
    )


def duckduckgo() -> MCPToolkit:
    """
    DuckDuckGo Search MCP server for web search.
    Free - no API key required.

    Provides privacy-focused web search capabilities.
    """
    return MCPToolkit(
        name="duckduckgo",
        command="npx",
        args=["-y", "duckduckgo-mcp-server"],
    )


def github(token: str) -> MCPToolkit:
    """
    GitHub MCP server for repository operations.

    Args:
        token: GitHub personal access token
    """
    return MCPToolkit(
        name="github",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
    )


def e2b_sandbox(api_key: str) -> MCPToolkit:
    """
    E2B Sandbox MCP server for secure code execution.

    Args:
        api_key: E2B API key
    """
    return MCPToolkit(
        name="e2b_sandbox",
        command="npx",
        args=["-y", "@e2b/mcp-server"],
        env={"E2B_API_KEY": api_key},
    )


def firecrawl(api_key: str) -> MCPToolkit:
    """
    Firecrawl MCP server for web scraping, content extraction, JS rendering.

    Args:
        api_key: Firecrawl API key
    """
    return MCPToolkit(
        name="firecrawl",
        command="npx",
        args=["-y", "firecrawl-mcp"],
        env={"FIRECRAWL_API_KEY": api_key},
    )


def notion(api_key: str) -> MCPToolkit:
    """
    Official Notion MCP server for reading/writing Notion pages, databases.

    Uses @notionhq/notion-mcp-server (official from Notion).
    See: https://github.com/makenotion/notion-mcp-server

    Args:
        api_key: Notion Integration token (from https://www.notion.so/my-integrations)
    """
    return MCPToolkit(
        name="notion",
        command="npx",
        args=["-y", "@notionhq/notion-mcp-server"],
        env={"NOTION_TOKEN": api_key.strip()},
    )


def gdrive(credentials_path: str | None = None) -> MCPToolkit:
    """
    Google Drive MCP server for file operations on Google Drive.
    Uses @modelcontextprotocol/server-gdrive.

    Args:
        credentials_path: Path to Google OAuth credentials JSON file.
                          If not provided, will prompt for OAuth on first use.

    Note: Requires running 'npx @modelcontextprotocol/server-gdrive auth' first
    to set up OAuth if no credentials path is provided.
    """
    env = {}
    if credentials_path:
        env["GOOGLE_CREDENTIALS_PATH"] = credentials_path
    return MCPToolkit(
        name="gdrive",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-gdrive"],
        env=env if env else None,
    )


def fetch() -> MCPToolkit:
    """
    Fetch MCP server for retrieving web content with readability parsing.
    Free - no API key required.
    """
    return MCPToolkit(
        name="fetch",
        command="npx",
        args=["-y", "@anthropics/mcp-fetch"],
    )


def exa(api_key: str) -> MCPToolkit:
    """
    Exa MCP server for AI-native web search.
    Used by the Market Analyst agent for real-time news and market research.

    Provides: web_search_exa — semantic web search optimised for LLMs.

    Note: Agno uses Exa via an HTTP URL (mcp.exa.ai). Astra uses the
    stdio-based npm package which is functionally identical.

    Args:
        api_key: Exa API key (from https://dashboard.exa.ai)
    """
    return MCPToolkit(
        name="exa",
        command="npx",
        args=["-y", "exa-mcp", "--tools=web_search_exa"],
        env={"EXA_API_KEY": api_key.strip()},
    )
