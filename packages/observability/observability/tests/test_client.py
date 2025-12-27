
import unittest
from unittest.mock import patch, MagicMock
from observability.client import Client
from observability.config import Config
from observability.tracing.tracer import AstraTracer

class TestClient(unittest.TestCase):
    def setUp(self):
        # Reset the singleton state
        AstraTracer._instance = None
        AstraTracer._is_initialized = False

    def tearDown(self):
        # Ensure clean shutdown
        if AstraTracer._instance:
            try:
                if AstraTracer._instance.is_initialized:
                    AstraTracer._instance.shutdown()
            except:
                pass
        AstraTracer._instance = None

    @patch("observability.tracing.tracer.AstraTracer.initialize")
    def test_client_init_defaults(self, mock_initialize):
        """Test Client initialization with default values."""
        client = Client()
        
        self.assertIsInstance(client.config, Config)
        mock_initialize.assert_called_once()
        
        # Verify default config values
        call_args = mock_initialize.call_args[1]
        config = call_args['config']
        self.assertEqual(config.SERVICE_NAME, "astra-service")
        self.assertEqual(config.OTLP_ENDPOINT, "http://localhost:4317")

    @patch("observability.tracing.tracer.AstraTracer.initialize")
    def test_client_init_custom_config(self, mock_initialize):
        """Test Client initialization with custom config."""
        custom_config = Config(
            SERVICE_NAME="my-test-service",
            OTLP_ENDPOINT="http://test-endpoint:4317",
            INSECURE=True
        )
        client = Client(config=custom_config)
        
        mock_initialize.assert_called_once()
        call_args = mock_initialize.call_args[1]
        passed_config = call_args['config']
        
        self.assertEqual(passed_config.SERVICE_NAME, "my-test-service")
        self.assertEqual(passed_config.OTLP_ENDPOINT, "http://test-endpoint:4317")
        self.assertTrue(passed_config.INSECURE)

    def test_tracer_access(self):
        """Test that client exposes the tracer instance."""
        # Mock the internal tracer logic to avoid real initialization side effects
        with patch("observability.tracing.tracer.AstraTracer.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_get_tracer.return_value = mock_tracer
            
            client = Client()
            self.assertEqual(client.tracer, mock_tracer)

if __name__ == "__main__":
    unittest.main()
