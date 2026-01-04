"""
Astra Server Configuration.

Server configuration with sensible defaults for production use.
"""

from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    """
    Configuration for Astra Server.

    Attributes:
        name: Server name displayed in docs
        version: API version
        description: Server description for docs
        docs_enabled: Enable OpenAPI docs (/docs, /redoc)
        cors_origins: List of allowed CORS origins (e.g., ["*"] or ["https://example.com"])
        cors_allow_credentials: Allow credentials in CORS
        cors_allow_methods: Allowed HTTP methods for CORS
        cors_allow_headers: Allowed headers for CORS
        request_id_header: Header name for request ID
        log_requests: Log all incoming requests
        debug: Enable debug mode (more verbose errors)
    """

    # Server identity
    name: str = "Astra Server"
    version: str = "1.0.0"
    description: str = "AI Agent Server powered by Astra"

    # Documentation
    docs_enabled: bool = True

    # CORS settings
    cors_origins: list[str] = field(default_factory=list)
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = field(default_factory=lambda: ["*"])

    # Request handling
    request_id_header: str = "X-Request-ID"
    log_requests: bool = True

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Playground
    playground_enabled: bool = True

    # Debug
    debug: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.name:
            raise ValueError("Server name cannot be empty")
        if not self.version:
            raise ValueError("Server version cannot be empty")
