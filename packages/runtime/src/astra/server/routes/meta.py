"""
Meta Routes for Astra Server.

Provides /v1/meta, /health, and /v1/providers endpoints.
"""

import time

from fastapi import APIRouter
from pydantic import BaseModel

from astra.server.config import ServerConfig
from astra.server.registry import AgentRegistry


# ============================================================================
# Response Models
# ============================================================================


class AgentEndpoints(BaseModel):
    """Agent endpoint URLs."""

    generate: str
    stream: str
    ingest: str | None = None


class AgentFeatures(BaseModel):
    """Agent feature flags."""

    tools: bool = False
    memory: bool = False
    rag: bool = False
    streaming: bool = True


class AgentInfo(BaseModel):
    """Agent information for meta endpoint."""

    name: str
    id: str | None = None
    description: str | None = None
    endpoints: AgentEndpoints
    features: AgentFeatures


class ServerInfo(BaseModel):
    """Server information."""

    name: str
    version: str
    uptime: int


class MetaResponse(BaseModel):
    """Response for /v1/meta endpoint."""

    version: str
    server: ServerInfo
    agents: list[AgentInfo]
    features: dict[str, bool]


class ComponentCounts(BaseModel):
    """Component counts for health check."""

    agents: int
    storage: int
    mcp_tools: int
    rag_pipelines: int


class HealthResponse(BaseModel):
    """Response for /health endpoint."""

    status: str  # "healthy", "degraded", "unhealthy"
    components: ComponentCounts
    dependencies: dict[str, str]
    uptime: int


class ProviderInfo(BaseModel):
    """Provider information."""

    id: str
    name: str
    description: str | None = None


class ProvidersResponse(BaseModel):
    """Response for /v1/providers endpoint."""

    providers: list[ProviderInfo]


# ============================================================================
# Router Factory
# ============================================================================


def create_meta_router(
    registry: AgentRegistry,
    config: ServerConfig,
    start_time: float,
) -> APIRouter:
    """
    Create router for meta endpoints.

    Args:
        registry: AgentRegistry with all resources
        config: Server configuration
        start_time: Server start timestamp

    Returns:
        FastAPI APIRouter
    """
    router = APIRouter(tags=["Meta"])

    @router.get(
        "/v1/meta",
        response_model=MetaResponse,
        summary="Get server metadata",
        description="Returns server information and list of available agents",
    )
    async def get_meta() -> MetaResponse:
        """Get server and agents metadata."""
        uptime = int(time.time() - start_time)

        agents_info = []
        for name, agent in registry.agents.items():
            # Determine features
            has_tools = bool(getattr(agent, "tools", None))
            has_memory = bool(getattr(agent, "storage", None))
            has_rag = bool(getattr(agent, "rag_pipeline", None))

            agents_info.append(
                AgentInfo(
                    name=name,
                    id=getattr(agent, "id", None) or name,
                    description=getattr(agent, "description", None),
                    endpoints=AgentEndpoints(
                        generate=f"/v1/agents/{name}/generate",
                        stream=f"/v1/agents/{name}/stream",
                        ingest=f"/v1/agents/{name}/ingest" if has_rag else None,
                    ),
                    features=AgentFeatures(
                        tools=has_tools,
                        memory=has_memory,
                        rag=has_rag,
                        streaming=True,
                    ),
                )
            )

        return MetaResponse(
            version=config.version,
            server=ServerInfo(
                name=config.name,
                version=config.version,
                uptime=uptime,
            ),
            agents=agents_info,
            features={
                "streaming": True,
                "tools": True,
                "memory": True,
                "rag": True,
            },
        )

    @router.get(
        "/health",
        response_model=HealthResponse,
        summary="Health check",
        description="Check server health and dependency status",
    )
    async def health_check() -> HealthResponse:
        """Check server health."""
        uptime = int(time.time() - start_time)

        # Check storage health
        dependencies: dict[str, str] = {}
        all_healthy = True

        for storage_info in registry.storage.values():
            storage = storage_info.instance
            storage_id = storage_info.id

            try:
                if hasattr(storage, "table_exists"):
                    await storage.table_exists("threads")
                dependencies[storage_id] = "healthy"
            except Exception as e:
                dependencies[storage_id] = f"unhealthy: {str(e)[:50]}"
                all_healthy = False

        # Check MCP tools (just count, don't ping)
        for tool in registry.mcp_tools:
            tool_name = getattr(tool, "name", "mcp-tool")
            # Assume healthy if no error on startup
            dependencies[tool_name] = "healthy"

        # Determine overall status
        if not dependencies:
            status = "healthy"
        elif all_healthy:
            status = "healthy"
        else:
            status = "degraded"

        return HealthResponse(
            status=status,
            components=ComponentCounts(
                agents=len(registry.agents),
                storage=len(registry.storage),
                mcp_tools=len(registry.mcp_tools),
                rag_pipelines=len(registry.rag_pipelines),
            ),
            dependencies=dependencies,
            uptime=uptime,
        )

    @router.get(
        "/v1/providers",
        response_model=ProvidersResponse,
        summary="List model providers",
        description="Returns list of available AI model providers",
    )
    async def list_providers() -> ProvidersResponse:
        """List available model providers."""
        # Discover providers from agents
        providers_seen: set[str] = set()
        providers: list[ProviderInfo] = []

        for agent in registry.agents.values():
            if hasattr(agent, "model") and agent.model is not None:
                model = agent.model
                provider_name = type(model).__name__

                if provider_name not in providers_seen:
                    providers_seen.add(provider_name)
                    providers.append(
                        ProviderInfo(
                            id=provider_name.lower(),
                            name=provider_name,
                            description=getattr(model, "description", None),
                        )
                    )

        # Add known providers
        known_providers = [
            ProviderInfo(id="gemini", name="Gemini", description="Google Gemini models"),
            ProviderInfo(id="bedrock", name="Bedrock", description="AWS Bedrock models"),
            ProviderInfo(
                id="huggingface",
                name="HuggingFace",
                description="HuggingFace local models",
            ),
        ]

        providers.extend(known for known in known_providers if known.id not in providers_seen)

        return ProvidersResponse(providers=providers)

    return router
