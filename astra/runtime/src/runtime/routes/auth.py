"""Auth routes for token generation."""

from fastapi import APIRouter
from pydantic import BaseModel

from runtime.auth.jwt import create_token, get_jwt_expiry_hours


router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


@router.post("/token")
async def get_token() -> TokenResponse:
    """
    Generate a JWT token for API access.

    Returns a short-lived JWT token that can be used for authenticating
    subsequent API requests.
    """
    expiry_hours = get_jwt_expiry_hours()
    token = create_token({"type": "playground"}, expires_in_hours=expiry_hours)

    return TokenResponse(
        access_token=token,
        expires_in=expiry_hours * 60 * 60,  # Convert to seconds
    )
