"""
Playground authentication middleware.

CSRF-protected cookie-based auth for playground routes only.
Mastra-style: config.jwt_secret first, ASTRA_JWT_SECRET env fallback.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import Cookie, HTTPException, Header, Request
import jwt


# Cookie names (must match routes.py)
SESSION_COOKIE = "astra_session"
CSRF_COOKIE = "astra_csrf"


def get_jwt_secret_from_request(request: Request) -> str:
    """
    Get JWT secret using Mastra-style priority.

    Priority:
    1. app.state.config.jwt_secret (from ServerConfig)
    2. ASTRA_JWT_SECRET environment variable
    """
    # Try config from app state
    config = getattr(request.app.state, "config", None)
    if config:
        secret = getattr(config, "jwt_secret", None)
        if secret:
            return secret

    # Fallback to env var
    secret = os.getenv("ASTRA_JWT_SECRET")
    if secret:
        return secret

    raise HTTPException(500, "JWT secret not configured")


async def require_playground_auth(
    request: Request,
    astra_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    astra_csrf: str | None = Cookie(default=None),
) -> dict[str, Any]:
    """
    Require authentication for playground routes.

    Verifies:
    1. Valid JWT session cookie
    2. Valid CSRF token for mutating requests (POST, PUT, DELETE, PATCH)

    Returns:
        User payload from JWT

    Raises:
        HTTPException 401: Not authenticated or invalid session
        HTTPException 403: CSRF validation failed
    """
    # Get JWT secret (Mastra-style: config first, env fallback)
    jwt_secret = get_jwt_secret_from_request(request)

    # Check session cookie
    if not astra_session:
        raise HTTPException(401, "Not authenticated")

    # Verify JWT
    try:
        payload = jwt.decode(astra_session, jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(401, "Session expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, "Invalid session") from e

    # CSRF validation for mutating methods
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if not x_csrf_token or not astra_csrf:
            raise HTTPException(403, "CSRF token missing")
        if x_csrf_token != astra_csrf:
            raise HTTPException(403, "CSRF token mismatch")

    return payload


async def get_current_user(
    request: Request,
    astra_session: str | None = Cookie(default=None),
) -> dict[str, Any] | None:
    """
    Get current user from session (optional auth).

    Returns None if not authenticated (doesn't raise).
    Use this for routes that work with or without auth.
    """
    if not astra_session:
        return None

    try:
        jwt_secret = get_jwt_secret_from_request(request)
        return jwt.decode(astra_session, jwt_secret, algorithms=["HS256"])
    except (jwt.InvalidTokenError, HTTPException):
        return None
