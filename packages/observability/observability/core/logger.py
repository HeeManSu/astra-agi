from datetime import datetime, timezone
import json
import logging
import os
from typing import Any

from opentelemetry import trace


class JsonLogger:
    def __init__(self, service_name: str = "astra", log_file: str | None = None, level: str = "INFO"):
        self.service_name = service_name
        self.log_file = log_file or "./jsons/astra_observability.json"
        self.level = getattr(logging, level.upper(), logging.INFO)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    def _span_ids(self) -> tuple[str | None, str | None]:
        try:
            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and getattr(ctx, "is_valid", lambda: False)():
                trace_id = f"{ctx.trace_id:032x}"
                span_id = f"{ctx.span_id:016x}"
                return trace_id, span_id
        except Exception:
            pass
        return None, None

    def _write(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        ts = self._now()
        trace_id, span_id = self._span_ids()
        frame = logging.currentframe()
        module = "observability.logger"
        function = "info"
        line = 0
        try:
            if frame and frame.f_back and frame.f_back.f_back:
                caller = frame.f_back.f_back
                module = caller.f_globals.get("__name__", module)
                function = caller.f_code.co_name
                line = caller.f_lineno
        except Exception:
            pass
        payload = {
            "timestamp": ts,
            "level": level.lower(),
            "message": message,
            "service": self.service_name,
            "trace_id": trace_id,
            "span_id": span_id,
            "module": module,
            "function": function,
            "line": line,
        }
        if extra:
            payload["extra"] = extra
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def info(self, message: str, **kwargs: Any) -> None:
        self._write("INFO", message, extra=kwargs if kwargs else None)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._write("WARNING", message, extra=kwargs if kwargs else None)

    def error(self, message: str, **kwargs: Any) -> None:
        self._write("ERROR", message, extra=kwargs if kwargs else None)

