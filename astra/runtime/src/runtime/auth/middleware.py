"""Auth middleware for protecting routes."""

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from runtime.app.config import server_config
from runtime.auth.jwt import verify_token


# Public endpoints that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/config",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API authentication.

    Supports two modes:
    1. Security Key: Simple string match (ASTRA_SECURITY_KEY)
    2. JWT: Signed token with expiry (ASTRA_JWT_SECRET)

    The middleware first tries security key match, then falls back to JWT.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Also skip for paths starting with /docs or /openapi
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return await call_next(request)

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header. Expected: Bearer <token>",
            )

        token = auth_header.split(" ", 1)[1].strip()

        if not token:
            raise HTTPException(status_code=401, detail="Empty token")

        # Method 1: Check against security key (simple mode)
        if server_config.security_key:
            if token == server_config.security_key:
                # Security key matched - allow request
                request.state.user = {"auth_type": "security_key"}
                return await call_next(request)

        # Method 2: Try JWT verification (advanced mode)
        if server_config.jwt_secret:
            payload = verify_token(token)
            if payload:
                # Valid JWT - allow request
                request.state.user = payload
                request.state.user["auth_type"] = "jwt"
                return await call_next(request)

        # Neither method succeeded
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )


def auth_middleware(app):
    """Add auth middleware to app."""
    app.add_middleware(AuthMiddleware)
