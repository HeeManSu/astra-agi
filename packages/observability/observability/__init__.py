from typing import Optional

from observability.client import Client
from observability.core.config import Config
from observability.instrumentation import init as instrumentation_init
from observability.core.logger import JsonLogger


def init(
    service_name: str | None = None,
    service_version: str | None = None,
    service_namespace: str | None = None,
    endpoint: str | None = None,
    insecure: bool | None = None,
    enable_tracing: bool = True,
    config: Config | None = None,
    auto_instrument: bool = True,
    enable_json_logs: bool = True,
    log_file: str | None = None,
    log_level: str | None = None,
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
    if enable_json_logs:
        client.logger = JsonLogger(
            service_name=service_name or client.config.SERVICE_NAME,
            log_file=log_file or "./jsons/astra_observability.json",
            level=(log_level or "INFO"),
        )
        client.logger.info("Observability initialized", components=["tracer", "metrics", "logger"])
    return client

class Observability:
    @staticmethod
    def init(
        service_name: str | None = None,
        service_version: str | None = None,
        service_namespace: str | None = None,
        endpoint: str | None = None,
        insecure: bool | None = None,
        enable_tracing: bool = True,
        config: Config | None = None,
        auto_instrument: bool = True,
        enable_json_logs: bool = True,
        log_file: str | None = None,
        log_level: str | None = None,
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
            enable_json_logs=enable_json_logs,
            log_file=log_file,
            log_level=log_level,
        )
