"""
Remote Model API Server for HuggingFace Local Models

This server exposes a HuggingFace local model via HTTP API, allowing remote clients
to use the model without running it locally.

Use Case:
- Run this on a laptop/desktop with GPU (e.g., NVIDIA GPU)
- Connect from your development machine (Mac) via HTTP
- No need to install heavy ML dependencies on your dev machine

Run on laptop:
    cd packages/runtime
    uv run --package astra-runtime python examples/remote_model_server/main.py

Or with custom settings:
    MODEL_ID=Qwen/Qwen2.5-7B-Instruct \
    DEVICE=cuda \
    LOAD_IN_8BIT=true \
    PORT=8001 \
    uv run --package astra-runtime python examples/remote_model_server/main.py

Connect from Mac:
    from framework.models.huggingface.remote import HuggingFaceRemote
    model = HuggingFaceRemote("http://192.168.1.100:8001")  # Laptop IP
"""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict


load_dotenv()

# PYTHONPATH Setup for Uvicorn Reload
current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent

runtime_path = str(runtime_dir)
pythonpath = os.environ.get("PYTHONPATH", "")
if runtime_path not in pythonpath:
    os.environ["PYTHONPATH"] = f"{runtime_path}:{pythonpath}" if pythonpath else runtime_path

# Imports after PYTHONPATH setup
from framework.models.huggingface.local import HuggingFaceLocal  # noqa: E402
import uvicorn  # noqa: E402


# ============================================================================
# Configuration
# ============================================================================

MODEL_ID = os.getenv("MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
DEVICE = os.getenv("DEVICE", "cuda")  # cuda, mps, cpu
LOAD_IN_8BIT = os.getenv("LOAD_IN_8BIT", "false").lower() == "true"
LOAD_IN_4BIT = os.getenv("LOAD_IN_4BIT", "false").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")  # 0.0.0.0 to accept connections from other machines
PORT = int(os.getenv("PORT", "8001"))


# ============================================================================
# Request/Response Models
# ============================================================================


class InvokeRequest(BaseModel):
    """Request model for invoke endpoint."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields for kwargs

    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None


class StreamRequest(BaseModel):
    """Request model for stream endpoint."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields for kwargs

    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Astra Remote Model Server",
    description="HTTP API server for HuggingFace local models",
    version="1.0.0",
)

# CORS middleware to allow connections from other machines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance (lazy loaded)
_model: HuggingFaceLocal | None = None


def get_model() -> HuggingFaceLocal:
    """Get or create model instance."""
    global _model
    if _model is None:
        print(f"Loading model: {MODEL_ID} on {DEVICE}...")
        print(f"Quantization: 8-bit={LOAD_IN_8BIT}, 4-bit={LOAD_IN_4BIT}")

        model_kwargs: dict[str, Any] = {}
        if LOAD_IN_8BIT:
            model_kwargs["load_in_8bit"] = True
        if LOAD_IN_4BIT:
            model_kwargs["load_in_4bit"] = True

        _model = HuggingFaceLocal(
            model_id=MODEL_ID,
            device=DEVICE,
            load_in_8bit=LOAD_IN_8BIT,
            load_in_4bit=LOAD_IN_4BIT,
            **model_kwargs,
        )
        print("Model loaded successfully!")
    return _model


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "model_id": MODEL_ID, "device": DEVICE}


@app.post("/v1/invoke")
async def invoke(request: InvokeRequest) -> dict[str, Any]:
    """
    Invoke the model and return complete response.

    Compatible with Astra Framework Model interface.
    """
    try:
        model = get_model()
        # Extract extra kwargs (fields not in the model)
        request_dict = request.model_dump(exclude_unset=True)
        known_fields = {"messages", "tools", "temperature", "max_tokens", "response_format"}
        extra_kwargs = {k: v for k, v in request_dict.items() if k not in known_fields}

        response = await model.invoke(
            messages=request.messages,
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_format=request.response_format,
            **extra_kwargs,
        )
        return response.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/v1/stream")
async def stream(request: StreamRequest):
    """
    Stream model responses token by token.

    Returns Server-Sent Events (SSE) stream.
    """

    async def generate():
        try:
            model = get_model()
            # Extract extra kwargs (fields not in the model)
            request_dict = request.model_dump(exclude_unset=True)
            known_fields = {"messages", "tools", "temperature", "max_tokens", "response_format"}
            extra_kwargs = {k: v for k, v in request_dict.items() if k not in known_fields}

            async for chunk in model.stream(
                messages=request.messages,
                tools=request.tools,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=request.response_format,
                **extra_kwargs,
            ):
                # Format as SSE
                data = json.dumps(chunk.to_dict())
                yield f"data: {data}\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/v1/info")
async def get_info():
    """Get model information."""
    get_model()
    return {
        "model_id": MODEL_ID,
        "device": DEVICE,
        "quantization": {
            "8bit": LOAD_IN_8BIT,
            "4bit": LOAD_IN_4BIT,
        },
        "provider": "huggingface-local",
    }


# ============================================================================
# Main
# ============================================================================


def main():
    """Run the server."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         Astra Remote Model Server                            ║
╠══════════════════════════════════════════════════════════════╣
║  Model:     {MODEL_ID!s:<45}                                 ║
║  Device:    {DEVICE!s:<45}                                   ║
║  8-bit:     {str(LOAD_IN_8BIT)!s:<45}                        ║
║  4-bit:     {str(LOAD_IN_4BIT)!s:<45}                        ║
║  Host:      {HOST!s:<45}                                     ║
║  Port:      {PORT!s:<45}                                     ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                                  ║
║    GET  /health          Health check                        ║
║    GET  /v1/info         Model information                   ║
║    POST /v1/invoke       Generate complete response          ║
║    POST /v1/stream       Stream tokens                       ║
╠══════════════════════════════════════════════════════════════╣
║  Connect from Mac:                                           ║
║    HuggingFaceRemote("http://<LAPTOP_IP>:{PORT}")            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    try:
        uvicorn.run(
            "examples.remote_model_server.main:app",
            host=HOST,
            port=PORT,
            log_level="info",
            reload=False,  # Disable reload for production use
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
