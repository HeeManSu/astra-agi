"""JWT token handling."""

from datetime import datetime, timedelta
import os
from typing import Any

import jwt


def get_jwt_secret() -> str | None:
    """Get JWT secret from environment."""
    return os.getenv("ASTRA_JWT_SECRET")


def get_jwt_expiry_hours() -> int:
    """Get JWT expiry hours from environment."""
    return int(os.getenv("ASTRA_JWT_EXPIRY_HOURS", "24"))


def create_token(payload: dict[str, Any], expires_in_hours: int | None = None) -> str:
    """
    Create a JWT token.

    Args:
        payload: Data to encode in the token
        expires_in_hours: Token expiry time in hours

    Returns:
        Encoded JWT token
    """
    jwt_secret = get_jwt_secret()
    if not jwt_secret:
        raise ValueError("ASTRA_JWT_SECRET environment variable is not set")

    exp_hours = expires_in_hours or get_jwt_expiry_hours()
    expiry = datetime.utcnow() + timedelta(hours=exp_hours)

    token_data = {
        **payload,
        "exp": expiry,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(token_data, jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Decoded payload if valid, None otherwise
    """
    jwt_secret = get_jwt_secret()
    if not jwt_secret:
        raise ValueError("ASTRA_JWT_SECRET environment variable is not set")

    try:
        return jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
