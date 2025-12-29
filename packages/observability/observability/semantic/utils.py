from __future__ import annotations
import json
from typing import Any, Dict, Tuple
from observability.core.span import truncate_text

_REDACT_KEYS = {"api_key", "apikey", "token", "auth", "authorization", "password", "secret", "key"}

def _redact_value(v: Any) -> Any:
    if isinstance(v, str):
        if len(v) > 8:
            return v[:4] + "..." + v[-2:]
        return "***"
    return "***"

def sanitize_args(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"args": [], "kwargs": {}}
    for a in args:
        out["args"].append(_to_jsonable(a))
    for k, v in kwargs.items():
        if k.lower() in _REDACT_KEYS:
            out["kwargs"][k] = _redact_value(v)
        else:
            out["kwargs"][k] = _to_jsonable(v)
    return out

def _to_jsonable(v: Any) -> Any:
    try:
        json.dumps(v)
        return v
    except Exception:
        if isinstance(v, (list, tuple)):
            return [_to_jsonable(i) for i in v]
        if isinstance(v, dict):
            return {str(k): _to_jsonable(val) for k, val in v.items()}
        return repr(v)

def to_json_str(data: Any, limit: int = 4096) -> str:
    try:
        s = json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        s = repr(data)
    return truncate_text(s, limit) or ""
