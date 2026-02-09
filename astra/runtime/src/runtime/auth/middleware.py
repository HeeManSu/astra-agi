"""Auth middleware for protecting routes."""

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from runtime.auth.jwt import verify_token


# Public endpoints that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/auth/token",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT authentication middleware.

    Validates Bearer token in Authorization header for all non-public endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for public endpoints
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip for paths starting with /docs or /redoc
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

        # Verify JWT
        payload = verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Attach user info to request
        request.state.user = payload
        return await call_next(request)
