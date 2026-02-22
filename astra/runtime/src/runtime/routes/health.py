"""Health check routes."""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response


router = APIRouter(tags=["health"])


def _get_runtime_health(request: Request) -> dict[str, Any]:
    """Fetch runtime health state from app state with safe defaults."""
    runtime_health = getattr(request.app.state, "runtime_health", None)
    if isinstance(runtime_health, dict):
        return runtime_health

    return {
        "liveness": {"status": "alive"},
        "readiness": {
            "status": "not_ready",
            "ready": False,
            "degraded": False,
            "reason": "startup_state_unavailable",
        },
        "startup": {"status": "unknown", "phase": "unknown"},
        "sync": {"mcp_connect": {}, "report": None},
    }


@router.options("/health")
async def health_options():
    """CORS preflight for health check."""
    return Response(status_code=200)


@router.get("/health")
async def health_check(request: Request):
    """Backward-compatible aggregated health endpoint."""
    runtime_health = _get_runtime_health(request)
    readiness = runtime_health.get("readiness", {})
    startup = runtime_health.get("startup", {})

    if not readiness.get("ready"):
        status = "starting" if startup.get("status") == "starting" else "unhealthy"
        status_code = 503
    elif readiness.get("degraded"):
        status = "degraded"
        status_code = 200
    else:
        status = "healthy"
        status_code = 200

    payload = {
        "status": status,
        "liveness": runtime_health.get("liveness"),
        "readiness": readiness,
        "startup": startup,
    }
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/health/liveness")
async def health_liveness(request: Request):
    """Liveness probe: process-level alive signal."""
    runtime_health = _get_runtime_health(request)
    return {"status": runtime_health.get("liveness", {}).get("status", "alive")}


@router.get("/health/readiness")
async def health_readiness(request: Request):
    """Readiness probe: can this instance serve requests now."""
    runtime_health = _get_runtime_health(request)
    readiness = runtime_health.get("readiness", {})
    status_code = 200 if readiness.get("ready") else 503
    return JSONResponse(content=readiness, status_code=status_code)


@router.get("/readiness")
async def readiness(request: Request):
    """Readiness alias for infrastructure probes."""
    return await health_readiness(request)


@router.get("/health/startup")
async def health_startup(request: Request):
    """Startup probe: startup progress and sync state."""
    runtime_health = _get_runtime_health(request)
    startup = runtime_health.get("startup", {})
    payload = {
        "startup": startup,
        "sync": runtime_health.get("sync", {}),
    }
    status_code = 200 if startup.get("status") == "completed" else 503
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/startup")
async def startup(request: Request):
    """Startup alias for infrastructure probes."""
    return await health_startup(request)


@router.get("/")
async def root(request: Request):
    """Root endpoint."""
    return {"message": "Astra Server", "version": request.app.version}
