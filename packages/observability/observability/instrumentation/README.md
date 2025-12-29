# AstraOps Instrumentation

This module provides automatic instrumentation for LLM providers (AWS Bedrock, Google GenAI) and agentic libraries. It hooks into Python’s import system to detect when target libraries load and wraps key methods to emit OpenTelemetry spans through AstraOps’ tracer.

## Features

- **Automatic Import Detection**: Uses `sys.meta_path` to instrument libraries as they are imported.
- **Unified Data Models**: Normalizes vendor-specific payloads into standard `LLMRequest` and `LLMResponse` objects.
- **Provider Adapters**: Decouples instrumentation logic from data parsing logic.
- **Privacy-Aware**: Configurable truncation for prompts and completions.
- Fail-Safe: Errors in instrumentation never crash the user application.

## Supported Providers

| Provider         | Library        | Supported Operations                                       |
| ---------------- | -------------- | ---------------------------------------------------------- |
| **Google GenAI** | `google-genai` | `generate_content` (Sync & Async), Streaming               |
| **AWS Bedrock**  | `boto3`        | `invoke_model` (Anthropic Claude, Amazon Titan), Streaming |
| **OpenAI**       | `openai`       | _(Coming Soon)_                                            |

## Structure

```text
instrumentation/
├── __init__.py                  # Entry; registers providers; attaches import hook
├── core/
│   ├── base_instrumentor.py     # Abstract base class & InstrumentorConfig
│   ├── import_monitor.py        # __import__ hook & lazy loading logic
│   ├── operations.py            # Operation specifications (e.g., 'generate', 'chat')
│   ├── registry.py              # Registry for mapping packages to instrumentors
│   ├── version_checker.py       # Version parsing & compatibility checks
│   └── wrapper_factory.py       # Generic wrapper for method interception
├── models/
│   ├── llm.py                   # Unified LLM Request/Response schemas
│   └── observation.py           # Root observation schema for export
├── providers/
│   ├── base/
│   │   ├── adapter.py           # Abstract ProviderAdapter class
│   │   └── config.py            # Base provider configuration
│   ├── bedrock/                 # AWS Bedrock implementation
│   ├── google_genai/            # Google GenAI implementation
│   └── registry.py              # Provider registration catalog
└── common/
    ├── metrics.py               # Metrics utilities
    ├── semconv.py               # Semantic conventions (attribute names)
    ├── span_management.py       # Span lifecycle helpers
    └── wrappers.py              # Low-level wrapper utilities
```

## How It Works

1.  **Initialization**:

    - `instrumentation.init()` is called (usually by `observability.client`).
    - It registers built-in providers (Bedrock, Google GenAI) into the `InstrumentationRegistry`.
    - It attaches an `ImportMonitor` to `sys.meta_path`.

2.  **Detection**:

    - When a user imports a target library (e.g., `import boto3`), the `ImportMonitor` detects it.
    - It looks up the corresponding `Instrumentor` in the registry.

3.  **Instrumentation**:

    - The `Instrumentor` (e.g., `BedrockInstrumentor`) patches the target methods (e.g., `_make_api_call`).
    - It uses `wrapper_factory` to create a safe wrapper around the original method.

4.  **Execution Flow**:
    - **Pre-Call**: The wrapper starts a Span and uses a `ProviderAdapter` to parse the input arguments into an `LLMRequest`.
    - **Call**: The original method is executed.
    - **Post-Call**: The wrapper intercepts the response, uses the `ProviderAdapter` to parse it into an `LLMResponse`, and sets attributes on the Span.
    - **Export**: The Span is ended and exported via the Tracer.

## Configuration

Use `InstrumentorConfig` to control behavior:

```python
@dataclass
class InstrumentorConfig:
    auto_instrument: bool = True          # Enable/disable auto-instrumentation
    instrument_llm_calls: bool = True     # Toggle LLM tracing
    privacy_truncate_chars: int = 2000    # Max chars for prompt/completion
    fail_safe: bool = True                # Suppress instrumentation errors
    provider_options: Optional[Dict] = None # Global provider settings
    provider_configs: Mapping[str, Any] = field(default_factory=dict) # Per-provider config
```

## Extending Providers

To add a new provider (e.g., OpenAI), you need to implement two main components:

1.  **Adapter (`providers/<provider>/adapter.py`)**:

    - Subclass `ProviderAdapter`.
    - Implement methods to parse requests/responses (`parse_request`, `parse_response`).
    - Implement attribute mapping (`build_request_attributes`, `build_usage_attributes`).

2.  **Instrumentor (`providers/<provider>/instrumentor.py`)**:

    - Subclass `BaseInstrumentor`.
    - Define `target_packages` (e.g., `("openai",)`).
    - Implement `_do_instrument` to patch the library's client methods.
    - Use your Adapter to process data within the wrapper.

3.  **Registration**:
    - Register your instrumentor in `providers/registry.py`.

## Testing

- Tests should mock the target library to avoid making real API calls.
- Use `InMemorySpanExporter` to verify that Spans are created with correct attributes.
- Ensure that `fail_safe` behavior works (i.e., app doesn't crash if parsing fails).
