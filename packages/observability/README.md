# Astra Observability Package

The **Astra Observability Package** is a powerful, automated observability solution designed specifically for LLM-based applications. Built on top of **OpenTelemetry (OTEL)**, it provides seamless interception, tracing, and metric collection for interactions with LLM providers (such as AWS Bedrock and Google GenAI) and internal agents.

This package serves as a middleware layer, abstracting the complexities of tracing and providing a unified view of your LLM application's performance, cost, and behavior.

---

## 🌟 Key Features

- **Auto-Instrumentation**: Automatically detects and instruments supported LLM libraries (e.g., `boto3`, `google-generativeai`) upon import. No manual wrapping required.
- **OpenTelemetry Native**: Built entirely on the OpenTelemetry standard, ensuring compatibility with any OTLP-compliant backend (Jaeger, Prometheus, Honeycomb, etc.).
- **Unified Data Model**: Normalizes requests and responses from different providers into a standard schema, making analysis consistent across models.
- **Vendor Agnostic**: Easily extensible architecture supporting multiple LLM providers via adapters.
- **Production Ready**: Includes batched span processing, error handling, and resource management designed for high-throughput environments.

---

## 📂 Directory Structure & File Responsibilities

This package is organized to separate concerns between the user-facing API, the core instrumentation engine, and the provider-specific logic.

```text
observability/
├── client.py                 # 🚀 Main Entry Point. Users interact primarily with this.
├── config.py                 # ⚙️ Configuration management (Env vars, Defaults).
├── decorators/               # 🎁 Decorators for manual tracing of functions.
│   └── __init__.py
├── instrumentation/          # 🧠 CORE LOGIC: The Auto-instrumentation Engine.
│   ├── __init__.py           # Exposes the `init()` function for bootstrapping.
│   ├── core/                 # Internal machinery for hooking into Python.
│   │   ├── base_instrumentor.py  # Abstract base class for all instrumentors.
│   │   ├── import_monitor.py     # Hooks `builtins.__import__` to detect library loads.
│   │   ├── operations.py         # Defines operation types (e.g., "chat", "embedding").
│   │   ├── registry.py           # Maps package names to their instrumentor implementations.
│   │   ├── version_checker.py    # Ensures target libraries meet version requirements.
│   │   └── wrapper_factory.py    # Helper to create consistent wrapper functions.
│   ├── models/               # 📊 Internal Data Models.
│   │   ├── llm.py                # Standardized Request/Response models.
│   │   └── observation.py        # The final "Observation" object exported to backends.
│   ├── providers/            # 🔌 Vendor-specific implementations.
│   │   ├── base/                 # Abstract classes for Adapters.
│   │   │   ├── adapter.py        # Defines how to parse vendor-specific data.
│   │   │   └── config.py         # Base config for providers.
│   │   ├── bedrock/              # AWS Bedrock implementation.
│   │   ├── google_genai/         # Google Gemini implementation.
│   │   └── registry.py           # Registers the providers with the core registry.
│   └── common/               # 🛠 Shared utilities.
│       ├── metrics.py            # Common metric definitions.
│       ├── semconv.py            # Semantic Conventions (Standard attribute names).
│       └── span_management.py    # Helpers for managing span lifecycle.
├── pricing/                  # 💰 Cost calculation logic.
├── tracing/                  # 📡 OpenTelemetry Wrapper.
│   ├── tracer.py             # Singleton TracerProvider manager.
│   ├── context.py            # Context propagation helpers.
│   └── exporters/            # OTLP Export logic.
└── utils/                    # 🔧 General utilities.
```

---

## 🏗 Architecture Deep Dive

The system architecture is designed to be non-intrusive. It "hooks" into the Python runtime to intercept calls to specific libraries.

### 1. The Client (`client.py`)

The `Client` class is the orchestrator. When you initialize it:

1.  It loads configuration from `config.py` (and environment variables).
2.  It initializes the `AstraTracer` singleton.
3.  It triggers the **Auto-Instrumentation** process.

### 2. The Auto-Instrumentation Engine (`instrumentation/core`)

This is the heart of the package.

- **Import Monitor (`import_monitor.py`)**: This component monkey-patches Python's built-in `__import__` function. It watches for imports of libraries we support (like `boto3`).
- **Registry (`registry.py`)**: Holds the mapping between a library name (e.g., `google.generativeai`) and its corresponding `Instrumentor`.
- **Instrumentors**: When a target library is imported, the specific `Instrumentor` is instantiated. It uses **Monkey Patching** to replace the library's core methods (e.g., `generate_content`) with a wrapper.

### 3. The Wrapper Flow

When your application calls an LLM method (e.g., `client.chat.completions.create`):

1.  **Interception**: The wrapper function defined in `instrumentation/common/wrappers.py` catches the call.
2.  **Start Span**: A new OpenTelemetry span is started.
3.  **Request Adaptation**: The specific **Provider Adapter** (e.g., `instrumentation/providers/bedrock/adapter.py`) takes the raw arguments and converts them into a standardized `LLMRequest` model.
4.  **Execution**: The original library method is called.
5.  **Response Adaptation**: The result (or exception) is captured. The Adapter converts it into a `LLMResponse` model.
6.  **End Span**: The span is ended, and data is sent to the exporter.

### 4. Data Normalization (`instrumentation/providers`)

Since every LLM provider has a different API, we use **Adapters** to normalize data.

- **Input**: Raw `args` and `kwargs` from the function call.
- **Output**: Unified `LLMRequest` and `LLMResponse` objects.
- **Benefit**: Your analysis backend only needs to understand ONE format, regardless of whether you used OpenAI, Bedrock, or Gemini.

---

## � Quick Start

### 1. Installation

Ensure the package is in your python path.

### 2. Basic Usage

Initialize the client at the start of your application. That's it!

```python
from observability.client import Client

# 1. Initialize the Client
# This sets up the tracer and hooks into the import system.
obs_client = Client(
    service_name="my-genai-service",
    endpoint="http://localhost:4317"  # Your OTLP Collector
)

# 2. Import your LLM library AFTER initializing the client
import boto3

# 3. Use the library as normal
bedrock = boto3.client("bedrock-runtime")
response = bedrock.invoke_model(...)

# The call above is automatically traced!
```

---

## ⚙️ Configuration

Configuration is managed via `observability/config.py`. You can override these using environment variables.

| Environment Variable       | Default                 | Description                              |
| -------------------------- | ----------------------- | ---------------------------------------- |
| `ASTRA_SERVICE_NAME`       | `astra-service`         | Name of your service in traces.          |
| `OTLP_ENDPOINT`            | `http://localhost:4317` | URL of the OTLP collector.               |
| `ASTRA_TRACE_ENABLED`      | `true`                  | Master switch to enable/disable tracing. |
| `ASTRA_ENABLE_OTLP_EXPORT` | `false`                 | Whether to send traces to the endpoint.  |

---

## � Extending: Adding a New Provider

To add support for a new LLM provider (e.g., "Anthropic"):

1.  **Create Directory**: Create `instrumentation/providers/anthropic/`.
2.  **Implement Adapter**: Inherit from `ProviderAdapter` in `adapter.py`. Implement `parse_request`, `parse_response`, etc.
3.  **Implement Instrumentor**: Create an `Instrumentor` class that defines which methods to patch.
4.  **Register**: Add the new provider to `instrumentation/providers/registry.py`.

---

## 📊 Data Models

### `LLMRequest`

- **model**: The name of the model used (e.g., "gpt-4").
- **messages**: A list of standardized message objects.
- **parameters**: Temperature, top_p, etc.

### `LLMResponse`

- **content**: The text generated by the model.
- **token_usage**: Input and output token counts.
- **status**: Success or failure status.

---

## 🎁 Decorators: Manual Tracing APIs

- Purpose: Provide lightweight, explicit tracing around agents, tools, LLM calls, workflow steps, and error handling, complementing auto-instrumentation.
- Standard: Built on OpenTelemetry spans and attributes, integrating with existing provider spans.

### `@trace_agent`

- Creates a root span for each agent invocation.
- Captures metadata:
  - agent.name
  - agent.type
  - agent.thread_id / agent.conversation_id
- Establishes parent-child relationships so internal operations appear under the agent span.

Usage:

```python
from observability.decorators import trace_agent

@trace_agent(name="ResearchAgent", agent_type="react", thread_id="thr-123", conversation_id="conv-456")
def run_agent(task: str):
    return "done"
```

### `@trace_tool`

- Generates spans for each tool invocation.
- Records:
  - tool.name
  - tool.input (sanitized)
  - tool.output or tool.error
  - span.duration_ms (auto)

Usage:

```python
from observability.decorators import trace_tool

@trace_tool(name="search_web")
def search_web(query: str, api_key: str):
    return {"hits": 3}
```

### `@trace_llm_call`

- Wraps logical LLM operations with semantic boundaries.
- Tracks:
  - llm.request.model
  - llm.request.temperature
  - llm.request.max_tokens
  - genai.request.prompt
  - genai.response.text
- Parent-child relation with provider spans is automatically maintained via the active context.

Usage:

```python
from observability.decorators import trace_llm_call

@trace_llm_call(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=256,
    prompt_extractor=lambda *args, **kwargs: kwargs.get("prompt", ""),
    response_extractor=lambda resp: resp.get("text", "") if isinstance(resp, dict) else str(resp),
)
def call_llm(prompt: str):
    return {"text": "Hello"}
```

### `@trace_step` (High Priority)

- Creates hierarchical spans for agent workflow steps:
  - Plan, Think, Decide, Execute
- Annotates each step with:
  - step.name
  - step.purpose

Usage:

```python
from observability.decorators import trace_step

@trace_step("Plan", "Outline solution path")
def plan_step(context):
    return {"plan": ["step1", "step2"]}
```

### `@trace_error`

- Captures comprehensive error context on the active span:
  - error.type
  - error.message
  - error.stacktrace
- Records exceptions and re-raises for normal application flow.

Usage:

```python
from observability.decorators import trace_error

@trace_error()
def fragile():
    raise RuntimeError("boom")
```

---

## ⚙️ Required Configuration

- Initialize the Observability client before use:

```python
from observability.client import Client

client = Client(service_name="my-service", endpoint="http://localhost:4317", enable_tracing=True)
```

- Environment variables (see Configuration section) control OTLP export, service identity, and batch processor behavior.

---

## 🧾 Expected Tracing Output

- Spans appear with names like:
  - agent.run
  - tool.<tool_name>
  - llm.call
  - agent.step.<StepName>
- Attributes include:
  - agent._, tool._, step._, error._, llm.request.\*, genai.request.prompt, genai.response.text
- Duration is emitted as span.duration_ms.
- Errors set StatusCode.ERROR and include recorded exceptions.

---

## 🛠 Troubleshooting

- No spans exported:
  - Ensure Client(enable_tracing=True) is called early.
  - Verify OTLP endpoint and exporter configuration.
- Missing child spans:
  - Ensure decorators wrap the logical parent function.
  - Import LLM libraries after initializing the Client.
- Large payloads truncated:
  - Inputs and outputs are length-limited to protect performance.
- Sensitive data leaked:
  - Tool inputs are sanitized; avoid passing secrets in arbitrary keys.

---

## ⚡ Performance Considerations

- Decorators add minimal overhead by reusing thread-safe span helpers.
- Attributes use truncation to limit large payloads.
- BatchSpanProcessor configuration in Config balances throughput and latency.
- Benchmarks included under tests/benchmarks for quick local evaluation.

---

## 🔗 Version Compatibility

- Requires Python 3.10–3.13.
- Depends on OpenTelemetry 1.38.x APIs and SDK.
- Integrates with existing provider instrumentations in this package without breaking changes.
