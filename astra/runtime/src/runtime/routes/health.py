"""Health check routes."""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Astra Server", "version": "0.1.0"}
