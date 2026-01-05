"""
Astra Server Configuration.

Server configuration with sensible defaults for production use.
"""

from dataclasses import dataclass, field
import os


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
        jwt_secret: Secret for signing JWTs (falls back to ASTRA_JWT_SECRET env var)
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

    # Authentication
    jwt_secret: str | None = None

    # Debug
    debug: bool = False

    def __post_init__(self) -> None:
        """Validate configuration and set defaults."""
        if not self.name:
            raise ValueError("Server name cannot be empty")
        if not self.version:
            raise ValueError("Server version cannot be empty")

        # Mastra-style: config first, then env var fallback
        if not self.jwt_secret:
            self.jwt_secret = os.getenv("ASTRA_JWT_SECRET")

        if not self.jwt_secret:
            raise ValueError(
                "JWT secret is required for playground authentication.\n"
                "Option 1 - Set in config:\n"
                "  config = ServerConfig(jwt_secret='your-secret')\n\n"
                "Option 2 - Set environment variable:\n"
                '  export ASTRA_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")'
            )
