# Astra Observability SDK

The `observability` package provides a robust, production-ready observability solution for Python applications, built on top of OpenTelemetry. It simplifies tracing, logging, and instrumenting LLM (Large Language Model) applications.

## Features

- **Automated Tracing**: Easy implementation of OpenTelemetry tracing.
- **LLM Instrumentation**: Dedicated support for tracking LLM token usage, costs, and prompts.
- **JSON Logging**: Structured JSON logging with trace context correlation.
- **OTLP Export**: Built-in support for exporting traces via OTLP (gRPC/HTTP), Console, or JSON files.
- **Configuration**: Flexible configuration via environment variables or code.

## Directory Structure

The package is organized modules for clarity and maintainability:

```
observability/
├── client.py             # Main entry point (Client class)
├── core/
│   ├── config.py         # Configuration management
│   ├── exceptions.py     # Custom exceptions
│   ├── logger.py         # JSON logger implementation
│   ├── span.py           # Span management helpers
│   └── tracer.py         # Singleton TracerProvider wrapper
├── exporters/
│   └── otlp_exporter.py  # OTLP and File exporters
├── instrumentation/      # Auto-instrumentation modules
├── semantic/             # Semantic conventions (Attributes)
└── utils/                # Helper utilities
```

## Usage

### Initialization

Initialize the SDK using the `Observability` helper or directly via `Client`.

```python
from observability import Observability

# Initialize global observability
client = Observability.init(
    service_name="my-service",
    enable_tracing=True,
    enable_json_logs=True
)

# Access the logger
client.logger.info("Service started")
```

### Manual Tracing

Use the provided decorators or context managers to trace specific functions or blocks of code.

```python
from observability.core.span_helpers import trace_span, start_span

@trace_span(name="process_data")
def process_data(data):
    # ... logic ...
    pass

def manual_trace():
    with start_span("manual_operation") as span:
        span.set_attribute("custom.key", "value")
        # ... logic ...
```

### Configuration

Configuration can be set via environment variables (e.g., `OTLP_ENDPOINT`, `SERVICE_NAME`) or passed programmatically using the `Config` object.

```python
from observability.core.config import Config

config = Config(
    SERVICE_NAME="custom-service",
    OTLP_ENDPOINT="http://localhost:4317"
)
```

## Exporters

The SDK supports multiple export destinations configurable via `OTLP_ENDPOINT`:

- **OTLP Grpc/Http**: Provide a standard URL (e.g., `http://localhost:4317`).
- **Console**: Set endpoint to `console` for standard output debugging.
- **JSON File**: Set endpoint to `json` to write trace files to `jsons/<trace_id>/trace.json`.

## Development

- **Tests**: Located in `tests/`. Run with `pytest`.
- **Core Logic**: Main tracing logic resides in `core/tracer.py`.
