
import unittest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from observability.tracing.tracer import AstraTracer
from observability.config import Config
from observability.exceptions import InitializationError

class TestAstraTracer(unittest.TestCase):
    def setUp(self):
        AstraTracer._instance = None
        AstraTracer._is_initialized = False
        self.tracer = AstraTracer()

    def tearDown(self):
        try:
            if self.tracer.is_initialized:
                self.tracer.shutdown()
        except:
            pass
        AstraTracer._instance = None

    def test_singleton_pattern(self):
        """Verify that AstraTracer behaves as a singleton."""
        tracer1 = AstraTracer()
        tracer2 = AstraTracer()
        self.assertIs(tracer1, tracer2)

    @patch("observability.tracing.tracer.create_astra_resource")
    @patch("observability.tracing.tracer.create_astra_exporter")
    @patch("observability.tracing.tracer.create_astra_processor")
    @patch("observability.tracing.tracer.TracerProvider")
    def test_initialize_success(self, mock_provider, mock_processor, mock_exporter, mock_resource):
        """Test successful initialization with mocking."""
        config = Config(SERVICE_NAME="test-service")
        
        # Setup mocks
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        
        self.tracer.initialize(config=config, enable_tracing=True)
        
        # Verify flow
        mock_resource.assert_called_once_with(config)
        mock_exporter.assert_called_once_with(config)
        mock_processor.assert_called_once()
        mock_provider_instance.add_span_processor.assert_called_once()
        
        self.assertTrue(self.tracer.is_initialized)
        self.assertIsNotNone(self.tracer.get_tracer())

    def test_initialize_disabled_tracing(self):
        """Test initialization when tracing is disabled."""
        self.tracer.initialize(enable_tracing=False)
        
        self.assertTrue(self.tracer.is_initialized)
        tracer = self.tracer.get_tracer()
        # Should rely on NoOp tracer
        self.assertTrue(isinstance(self.tracer._tracer_provider, trace.NoOpTracerProvider))

    def test_get_tracer_uninitialized(self):
        """Test that get_tracer raises error if not initialized."""
        with self.assertRaises(InitializationError):
            self.tracer.get_tracer()

if __name__ == "__main__":
    unittest.main()
