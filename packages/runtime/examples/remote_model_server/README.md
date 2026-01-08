# Remote Model Server - Engineering Documentation

## Table of Contents

1. [Overview](#overview)
2. [Objectives](#objectives)
3. [Requirements](#requirements)
4. [Architecture](#architecture)
5. [How It Works](#how-it-works)
6. [Complete Flow](#complete-flow)
7. [Quantization Explained](#quantization-explained)
8. [Implementation Details](#implementation-details)
9. [Setup Guide](#setup-guide)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Remote Model Server is a distributed inference solution that allows you to run large language models (LLMs) on a machine with GPU resources (e.g., an old laptop) while developing and testing your Astra Framework applications on a different machine (e.g., a Mac) without heavy ML dependencies.

This architecture separates **model inference** (GPU-intensive) from **application development** (lightweight), enabling efficient resource utilization and improved developer experience.

---

## Objectives

### Primary Goals

1. **Resource Optimization**: Utilize GPU resources on a dedicated machine while keeping development machines lightweight
2. **Cost Efficiency**: Avoid rate limits and costs from cloud APIs (e.g., Gemini) by using local open-source models
3. **Developer Experience**: Enable seamless development without installing heavy ML libraries (PyTorch, transformers, CUDA) on development machines
4. **Local Testing**: Provide a local alternative to cloud APIs for testing framework features (streaming, tool calling, memory, etc.)
5. **Network Efficiency**: Use standard HTTP/JSON protocols for cross-platform compatibility

### Use Cases

- **Development Workflow**: Develop Astra Framework on Mac while model runs on Linux laptop
- **Resource Constraints**: Run models on machines with sufficient GPU/RAM while developing on constrained devices
- **Testing**: Test framework features locally without cloud API dependencies
- **Cost Savings**: Avoid cloud API costs and rate limits during development

---

## Requirements

### Hardware Requirements

#### Model Server Machine (Linux Laptop with GPU)

| Component   | Minimum                                         | Recommended           |
| ----------- | ----------------------------------------------- | --------------------- |
| **OS**      | Linux (Ubuntu 20.04+) or Windows with WSL2      | Linux (Ubuntu 22.04+) |
| **CPU**     | x86_64, 4+ cores                                | x86_64, 8+ cores      |
| **RAM**     | 8GB (4-bit) / 16GB (8-bit)                      | 16GB+                 |
| **GPU**     | NVIDIA GPU, 2GB VRAM (4-bit) / 4GB VRAM (8-bit) | NVIDIA GPU, 6GB+ VRAM |
| **Storage** | 10GB free (for model cache)                     | 20GB+ free            |
| **Network** | Ethernet or WiFi (for client connections)       | Gigabit Ethernet      |

#### Client Machine (Development - Mac)

| Component   | Minimum                                | Recommended            |
| ----------- | -------------------------------------- | ---------------------- |
| **OS**      | macOS 11+                              | macOS 13+              |
| **CPU**     | Any Apple Silicon or Intel             | Apple Silicon (M1+)    |
| **RAM**     | 8GB                                    | 16GB+                  |
| **Storage** | 1GB free                               | 5GB+ free              |
| **Network** | Same network as server (WiFi/Ethernet) | Same network as server |

### Software Requirements

#### Model Server

```bash
# Core ML Libraries
- Python 3.10+
- PyTorch 2.0+ (with CUDA support)
- transformers 4.30+
- accelerate 0.20+
- bitsandbytes 0.41+ (for quantization)

# Server Libraries
- FastAPI 0.100+
- uvicorn 0.23+
- httpx 0.24+
- python-dotenv 1.0+

# System
- CUDA 11.8+ or 12.1+ (matching PyTorch version)
- NVIDIA GPU drivers
```

#### Client Machine

```bash
# Minimal Requirements
- Python 3.10+
- httpx 0.24+ (HTTP client only)
```

**Note**: Client does NOT need PyTorch, transformers, CUDA, or any ML libraries!

### Network Requirements

- **Same Network**: Both machines must be on the same local network (same WiFi router or Ethernet switch)
- **Firewall**: Port 8001 (or configured port) must be open on the server machine
- **IP Accessibility**: Server must bind to `0.0.0.0` to accept external connections
- **Latency**: < 10ms network latency recommended for optimal performance

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Local Network (192.168.1.x)                 │
│                                                                 │
│  ┌──────────────────────┐         ┌──────────────────────┐   │
│  │   Client Machine     │         │   Server Machine     │   │
│  │   (Mac - Dev)        │         │   (Linux - GPU)      │   │
│  │                      │         │                      │   │
│  │  IP: 192.168.1.50   │         │  IP: 192.168.1.100   │   │
│  │                      │         │                      │   │
│  │  ┌────────────────┐ │         │  ┌────────────────┐  │   │
│  │  │ Astra Framework│ │         │  │ Model Server  │  │   │
│  │  │                │ │         │  │ (FastAPI)     │  │   │
│  │  │ ┌────────────┐│ │         │  │               │  │   │
│  │  │ │HuggingFace ││ │ HTTP    │  │ ┌───────────┐ │  │   │
│  │  │ │Remote      ││ │◄───────►│  │ │HuggingFace│ │  │   │
│  │  │ │(HTTP Client)││ │ Port    │  │ │Local      │ │  │   │
│  │  │ └────────────┘│ │ 8001    │  │ │(Model)    │ │  │   │
│  │  └────────────────┘ │         │  │ └───────────┘ │  │   │
│  │                      │         │  │      │        │  │   │
│  │                      │         │  │      ▼        │  │   │
│  │                      │         │  │  ┌─────────┐ │  │   │
│  │                      │         │  │  │  GPU    │ │  │   │
│  │                      │         │  │  │ (CUDA)  │ │  │   │
│  │                      │         │  │  └─────────┘ │  │   │
│  └──────────────────────┘         └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### Client Side (Mac)

- **HuggingFaceRemote**: HTTP client wrapper that implements the `Model` interface
- **httpx.AsyncClient**: Async HTTP client for making requests
- **Astra Framework**: Uses `HuggingFaceRemote` as a drop-in replacement for `HuggingFaceLocal`

#### Server Side (Linux Laptop)

- **FastAPI Application**: HTTP server exposing REST API endpoints
- **uvicorn**: ASGI server running the FastAPI app
- **HuggingFaceLocal**: Actual model implementation running inference
- **PyTorch + CUDA**: ML framework and GPU acceleration
- **Model**: Loaded in GPU memory (quantized or full precision)

### Protocol Stack

```
┌─────────────────────────────────────┐
│   Application Layer                 │
│   (Astra Framework / FastAPI)      │
├─────────────────────────────────────┤
│   HTTP/1.1                          │
│   (REST API / SSE Streaming)        │
├─────────────────────────────────────┤
│   JSON                              │
│   (Request/Response Serialization)  │
├─────────────────────────────────────┤
│   TCP/IP                            │
│   (Reliable Network Transport)     │
├─────────────────────────────────────┤
│   Network Interface                 │
│   (WiFi / Ethernet)                │
└─────────────────────────────────────┘
```

---

## How It Works

### Network Connection Flow

1. **Server Startup**:

   - Server binds to `0.0.0.0:8001` (all network interfaces)
   - Model is loaded into GPU memory (lazy loading on first request)
   - FastAPI routes are registered (`/v1/invoke`, `/v1/stream`, `/health`)

2. **Client Initialization**:

   - `HuggingFaceRemote` is instantiated with server URL
   - HTTP client (`httpx.AsyncClient`) is created (lazy initialization)
   - No network connection until first request

3. **Request Flow**:
   - Client serializes request to JSON
   - HTTP POST request sent over TCP/IP
   - Server receives request, deserializes JSON
   - Model inference runs on GPU
   - Response serialized to JSON, sent back over HTTP
   - Client deserializes response, returns `ModelResponse`

### Key Design Decisions

1. **HTTP over Custom Protocol**: Standard HTTP/JSON ensures cross-platform compatibility and easy debugging
2. **Lazy Model Loading**: Model only loads on first request to speed up server startup
3. **Stateless API**: Each request is independent (HTTP is stateless)
4. **SSE for Streaming**: Server-Sent Events (SSE) for token-by-token streaming
5. **Drop-in Replacement**: `HuggingFaceRemote` implements same interface as `HuggingFaceLocal`

---

## Complete Flow

### Flow Diagram: Invoke Request

```
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT SIDE (Mac)                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. User Code:                                                   │
│    model = HuggingFaceRemote("http://192.168.1.100:8001")       │
│    response = await model.invoke([                              │
│        {"role": "user", "content": "Hello!"}                    │
│    ])                                                           │
│                                                                 │
│ 2. HuggingFaceRemote.invoke():                                  │
│    - Build payload: {"messages": [...], "temperature": 0.7}     │
│    - Get HTTP client (create if needed)                         │
│    - Serialize payload to JSON                                  │
│                                                                 │
│ 3. httpx.AsyncClient.post():                                    │
│    - Create TCP socket                                          │
│    - Send HTTP request:                                         │
│      POST /v1/invoke HTTP/1.1                                   │
│      Host: 192.168.1.100:8001                                   │
│      Content-Type: application/json                             │
│      Content-Length: 123                                        │
│                                                                 │
│      {"messages": [...], "temperature": 0.7}                    │
│                                                                 │
│ 4. Network Stack (TCP/IP):                                      │
│    - TCP handshake (SYN → SYN-ACK → ACK)                        │
│    - Send TCP packets over network interface                    │
│    - Wait for response                                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    [Network Layer]
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ SERVER SIDE (Linux Laptop)                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 5. Network Stack (TCP/IP):                                     │
│    - Receive TCP packets                                        │
│    - Reassemble HTTP request                                    │
│    - Pass to uvicorn                                            │
│                                                                 │
│ 6. uvicorn (ASGI Server):                                      │
│    - Parse HTTP request                                         │
│    - Route to FastAPI app                                       │
│                                                                 │
│ 7. FastAPI Router:                                              │
│    - Match route: POST /v1/invoke                              │
│    - Parse JSON body → InvokeRequest Pydantic model            │
│    - Call endpoint handler                                       │
│                                                                 │
│ 8. Endpoint Handler (@app.post("/v1/invoke")):                │
│    - Call get_model() → Returns HuggingFaceLocal instance      │
│    - If first request: Load model into GPU memory              │
│                                                                 │
│ 9. HuggingFaceLocal.invoke():                                  │
│    - Tokenize input messages                                     │
│    - Move tensors to GPU                                        │
│    - Run model.generate() on GPU                                │
│    - Decode output tokens                                        │
│    - Parse tool calls (if any)                                  │
│    - Return ModelResponse                                       │
│                                                                 │
│ 10. Endpoint Handler:                                           │
│     - Convert ModelResponse to dict (response.to_dict())       │
│     - Serialize to JSON                                         │
│                                                                 │
│ 11. uvicorn:                                                    │
│     - Send HTTP response:                                       │
│       HTTP/1.1 200 OK                                           │
│       Content-Type: application/json                            │
│       Content-Length: 456                                       │
│                                                                 │
│       {"content": "...", "usage": {...}, "metadata": {...}}    │
│                                                                 │
│ 12. Network Stack:                                             │
│     - Send TCP packets back to client                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    [Network Layer]
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT SIDE (Mac) - Response                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 13. httpx.AsyncClient:                                         │
│     - Receive HTTP response                                     │
│     - Parse status code, headers                                │
│     - Read response body                                         │
│                                                                 │
│ 14. HuggingFaceRemote.invoke():                                │
│     - Parse JSON: response.json()                               │
│     - Create ModelResponse from dict                           │
│     - Add metadata (provider: "huggingface-remote")            │
│                                                                 │
│ 15. User Code:                                                  │
│     - Receives ModelResponse                                    │
│     - Access: response.content, response.usage, etc.            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Flow Diagram: Streaming Request (SSE)

```
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT SIDE                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. User Code:                                                  │
│    async for chunk in model.stream([...]):                    │
│        print(chunk.content)                                    │
│                                                                 │
│ 2. HuggingFaceRemote.stream():                                 │
│    - Build payload (same as invoke)                            │
│    - client.stream("POST", "/v1/stream", json=payload)         │
│                                                                 │
│ 3. httpx streams response:                                     │
│    - Keep connection open                                      │
│    - Read lines as they arrive                                 │
│                                                                 │
│ 4. Parse SSE format:                                           │
│    - Line format: "data: {...}\n\n"                            │
│    - Extract JSON: line[6:]                                    │
│    - Parse JSON → ModelResponse                                 │
│    - Yield chunk to user code                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ SERVER SIDE                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 5. FastAPI endpoint: @app.post("/v1/stream")                   │
│    - Parse request (same as invoke)                             │
│                                                                 │
│ 6. StreamingResponse:                                           │
│    - Create async generator function                           │
│    - Set media_type="text/event-stream"                        │
│                                                                 │
│ 7. Generator function:                                         │
│    async def generate():                                        │
│        model = get_model()                                     │
│        async for chunk in model.stream(...):                   │
│            # Format as SSE                                     │
│            data = json.dumps(chunk.to_dict())                  │
│            yield f"data: {data}\n\n"                           │
│                                                                 │
│ 8. HuggingFaceLocal.stream():                                  │
│    - Uses TextIteratorStreamer + threading                     │
│    - Model generates tokens in background thread                │
│    - Yields tokens as they're generated                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Network Protocol Details

#### TCP Connection Establishment

```
Client (Mac)                    Server (Linux Laptop)
    │                                │
    │─── SYN (seq=x) ───────────────>│
    │                                │
    │<── SYN-ACK (seq=y, ack=x+1) ──│
    │                                │
    │─── ACK (ack=y+1) ────────────>│
    │                                │
    │     [Connection Established]   │
    │                                │
```

#### HTTP Request/Response

```
Request:
POST /v1/invoke HTTP/1.1
Host: 192.168.1.100:8001
Content-Type: application/json
Content-Length: 123

{"messages": [{"role": "user", "content": "Hello!"}], "temperature": 0.7}

Response:
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 456

{"content": "Hi there!", "usage": {"input_tokens": 3, "output_tokens": 2}, ...}
```

#### SSE Streaming Format

```
data: {"content": "Hello", "metadata": {"is_stream": true}}

data: {"content": " world", "metadata": {"is_stream": true}}

data: {"content": "", "tool_calls": null, "usage": {...}, "metadata": {"final": true}}

```

---

## Quantization Explained

### What is Quantization?

**Quantization** is a technique to reduce the memory footprint and computational requirements of neural networks by using lower-precision data types to represent model weights and activations.

### Precision Levels

| Precision                 | Bits per Weight | Memory Reduction | Quality Impact          |
| ------------------------- | --------------- | ---------------- | ----------------------- |
| **FP32** (Full Precision) | 32 bits         | 1x (baseline)    | Highest quality         |
| **FP16** (Half Precision) | 16 bits         | 2x smaller       | Minimal quality loss    |
| **INT8** (8-bit)          | 8 bits          | 4x smaller       | Small quality loss      |
| **INT4** (4-bit)          | 4 bits          | 8x smaller       | Noticeable quality loss |

### How 8-bit Quantization Works

#### Traditional (FP32) Storage

```
Weight Value: 0.123456789
Storage: 32 bits (4 bytes)
Memory: 7B parameters × 4 bytes = 28 GB
```

#### 8-bit Quantized Storage

```
Weight Value: 0.123456789
Quantization:
  1. Find min/max range: [-2.0, 2.0]
  2. Scale factor: (2.0 - (-2.0)) / 255 = 0.0157
  3. Quantize: round(0.123456789 / 0.0157) = 8
  4. Store: 8 (1 byte, 0-255 range)

Dequantization (at runtime):
  5. Dequantize: 8 × 0.0157 + (-2.0) = -0.8744
  6. Use dequantized value for computation

Memory: 7B parameters × 1 byte = 7 GB (4x reduction!)
```

### Implementation: bitsandbytes Library

The `bitsandbytes` library implements efficient 8-bit and 4-bit quantization:

```python
# How it works internally (simplified)
from transformers import AutoModelForCausalLM
import bitsandbytes as bnb

# 8-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    load_in_8bit=True,  # ← Enables quantization
    device_map="auto",  # Automatically places layers on GPU
)

# What happens:
# 1. Model weights are quantized from FP32 → INT8
# 2. Quantization parameters (scale, zero_point) stored per layer
# 3. During inference: weights dequantized on-the-fly
# 4. Computations still use FP16/FP32, but weights are INT8
```

### Memory Savings

#### Qwen2.5-7B-Instruct Example

| Format           | Disk Size | RAM Usage | VRAM Usage |
| ---------------- | --------- | --------- | ---------- |
| **FP32**         | ~28 GB    | ~30 GB    | ~14 GB     |
| **FP16**         | ~14 GB    | ~16 GB    | ~8 GB      |
| **INT8** (8-bit) | ~7 GB     | ~8-10 GB  | ~4 GB      |
| **INT4** (4-bit) | ~4 GB     | ~6-8 GB   | ~2 GB      |

### Quality Impact

**8-bit Quantization**:

- **Quality Loss**: ~1-3% degradation in most tasks
- **Perplexity**: Slight increase (worse is better for perplexity)
- **Tool Calling**: Works well, minimal impact
- **Reasoning**: Slight reduction in complex reasoning tasks

**4-bit Quantization**:

- **Quality Loss**: ~5-10% degradation
- **Perplexity**: Noticeable increase
- **Tool Calling**: May have issues with complex tools
- **Reasoning**: More significant impact on reasoning

### When to Use Each

| Use Case                      | Recommended Format | Reason                      |
| ----------------------------- | ------------------ | --------------------------- |
| **Production (high quality)** | FP16 or FP32       | Best quality                |
| **Development (4GB GPU)**     | INT8 (8-bit)       | Good balance                |
| **Testing (2GB GPU)**         | INT4 (4-bit)       | Fits in memory              |
| **Maximum speed**             | INT8               | Faster inference            |
| **Maximum quality**           | FP16               | Best quality/speed tradeoff |

### Technical Details

#### Quantization Process

1. **Calibration**: Model weights analyzed to find optimal quantization parameters
2. **Quantization**: Weights converted from FP32 → INT8/INT4
3. **Storage**: Quantized weights + scale/zero_point parameters stored
4. **Runtime**: Weights dequantized on-the-fly during forward pass

#### Performance Characteristics

- **Memory**: 4x reduction (8-bit) or 8x reduction (4-bit)
- **Speed**: 1.5-2x faster inference (less memory bandwidth)
- **Accuracy**: Minimal impact for most tasks
- **Compatibility**: Works with all transformer architectures

---

## Implementation Details

### Client Implementation (`HuggingFaceRemote`)

**Location**: `packages/framework/src/framework/models/huggingface/remote.py`

**Key Components**:

```python
class HuggingFaceRemote(Model):
    def __init__(self, base_url: str, timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def invoke(...) -> ModelResponse:
        """Sends POST /v1/invoke, parses JSON response."""
        client = self._get_client()
        response = await client.post("/v1/invoke", json=payload)
        data = response.json()
        return ModelResponse(...)

    async def stream(...) -> AsyncIterator[ModelResponse]:
        """Sends POST /v1/stream, parses SSE format."""
        async with client.stream("POST", "/v1/stream", json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    yield ModelResponse(...)
```

**Design Patterns**:

- **Lazy Initialization**: HTTP client created on first use
- **Drop-in Replacement**: Implements same `Model` interface as `HuggingFaceLocal`
- **Error Handling**: Converts HTTP errors to framework exceptions
- **Async Context Manager**: Supports `async with` for cleanup

### Server Implementation (`remote_model_server`)

**Location**: `packages/runtime/examples/remote_model_server/main.py`

**Key Components**:

```python
# Global model instance (singleton pattern)
_model: HuggingFaceLocal | None = None

def get_model() -> HuggingFaceLocal:
    """Lazy loading - model only loaded on first request."""
    global _model
    if _model is None:
        _model = HuggingFaceLocal(
            model_id=MODEL_ID,
            device=DEVICE,
            load_in_8bit=LOAD_IN_8BIT,
            load_in_4bit=LOAD_IN_4BIT,
        )
    return _model

@app.post("/v1/invoke")
async def invoke(request: InvokeRequest) -> dict[str, Any]:
    """Invoke endpoint - returns complete response."""
    model = get_model()
    response = await model.invoke(...)
    return response.to_dict()

@app.post("/v1/stream")
async def stream(request: StreamRequest):
    """Stream endpoint - returns SSE stream."""
    async def generate():
        model = get_model()
        async for chunk in model.stream(...):
            yield f"data: {json.dumps(chunk.to_dict())}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Design Patterns**:

- **Singleton Pattern**: Single model instance shared across requests
- **Lazy Loading**: Model loaded on first request (faster startup)
- **CORS Middleware**: Allows cross-origin requests
- **Error Handling**: Converts exceptions to HTTP errors

### Model Loading (`HuggingFaceLocal`)

**Location**: `packages/framework/src/framework/models/huggingface/local.py`

**Quantization Support**:

```python
def __init__(self, ..., load_in_8bit: bool = False, load_in_4bit: bool = False):
    if load_in_8bit or load_in_4bit:
        if self.device != "cuda":
            raise ValueError("Quantization requires CUDA")
        # bitsandbytes handles quantization automatically
        self.model_kwargs["load_in_8bit"] = True  # or load_in_4bit

def _load_model(self):
    self._model = AutoModelForCausalLM.from_pretrained(
        self.model_id,
        device_map="auto",  # Required for quantization
        **self.model_kwargs,  # Includes quantization flags
    )
```

---

## Setup Guide

### Step 1: Server Setup (Linux Laptop)

#### 1.1 Install Dependencies

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install ML libraries
pip install transformers accelerate bitsandbytes

# Install server libraries
pip install fastapi uvicorn httpx python-dotenv

# Or with uv (recommended)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
uv pip install transformers accelerate bitsandbytes fastapi uvicorn httpx python-dotenv
```

#### 1.2 Verify GPU

```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

Expected: `CUDA: True`, `GPU: NVIDIA GeForce ...`

#### 1.3 Configure Server

Create `.env` file in `packages/runtime/examples/remote_model_server/`:

```bash
# Model configuration
MODEL_ID=Qwen/Qwen2.5-7B-Instruct
DEVICE=cuda

# Quantization (choose one)
LOAD_IN_8BIT=true   # Recommended for 4GB GPU
LOAD_IN_4BIT=false

# Server configuration
HOST=0.0.0.0        # Accept connections from other machines
PORT=8001           # Port for the API server
```

#### 1.4 Find IP Address

```bash
# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1
# Output: inet 192.168.1.100/24 ...

# Windows (PowerShell)
ipconfig | findstr IPv4
```

**Note the IP address** (e.g., `192.168.1.100`)

#### 1.5 Configure Firewall

```bash
# Linux (ufw)
sudo ufw allow 8001/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 8001 -j ACCEPT

# Windows: Open Windows Defender Firewall → Advanced → Inbound Rules → New Rule → Port → TCP 8001
```

#### 1.6 Start Server

```bash
cd packages/runtime
uv run --package astra-runtime python examples/remote_model_server/main.py
```

Expected output:

```
╔══════════════════════════════════════════════════════════════╗
║         Astra Remote Model Server                            ║
╠══════════════════════════════════════════════════════════════╣
║  Model:     Qwen/Qwen2.5-7B-Instruct                         ║
║  Device:    cuda                                             ║
║  8-bit:     True                                             ║
║  4-bit:     False                                            ║
║  Host:      0.0.0.0                                          ║
║  Port:      8001                                             ║
...
```

**First run downloads model (~7GB for 8-bit)** - may take 10-30 minutes.

### Step 2: Client Setup (Mac)

#### 2.1 Install Dependencies

```bash
# Only HTTP client needed - no ML libraries!
pip install httpx

# Or with uv
uv pip install httpx
```

#### 2.2 Test Connection

```bash
# Replace with your laptop's IP
curl http://192.168.1.100:8001/health
```

Expected response:

```json
{ "status": "ok", "model_id": "Qwen/Qwen2.5-7B-Instruct", "device": "cuda" }
```

#### 2.3 Use in Code

```python
from framework.models.huggingface.remote import HuggingFaceRemote
from framework.agents.agent import Agent

# Replace with your laptop's IP
LAPTOP_IP = "192.168.1.100"
MODEL_SERVER_URL = f"http://{LAPTOP_IP}:8001"

# Create agent with remote model
agent = Agent(
    name="Agent 1",
    id="agent-1",
    model=HuggingFaceRemote(MODEL_SERVER_URL),  # ← Drop-in replacement!
    instructions="You are a helpful assistant...",
)
```

---

## Troubleshooting

### Connection Refused

**Symptoms**: `Connection refused` or `Failed to connect`

**Solutions**:

1. Verify server is running: `curl http://localhost:8001/health` on laptop
2. Check firewall: `sudo ufw status` (Linux) or Windows Firewall settings
3. Verify IP address: Use `ip addr` or `ipconfig` to confirm
4. Check network: Ensure both machines on same network
5. Verify port binding: Server should show `Host: 0.0.0.0` (not `127.0.0.1`)

### CUDA Out of Memory

**Symptoms**: `RuntimeError: CUDA out of memory`

**Solutions**:

1. Use 4-bit quantization: `LOAD_IN_4BIT=true LOAD_IN_8BIT=false`
2. Use smaller model: `MODEL_ID=Qwen/Qwen2.5-3B-Instruct`
3. Close other GPU applications: `nvidia-smi` to check usage
4. Reduce batch size: Not applicable for single requests
5. Check GPU memory: `nvidia-smi` to verify available VRAM

### Slow Performance

**Symptoms**: High latency, slow token generation

**Solutions**:

1. Check GPU utilization: `watch -n 1 nvidia-smi` (should be >80%)
2. Verify model on GPU: Check server logs for device placement
3. Reduce `max_tokens`: Smaller responses = faster generation
4. Use smaller model: 3B instead of 7B
5. Check network latency: `ping 192.168.1.100` (should be <10ms)

### Model Download Fails

**Symptoms**: Timeout or connection error during download

**Solutions**:

1. Pre-download model:
   ```bash
   pip install huggingface_hub
   huggingface-cli download Qwen/Qwen2.5-7B-Instruct
   ```
2. Set custom cache: `export HF_HOME=/path/to/cache`
3. Use VPN: If behind corporate firewall
4. Retry: Downloads are resumable

### Import Errors

**Symptoms**: `ModuleNotFoundError: No module named 'bitsandbytes'`

**Solutions**:

1. Install bitsandbytes: `pip install bitsandbytes`
2. Verify CUDA compatibility: bitsandbytes requires CUDA
3. Check Python version: Requires Python 3.8+
4. Reinstall: `pip uninstall bitsandbytes && pip install bitsandbytes`

### SSE Parsing Errors

**Symptoms**: `JSONDecodeError` or malformed streaming responses

**Solutions**:

1. Check server logs: Verify SSE format is correct
2. Update httpx: `pip install --upgrade httpx`
3. Verify network stability: Check for packet loss
4. Test with curl: `curl -N http://192.168.1.100:8001/v1/stream -d '{"messages":[...]}'`

---

## Performance Benchmarks

### Resource Usage

| Configuration | Disk  | RAM     | VRAM  | Tokens/sec |
| ------------- | ----- | ------- | ----- | ---------- |
| FP32          | 28 GB | 30 GB   | 14 GB | 10-20      |
| FP16          | 14 GB | 16 GB   | 8 GB  | 15-30      |
| INT8 (8-bit)  | 7 GB  | 8-10 GB | 4 GB  | 20-50      |
| INT4 (4-bit)  | 4 GB  | 6-8 GB  | 2 GB  | 15-40      |

### Latency

- **First Token**: 1-3 seconds (model loading + generation)
- **Subsequent Tokens**: 20-50ms per token (streaming)
- **Network Overhead**: <10ms per request (local network)

### Throughput

- **Concurrent Requests**: Limited by GPU memory (typically 1-4 concurrent)
- **Request Rate**: ~2-5 requests/second (depending on model size)

---

## Security Considerations

⚠️ **Important**: Default configuration allows connections from any IP.

### Production Recommendations

1. **Firewall Rules**: Restrict access to specific IPs/subnets
2. **Authentication**: Add API key or token authentication
3. **HTTPS**: Use SSL/TLS certificates for encrypted connections
4. **VPN**: Use VPN for remote access instead of exposing to internet
5. **Rate Limiting**: Implement rate limiting to prevent abuse

### Example: Adding Authentication

```python
# In remote_model_server/main.py
API_KEY = os.getenv("API_KEY", "your-secret-key")

@app.post("/v1/invoke")
async def invoke(request: InvokeRequest, api_key: str = Header(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of handler
```

---

## Future Improvements

1. **Authentication**: API key or JWT token support
2. **Load Balancing**: Multiple model servers behind a load balancer
3. **Model Caching**: Cache multiple models, switch on demand
4. **Metrics**: Prometheus metrics for monitoring
5. **Health Checks**: More detailed health endpoint with GPU status
6. **Batch Processing**: Support for batch inference
7. **WebSocket**: WebSocket support for bidirectional streaming

---

## Support

For issues or questions:

1. Check server logs on laptop
2. Verify network connectivity: `ping <laptop-ip>`
3. Test with curl: `curl http://<laptop-ip>:8001/health`
4. Check GPU status: `nvidia-smi`
5. Review this documentation

---

## References

- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [bitsandbytes Quantization](https://github.com/TimDettmers/bitsandbytes)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

## Architecture

```
┌─────────────────┐         HTTP API          ┌─────────────────┐
│                 │ ──────────────────────────> │                 │
│   Mac (Dev)     │                            │  Laptop (GPU)   │
│                 │ <────────────────────────── │                 │
│  Astra Framework│      Model Responses       │  Model Server   │
└─────────────────┘                            └─────────────────┘
```

## Prerequisites

### On Laptop (Old Laptop with GPU)

- **OS**: Linux or Windows with WSL2
- **RAM**: 16GB+ (for 8-bit quantized models)
- **GPU**: NVIDIA GPU with 4GB+ VRAM
- **Python**: 3.10+
- **CUDA**: Installed and working

### On Mac (Development Machine)

- **OS**: macOS (any version)
- **Python**: 3.10+
- **Network**: Both machines on same network (or VPN)

## Step 1: Setup on Laptop

### 1.1 Install Dependencies

```bash
# Install Python dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes
pip install fastapi uvicorn httpx python-dotenv

# Or if using uv (recommended)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
uv pip install transformers accelerate bitsandbytes fastapi uvicorn httpx python-dotenv
```

### 1.2 Verify GPU

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

Expected output:

```
CUDA available: True
GPU: NVIDIA GeForce GTX 1650
```

### 1.3 Clone Astra Repository

```bash
git clone <your-repo-url>
cd Astra
```

### 1.4 Configure Server

Create `.env` file in `packages/runtime/examples/remote_model_server/`:

```bash
# Model configuration
MODEL_ID=Qwen/Qwen2.5-7B-Instruct
DEVICE=cuda

# Quantization (choose one)
LOAD_IN_8BIT=true   # Recommended for 4GB GPU
LOAD_IN_4BIT=false

# Server configuration
HOST=0.0.0.0        # Accept connections from other machines
PORT=8001           # Port for the API server
```

### 1.5 Find Laptop IP Address

```bash
# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1

# Windows (PowerShell)
ipconfig | findstr IPv4

# Example output: 192.168.1.100
```

**Note the IP address** - you'll need it on your Mac!

### 1.6 Start Server

```bash
cd packages/runtime
uv run --package astra-runtime python examples/remote_model_server/main.py
```

You should see:

```
╔══════════════════════════════════════════════════════════════╗
║         Astra Remote Model Server                           ║
╠══════════════════════════════════════════════════════════════╣
║  Model:     Qwen/Qwen2.5-7B-Instruct                        ║
║  Device:    cuda                                            ║
║  8-bit:     True                                            ║
║  4-bit:     False                                           ║
║  Host:      0.0.0.0                                         ║
║  Port:      8001                                            ║
...
```

**First run will download the model (~7GB for 8-bit quantized)**. This may take 10-30 minutes depending on your internet speed.

## Step 2: Setup on Mac

### 2.1 Install Dependencies

```bash
# Only need HTTP client, not ML libraries!
pip install httpx

# Or with uv
uv pip install httpx
```

### 2.2 Test Connection

```bash
# Replace 192.168.1.100 with your laptop's IP
curl http://192.168.1.100:8001/health
```

Expected response:

```json
{ "status": "ok", "model_id": "Qwen/Qwen2.5-7B-Instruct", "device": "cuda" }
```

### 2.3 Use in Your Code

Update `packages/runtime/examples/test_server/main.py`:

```python
from framework.models.huggingface.remote import HuggingFaceRemote

# Replace with your laptop's IP address
LAPTOP_IP = "192.168.1.100"
MODEL_SERVER_URL = f"http://{LAPTOP_IP}:8001"

# Use remote model instead of local
agent1 = Agent(
    name="Agent 1",
    id="agent-1",
    model=HuggingFaceRemote(MODEL_SERVER_URL),  # ← Changed here
    instructions="You are a helpful assistant...",
    description="A simple assistant agent",
)
```

## Step 3: Firewall Configuration

### On Laptop (Linux)

```bash
# Allow incoming connections on port 8001
sudo ufw allow 8001/tcp
```

### On Laptop (Windows)

1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Create new Inbound Rule:
   - Port → TCP → 8001
   - Allow connection
   - Apply to all profiles

## Troubleshooting

### Connection Refused

**Problem**: `Connection refused` when connecting from Mac

**Solutions**:

1. Check laptop firewall allows port 8001
2. Verify server is running: `curl http://localhost:8001/health` on laptop
3. Check IP address is correct
4. Ensure both machines on same network

### Out of Memory

**Problem**: `CUDA out of memory` error

**Solutions**:

1. Use 4-bit quantization instead of 8-bit:
   ```bash
   LOAD_IN_8BIT=false
   LOAD_IN_4BIT=true
   ```
2. Use smaller model: `MODEL_ID=Qwen/Qwen2.5-3B-Instruct`
3. Close other GPU applications

### Model Download Fails

**Problem**: Model download times out or fails

**Solutions**:

1. Use HuggingFace CLI to download first:
   ```bash
   pip install huggingface_hub
   huggingface-cli download Qwen/Qwen2.5-7B-Instruct
   ```
2. Set `HF_HOME` environment variable to custom cache location
3. Use VPN if behind firewall

### Slow Performance

**Problem**: Responses are slow

**Solutions**:

1. Check GPU utilization: `nvidia-smi`
2. Ensure model is on GPU (not CPU)
3. Reduce `max_tokens` in requests
4. Use smaller model if acceptable

## Performance Expectations

### With 8-bit Quantization (Recommended)

- **Model Size**: ~7GB disk, ~8-10GB RAM, ~4GB VRAM
- **Speed**: 20-50 tokens/second
- **Latency**: 1-3 seconds first token, then streaming

### With 4-bit Quantization

- **Model Size**: ~4GB disk, ~6-8GB RAM, ~2GB VRAM
- **Speed**: 15-40 tokens/second
- **Latency**: 1-3 seconds first token, then streaming

## Security Considerations

⚠️ **Important**: The default configuration allows connections from any IP (`HOST=0.0.0.0`). For production:

1. Use firewall rules to restrict access
2. Add authentication to the API server
3. Use HTTPS with SSL certificates
4. Consider VPN for remote access

## Next Steps

- Test with your agents in `test_server/main.py`
- Monitor GPU usage: `watch -n 1 nvidia-smi`
- Check server logs for errors
- Adjust quantization based on performance

## Example: Full Test Server Configuration

```python
# packages/runtime/examples/test_server/main.py
import os
from framework.models.huggingface.remote import HuggingFaceRemote
from framework.agents.agent import Agent

# Get laptop IP from environment or use default
LAPTOP_IP = os.getenv("REMOTE_MODEL_IP", "192.168.1.100")
MODEL_SERVER_URL = f"http://{LAPTOP_IP}:8001"

# Create agents with remote model
agent1 = Agent(
    name="Agent 1",
    id="agent-1",
    model=HuggingFaceRemote(MODEL_SERVER_URL),
    instructions="You are a helpful assistant...",
)
```

Run with:

```bash
REMOTE_MODEL_IP=192.168.1.100 uv run --package astra-runtime python examples/test_server/main.py
```

## Support

If you encounter issues:

1. Check server logs on laptop
2. Verify network connectivity
3. Test with `curl` commands
4. Check GPU memory: `nvidia-smi`
