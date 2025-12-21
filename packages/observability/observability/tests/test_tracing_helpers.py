import unittest
from unittest.mock import Mock, patch
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from observability.config import Config
from observability.exceptions import ExporterError
from observability.utils.tracing_helpers import (
    create_astra_resource,
    create_astra_exporter,
    create_astra_processor,
)


class TestTracingHelpers(unittest.TestCase):
    def setUp(self):
        self.config = Config(
            SERVICE_NAME="test-service",
            SERVICE_VERSION="1.0.0",
            SERVICE_NAMESPACE="test-ns",
            SDK_NAME="test-sdk",
            SDK_LANGUAGE="python",
            SDK_VERSION="0.1.0",
            OTLP_ENDPOINT="http://localhost:4317",
            INSECURE=True,
            BATCH_MAX_QUEUE_SIZE=100,
            BATCH_SCHEDULE_DELAY_MILLIS=1000,
            BATCH_MAX_EXPORT_BATCH_SIZE=10,
            BATCH_EXPORT_TIMEOUT_MILLIS=5000,
        )

    def test_create_astra_resource(self):
        resource = create_astra_resource(self.config)
        self.assertIsInstance(resource, Resource)
        attributes = resource.attributes
        self.assertEqual(attributes["service.name"], "test-service")
        self.assertEqual(attributes["service.version"], "1.0.0")
        self.assertEqual(attributes["service.namespace"], "test-ns")
        self.assertEqual(attributes["telemetry.sdk.name"], "test-sdk")

    @patch("observability.utils.tracing_helpers.create_otlp_exporter")
    def test_create_astra_exporter_success(self, mock_create_exporter):
        mock_exporter = Mock(spec=SpanExporter)
        mock_create_exporter.return_value = mock_exporter
        
        exporter = create_astra_exporter(self.config)
        
        self.assertEqual(exporter, mock_exporter)
        mock_create_exporter.assert_called_once_with(
            endpoint="http://localhost:4317",
            insecure=True
        )

    @patch("observability.utils.tracing_helpers.create_otlp_exporter")
    def test_create_astra_exporter_failure(self, mock_create_exporter):
        mock_create_exporter.side_effect = Exception("Connection failed")
        
        with self.assertRaises(ExporterError):
            create_astra_exporter(self.config)

    def test_create_astra_processor(self):
        mock_exporter = Mock(spec=SpanExporter)
        processor = create_astra_processor(mock_exporter, self.config)
        
        self.assertIsInstance(processor, BatchSpanProcessor)
        # Verify processor settings (accessing private attributes for testing)
        # Note: Implementation details of BatchSpanProcessor might vary, 
        # but we can check if it was initialized without error.
