from collections.abc import Sequence
import json
import sys

from observability.utils.span_json import SpanJsonMapper, TraceJsonWriter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExportResult, SpanExporter


class AgentRunConsoleExporter(ConsoleSpanExporter):
    """
    Custom Console Exporter that prints the AgentRun JSON (pretty-printed) if present.
    If AgentRun data is found, the standard OpenTelemetry span output is suppressed.
    Otherwise, it behaves like the standard ConsoleSpanExporter.
    """
    def __init__(self):
        super().__init__()
        self._mapper = SpanJsonMapper()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            if span.attributes and "astra.agent_run" in span.attributes:
                try:
                    agent_run_str = span.attributes["astra.agent_run"]
                    if isinstance(agent_run_str, str):
                        # Parse and re-dump for pretty printing
                        agent_run_data = json.loads(agent_run_str)
                        sys.stdout.write(json.dumps(agent_run_data, indent=4) + "\n")
                        continue
                except Exception:
                    pass

            try:
                sys.stdout.write(json.dumps(self._mapper.to_span_dict(span), indent=2) + "\n")
            except Exception:
                super().export([span])

        return SpanExportResult.SUCCESS

class JsonFileSpanExporter(SpanExporter):
    def __init__(self, output_dir: str | None = None):
        self._writer = TraceJsonWriter(output_dir=output_dir)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            self._writer.export_spans(list(spans))
        except Exception as e:
            sys.stderr.write(f"Error exporting spans to JSON: {e}\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

def create_otlp_exporter(endpoint: str, insecure: bool):
    """
    Creates and configures an OTLP Span Exporter.

    Args:
        endpoint (str): The OTLP endpoint URL (e.g., "localhost:4317").
        insecure (bool): Whether to use an insecure connection (HTTP/gRPC without TLS).

    Returns:
        OTLPSpanExporter: The configured exporter instance.
    """
    if not endpoint:
        raise ValueError("Endpoint must be provided")

    if endpoint.lower() == "console":
        return AgentRunConsoleExporter()

    if endpoint.lower() == "json":
        return JsonFileSpanExporter()

    return OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
