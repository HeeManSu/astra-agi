"""
Playground Tools Routes.

Provides /api/tools/* endpoints for listing and inspecting tools.
"""

import inspect
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Response Models
# ============================================================================


class ToolParameter(BaseModel):
    """Tool parameter schema."""

    name: str
    type: str
    description: str | None = None
    required: bool = True
    default: Any | None = None


class ToolResponse(BaseModel):
    """Tool info response."""

    name: str
    description: str | None = None
    parameters: list[ToolParameter] = []
    agent_names: list[str] = []  # Which agents use this tool


class ToolDetailResponse(ToolResponse):
    """Detailed tool info with source code."""

    source: str | None = None


# ============================================================================
# Router Factory
# ============================================================================


def create_tools_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for tool endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter for tool endpoints
    """
    router = APIRouter(tags=["Playground - Tools"])

    def _extract_tool_info(tool: Any) -> dict[str, Any]:
        """Extract info from a tool object."""
        name = getattr(tool, "name", None) or getattr(tool, "__name__", str(tool))
        description = getattr(tool, "description", None) or getattr(tool, "__doc__", None)

        # Try to extract parameters from function signature
        parameters = []
        try:
            if callable(tool):
                sig = inspect.signature(tool)
                for param_name, param in sig.parameters.items():
                    if param_name in ("self", "cls"):
                        continue

                    param_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        param_type = str(param.annotation)

                    parameters.append(
                        {
                            "name": param_name,
                            "type": param_type,
                            "required": param.default == inspect.Parameter.empty,
                            "default": None
                            if param.default == inspect.Parameter.empty
                            else param.default,
                        }
                    )
        except (ValueError, TypeError):
            pass

        return {
            "name": name,
            "description": description,
            "parameters": parameters,
        }

    @router.get("/tools", response_model=list[ToolResponse])
    async def list_tools() -> list[ToolResponse]:
        """List all tools across all agents."""
        tools_map: dict[str, dict[str, Any]] = {}  # name -> {info, agents}

        for agent_name, agent in registry.agents.items():
            if hasattr(agent, "tools") and agent.tools:
                for tool in agent.tools:
                    info = _extract_tool_info(tool)
                    tool_name = info["name"]

                    if tool_name not in tools_map:
                        tools_map[tool_name] = {
                            **info,
                            "agent_names": [],
                        }

                    if agent_name not in tools_map[tool_name]["agent_names"]:
                        tools_map[tool_name]["agent_names"].append(agent_name)

        return [
            ToolResponse(
                name=t["name"],
                description=t["description"],
                parameters=[ToolParameter(**p) for p in t.get("parameters", [])],
                agent_names=t["agent_names"],
            )
            for t in tools_map.values()
        ]

    @router.get("/tools/{tool_name}", response_model=ToolDetailResponse)
    async def get_tool(tool_name: str) -> ToolDetailResponse:
        """Get detailed info about a specific tool."""
        # Find the tool
        found_tool = None
        agent_names = []

        for agent_name, agent in registry.agents.items():
            if hasattr(agent, "tools") and agent.tools:
                for tool in agent.tools:
                    name = getattr(tool, "name", None) or getattr(tool, "__name__", "")
                    if name == tool_name:
                        found_tool = tool
                        if agent_name not in agent_names:
                            agent_names.append(agent_name)

        if not found_tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        info = _extract_tool_info(found_tool)

        # Try to get source code
        source = None
        try:
            source = inspect.getsource(found_tool)
        except (OSError, TypeError):
            pass

        return ToolDetailResponse(
            name=info["name"],
            description=info["description"],
            parameters=[ToolParameter(**p) for p in info.get("parameters", [])],
            agent_names=agent_names,
            source=source,
        )

    return router
