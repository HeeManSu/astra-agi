from typing import Optional
from observability.config import Config
from observability.client import Client
from observability.instrumentation import init as instrumentation_init

def init(
    service_name: Optional[str] = None,
    service_version: Optional[str] = None,
    service_namespace: Optional[str] = None,
    endpoint: Optional[str] = None,
    insecure: Optional[bool] = None,
    enable_tracing: bool = True,
    config: Optional[Config] = None,
    auto_instrument: bool = True,
):
    client = Client(
        service_name=service_name,
        service_version=service_version,
        service_namespace=service_namespace,
        endpoint=endpoint,
        insecure=insecure,
        enable_tracing=enable_tracing,
        config=config,
    )
    if auto_instrument:
        try:
            instrumentation_init(auto_instrument=True)
        except Exception:
            pass
    return client

class Observability:
    @staticmethod
    def init(
        service_name: Optional[str] = None,
        service_version: Optional[str] = None,
        service_namespace: Optional[str] = None,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        enable_tracing: bool = True,
        config: Optional[Config] = None,
        auto_instrument: bool = True,
    ):
        return init(
            service_name=service_name,
            service_version=service_version,
            service_namespace=service_namespace,
            endpoint=endpoint,
            insecure=insecure,
            enable_tracing=enable_tracing,
            config=config,
            auto_instrument=auto_instrument,
        )

