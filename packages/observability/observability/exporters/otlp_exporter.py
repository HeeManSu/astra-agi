from collections.abc import Sequence
import json
import os
import shutil
import time
from typing import Any

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExportResult


try:
    import fcntl as _fcntl
    def _lock_file(f):
        _fcntl.flock(f, _fcntl.LOCK_EX)
    def _unlock_file(f):
        _fcntl.flock(f, _fcntl.LOCK_UN)
except Exception:
    import msvcrt
    def _lock_file(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    def _unlock_file(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

class AgentRunConsoleExporter(ConsoleSpanExporter):
    """
    Custom Console Exporter that prints the AgentRun JSON (pretty-printed) if present.
    If AgentRun data is found, the standard OpenTelemetry span output is suppressed.
    Otherwise, it behaves like the standard ConsoleSpanExporter.
    """
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            if span.attributes and "astra.agent_run" in span.attributes:
                try:
                    agent_run_str = span.attributes["astra.agent_run"]
                    if isinstance(agent_run_str, str):
                        # Parse and re-dump for pretty printing
                        agent_run_data = json.loads(agent_run_str)
                        print(json.dumps(agent_run_data, indent=4))
                        # Skip standard span output for agent runs
                        continue
                except Exception:
                    pass

            # Print the standard span output for non-agent runs
            super().export([span])

        return SpanExportResult.SUCCESS

class JsonFileSpanExporter(ConsoleSpanExporter):
    """
    Exporter that saves spans as a structured JSON array in a single file.
    Supports file rotation, atomic writes, and hierarchical nesting of spans.
    """
    OUTPUT_DIR = "/Users/apple/OpenSource/astra-v2/astra-agi/jsons"
    FILE_NAME = "traces.json"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)

        file_path = os.path.join(self.OUTPUT_DIR, self.FILE_NAME)

        # 1. Rotate file if too large
        self._rotate_file_if_needed(file_path)

        # 2. Prepare new spans grouped by trace_id
        new_spans_by_trace: dict[str, list[dict[str, Any]]] = {}
        for span in spans:
            trace_id = f"{span.get_span_context().trace_id:032x}"
            if trace_id not in new_spans_by_trace:
                new_spans_by_trace[trace_id] = []

            # Convert ReadableSpan to dict
            span_dict = json.loads(span.to_json())
            # Ensure attributes are present and useful
            if span.attributes:
                attrs = dict(span.attributes)
                span_dict["attributes"] = attrs

                # Enrich structure by hoisting key attributes
                if "llm.response.text" in attrs:
                    span_dict["output"] = attrs["llm.response.text"]
                elif "genai.response.text" in attrs:
                    span_dict["output"] = attrs["genai.response.text"]
                elif "tool.output" in attrs:
                    # Try to parse tool output if it's a JSON string
                    val = attrs["tool.output"]
                    if isinstance(val, str):
                        try:
                            span_dict["output"] = json.loads(val)
                        except (TypeError, json.JSONDecodeError):
                            span_dict["output"] = val
                    else:
                        span_dict["output"] = val

                if "tool.input" in attrs:
                    val = attrs["tool.input"]
                    if isinstance(val, str):
                        try:
                            span_dict["input"] = json.loads(val)
                        except (TypeError, json.JSONDecodeError):
                            span_dict["input"] = val
                    else:
                        span_dict["input"] = val
                elif "llm.request.prompt" in attrs:
                    span_dict["input"] = attrs["llm.request.prompt"]
                elif "genai.request.prompt" in attrs:
                    span_dict["input"] = attrs["genai.request.prompt"]

                if "tool.error" in attrs:
                    val = attrs["tool.error"]
                    if isinstance(val, str):
                        try:
                            span_dict["error"] = json.loads(val)
                        except (TypeError, json.JSONDecodeError):
                            span_dict["error"] = val
                    else:
                        span_dict["error"] = val

            new_spans_by_trace[trace_id].append(span_dict)

        # 3. Process spans and update individual trace files
        try:
            # We don't maintain a monolithic file anymore, just process per-trace
            # Update traces
            for trace_id, new_spans in new_spans_by_trace.items():
                # For individual files, we need to load existing trace if it exists to merge
                trace_dir = os.path.join(self.OUTPUT_DIR, trace_id)
                trace_file = os.path.join(trace_dir, "trace.json")
                
                trace_entry = None
                if os.path.exists(trace_file):
                    try:
                        with open(trace_file, "r") as f:
                            trace_entry = json.load(f)
                    except Exception:
                        pass
                
                if not trace_entry:
                    trace_entry = {
                        "trace_id": trace_id,
                        "spans": []
                    }

                # Flatten existing tree to list for merging
                existing_flat_spans = self._flatten_spans(trace_entry.get("spans", []))

                # Merge and deduplicate (by span_id)
                all_spans_map = {s["context"]["span_id"]: s for s in existing_flat_spans}
                for ns in new_spans:
                    sid = ns.get("context", {}).get("span_id")
                    if sid:
                        all_spans_map[sid] = ns

                all_spans = list(all_spans_map.values())

                # Re-build tree
                trace_entry["spans"] = self._build_tree(all_spans)
                
                # Write individual trace file
                self._write_individual_trace(trace_id, trace_entry)

        except Exception as e:
            # Fallback: print error to console so we don't lose visibility
            print(f"Error exporting spans to JSON: {e}")

        return SpanExportResult.SUCCESS
    
    def _write_individual_trace(self, trace_id: str, trace_entry: dict[str, Any]) -> None:
        """Write individual trace to its own folder as trace.json with aggregated metrics."""
        try:
            # Calculate aggregated metrics
            usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": {
                    "input": 0.0,
                    "output": 0.0,
                    "total": 0.0
                }
            }
            
            def aggregate_metrics(spans: list[dict[str, Any]]):
                for span in spans:
                    attrs = span.get("attributes", {})
                    usage["input_tokens"] += attrs.get("llm.usage.prompt_tokens", 0)
                    usage["output_tokens"] += attrs.get("llm.usage.completion_tokens", 0)
                    usage["total_tokens"] += attrs.get("llm.usage.total_tokens", 0)
                    usage["cost"]["input"] += attrs.get("llm.cost.input", 0.0)
                    usage["cost"]["output"] += attrs.get("llm.cost.output", 0.0)
                    usage["cost"]["total"] += attrs.get("llm.cost.total", 0.0)
                    
                    if "children" in span:
                        aggregate_metrics(span["children"])

            aggregate_metrics(trace_entry.get("spans", []))
            
            # Reconstruct dictionary to put metrics at the top for readability
            new_trace_entry = {"trace_id": trace_entry["trace_id"]}
            new_trace_entry["usage"] = usage
            new_trace_entry["spans"] = trace_entry["spans"]
            
            trace_dir = os.path.join(self.OUTPUT_DIR, trace_id)
            if not os.path.exists(trace_dir):
                os.makedirs(trace_dir)
            
            trace_file = os.path.join(trace_dir, "trace.json")
            with open(trace_file, "w") as f:
                json.dump(new_trace_entry, f, indent=2)
        except Exception as e:
            print(f"Error writing individual trace file for {trace_id}: {e}")

    def _rotate_file_if_needed(self, file_path: str):
        if os.path.exists(file_path) and os.path.getsize(file_path) > self.MAX_FILE_SIZE:
            timestamp = int(time.time())
            archive_path = os.path.join(self.OUTPUT_DIR, f"traces.{timestamp}.json")
            try:
                shutil.move(file_path, archive_path)
            except Exception:
                pass

    def _load_data(self, file_path: str) -> list[dict[str, Any]]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    if content:
                        data = json.loads(content)
                        if isinstance(data, list):
                            return data
            except Exception:
                pass
        return []

    def _flatten_spans(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flat = []
        for span in spans:
            # Copy span without children to avoid deep nesting in flat list
            # But we need to keep the children's data, so we recursively flatten
            children = span.pop("children", [])
            flat.append(span)
            flat.extend(self._flatten_spans(children))
        return flat

    def _build_tree(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Map span_id -> span
        span_map = {}
        for s in spans:
            sid = s.get("context", {}).get("span_id")
            if sid:
                s["children"] = [] # Initialize children
                span_map[sid] = s

        roots = []
        for s in spans:
            sid = s.get("context", {}).get("span_id")
            parent_id = s.get("parent_id")
            # Note: OTel JSON might have parent_id at top level or in context?
            # Checking OTel Python implementation: to_json() uses json.dumps(self.to_dict())
            # self.to_dict() puts parent_id at top level if it exists.

            if parent_id and parent_id in span_map:
                span_map[parent_id]["children"].append(s)
            else:
                roots.append(s)

        return roots

def create_otlp_exporter(endpoint: str, insecure: bool):
    """
    Creates and configures an OTLP Span Exporter.

    Args:
        endpoint (str): The OTLP endpoint URL (e.g., "localhost:4317").
        insecure (bool): Whether to use an insecure connection (HTTP/gRPC without TLS).

    Returns:
        OTLPSpanExporter: The configured exporter instance.
    """
    if not endpoint:
        raise ValueError("Endpoint must be provided")

    if endpoint.lower() == "console":
        return AgentRunConsoleExporter()

    if endpoint.lower() == "json":
        return JsonFileSpanExporter()

    return OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
