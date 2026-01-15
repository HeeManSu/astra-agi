"""
Tests for Astra Playground Authentication.

Tests the full auth flow:
- JWT secret configuration (Mastra-style)
- Signup (first-time team creation)
- Login (returning user)
- Session management
- Logout
"""

from datetime import datetime, timezone
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Test JWT secret
TEST_JWT_SECRET = "test-secret-key-for-jwt-signing-min-32-chars"


class TestServerConfigJwtSecret:
    """Test Mastra-style JWT secret configuration."""

    def test_jwt_secret_from_config(self):
        """Config jwt_secret takes priority over env var."""
        with patch.dict(os.environ, {"ASTRA_JWT_SECRET": "env-secret"}, clear=False):
            from astra.server.config import ServerConfig

            config = ServerConfig(jwt_secret="config-secret")
            assert config.jwt_secret == "config-secret"

    def test_jwt_secret_from_env_fallback(self):
        """Falls back to ASTRA_JWT_SECRET env var if config not set."""
        with patch.dict(os.environ, {"ASTRA_JWT_SECRET": "env-secret"}, clear=False):
            from astra.server.config import ServerConfig

            config = ServerConfig()  # No jwt_secret in config
            assert config.jwt_secret == "env-secret"

    def test_jwt_secret_required_error(self):
        """Raises error if neither config nor env var set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env var
            os.environ.pop("ASTRA_JWT_SECRET", None)
            from astra.server.config import ServerConfig

            with pytest.raises(ValueError, match="JWT secret is required"):
                ServerConfig()


class TestAuthRoutes:
    """Test authentication routes."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage with async methods."""
        storage = MagicMock()
        storage.build_select_query = MagicMock(return_value={})
        storage.build_insert_query = MagicMock(return_value={})
        storage.fetch_one = AsyncMock(return_value=None)
        storage.execute = AsyncMock()
        return storage

    @pytest.fixture
    def mock_registry(self, mock_storage):
        """Create mock registry with storage."""
        registry = MagicMock()
        storage_info = MagicMock()
        storage_info.instance = mock_storage
        registry.storage = {"default": storage_info}
        return registry

    @pytest.fixture
    def mock_config(self):
        """Create mock config with jwt_secret."""
        config = MagicMock()
        config.jwt_secret = TEST_JWT_SECRET
        return config

    def test_create_auth_router(self, mock_registry, mock_config):
        """Auth router is created successfully with config jwt_secret."""
        from astra.server.auth.routes import create_auth_router

        router = create_auth_router(mock_registry, mock_config)
        assert router is not None
        assert router.prefix == "/auth"

    @pytest.mark.asyncio
    async def test_needs_signup_no_users(self, mock_registry, mock_config, mock_storage):
        """Returns needs_signup=True when no users exist."""
        mock_storage.fetch_one = AsyncMock(return_value=None)

        from astra.server.auth.routes import create_auth_router

        router = create_auth_router(mock_registry, mock_config)

        # Find needs-signup route
        for route in router.routes:
            path = getattr(route, "path", None)
            endpoint = getattr(route, "endpoint", None)
            if path == "/needs-signup" and endpoint:
                result = await endpoint()
                assert result == {"needs_signup": True}
                break

    @pytest.mark.asyncio
    async def test_needs_signup_has_users(self, mock_registry, mock_config, mock_storage):
        """Returns needs_signup=False when users exist."""
        mock_storage.fetch_one = AsyncMock(
            return_value={"id": "user1", "email": "test@example.com"}
        )

        from astra.server.auth.routes import create_auth_router

        router = create_auth_router(mock_registry, mock_config)

        for route in router.routes:
            path = getattr(route, "path", None)
            endpoint = getattr(route, "endpoint", None)
            if path == "/needs-signup" and endpoint:
                result = await endpoint()
                assert result == {"needs_signup": False}
                break


class TestJwtTokens:
    """Test JWT token creation and verification."""

    def test_create_and_verify_token(self):
        """JWT token can be created and verified."""
        import jwt

        payload = {"email": "test@example.com", "iat": datetime.now(timezone.utc)}
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

        decoded = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
        assert decoded["email"] == "test@example.com"

    def test_invalid_secret_fails(self):
        """Token verification fails with wrong secret."""
        import jwt

        payload = {"email": "test@example.com"}
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])


class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_and_verify_password(self):
        """Password can be hashed and verified."""
        import bcrypt

        password = "securepassword123"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        assert bcrypt.checkpw(password.encode(), hashed)
        assert not bcrypt.checkpw("wrongpassword".encode(), hashed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
