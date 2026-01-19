"""JWT token handling."""

from datetime import datetime, timedelta
from typing import Any

import jwt

from runtime.app.config import server_config


def create_token(payload: dict[str, Any], expires_in_hours: int | None = None) -> str:
    """
    Create a JWT token.

    Args:
        payload: Data to encode in the token
        expires_in_hours: Token expiry time in hours

    Returns:
        Encoded JWT token
    """
    if not server_config.jwt_secret:
        raise ValueError("JWT_SECRET is not configured")

    exp_hours = expires_in_hours or server_config.jwt_expiry_hours
    expiry = datetime.utcnow() + timedelta(hours=exp_hours)

    token_data = {
        **payload,
        "exp": expiry,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(
        token_data,
        server_config.jwt_secret,
        algorithm=server_config.jwt_algorithm,
    )


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Decoded payload if valid, None otherwise
    """
    if not server_config.jwt_secret:
        raise ValueError("JWT_SECRET is not configured")

    try:
        return jwt.decode(
            token,
            server_config.jwt_secret,
            algorithms=[server_config.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
