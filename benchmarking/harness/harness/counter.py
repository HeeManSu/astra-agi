"""TokenCounter — full-payload SDK-boundary observer for the token audit.

Same patching strategy as
benchmarking/harness/harness/counter.py:172-178: wraps
google.genai.models.{Models,AsyncModels}.{generate_content,generate_content_stream}.

The framework code does not see the wrapper. The kwargs forwarded to
the original SDK methods are unchanged. The model receives the same
request research.md's benchmark sent.

What the wrapper additionally does, on each call:

  1. Dumps the full request kwargs (`model`, `contents`, `config`) to
     dumps/call_NNN_request.json.
  2. Dumps the full response (candidates, usage_metadata, model_version)
     to dumps/call_NNN_response.json.
  3. Records a CallRecord with SDK-reported tokens read from
     `response.usage_metadata` (matches existing counter behavior).

For streaming responses, accumulates chunks and dumps the *concatenated*
final chunk — usage_metadata arrives on the final chunk.
"""

from __future__ import annotations

import json
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CallRecord:
    """One LLM call: SDK-reported usage + dump file pointers."""

    call_index: int
    method: str  # "generate_content" | "generate_content_stream"
    is_async: bool
    is_stream: bool
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    thoughts_tokens: int
    total_tokens: int
    latency_ms: float
    request_dump: str  # path to call_NNN_request.json (relative)
    response_dump: str  # path to call_NNN_response.json (relative)
    tool_calls: list[dict] = field(default_factory=list)
    text_preview: str | None = None


@dataclass
class CounterSummary:
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def num_calls(self) -> int:
        return len(self.calls)

    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    @property
    def thoughts_tokens(self) -> int:
        return sum(c.thoughts_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.calls)

    @property
    def llm_latency_ms(self) -> float:
        return sum(c.latency_ms for c in self.calls)

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_calls": self.num_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "thoughts_tokens": self.thoughts_tokens,
            "total_tokens": self.total_tokens,
            "llm_latency_ms": round(self.llm_latency_ms, 2),
            "calls": [c.__dict__ for c in self.calls],
        }


def _short_json(obj: Any, limit: int = 240) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "...(truncated)"


def _render_text_or_json(obj: Any) -> str:
    """Pretty-render system_instruction or contents for the human-readable log.

    Pulls .text out of nested {role, parts:[{text}, {function_call}, ...]} shapes
    so the prompt reads as plain prose. Falls back to JSON for everything else.
    """
    if obj is None:
        return "(none)"
    if isinstance(obj, str):
        return obj
    chunks: list[str] = []
    items = obj if isinstance(obj, list) else [obj]
    for item in items:
        if isinstance(item, str):
            chunks.append(item)
            continue
        if not isinstance(item, dict):
            chunks.append(_short_json(item))
            continue
        role = item.get("role")
        parts = item.get("parts", [])
        if role:
            chunks.append(f"\n[role={role}]")
        if not parts:
            txt = item.get("text")
            if txt:
                chunks.append(txt)
            else:
                chunks.append(_short_json(item))
            continue
        for p in parts:
            if not isinstance(p, dict):
                chunks.append(str(p))
                continue
            if p.get("text"):
                chunks.append(p["text"])
            if p.get("function_call"):
                fc = p["function_call"]
                chunks.append(
                    f"  -> TOOL CALL: {fc.get('name')}({_short_json(fc.get('args', {}))})"
                )
            if p.get("function_response"):
                fr = p["function_response"]
                resp = fr.get("response", fr.get("result", fr))
                chunks.append(
                    f"  <- TOOL RESULT [{fr.get('name')}]: {_short_json(resp, limit=400)}"
                )
    return "\n".join(chunks)


def _to_jsonable(obj: Any) -> Any:
    """Recursively turn anything into a JSON-serializable structure.

    Pydantic objects → model_dump(mode="json"). Lists/tuples → recurse.
    Dicts → recurse on values. Bytes → length marker. Else → str().
    """
    # Pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json", exclude_none=True)
        except Exception:
            try:
                return obj.model_dump(exclude_none=True)
            except Exception:
                pass
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, bytes):
        return {"__bytes_len__": len(obj)}
    if hasattr(obj, "__dict__"):
        try:
            return {
                str(k): _to_jsonable(v) for k, v in obj.__dict__.items() if not k.startswith("_")
            }
        except Exception:
            pass
    return str(obj)


def _extract_usage(response: Any) -> tuple[int, int, int, int, str]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        model_id = getattr(response, "model_version", "") or ""
        return 0, 0, 0, 0, model_id
    prompt = getattr(usage, "prompt_token_count", 0) or 0
    completion = getattr(usage, "candidates_token_count", 0) or 0
    thoughts = getattr(usage, "thoughts_token_count", 0) or 0
    total = getattr(usage, "total_token_count", 0) or 0
    model_id = getattr(response, "model_version", "") or ""
    return prompt, completion, thoughts, total, model_id


def _extract_tool_calls_and_text(response: Any) -> tuple[list[dict], str | None]:
    tool_calls: list[dict] = []
    text_chunks: list[str] = []
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return [], None
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is not None and getattr(fc, "name", None):
                args = {}
                try:
                    raw_args = getattr(fc, "args", None)
                    if raw_args is not None:
                        args = dict(raw_args)
                except Exception:
                    args = {"_unparseable": str(getattr(fc, "args", ""))[:200]}
                tool_calls.append({"name": fc.name, "args": args})
            txt = getattr(part, "text", None)
            if txt:
                text_chunks.append(txt)
    except Exception:
        pass
    text_preview: str | None = None
    if text_chunks:
        joined = "".join(text_chunks)
        text_preview = joined[:200]
    return tool_calls, text_preview


class TokenCounter:
    """Patches google.genai SDK methods, dumps every request/response.

    Usage:
        with TokenCounter(out_dir="dumps/", log_fp=fp) as counter:
            run_my_framework_code()
        summary = counter.summary

    If `log_fp` is provided, every call also gets a structured
    "=== CALL N ===" block written to it with system prompt, user messages,
    tools, model response, and usage. Lets a single log file be the audit
    artifact for frameworks that don't print payloads natively (CrewAI
    via native google.genai).
    """

    def __init__(self, out_dir: str | Path, log_fp=None) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._log_fp = log_fp
        self._records: list[CallRecord] = []
        self._stack = ExitStack()
        self._call_counter = 0

    @property
    def summary(self) -> CounterSummary:
        return CounterSummary(calls=list(self._records))

    def __enter__(self) -> TokenCounter:
        from google.genai.models import AsyncModels, Models

        self._patch(Models, "generate_content", is_async=False, is_stream=False)
        self._patch(Models, "generate_content_stream", is_async=False, is_stream=True)
        self._patch(AsyncModels, "generate_content", is_async=True, is_stream=False)
        self._patch(AsyncModels, "generate_content_stream", is_async=True, is_stream=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stack.close()

    def _next_call_index(self) -> int:
        self._call_counter += 1
        return self._call_counter

    def _dump_request(
        self, idx: int, method_name: str, is_async: bool, is_stream: bool, kwargs: dict
    ) -> str:
        """Write request kwargs to call_NNN_request.json. Returns relative path."""
        path = self.out_dir / f"call_{idx:03d}_request.json"
        payload = {
            "call_index": idx,
            "method": method_name,
            "is_async": is_async,
            "is_stream": is_stream,
            "kwargs": _to_jsonable(kwargs),
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        return path.name

    def _dump_response(
        self, idx: int, response: Any, latency_ms: float, request_kwargs: dict | None = None
    ) -> str:
        """Write response to call_NNN_response.json. Returns relative path."""
        path = self.out_dir / f"call_{idx:03d}_response.json"
        payload = {
            "call_index": idx,
            "latency_ms": round(latency_ms, 2),
            "response": _to_jsonable(response),
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        # Also write a human-readable block to the inline log file, if configured.
        if self._log_fp is not None:
            try:
                self._write_log_block(idx, request_kwargs or {}, payload["response"], latency_ms)
            except Exception:
                pass
        return path.name

    def _write_log_block(
        self, idx: int, request_kwargs: dict, response_jsonable: Any, latency_ms: float
    ) -> None:
        """Append a human-readable per-call block to the log file.

        Format mirrors what Agno's debug_mode=True prints natively, so an
        Agno log and a CrewAI log read the same way for manual counting.
        """
        fp = self._log_fp
        bar = "=" * 78
        fp.write(f"\n\n{bar}\n=== LLM CALL {idx} ===\n{bar}\n")

        kw = _to_jsonable(request_kwargs)
        model = kw.get("model", "")
        config = kw.get("config", {}) or {}
        sys_inst = config.get("system_instruction", None)
        tools = config.get("tools", None)
        contents = kw.get("contents", None)

        fp.write(f"\nMODEL: {model}\n")
        if isinstance(config, dict):
            fp.write(
                f"GENERATION CONFIG: temperature={config.get('temperature')}, "
                f"thinking_config={config.get('thinking_config')}\n"
            )

        # System instruction
        fp.write("\n----- SYSTEM INSTRUCTION -----\n")
        fp.write(_render_text_or_json(sys_inst))

        # Tools
        fp.write("\n\n----- TOOLS DECLARED -----\n")
        if tools:
            tool_names = []
            for t in tools if isinstance(tools, list) else [tools]:
                fns = (t or {}).get("function_declarations", []) if isinstance(t, dict) else []
                for fn in fns:
                    tool_names.append(fn.get("name", "?"))
            fp.write("\n".join(f"  - {n}" for n in tool_names) or "(none)")
        else:
            fp.write("(none)")

        # Contents (full conversation forwarded)
        fp.write("\n\n----- CONTENTS (conversation forwarded to model) -----\n")
        fp.write(_render_text_or_json(contents))

        # Response
        fp.write("\n\n----- RESPONSE -----\n")
        usage = (
            (response_jsonable or {}).get("usage_metadata", {})
            if isinstance(response_jsonable, dict)
            else {}
        )
        candidates = (
            (response_jsonable or {}).get("candidates", [])
            if isinstance(response_jsonable, dict)
            else []
        )
        if candidates:
            content = candidates[0].get("content", {}) if isinstance(candidates[0], dict) else {}
            for part in content.get("parts", []) or []:
                if not isinstance(part, dict):
                    continue
                if part.get("function_call"):
                    fc = part["function_call"]
                    fp.write(f"  TOOL CALL: {fc.get('name')}({_short_json(fc.get('args', {}))})\n")
                if part.get("text"):
                    fp.write(f"  TEXT: {part['text']}\n")

        fp.write("\n----- USAGE (SDK-reported) -----\n")
        fp.write(f"  prompt_token_count     : {usage.get('prompt_token_count')}\n")
        fp.write(f"  candidates_token_count : {usage.get('candidates_token_count')}\n")
        fp.write(f"  thoughts_token_count   : {usage.get('thoughts_token_count')}\n")
        fp.write(f"  total_token_count      : {usage.get('total_token_count')}\n")
        fp.write(f"  latency_ms             : {round(latency_ms, 2)}\n")
        fp.flush()

    def _patch(self, cls: type, method_name: str, *, is_async: bool, is_stream: bool) -> None:
        original = getattr(cls, method_name)
        wrapper = self._make_wrapper(
            original, method_name=method_name, is_async=is_async, is_stream=is_stream
        )
        setattr(cls, method_name, wrapper)
        self._stack.callback(setattr, cls, method_name, original)

    def _make_wrapper(self, original, *, method_name: str, is_async: bool, is_stream: bool):
        records = self._records
        next_idx = self._next_call_index
        dump_request = self._dump_request
        dump_response = self._dump_response

        if not is_async and not is_stream:

            def wrapped(self, *args, **kwargs):
                idx = next_idx()
                req_path = dump_request(idx, method_name, False, False, kwargs)
                t0 = time.perf_counter()
                response = original(self, *args, **kwargs)
                dt_ms = (time.perf_counter() - t0) * 1000
                resp_path = dump_response(idx, response, dt_ms, kwargs)
                _record(
                    records, response, idx, method_name, False, False, dt_ms, req_path, resp_path
                )
                return response

            return wrapped

        if not is_async and is_stream:

            def wrapped(self, *args, **kwargs):
                idx = next_idx()
                req_path = dump_request(idx, method_name, False, True, kwargs)
                t0 = time.perf_counter()
                stream = original(self, *args, **kwargs)
                return _wrap_sync_stream(
                    stream, records, idx, method_name, dump_response, req_path, t0
                )

            return wrapped

        if is_async and not is_stream:

            async def wrapped(self, *args, **kwargs):
                idx = next_idx()
                req_path = dump_request(idx, method_name, True, False, kwargs)
                t0 = time.perf_counter()
                response = await original(self, *args, **kwargs)
                dt_ms = (time.perf_counter() - t0) * 1000
                resp_path = dump_response(idx, response, dt_ms, kwargs)
                _record(
                    records, response, idx, method_name, True, False, dt_ms, req_path, resp_path
                )
                return response

            return wrapped

        # async streaming
        async def wrapped(self, *args, **kwargs):
            idx = next_idx()
            req_path = dump_request(idx, method_name, True, True, kwargs)
            t0 = time.perf_counter()
            stream = await original(self, *args, **kwargs)
            return _wrap_async_stream(
                stream, records, idx, method_name, dump_response, req_path, t0
            )

        return wrapped


def _record(
    records: list[CallRecord],
    response: Any,
    idx: int,
    method_name: str,
    is_async: bool,
    is_stream: bool,
    latency_ms: float,
    req_path: str,
    resp_path: str,
) -> None:
    prompt, completion, thoughts, total, model_id = _extract_usage(response)
    tool_calls, text_preview = _extract_tool_calls_and_text(response)
    records.append(
        CallRecord(
            call_index=idx,
            method=method_name,
            is_async=is_async,
            is_stream=is_stream,
            model_id=model_id,
            prompt_tokens=prompt,
            completion_tokens=completion,
            thoughts_tokens=thoughts,
            total_tokens=total,
            latency_ms=round(latency_ms, 2),
            request_dump=req_path,
            response_dump=resp_path,
            tool_calls=tool_calls,
            text_preview=text_preview,
        )
    )


def _wrap_sync_stream(stream, records, idx, method_name, dump_response, req_path, t0):
    last_chunk: Any = None

    def gen():
        nonlocal last_chunk
        for chunk in stream:
            last_chunk = chunk
            yield chunk
        dt_ms = (time.perf_counter() - t0) * 1000
        if last_chunk is not None:
            resp_path = dump_response(idx, last_chunk, dt_ms)
            _record(records, last_chunk, idx, method_name, False, True, dt_ms, req_path, resp_path)

    return gen()


def _wrap_async_stream(stream, records, idx, method_name, dump_response, req_path, t0):
    last_chunk: Any = None

    async def agen():
        nonlocal last_chunk
        async for chunk in stream:
            last_chunk = chunk
            yield chunk
        dt_ms = (time.perf_counter() - t0) * 1000
        if last_chunk is not None:
            resp_path = dump_response(idx, last_chunk, dt_ms)
            _record(records, last_chunk, idx, method_name, True, True, dt_ms, req_path, resp_path)

    return agen()


def write_summary(out_dir: str | Path, summary: CounterSummary) -> Path:
    """Write a top-level summary.json next to the per-call dumps."""
    path = Path(out_dir) / "summary.json"
    path.write_text(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
    return path
