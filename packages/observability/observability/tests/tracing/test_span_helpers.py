import unittest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from observability.tracing.span_helpers import trace_span, start_span, set_span_attributes, add_event
from observability.tracing.tracer import AstraTracer
from observability.config import Config

class TestSpanHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize with console exporter to avoid network calls
        AstraTracer._instance = None
        AstraTracer._is_initialized = False
        cls.tracer = AstraTracer()
        config = Config(SERVICE_NAME="test-service", OTLP_ENDPOINT="console")
        cls.tracer.initialize(config=config, enable_tracing=True)

    @classmethod
    def tearDownClass(cls):
        # Clean up after all tests
        try:
            if cls.tracer.is_initialized:
                cls.tracer.shutdown()
        except:
            pass
        AstraTracer._instance = None

    def test_trace_span_decorator(self):
        @trace_span(name="decorated-function", attributes={"key": "value"})
        def my_func():
            return "success"

        result = my_func()
        self.assertEqual(result, "success")
        # Verification of span creation would ideally involve a memory exporter or mock

    def test_start_span_context_manager(self):
        with start_span("manual-span", attributes={"foo": "bar"}) as span:
            self.assertTrue(span.is_recording())
            set_span_attributes({"extra": "attr"})
            add_event("something_happened")

    def test_trace_span_exception(self):
        @trace_span()
        def failing_func():
            raise ValueError("oops")

        with self.assertRaises(ValueError):
            failing_func()

if __name__ == "__main__":
    unittest.main()
