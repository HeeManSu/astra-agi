import os
from dataclasses import dataclass

@dataclass
class Config:
    """
    Central configuration for Observability SDK.
    """
    # SDK Version Information
    SDK_VERSION: str = "0.1.0"  # Update this with each release
    SDK_NAME: str = "Observability"
    SDK_LANGUAGE: str = "python"
    
    # Service Configuration
    OTLP_ENDPOINT: str = os.getenv("ASTRA_OTLP_ENDPOINT", "http://localhost:4317")
    SERVICE_NAME: str = os.getenv("ASTRA_SERVICE_NAME", "astra-service")
    SERVICE_VERSION: str = os.getenv("ASTRA_SERVICE_VERSION", "1.0.0")
    SERVICE_NAMESPACE: str = os.getenv("ASTRA_SERVICE_NAMESPACE", "Observability")
    INSECURE: bool = os.getenv("ASTRA_INSECURE", "False").lower() == "true"
    
    # Exporter Configuration
    ENABLE_OTLP_EXPORT: bool = os.getenv("ASTRA_ENABLE_OTLP_EXPORT", "True").lower() == "true"

    # BatchSpanProcessor Configuration (production-ready defaults)
    # Maximum queue size - spans will be dropped if queue is full
    BATCH_MAX_QUEUE_SIZE: int = int(os.getenv("ASTRA_BATCH_MAX_QUEUE_SIZE", "2048"))
    
    # Maximum batch size - number of spans to export in one batch
    BATCH_MAX_EXPORT_BATCH_SIZE: int = int(os.getenv("ASTRA_BATCH_MAX_EXPORT_BATCH_SIZE", "512"))
    
    # Schedule delay in milliseconds - how often to export batches
    BATCH_SCHEDULE_DELAY_MILLIS: int = int(os.getenv("ASTRA_BATCH_SCHEDULE_DELAY_MILLIS", "5000"))
    
    # Export timeout in milliseconds - timeout for export operations
    BATCH_EXPORT_TIMEOUT_MILLIS: int = int(os.getenv("ASTRA_BATCH_EXPORT_TIMEOUT_MILLIS", "30000"))