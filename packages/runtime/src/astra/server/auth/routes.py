"""
Authentication routes for Astra Playground.

Cookie-based JWT auth with CSRF protection.
Mastra-style: config.jwt_secret first, ASTRA_JWT_SECRET env fallback.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import secrets
from typing import Any
import uuid

import bcrypt
from fastapi import APIRouter, Cookie, HTTPException, Response
import jwt
from pydantic import BaseModel, EmailStr


# Cookie names
SESSION_COOKIE = "astra_session"
CSRF_COOKIE = "astra_csrf"


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    """Signup request body."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response."""

    success: bool
    message: str
    email: str | None = None


class SessionResponse(BaseModel):
    """Session status response."""

    authenticated: bool
    email: str | None = None


def get_jwt_secret(config: Any) -> str:
    """
    Get JWT secret using Mastra-style priority.

    Priority:
    1. config.jwt_secret (passed in ServerConfig)
    2. ASTRA_JWT_SECRET environment variable
    3. Raise error if neither
    """
    # Try config first
    if config:
        secret = getattr(config, "jwt_secret", None)
        if secret:
            return secret

    # Fallback to env var
    secret = os.getenv("ASTRA_JWT_SECRET")
    if secret:
        return secret

    raise ValueError(
        "JWT secret is required. Set jwt_secret in ServerConfig or ASTRA_JWT_SECRET env var."
    )


def create_auth_router(registry: Any, config: Any) -> APIRouter:
    """
    Create authentication router.

    Args:
        registry: Agent registry with storage access
        config: ServerConfig with jwt_secret

    Returns:
        FastAPI router with auth endpoints
    """
    router = APIRouter(prefix="/auth", tags=["auth"])

    # Get JWT secret (Mastra-style: config first, env fallback)
    jwt_secret = get_jwt_secret(config)

    def get_storage():
        """Get first storage instance from registry."""
        storage_dict = getattr(registry, "storage", {})
        if storage_dict:
            first_info = next(iter(storage_dict.values()), None)
            if first_info:
                return first_info.instance
        return None

    def create_jwt_token(payload: dict[str, Any]) -> str:
        """Create a signed JWT token."""
        return jwt.encode(payload, jwt_secret, algorithm="HS256")

    def verify_jwt_token(token: str) -> dict[str, Any]:
        """Verify and decode a JWT token."""
        return jwt.decode(token, jwt_secret, algorithms=["HS256"])

    def generate_csrf_token() -> str:
        """Generate a secure CSRF token."""
        return secrets.token_urlsafe(32)

    def set_auth_cookies(response: Response, email: str) -> None:
        """Set session and CSRF cookies."""
        # Create JWT
        token = create_jwt_token(
            {
                "email": email,
                "exp": datetime.now(timezone.utc) + timedelta(days=7),
                "iat": datetime.now(timezone.utc),
            }
        )

        # Generate CSRF token
        csrf_token = generate_csrf_token()

        is_secure = os.getenv("HTTPS", "").lower() == "true"

        # Session cookie (HttpOnly - JS can't read)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
            path="/",
        )

        # CSRF cookie (readable by JS for header inclusion)
        response.set_cookie(
            key=CSRF_COOKIE,
            value=csrf_token,
            httponly=False,  # JS needs to read this
            secure=is_secure,
            samesite="strict",
            max_age=60 * 60 * 24 * 7,
            path="/",
        )

    def clear_auth_cookies(response: Response) -> None:
        """Clear all auth cookies."""
        response.delete_cookie(key=SESSION_COOKIE, path="/")
        response.delete_cookie(key=CSRF_COOKIE, path="/")

    @router.get("/session")
    async def get_session(
        astra_session: str | None = Cookie(default=None),
    ) -> SessionResponse:
        """Check current session status."""
        if not astra_session:
            return SessionResponse(authenticated=False, email=None)

        try:
            payload = verify_jwt_token(astra_session)
            return SessionResponse(
                authenticated=True,
                email=payload.get("email"),
            )
        except Exception:
            return SessionResponse(authenticated=False, email=None)

    @router.get("/needs-signup")
    async def needs_signup() -> dict[str, bool]:
        """Check if first-time signup is needed (no users exist)."""
        storage = get_storage()
        if not storage:
            return {"needs_signup": True}

        # Check if team_auth has any rows
        query = storage.build_select_query("astra_team_auth", limit=1)
        result = await storage.fetch_one(query)
        return {"needs_signup": result is None}

    @router.post("/signup")
    async def signup(
        request: SignupRequest,
        response: Response,
    ) -> AuthResponse:
        """First-time signup: create team credentials."""
        storage = get_storage()
        if not storage:
            raise HTTPException(500, "Storage not configured")

        # Check if already signed up
        query = storage.build_select_query("astra_team_auth", limit=1)
        existing = await storage.fetch_one(query)
        if existing:
            raise HTTPException(400, "Signup already completed. Please login.")

        # Hash password
        password_hash = bcrypt.hashpw(
            request.password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        # Insert credentials
        now = datetime.now(timezone.utc)
        insert_query = storage.build_insert_query(
            "astra_team_auth",
            {
                "id": str(uuid.uuid4()),
                "email": request.email,
                "password_hash": password_hash,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            },
        )
        await storage.execute(insert_query)

        # Set auth cookies
        set_auth_cookies(response, request.email)

        return AuthResponse(
            success=True,
            message="Signup completed",
            email=request.email,
        )

    @router.post("/login")
    async def login(
        request: LoginRequest,
        response: Response,
    ) -> AuthResponse:
        """Login with email/password."""
        storage = get_storage()
        if not storage:
            raise HTTPException(500, "Storage not configured")

        # Get credentials
        query = storage.build_select_query(
            "astra_team_auth",
            filter_dict={"email": request.email},
        )
        row = await storage.fetch_one(query)

        if not row:
            raise HTTPException(401, "Invalid email or password")

        # Verify password
        if not bcrypt.checkpw(
            request.password.encode("utf-8"),
            row["password_hash"].encode("utf-8"),
        ):
            raise HTTPException(401, "Invalid email or password")

        # Set auth cookies
        set_auth_cookies(response, request.email)

        return AuthResponse(
            success=True,
            message="Login successful",
            email=request.email,
        )

    @router.post("/logout")
    async def logout(response: Response) -> AuthResponse:
        """Clear session cookies."""
        clear_auth_cookies(response)
        return AuthResponse(
            success=True,
            message="Logged out",
        )

    return router
