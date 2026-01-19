"""Server configuration."""

from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """Server configuration settings."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Auth
    security_key: str | None = None  # Simple auth: ASTRA_SECURITY_KEY
    jwt_secret: str | None = None  # Advanced auth: ASTRA_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # CORS
    cors_origins: list[str] = ["*"]

    class Config:
        env_prefix = "ASTRA_"
        env_file = ".env"
        extra = "ignore"


server_config = ServerConfig()
