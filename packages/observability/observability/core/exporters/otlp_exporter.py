from typing import Sequence
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan
import json
import os

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

class JsonFileSpanExporter(ConsoleSpanExporter):
    """
    Exporter that saves spans as JSON arrays in the 'jsons' directory.
    Each trace is saved in a separate file named <trace_id>.json.
    """
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        # Hardcoded path as per requirement/environment
        output_dir = "/Users/apple/OpenSource/astra-v2/astra-agi/jsons"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for span in spans:
            trace_id = f"{span.get_span_context().trace_id:032x}"
            file_path = os.path.join(output_dir, f"{trace_id}.json")
            
            span_data = json.loads(span.to_json())
            
            current_data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                        if content:
                            current_data = json.loads(content)
                            if not isinstance(current_data, list):
                                # If existing content is not a list, wrap it or start new (safest to listify)
                                current_data = [current_data]
                except Exception:
                    # If file is corrupt or unreadable, start fresh
                    pass
            
            current_data.append(span_data)
            
            with open(file_path, "w") as f:
                json.dump(current_data, f, indent=4)
        
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

    if endpoint.lower() == "console":
        return AgentRunConsoleExporter()

    if endpoint.lower() == "json":
        return JsonFileSpanExporter()

    return OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
