"""Health check routes."""

from fastapi import APIRouter
from fastapi.responses import Response


router = APIRouter(tags=["health"])


@router.options("/health")
async def health_options():
    """CORS preflight for health check."""
    return Response(status_code=200)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Astra Server", "version": "0.1.0"}
