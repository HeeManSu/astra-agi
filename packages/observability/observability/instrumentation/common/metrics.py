from __future__ import annotations

from opentelemetry import metrics

def get_meter(name: str = "observability.instrumentation"):
    try:
        return metrics.get_meter(name)
    except Exception:
        return None
