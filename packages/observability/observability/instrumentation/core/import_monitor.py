from __future__ import annotations

import builtins
import importlib
import logging
import sys
from typing import Any

from observability.instrumentation.core.base_instrumentor import InstrumentorConfig
from observability.instrumentation.core.registry import InstrumentationRegistry, InstrumentorSpec
from observability.instrumentation.core.version_checker import VersionChecker


logger = logging.getLogger(__name__)


def _is_third_party_module(module_name: str, module: Any) -> bool:
    try:
        spec = importlib.util.find_spec(module_name)
        if not spec or not spec.origin:
            return False
        origin = spec.origin or ""
        if origin == "built-in":
            return False
        return "site-packages" in origin or "dist-packages" in origin
    except Exception:
        return False


class ImportMonitor:
    def __init__(
        self,
        registry: InstrumentationRegistry,
        version_checker: VersionChecker,
        config: InstrumentorConfig,
    ) -> None:
        self._registry = registry
        self._version_checker = version_checker
        self._config = config
        self._orig_import = builtins.__import__
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        builtins.__import__ = self._import_hook  # type: ignore[assignment]
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return
        builtins.__import__ = self._orig_import  # type: ignore[assignment]
        self._attached = False

    def instrument_already_imported(self) -> None:
        for pkg_name, spec in self._registry.all_specs().items():
            if pkg_name in sys.modules:
                module = sys.modules[pkg_name]
                if _is_third_party_module(pkg_name, module):
                    self._try_instrument(pkg_name, module, spec)

    def uninstrument_all(self) -> None:
        for inst in self._registry.all_instances().values():
            try:
                inst.uninstrument()
            except Exception:
                logger.exception("Failed to uninstrument %s", inst.__class__.__name__)

    def _import_hook(self, name: str, globals=None, locals=None, fromlist=(), level=0):
        module = self._orig_import(name, globals, locals, fromlist, level)
        full_name = name
        if fromlist:
            for item in fromlist:
                sub_name = f"{name}.{item}"
                if sub_name in sys.modules:
                    self._maybe_instrument(sub_name)
        self._maybe_instrument(full_name)
        return module

    def _maybe_instrument(self, module_name: str) -> None:
        spec = self._registry.get_spec(module_name)
        if not spec:
            return
        module = sys.modules.get(module_name)
        if not module:
            return
        if not _is_third_party_module(module_name, module):
            logger.debug("Skipping local module %s for instrumentation", module_name)
            return
        self._try_instrument(module_name, module, spec)

    def _try_instrument(self, module_name: str, module: Any, spec: InstrumentorSpec) -> None:
        try:
            installed_version = getattr(module, "__version__", None)
            if not self._version_checker.is_compatible(installed_version, spec.min_version):
                logger.warning(
                    "Skipping instrumentation for %s: version %s < required %s",
                    module_name, installed_version, spec.min_version,
                )
                return
            instrumentor = self._registry.get_or_create(module_name)
            if not instrumentor:
                return
            instrumentor.instrument(module, self._config)
        except Exception as e:
            if self._config.fail_safe:
                logger.exception("Error instrumenting %s: %s", module_name, e)
            else:
                raise

