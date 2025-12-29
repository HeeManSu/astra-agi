# AstraOps Tracing

This module manages the core OpenTelemetry (OTEL) integration for AstraOps. It abstracts the complexity of the OpenTelemetry SDK to provide a robust, production-ready tracing engine that handles span lifecycle, context propagation, and data export.

## High-Level Architecture

The tracing system follows a standard **Provider-Processor-Exporter** pipeline:

```text
┌─────────────────────────────┐
│  User Code / Instrumentation│
└──────────────┬──────────────┘
               │ Start Span
               ▼
┌─────────────────────────────┐
│         AstraTracer         │
└──────────────┬──────────────┘
               │ Span Created
               ▼
┌─────────────────────────────┐
│     BatchSpanProcessor      │
└──────────────┬──────────────┘
               │ Buffer Spans
               ▼
┌─────────────────────────────────────────────────────────┐
│           Processing Loop (Background Thread)           │
│                                                         │
│  ┌──────────────┐          ┌───────────────────────┐    │
│  │  Span Queue  │ ───────► │    OTLP Exporter      │    │
│  └──────────────┘          └───────────┬───────────┘    │
│                                        │                │
└────────────────────────────────────────┼────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼                                         ▼
        ┌───────────────────────┐                 ┌───────────────────────┐
        │    OTEL Collector     │                 │  Console (Debug Mode) │
        │    (gRPC Backend)     │                 │       (JSON)          │
        └───────────────────────┘                 └───────────────────────┘
```

---

## Component Breakdown

### 1. The Engine: `AstraTracer` (`tracer.py`)

A thread-safe Singleton that orchestrates the entire tracing system.

- **Responsibility**:
  - Initializes the Global `TracerProvider`.
  - Attaches the `BatchSpanProcessor`.
  - Manages the "Resource" (service name, version, environment).
  - Handles graceful shutdown via `atexit` to ensure no data is lost when the app exits.
- **Fail-Safe**: If tracing is disabled or fails to initialize, it falls back to a `NoOpTracer` so the user's application never crashes.

### 2. The Transporter: `OTLP Exporter` (`exporters/otlp_exporter.py`)

Responsible for sending the collected data to the outside world.

- **Protocol**: Uses **gRPC** (via `OTLPSpanExporter`) for high-throughput, low-latency export.
- **Modes**:
  - `remote` (Default): Sends data to `OTLP_ENDPOINT`.
  - `console`: Prints Spans to stdout. Special logic exists to pretty-print `astra.agent_run` JSON attributes for easier debugging of Agent flows.
- **Security**: Supports `insecure` mode (no TLS) for local development setups.

### 3. Context & Helpers (`context.py`, `span_helpers.py`)

Utilities to make manual tracing easy for developers.

- **Context Propagation**: Ensures Trace IDs are preserved across threads and async tasks (using Python's `contextvars` under the hood).
- **Decorators**: The `@trace_span` decorator eliminates boilerplate for tracing function execution.

---

## Detailed Usage

### 1. Initialization

The tracer is usually initialized automatically by `observability.client`. However, for custom setups:

```python
from observability.tracing.tracer import AstraTracer
from observability.config import Config

tracer = AstraTracer()
tracer.initialize(
    config=Config(),    # Loads env vars automatically
    enable_tracing=True # Set to False to disable all overhead
)
```

### 2. Manual Instrumentation

While auto-instrumentation covers libraries, you often want to trace your own business logic.

#### A. Decorator (Recommended)

Automatically starts a span named after the function, captures arguments (optional), and records exceptions.

```python
from observability.tracing.span_helpers import trace_span

@trace_span(name="process_payment", attributes={"payment.currency": "USD"})
def process_payment(amount: float):
    # ... logic ...
    pass
```

#### B. Context Manager

For granular control over a specific block of code.

```python
from observability.tracing.span_helpers import start_span

def main_loop():
    # ... setup ...
    with start_span("complex_calculation") as span:
        result = do_math()
        span.set_attribute("calc.result", result)
        if result < 0:
            span.add_event("negative_result_warning")
```

### 3. Debugging with Console Exporter

To see what's being collected without setting up a backend:

1.  Set `OTLP_ENDPOINT=console` in your environment.
2.  Run your app.
3.  You will see formatted JSON output in your terminal.

---

## Configuration Reference

The behavior is driven by environment variables loaded into `observability.config.Config`:

| Variable                | Default           | Description                                                 |
| ----------------------- | ----------------- | ----------------------------------------------------------- |
| `ASTRA_SERVICE_NAME`    | `unknown_service` | The name of your service (e.g., `my-chatbot`).              |
| `OTLP_ENDPOINT`         | `localhost:4317`  | The gRPC address of the collector. Use `console` for debug. |
| `ASTRA_TRACING_ENABLED` | `true`            | Master switch to enable/disable tracing.                    |

---

## Technical Specifications

### Thread Safety

`AstraTracer` uses a `threading.Lock()` during initialization and singleton access, making it safe to use in multi-threaded applications (e.g., Flask, FastAPI).

### Batch Processing

We use `BatchSpanProcessor` instead of `SimpleSpanProcessor`.

- **Why?** Sending a network request for _every_ span would slow down your app.
- **How?** Spans are buffered in memory and sent in batches (default: every 5s or when 512 spans accumulate).
- **Shutdown**: When `tracer.shutdown()` is called (or app exits), the buffer is flushed immediately.
