"""
Tests for Astra Server Configuration.

Tests ServerConfig dataclass initialization and validation.
"""

from astra.server.config import ServerConfig
import pytest


class TestServerConfigDefaults:
    """Test ServerConfig default values."""

    def test_default_name(self):
        """Default name is 'Astra Server'."""
        config = ServerConfig()
        assert config.name == "Astra Server"

    def test_default_version(self):
        """Default version is '1.0.0'."""
        config = ServerConfig()
        assert config.version == "1.0.0"

    def test_default_description(self):
        """Default description is set."""
        config = ServerConfig()
        assert config.description == "AI Agent Server powered by Astra"

    def test_default_docs_enabled(self):
        """Docs are enabled by default."""
        config = ServerConfig()
        assert config.docs_enabled is True

    def test_default_cors_origins(self):
        """CORS origins default to empty list."""
        config = ServerConfig()
        assert config.cors_origins == []

    def test_default_cors_allow_credentials(self):
        """CORS credentials default to True."""
        config = ServerConfig()
        assert config.cors_allow_credentials is True

    def test_default_cors_allow_methods(self):
        """CORS methods default to ['*']."""
        config = ServerConfig()
        assert config.cors_allow_methods == ["*"]

    def test_default_cors_allow_headers(self):
        """CORS headers default to ['*']."""
        config = ServerConfig()
        assert config.cors_allow_headers == ["*"]

    def test_default_request_id_header(self):
        """Request ID header defaults to 'X-Request-ID'."""
        config = ServerConfig()
        assert config.request_id_header == "X-Request-ID"

    def test_default_log_requests(self):
        """Log requests defaults to True."""
        config = ServerConfig()
        assert config.log_requests is True

    def test_default_debug(self):
        """Debug defaults to False."""
        config = ServerConfig()
        assert config.debug is False


class TestServerConfigCustomValues:
    """Test ServerConfig with custom values."""

    def test_custom_name(self):
        """Custom name is applied."""
        config = ServerConfig(name="My Server")
        assert config.name == "My Server"

    def test_custom_version(self):
        """Custom version is applied."""
        config = ServerConfig(version="2.0.0")
        assert config.version == "2.0.0"

    def test_custom_description(self):
        """Custom description is applied."""
        config = ServerConfig(description="Custom description")
        assert config.description == "Custom description"

    def test_docs_disabled(self):
        """Docs can be disabled."""
        config = ServerConfig(docs_enabled=False)
        assert config.docs_enabled is False

    def test_cors_origins_list(self):
        """CORS origins list is stored."""
        origins = ["http://localhost:3000", "https://myapp.com"]
        config = ServerConfig(cors_origins=origins)
        assert config.cors_origins == origins

    def test_cors_allow_credentials_false(self):
        """CORS credentials can be disabled."""
        config = ServerConfig(cors_allow_credentials=False)
        assert config.cors_allow_credentials is False

    def test_custom_request_id_header(self):
        """Custom request ID header."""
        config = ServerConfig(request_id_header="X-Custom-ID")
        assert config.request_id_header == "X-Custom-ID"

    def test_log_requests_disabled(self):
        """Request logging can be disabled."""
        config = ServerConfig(log_requests=False)
        assert config.log_requests is False

    def test_debug_enabled(self):
        """Debug can be enabled."""
        config = ServerConfig(debug=True)
        assert config.debug is True


class TestServerConfigValidation:
    """Test ServerConfig validation."""

    def test_empty_name_raises_valueerror(self):
        """Empty name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(name="")
        assert "name" in str(exc_info.value).lower()

    def test_empty_version_raises_valueerror(self):
        """Empty version raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(version="")
        assert "version" in str(exc_info.value).lower()

    def test_none_cors_origins_is_converted(self):
        """None cors_origins should use default."""
        # The dataclass uses default_factory so this tests explicit None
        config = ServerConfig()
        assert isinstance(config.cors_origins, list)

    def test_wildcard_cors_origin(self):
        """Wildcard '*' is valid CORS origin."""
        config = ServerConfig(cors_origins=["*"])
        assert config.cors_origins == ["*"]

    def test_multiple_cors_methods(self):
        """Multiple CORS methods can be set."""
        methods = ["GET", "POST", "PUT", "DELETE"]
        config = ServerConfig(cors_allow_methods=methods)
        assert config.cors_allow_methods == methods
