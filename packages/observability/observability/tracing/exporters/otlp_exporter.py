from typing import Sequence
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan
import json

class AgentRunConsoleExporter(ConsoleSpanExporter):
    """
    Custom Console Exporter that prints the AgentRun JSON (pretty-printed) if present.
    If AgentRun data is found, the standard OpenTelemetry span output is suppressed.
    Otherwise, it behaves like the standard ConsoleSpanExporter.
    """
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            if span.attributes and "astra.agent_run" in span.attributes:
                try:
                    agent_run_str = span.attributes["astra.agent_run"]
                    if isinstance(agent_run_str, str):
                        # Parse and re-dump for pretty printing
                        agent_run_data = json.loads(agent_run_str)
                        print(json.dumps(agent_run_data, indent=4))
                        # Skip standard span output for agent runs
                        continue
                except Exception:
                    pass
            
            # Print the standard span output for non-agent runs
            super().export([span])
            
        return SpanExportResult.SUCCESS

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

    # For debugging purposes, if endpoint is 'console', return AgentRunConsoleExporter
    if endpoint.lower() == "console":
        return AgentRunConsoleExporter()

    return OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
