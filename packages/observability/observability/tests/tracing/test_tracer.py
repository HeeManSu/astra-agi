import unittest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from observability.tracing.tracer import AstraTracer
from observability.config import Config

class TestAstraTracer(unittest.TestCase):
    def setUp(self):
        # Reset singleton for testing
        AstraTracer._instance = None
        AstraTracer._is_initialized = False
        self.tracer = AstraTracer()

    def tearDown(self):
        # Clean up after each test
        try:
            if self.tracer.is_initialized:
                self.tracer.shutdown()
        except:
            pass
        AstraTracer._instance = None

    @patch("observability.tracing.tracer.create_astra_resource")
    @patch("observability.tracing.tracer.create_astra_exporter")
    @patch("observability.tracing.tracer.create_astra_processor")
    @patch("observability.tracing.tracer.TracerProvider")
    def test_initialization(self, mock_provider, mock_processor, mock_exporter, mock_resource):
        # Create config
        config = Config(
            SERVICE_NAME="test-service",
            OTLP_ENDPOINT="http://localhost:4317"
        )

        # Setup mocks
        mock_resource.return_value = MagicMock()
        mock_exporter.return_value = MagicMock()
        mock_processor.return_value = MagicMock()
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance

        # Initialize
        self.tracer.initialize(config=config, enable_tracing=True)

        # Verify calls
        mock_resource.assert_called_once_with(config)
        mock_exporter.assert_called_once_with(config)
        mock_processor.assert_called_once()
        mock_provider_instance.add_span_processor.assert_called_once()

        # Verify tracer is initialized
        self.assertTrue(self.tracer.is_initialized)
        tracer = self.tracer.get_tracer()
        self.assertIsNotNone(tracer)

    def test_singleton_behavior(self):
        tracer1 = AstraTracer()
        tracer2 = AstraTracer()
        self.assertIs(tracer1, tracer2)

if __name__ == "__main__":
    unittest.main()
