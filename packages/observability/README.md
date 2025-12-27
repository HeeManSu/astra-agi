# Astra Observability Package

The **Astra Observability Package** provides a comprehensive, automated observability solution for LLM-based applications. It is built on top of **OpenTelemetry (OTEL)** and designed to seamlessly intercept, trace, and metricize interactions with LLM providers (AWS Bedrock, Google GenAI) and internal agents.

---

## 📂 Directory Structure

Here is a breakdown of the package structure and the responsibilities of each module:

```text
observability/
├── decorators/               # Decorators for manual tracing.
├── instrumentation/          # CORE LOGIC: Auto-instrumentation engine.
│   ├── core/                 # The engine under the hood (Registry, Import Monitor, Base Instrumentor).
│   ├── models/               # Internal Data Models (Standardized Request/Response, Observation schema).
│   ├── providers/            # Vendor-specific logic (Bedrock, Gemini).
│   └── common/               # Shared utilities (Metrics, SemConv, Span Helpers).
├── tracing/                  # OpenTelemetry Wrapper (Tracer, Context, Exporters).
├── utils/                    # General utilities.
└── client.py                 # Main entry point.
```

---

## 🏗 High-Level Architecture

The system operates as a middleware layer that sits between your user application and the external LLM SDKs.

```text
 ┌───────────────────────────────────────────────────────────────────────────┐
 │                         OBSERVABILITY SDK                                 │
 │  ┌─────────────────────────────────────────────────────────────────────┐  │
 │  │                     INSTRUMENTATION LAYER                           │  │
 │  │                                                                     │  │
 │  │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │  │
 │  │   │   REGISTRY     │  │   PATCHING     │  │   WRAPPERS     │        │  │
 │  │   │                │  │                │  │                │        │  │
 │  │   │ • Auto-Detect  │  │ • Monkey Patch │  │ • Start Span   │        │  │
 │  │   │ • Lazy Load    │  │ • Restore      │  │ • End Span     │        │  │
 │  │   └───────┬────────┘  └───────┬────────┘  └───────┬────────┘        │  │
 │  │           │                   │                   │                 │  │
 │  │           └───────────────────┼───────────────────┘                 │  │
 │  │                               │                                     │  │
 │  │                               ▼                                     │  │
 │  │           ┌─────────────────────────────────────────┐               │  │
 │  │           │            PROVIDER ADAPTERS            │               │  │
 │  │           │  ┌─────────┐ ┌─────────┐ ┌─────────┐    │               │  │
 │  │           │  │ Bedrock │ │ Gemini  │ │ OpenAI* │    │               │  │
 │  │           │  └────┬────┘ └───┬─────┘ └───┬─────┘    │               │  │
 │  │           └───────┼──────────┼───────────┼──────────┘               │  │
 │  │                   │          │           │                          │  │
 │  │                   ▼          ▼           ▼                          │  │
 │  │           ┌─────────────────────────────────────────┐               │  │
 │  │           │           DATA NORMALIZATION            │               │  │
 │  │           │  (Unified Request/Response Model)       │               │  │
 │  │           └───────────────────┬─────────────────────┘               │  │
 │  └───────────────────────────────┼─────────────────────────────────────┘  │
 │                                  │                                        │
 │                                  ▼                                        │
 │                    ┌──────────────────────────┐                           │
 │                    │       TRACING CORE       │                           │
 │                    │   (OpenTelemetry SDK)    │                           │
 │                    └─────────────┬────────────┘                           │
 │                                  │                                        │
 │                                  ▼                                        │
 │                    ┌──────────────────────────┐                           │
 │                    │      OTLP EXPORTER       │                           │
 │                    │   (To Collector/Cloud)   │                           │
 │                    └──────────────────────────┘                           │
 └───────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Low-Level Design (LLD) & Execution Flow

### 1. Initialization Phase

**Entry Point**: `Client`.

1.  **Configuration**: Loads settings from environment variables.
2.  **Tracer Setup**: Initializes the `AstraTracer` singleton, setting up the TracerProvider and Exporters.
3.  **Auto-Instrumentation**: Bootstraps the instrumentation engine.
    - **Registry**: Loads available providers.
    - **Import Monitor**: Attaches hooks to the import system to detect when target libraries are loaded.

### 2. Instrumentation Phase (The "Hook")

**Core Logic**: `instrumentation/core`.

1.  **Target Detection**: Detects when a supported library is imported.
2.  **Monkey Patching**: Replaces core API methods with wrapper functions.
3.  **Wrapper Logic**:
    - **Start Span**: Initiates a new trace span.
    - **Parse Request**: Uses an **Adapter** to normalize the input arguments.
    - **Call Original**: Executes the original library method.
    - **Parse Response**: Uses an **Adapter** to normalize the output.
    - **End Span**: Completes the trace span.

### 3. Data Normalization (Adapters)

**Core Logic**: `instrumentation/providers`.

- **Problem**: Every LLM provider has a different API schema.
- **Solution**: **Adapters** convert these into a unified **Internal Model**.
- **Benefits**: The backend analysis tools only need to understand ONE format.

---

## 📊 Data Models

The system uses strict models to ensure validation of telemetry data.

### 1. `LLMRequest`

Represents the input to the model.

- **Attributes**: Model name, messages, temperature, max tokens.
- **Normalization**: All provider-specific prompts are converted to a standard message format.

### 2. `LLMResponse`

Represents the output from the model.

- **Attributes**: Content, role, finish reason, token usage.

### 3. `Observation` (Root Model)

The final object that is constructed and exported.

- **Components**: Trace Info, LLM Info, Usage Info (Tokens, Latency, Cost), and Conversation Data.

---

## 🚀 Quick Start

```python
from observability.client import Client

# 1. Initialize the Client
obs_client = Client(
    service_name="my-ai-service",
    endpoint="http://localhost:4317"
)

# 2. Use your library as normal (e.g., boto3)
# Calls are AUTOMATICALLY intercepted and traced!
```
