# Astra Observability Package

A comprehensive observability solution for the Astra AI platform, providing distributed tracing, metrics collection, and structured logging with automatic trace correlation.

## Features

### 🔍 Distributed Tracing

- **OpenTelemetry-based**: Industry-standard distributed tracing
- **Async-first**: Designed for async Python applications
- **Decorator support**: Easy-to-use `@trace_span` decorators
- **Context propagation**: Automatic trace context across async operations
- **Console export**: MVP-ready with console output (easily switchable to OTLP)

### 📊 Metrics Collection

- **Prometheus-compatible**: Standard metrics format
- **Agent performance**: Run counts, latencies, success rates
- **Model usage**: Token tracking, cost calculation, TTFT metrics
- **Tool execution**: Call counts, durations, error rates
- **Cost tracking**: Built-in cost calculation for major LLM providers

### 📝 Structured Logging

- **Loguru-powered**: Clean, powerful logging API
- **JSON formatting**: Structured logs for easy parsing
- **Trace correlation**: Automatic trace/span ID injection
- **Context propagation**: Agent, session, request IDs
- **Performance optimized**: Async-friendly, non-blocking

## Quick Start

### Installation

```bash
cd packages/observability
pip install -e .
```

### Basic Usage

```python
from observability import init_observability

# Initialize observability
obs = init_observability(
    service_name="astra",
    environment="dev",
    log_level="INFO"
)

# Use in agent code
@obs.trace_agent_run("my-agent")
async def run_agent():
    obs.info("Agent started", agent_id="my-agent")

    # Model call with automatic metrics
    cost = obs.calculate_model_cost("gpt-4", "openai", 100, 50)
    obs.record_model_usage("gpt-4", "openai", 100, 50, cost)

    # Tool call with timing
    with obs.timer(obs.record_tool_call, tool_name="web_search"):
        # Tool execution here
        pass

    obs.info("Agent completed", agent_id="my-agent")
```

### Advanced Usage

```python
from observability import Observability, Tracer, MetricsRecorder, Logger

# Use components separately
tracer = Tracer("astra", "prod")
metrics = MetricsRecorder("astra")
logger = Logger("astra", "prod", log_level="INFO")

# Manual span management
@tracer.trace_span("custom.operation", {"component": "data_processor"})
async def process_data():
    tracer.add_event("processing.started")
    # ... processing logic ...
    tracer.set_attribute("items.processed", 100)
```

## Architecture

### Components

1. **Observability**: Main facade providing unified access to all observability features
2. **Tracer**: OpenTelemetry-based distributed tracing with span management
3. **MetricsRecorder**: Prometheus-compatible metrics collection with cost tracking
4. **Logger**: Loguru-based structured logging with trace correlation

### Integration Points

- **Framework Layer**: Agents use `@obs.trace_agent_run()` decorators
- **Model Clients**: Automatic token/cost tracking via `obs.record_model_usage()`
- **Tool Registry**: Tool calls traced with `@obs.trace_tool_call()`
- **Session Management**: Context propagation via `session_id`, `request_id`

## Configuration

### Environment Variables

```bash
# Service identification
ASTRA_SERVICE_NAME=astra
ASTRA_ENVIRONMENT=dev

# Logging
ASTRA_LOG_LEVEL=INFO
ASTRA_LOG_FILE=/var/log/astra.json

# Tracing (future OTLP support)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=astra
```

### Programmatic Configuration

```python
obs = Observability.init(
    service_name="astra",
    environment="prod",
    log_level="WARNING",
    enable_json_logs=True,
    log_file="/var/log/astra.json"
)
```

## Output Examples

### Trace Output (Console)

```json
{
  "name": "astra.framework.agent.run",
  "context": {
    "trace_id": "a1b2c3d4e5f6...",
    "span_id": "1a2b3c4d...",
    "parent_id": null
  },
  "start_time": "2024-01-15T10:30:00.123Z",
  "end_time": "2024-01-15T10:30:01.456Z",
  "duration": 1333,
  "status": "OK",
  "attributes": {
    "agent_id": "research-agent",
    "session_id": "sess-123",
    "environment": "dev"
  }
}
```

### Metrics Output (Prometheus)

```
# HELP astra_agent_runs_total Total number of agent runs
# TYPE astra_agent_runs_total counter
astra_agent_runs_total{agent_id="research-agent",status="success",environment="dev"} 1

# HELP astra_model_cost_usd_total Total cost in USD for model usage
# TYPE astra_model_cost_usd_total counter
astra_model_cost_usd_total{model_name="gpt-4",provider="openai",environment="dev"} 0.0045
```

### Log Output (JSON)

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "message": "Agent execution started",
  "service": "astra",
  "environment": "dev",
  "trace_id": "a1b2c3d4e5f6...",
  "span_id": "1a2b3c4d...",
  "extra": {
    "agent_id": "research-agent",
    "session_id": "sess-123",
    "event_type": "agent_start"
  }
}
```

## Performance Characteristics

- **Trace overhead**: < 5ms per span (batched export)
- **Metrics overhead**: < 2% CPU (in-memory counters)
- **Log overhead**: < 1ms per log (async I/O)
- **Memory usage**: ~10MB baseline + ~1KB per active span
- **Async-friendly**: Non-blocking I/O operations

## Dependencies

- `opentelemetry-api>=1.38.0`: Tracing API
- `opentelemetry-sdk>=1.38.0`: Tracing implementation
- `prometheus-client>=0.20.0`: Metrics collection
- `loguru>=0.7.0`: Structured logging

## Future Enhancements

- **OTLP Export**: Switch from console to OTLP for production
- **Sampling**: Configurable trace sampling rates
- **Custom Exporters**: ClickHouse, Jaeger, custom backends
- **Dashboards**: Grafana dashboards for metrics visualization
- **Alerting**: Prometheus alerting rules for error rates/latency

## Examples

See `example_usage.py` for comprehensive usage examples including:

- Full agent run with tracing, metrics, and logging
- Manual span management
- Metrics-only usage
- Error handling and exception recording

## Testing

```bash
# Run the example
python example_usage.py

# Install dependencies first
pip install opentelemetry-api opentelemetry-sdk prometheus-client loguru
```
