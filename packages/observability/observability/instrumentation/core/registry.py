from __future__ import annotations

from dataclasses import dataclass
import importlib
import logging

from observability.instrumentation.core.base_instrumentor import BaseInstrumentor


logger = logging.getLogger(__name__)


@dataclass
class InstrumentorSpec:
    module_path: str
    class_name: str
    min_version: str | None = None
    priority: int = 0


class InstrumentationRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, InstrumentorSpec] = {}
        self._instances: dict[str, BaseInstrumentor] = {}

    def register(self, package_name: str, spec: InstrumentorSpec) -> None:
        self._specs[package_name] = spec

    def get_spec(self, package_name: str) -> InstrumentorSpec | None:
        return self._specs.get(package_name)

    def get_or_create(self, package_name: str) -> BaseInstrumentor | None:
        if package_name in self._instances:
            return self._instances[package_name]
        spec = self._specs.get(package_name)
        if not spec:
            return None
        try:
            mod = importlib.import_module(spec.module_path)
            klass = getattr(mod, spec.class_name)
            instance: BaseInstrumentor = klass()
            self._instances[package_name] = instance
            return instance
        except Exception as e:
            logger.exception("Failed to instantiate instrumentor for %s: %s", package_name, e)
            return None

    def all_specs(self) -> dict[str, InstrumentorSpec]:
        return dict(self._specs)

    def all_instances(self) -> dict[str, BaseInstrumentor]:
        return dict(self._instances)

