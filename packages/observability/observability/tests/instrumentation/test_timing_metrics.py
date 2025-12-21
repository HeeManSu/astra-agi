import time
import unittest
from unittest.mock import patch
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from observability.instrumentation.common.span_management import start_span, end_span
from opentelemetry.trace import StatusCode

class _MemoryExporter(SpanExporter):
    def __init__(self):
        self.spans = []
    def export(self, spans) -> "SpanExportResult":  # type: ignore[override]
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS
    def shutdown(self) -> None:
        pass

class TestTimingMetrics(unittest.TestCase):
    def setUp(self):
        provider = TracerProvider()
        self.exporter = _MemoryExporter()
        provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self._tracer = provider.get_tracer("observability.instrumentation")
        self._get_tracer_patch = patch("observability.instrumentation.common.span_management.get_tracer", return_value=self._tracer)
        self._get_tracer_patch.start()

    def tearDown(self):
        self._get_tracer_patch.stop()

    def _find_span(self, name: str):
        for s in self.exporter.spans:
            if s.name == name:
                return s
        return None

    def test_duration_attribute(self):
        span_ctx, span = start_span("timing-test", {})
        time.sleep(0.05)
        end_span(span_ctx, span, status_code=StatusCode.OK)
        s = self._find_span("timing-test")
        self.assertIsNotNone(s)
        attrs = s.attributes
        self.assertIn("span.start_time_unix_ns", attrs)
        self.assertIn("span.end_time_unix_ns", attrs)
        self.assertIn("span.duration_ms", attrs)
        self.assertGreater(attrs["span.duration_ms"], 40.0)
        self.assertLess(attrs["span.duration_ms"], 500.0)

    def test_parent_child_relationship_attribute(self):
        p_ctx, p_span = start_span("parent", {})
        c_ctx, c_span = start_span("child", {})
        end_span(c_ctx, c_span, status_code=StatusCode.OK)
        end_span(p_ctx, p_span, status_code=StatusCode.OK)
        parent = self._find_span("parent")
        child = self._find_span("child")
        self.assertIsNotNone(parent)
        self.assertIsNotNone(child)
        parent_ctx = getattr(parent, "context", None)
        child_parent_ctx = getattr(child, "parent", None)
        self.assertIsNotNone(parent_ctx)
        self.assertIsNotNone(child_parent_ctx)
        self.assertEqual(getattr(child_parent_ctx, "span_id", None), getattr(parent_ctx, "span_id", None))

if __name__ == "__main__":
    unittest.main()
