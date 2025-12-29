# Adding New LLM Providers

This directory contains the implementations for various LLM provider instrumentors.

## Architecture

The instrumentation system is designed to be modular and extensible. Key components:

1.  **Registry (`observability.instrumentation.providers.registry`)**: The central catalog where built-in providers are registered.
2.  **Base Adapter (`observability.instrumentation.providers.base.adapter.ProviderAdapter`)**: The abstract base class that all provider adapters must implement.
3.  **Instrumentor (`observability.instrumentation.core.base_instrumentor.BaseInstrumentor`)**: The class responsible for patching the provider's library.

## How to Add a New Provider (e.g., AWS Bedrock)

### 1. Create Provider Directory

Create a new directory for your provider, e.g., `observability/instrumentation/providers/aws_bedrock/`.

### 2. Implement the Adapter

Create `adapter.py` inheriting from `ProviderAdapter`. You must implement methods to parse requests/responses and calculate costs.

**Streaming Support:**
If the provider returns a custom object for streaming (not a simple iterator), override `instrument_stream` (and `instrument_async_stream`).
This allows you to wrap the response object (e.g., `boto3`'s dict response) and intercept the stream consumption while preserving the original API contract.

```python
    def instrument_stream(self, operation, request, response, callback, truncate_limit):
        # Example for boto3
        original_stream = response['body']
        wrapped_stream = self._wrap_iterator(..., original_stream, callback, ...)
        response['body'] = wrapped_stream
        return response
```

### 3. Implement the Instrumentor

Create `instrumentor.py` inheriting from `BaseInstrumentor`.

- Define `target_packages`.
- Implement `_do_instrument` to wrap the target methods using `wrapper_factory`.

### 4. Register the Provider

Add your provider to `observability/instrumentation/providers/registry.py`:

```python
    registry.register(
        package_name="boto3",
        spec=InstrumentorSpec(
            module_path="observability.instrumentation.providers.aws_bedrock.instrumentor",
            class_name="AWSBedrockInstrumentor",
            min_version="1.0.0",
        ),
    )
```

## Best Practices

- **Separation of Concerns**: Keep pricing logic separate or within the adapter's `calculate_cost`.
- **Backward Compatibility**: Ensure your adapter handles different versions of the provider library if necessary.
- **Testing**: Add unit tests for your adapter's parsing logic.
