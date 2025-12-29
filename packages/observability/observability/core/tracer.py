import atexit
import logging
import threading
from typing import Optional
import warnings

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from observability.core.config import Config
from observability.core.exceptions import (
    ExporterError,
    InitializationError,
    ShutdownError,
    TracingDisabledWarning,
)
from observability.utils.tracing_helpers import (
    create_astra_exporter,
    create_astra_processor,
    create_astra_resource,
)


logger = logging.getLogger(__name__)


class AstraTracer:
    """
    Thread-safe singleton class to manage the OpenTelemetry TracerProvider and Tracer.
    
    Features:
    - Complete resource attributes with SDK metadata
    - Configurable BatchSpanProcessor for production use
    - No-op mode support for disabling tracing
    - Graceful shutdown with atexit handler
    - Force flush support
    - Comprehensive error handling
    
    Usage:
        # Initialize with tracing enabled
        tracer = AstraTracer()
        tracer.initialize(
            service_name="my-service",
            endpoint="localhost:4317",
            enable_tracing=True
        )
        
        # Get tracer and create spans
        t = tracer.get_tracer()
        with t.start_as_current_span("operation"):
            # Your code here
            pass
        
        # Shutdown gracefully
        tracer.shutdown()
    """

    _instance: Optional["AstraTracer"] = None
    _lock = threading.Lock()
    _tracer_provider: trace.TracerProvider | None = None
    _tracer: trace.Tracer | None = None
    _span_processor: BatchSpanProcessor | None = None
    _is_initialized: bool = False
    _tracing_enabled: bool = True

    def __new__(cls):
        """Thread-safe singleton implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AstraTracer, cls).__new__(cls)
        return cls._instance

    def initialize(
        self,
        config: Config | None = None,
        enable_tracing: bool = True,
    ) -> None:
        """
        Initializes the TracerProvider with complete resource attributes and production-ready settings.

        Args:
            config: Configuration object (required if tracing is enabled)
            enable_tracing: If False, creates a no-op tracer that doesn't send data

        Raises:
            InitializationError: If initialization fails
        """
        with self._lock:
            if self._is_initialized:
                logger.warning("AstraTracer is already initialized.")
                return

            try:
                # Store tracing state
                self._tracing_enabled = enable_tracing

                if not enable_tracing:
                    logger.info("Tracing is disabled. Using no-op tracer.")
                    # Set a no-op tracer provider
                    self._tracer_provider = trace.NoOpTracerProvider()
                    trace.set_tracer_provider(self._tracer_provider)
                    self._tracer = self._tracer_provider.get_tracer(__name__)
                    self._is_initialized = True
                    return

                # Ensure config is provided
                if config is None:
                     raise InitializationError("Config object is required for initialization when tracing is enabled")

                cfg = config

                # Create resource
                resource = create_astra_resource(cfg)

                # Create tracer provider
                self._tracer_provider = TracerProvider(resource=resource)

                if cfg.ENABLE_OTLP_EXPORT:
                    # Create exporter
                    exporter = create_astra_exporter(cfg)

                    # Configure BatchSpanProcessor
                    self._span_processor = create_astra_processor(exporter, cfg)
                    self._tracer_provider.add_span_processor(self._span_processor)

                # Set as global tracer provider
                trace.set_tracer_provider(self._tracer_provider)

                # Create the tracer
                self._tracer = trace.get_tracer(
                    instrumenting_module_name=cfg.SDK_NAME,
                    instrumenting_library_version=cfg.SDK_VERSION,
                )

                # Register shutdown handler
                atexit.register(self._atexit_handler)

                self._is_initialized = True
                logger.info(
                    f"AstraTracer initialized for service: {cfg.SERVICE_NAME} "
                    f"(version: {cfg.SERVICE_VERSION}, namespace: {cfg.SERVICE_NAMESPACE})"
                )

            except Exception as e:
                if isinstance(e, (ExporterError, InitializationError)):
                    raise
                raise InitializationError(
                    "Failed to initialize AstraTracer", cause=e
                )

    def get_tracer(self) -> trace.Tracer:
        """
        Returns the initialized tracer instance.

        Returns:
            trace.Tracer: The OpenTelemetry tracer instance

        Raises:
            InitializationError: If tracer has not been initialized
        """
        if not self._is_initialized or self._tracer is None:
            raise InitializationError(
                "Tracer has not been initialized. Call initialize() first."
            )

        if not self._tracing_enabled:
            warnings.warn(
                "Tracing is disabled. Operations will be no-ops.",
                TracingDisabledWarning,
                stacklevel=2,
            )

        return self._tracer

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Forces the span processor to flush all pending spans.

        Args:
            timeout_millis: Maximum time to wait for flush in milliseconds

        Returns:
            bool: True if flush was successful, False otherwise

        Raises:
            ShutdownError: If flush operation fails critically
        """
        if not self._is_initialized:
            logger.warning("Cannot flush: tracer not initialized")
            return False

        if not self._tracing_enabled:
            logger.debug("Tracing disabled, skipping flush")
            return True

        try:
            if self._span_processor:
                result = self._span_processor.force_flush(timeout_millis)
                if result:
                    logger.info("Successfully flushed pending spans")
                else:
                    logger.warning("Flush operation timed out or failed")
                return result
            return True
        except Exception as e:
            raise ShutdownError("Failed to flush spans", cause=e)

    def shutdown(self, timeout_millis: int = 30000) -> bool:
        """
        Gracefully shuts down the tracer provider and flushes remaining spans.

        Args:
            timeout_millis: Maximum time to wait for shutdown in milliseconds

        Returns:
            bool: True if shutdown was successful, False otherwise

        Raises:
            ShutdownError: If shutdown operation fails critically
        """
        with self._lock:
            if not self._is_initialized:
                logger.warning("Cannot shutdown: tracer not initialized")
                return False

            if not self._tracing_enabled:
                logger.debug("Tracing disabled, skipping shutdown")
                self._is_initialized = False
                return True

            try:
                if self._tracer_provider and isinstance(self._tracer_provider, TracerProvider):
                    self._tracer_provider.shutdown()
                    logger.info("AstraTracer shutdown successfully")

                    self._is_initialized = False
                    self._tracer = None
                    self._span_processor = None
                    self._tracer_provider = None
                    return True

                return True
            except Exception as e:
                raise ShutdownError("Failed to shutdown tracer", cause=e)

    def _atexit_handler(self) -> None:
        """
        Automatic shutdown handler registered with atexit.
        Ensures graceful shutdown when the process exits.
        """
        try:
            if self._is_initialized:
                logger.info("Running atexit shutdown handler")
                self.shutdown()
        except Exception as e:
            logger.error(f"Error during atexit shutdown: {e}")

    @property
    def is_initialized(self) -> bool:
        """Check if the tracer is initialized."""
        return self._is_initialized

    @property
    def is_tracing_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._tracing_enabled
