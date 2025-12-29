from typing import Optional
from opentelemetry import trace
from observability.config import Config
from observability.core.tracer import AstraTracer
from observability.instrumentation import init as instrumentation_init

class Client:
    """
    Main entry point for Observability SDK.
    Manages configuration and initialization of tracing and other components.
    
    Usage:
        client = Client(
            service_name="my-service",
            endpoint="http://localhost:4317"
        )
        tracer = client.tracer
    """
    def __init__(
        self, 
        service_name: Optional[str] = None,
        service_version: Optional[str] = None,
        service_namespace: Optional[str] = None,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        enable_tracing: bool = True,
        enable_otlp_export: Optional[bool] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize the Observability Client.

        Args:
            service_name: Name of the service (overrides env var)
            service_version: Version of the service (overrides env var)
            service_namespace: Namespace of the service (overrides env var)
            endpoint: OTLP endpoint URL (overrides env var)
            insecure: Whether to use insecure connection (overrides env var)
            enable_tracing: Whether to enable tracing (default: True)
            enable_otlp_export: Whether to enable OTLP export (overrides env var)
            config: Optional Config object to use
        """
        # Initialize config with defaults or provided object
        self.config = config or Config()
        
        # Override config with direct arguments if provided
        if service_name:
            self.config.SERVICE_NAME = service_name
        if service_version:
            self.config.SERVICE_VERSION = service_version
        if service_namespace:
            self.config.SERVICE_NAMESPACE = service_namespace
        if endpoint:
            self.config.OTLP_ENDPOINT = endpoint
        if insecure is not None:
            self.config.INSECURE = insecure
        if enable_otlp_export is not None:
            self.config.ENABLE_OTLP_EXPORT = enable_otlp_export
            
        self.tracer_manager = AstraTracer()
        
        # Initialize tracing with config object
        self.tracer_manager.initialize(
            config=self.config,
            enable_tracing=enable_tracing
        )
        try:
            instrumentation_init(auto_instrument=True)
        except Exception:
            pass

    @property
    def tracer(self) -> trace.Tracer:
        """Access the OpenTelemetry tracer instance."""
        return self.tracer_manager.get_tracer()
