import unittest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from observability.tracing.tracer import AstraTracer
from observability.tracing.context import get_current_trace_id, get_current_span_id
from observability.config import Config

class TestContext(unittest.TestCase):
    def setUp(self):
        # Initialize with console exporter for testing
        AstraTracer._instance = None
        AstraTracer._is_initialized = False
        self.tracer = AstraTracer()
        config = Config(SERVICE_NAME="test-service", OTLP_ENDPOINT="console")
        self.tracer.initialize(config=config, enable_tracing=True)

    def tearDown(self):
        # Clean up
        try:
            if self.tracer.is_initialized:
                self.tracer.shutdown()
        except:
            pass
        AstraTracer._instance = None

    def test_get_current_trace_id_no_span(self):
        # No active span
        self.assertIsNone(get_current_trace_id())

    def test_get_current_span_id_no_span(self):
        # No active span
        self.assertIsNone(get_current_span_id())

    def test_with_active_span(self):
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("test-span") as span:
            trace_id = get_current_trace_id()
            span_id = get_current_span_id()
            
            self.assertIsNotNone(trace_id)
            self.assertIsNotNone(span_id)
            self.assertEqual(len(trace_id), 32)
            self.assertEqual(len(span_id), 16)

if __name__ == "__main__":
    unittest.main()
