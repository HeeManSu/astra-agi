from __future__ import annotations

import importlib
import logging
from typing import Any

from observability.instrumentation.core.base_instrumentor import BaseInstrumentor
from observability.instrumentation.core.operations import OperationSpec
from observability.instrumentation.core.wrapper_factory import (
    create_async_streaming_wrapper,
    create_async_wrapper,
    create_streaming_wrapper,
    create_sync_wrapper,
)
from observability.instrumentation.providers.google_genai.adapter import GoogleGenAIAdapter


logger = logging.getLogger(__name__)


class GoogleGenAIInstrumentor(BaseInstrumentor):
    def __init__(self) -> None:
        super().__init__()
        self._originals: dict[str, Any] = {}

    @property
    def target_packages(self) -> tuple[str, ...]:
        return ("google.genai", "google.genai.aio")

    def _do_instrument(self, module: Any) -> None:
        modname = getattr(module, "__name__", "")
        if modname == "google.genai":
            self._instrument_sync()
        elif modname == "google.genai.aio":
            self._instrument_async()

    def _do_uninstrument(self) -> None:
        for key, fn in list(self._originals.items()):
            try:
                module_path, attr_path = key.split("::", 1)
                mod = importlib.import_module(module_path)
                target = mod
                parts = attr_path.split(".")
                for p in parts[:-1]:
                    target = getattr(target, p)
                setattr(target, parts[-1], fn)
            except Exception:
                logger.exception("Failed to restore original %s", key)
        self._originals.clear()

    def _instrument_sync(self) -> None:
        models_mod = importlib.import_module("google.genai.models")
        Models = getattr(models_mod, "Models", None)
        if not Models:
            return
        adapter = GoogleGenAIAdapter()
        operations = [
            OperationSpec(
                name="generate_content",
                method_name="generate_content",
                span_name="generate_content.client",
                kind="generate",
                streaming=False,
                asynchronous=False,
            ),
            OperationSpec(
                name="generate_content_stream",
                method_name="generate_content_stream",
                span_name="generate_content_stream.client",
                kind="generate",
                streaming=True,
                asynchronous=False,
            ),
            OperationSpec(
                name="count_tokens",
                method_name="count_tokens",
                span_name="count_tokens.client",
                kind="tokens",
                streaming=False,
                asynchronous=False,
            ),
            OperationSpec(
                name="compute_tokens",
                method_name="compute_tokens",
                span_name="compute_tokens.client",
                kind="tokens",
                streaming=False,
                asynchronous=False,
            ),
        ]
        for op in operations:
            orig = getattr(Models, op.method_name, None)
            if orig is None:
                continue
            if op.streaming:
                wrapped = create_streaming_wrapper(adapter, op, self._config)(orig)
            else:
                wrapped = create_sync_wrapper(adapter, op, self._config)(orig)
            key = f"google.genai.models::Models.{op.method_name}"
            self._store_and_set(key, Models, op.method_name, wrapped, orig)

    def _instrument_async(self) -> None:
        models_mod = importlib.import_module("google.genai.aio.models")
        Models = getattr(models_mod, "Models", None)
        if not Models:
            return
        adapter = GoogleGenAIAdapter()
        operations = [
            OperationSpec(
                name="generate_content",
                method_name="generate_content",
                span_name="generate_content.client",
                kind="generate",
                streaming=False,
                asynchronous=True,
            ),
            OperationSpec(
                name="generate_content_stream",
                method_name="generate_content_stream",
                span_name="generate_content_stream.client",
                kind="generate",
                streaming=True,
                asynchronous=True,
            ),
            OperationSpec(
                name="count_tokens",
                method_name="count_tokens",
                span_name="count_tokens.client",
                kind="tokens",
                streaming=False,
                asynchronous=True,
            ),
            OperationSpec(
                name="compute_tokens",
                method_name="compute_tokens",
                span_name="compute_tokens.client",
                kind="tokens",
                streaming=False,
                asynchronous=True,
            ),
        ]
        for op in operations:
            orig = getattr(Models, op.method_name, None)
            if orig is None:
                continue
            if op.streaming:
                wrapped = create_async_streaming_wrapper(adapter, op, self._config)(orig)
            else:
                wrapped = create_async_wrapper(adapter, op, self._config)(orig)
            key = f"google.genai.aio.models::Models.{op.method_name}"
            self._store_and_set(key, Models, op.method_name, wrapped, orig)

    def _store_and_set(self, key: str, target: Any, attr: str, wrapped: Any, orig: Any) -> None:
        if key in self._originals:
            return
        self._originals[key] = orig
        setattr(target, attr, wrapped)
