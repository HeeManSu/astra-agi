from __future__ import annotations

import json
import os
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan


def _maybe_parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(float(value))
            except ValueError:
                return default
    return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


class SpanJsonMapper:
    def to_span_dict(self, span: ReadableSpan) -> dict[str, Any]:
        span_dict: dict[str, Any] = json.loads(span.to_json())
        if span.attributes:
            attrs = dict(span.attributes)
            span_dict["attributes"] = attrs
            self._hoist_io(span_dict, attrs)
        return span_dict

    def _hoist_io(self, span_dict: dict[str, Any], attrs: dict[str, Any]) -> None:
        if "llm.response.text" in attrs:
            span_dict["output"] = attrs["llm.response.text"]
        elif "genai.response.text" in attrs:
            span_dict["output"] = attrs["genai.response.text"]
        elif "tool.output" in attrs:
            span_dict["output"] = _maybe_parse_json(attrs["tool.output"])

        if "tool.input" in attrs:
            span_dict["input"] = _maybe_parse_json(attrs["tool.input"])
        elif "llm.request.prompt" in attrs:
            span_dict["input"] = attrs["llm.request.prompt"]
        elif "genai.request.prompt" in attrs:
            span_dict["input"] = attrs["genai.request.prompt"]

        if "tool.error" in attrs:
            span_dict["error"] = _maybe_parse_json(attrs["tool.error"])


class TraceJsonWriter:
    def __init__(self, output_dir: str | None = None, mapper: SpanJsonMapper | None = None):
        self.output_dir = output_dir or os.getenv("ASTRA_JSON_TRACE_DIR", "./jsons")
        self.mapper = mapper or SpanJsonMapper()

    def export_spans(self, spans: list[ReadableSpan]) -> None:
        spans_by_trace: dict[str, list[dict[str, Any]]] = {}
        for span in spans:
            ctx = span.get_span_context()
            trace_id = f"{ctx.trace_id:032x}" if ctx is not None else "unknown"
            spans_by_trace.setdefault(trace_id, []).append(self.mapper.to_span_dict(span))

        for trace_id, new_spans in spans_by_trace.items():
            trace_entry = self._load_trace_entry(trace_id)
            merged_spans = self._merge_spans(trace_entry.get("spans", []), new_spans)
            trace_entry["spans"] = self._build_tree(merged_spans)
            trace_entry["usage"] = self._aggregate_usage(trace_entry["spans"])
            self._write_trace_entry(trace_id, trace_entry)

    def _load_trace_entry(self, trace_id: str) -> dict[str, Any]:
        trace_file = self._trace_file_path(trace_id)
        if os.path.exists(trace_file):
            try:
                with open(trace_file, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and loaded.get("trace_id") == trace_id:
                    loaded.setdefault("spans", [])
                    return loaded
            except Exception:
                pass
        return {"trace_id": trace_id, "spans": []}

    def _merge_spans(
        self,
        existing_spans_tree: list[dict[str, Any]],
        new_spans_flat: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        existing_flat = self._flatten_spans(existing_spans_tree)
        all_spans_map: dict[str, dict[str, Any]] = {}

        for s in existing_flat:
            sid = (s.get("context") or {}).get("span_id")
            if isinstance(sid, str):
                all_spans_map[sid] = s

        for s in new_spans_flat:
            sid = (s.get("context") or {}).get("span_id")
            if isinstance(sid, str):
                all_spans_map[sid] = s

        return list(all_spans_map.values())

    def _write_trace_entry(self, trace_id: str, trace_entry: dict[str, Any]) -> None:
        trace_dir = os.path.join(self.output_dir, trace_id)
        os.makedirs(trace_dir, exist_ok=True)
        trace_file = os.path.join(trace_dir, "trace.json")
        tmp_file = trace_file + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(trace_entry, f, indent=2)
        os.replace(tmp_file, trace_file)

    def _trace_file_path(self, trace_id: str) -> str:
        return os.path.join(self.output_dir, trace_id, "trace.json")

    def _flatten_spans(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flat: list[dict[str, Any]] = []
        for span in spans:
            children = span.get("children", [])
            span_copy = {k: v for k, v in span.items() if k != "children"}
            flat.append(span_copy)
            if isinstance(children, list):
                flat.extend(self._flatten_spans(children))
        return flat

    def _build_tree(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        span_map: dict[str, dict[str, Any]] = {}
        for s in spans:
            sid = (s.get("context") or {}).get("span_id")
            if isinstance(sid, str):
                node = dict(s)
                node["children"] = []
                span_map[sid] = node

        roots: list[dict[str, Any]] = []
        for node in span_map.values():
            parent_id = node.get("parent_id")
            if isinstance(parent_id, str) and parent_id in span_map:
                span_map[parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots

    def _aggregate_usage(self, spans: list[dict[str, Any]]) -> dict[str, Any]:
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": {"input": 0.0, "output": 0.0, "total": 0.0},
        }

        def walk(nodes: list[dict[str, Any]]) -> None:
            for node in nodes:
                attrs = node.get("attributes", {})
                if isinstance(attrs, dict):
                    usage["input_tokens"] += _coerce_int(attrs.get("llm.usage.prompt_tokens", 0))
                    usage["output_tokens"] += _coerce_int(attrs.get("llm.usage.completion_tokens", 0))
                    usage["total_tokens"] += _coerce_int(attrs.get("llm.usage.total_tokens", 0))
                    usage["cost"]["input"] += _coerce_float(attrs.get("llm.cost.input", 0.0))
                    usage["cost"]["output"] += _coerce_float(attrs.get("llm.cost.output", 0.0))
                    usage["cost"]["total"] += _coerce_float(attrs.get("llm.cost.total", 0.0))

                children = node.get("children", [])
                if isinstance(children, list) and children:
                    walk(children)

        walk(spans)
        return usage

