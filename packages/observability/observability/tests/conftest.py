
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

class InMemorySpanExporter(SpanExporter):
    """
    A simple in-memory exporter for testing purposes.
    Captures spans in a list for assertion.
    """
    def __init__(self):
        self.spans = []

    def export(self, spans) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.spans.clear()

    def clear(self):
        self.spans.clear()
