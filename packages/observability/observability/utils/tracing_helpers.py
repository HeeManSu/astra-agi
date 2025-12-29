from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from observability.core.config import Config
from observability.core.exceptions import ExporterError
from observability.exporters.otlp_exporter import create_otlp_exporter


def create_astra_resource(config: Config) -> Resource:
    """
    Creates an OpenTelemetry Resource with standard attributes from config.
    """
    return Resource.create(
        attributes={
            # Service attributes
            "service.name": config.SERVICE_NAME,
            "service.version": config.SERVICE_VERSION,
            "service.namespace": config.SERVICE_NAMESPACE,
            # Telemetry SDK attributes
            "telemetry.sdk.name": config.SDK_NAME,
            "telemetry.sdk.language": config.SDK_LANGUAGE,
            "telemetry.sdk.version": config.SDK_VERSION,
        }
    )


def create_astra_exporter(config: Config) -> SpanExporter:
    """
    Creates an OTLP exporter based on configuration.
    Raises ExporterError if creation fails.
    """
    try:
        return create_otlp_exporter(
            endpoint=config.OTLP_ENDPOINT,
            insecure=config.INSECURE
        )
    except Exception as e:
        raise ExporterError(
            f"Failed to create OTLP exporter for endpoint {config.OTLP_ENDPOINT}",
            cause=e
        )


def create_astra_processor(exporter: SpanExporter, config: Config) -> BatchSpanProcessor:
    """
    Creates a BatchSpanProcessor with production-ready settings from config.
    """
    return BatchSpanProcessor(
        exporter,
        max_queue_size=config.BATCH_MAX_QUEUE_SIZE,
        schedule_delay_millis=config.BATCH_SCHEDULE_DELAY_MILLIS,
        max_export_batch_size=config.BATCH_MAX_EXPORT_BATCH_SIZE,
        export_timeout_millis=config.BATCH_EXPORT_TIMEOUT_MILLIS,
    )
