import unittest
from unittest.mock import patch
from observability.client import Client
from observability.config import Config
from observability.tracing.tracer import AstraTracer

class TestClient(unittest.TestCase):
    def setUp(self):
        AstraTracer._instance = None

    @patch("observability.tracing.tracer.AstraTracer.initialize")
    def test_client_initialization_defaults(self, mock_initialize):
        client = Client()
        self.assertIsInstance(client.config, Config)
        mock_initialize.assert_called_once()
        
        # Check default values from Config passed to initialize
        args = mock_initialize.call_args[1]
        config = args['config']
        self.assertEqual(config.SERVICE_NAME, "astra-service")
        self.assertEqual(config.OTLP_ENDPOINT, "http://localhost:4317")
        self.assertEqual(config.INSECURE, False)

    @patch("observability.tracing.tracer.AstraTracer.initialize")
    def test_client_initialization_custom_config(self, mock_initialize):
        config = Config(
            SERVICE_NAME="custom-service",
            OTLP_ENDPOINT="custom-endpoint",
            INSECURE=True
        )
        client = Client(config=config)
        
        mock_initialize.assert_called_once()
        args = mock_initialize.call_args[1]
        passed_config = args['config']
        
        self.assertEqual(passed_config.SERVICE_NAME, "custom-service")
        self.assertEqual(passed_config.OTLP_ENDPOINT, "custom-endpoint")
        self.assertEqual(passed_config.INSECURE, True)

    def test_tracer_property(self):
        client = Client()
        self.assertIsNotNone(client.tracer)

if __name__ == "__main__":
    unittest.main()
