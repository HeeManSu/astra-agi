from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any
import importlib
import logging

from observability.instrumentation.core.base_instrumentor import BaseInstrumentor

logger = logging.getLogger(__name__)


@dataclass
class InstrumentorSpec:
    module_path: str
    class_name: str
    min_version: Optional[str] = None
    priority: int = 0


class InstrumentationRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, InstrumentorSpec] = {}
        self._instances: Dict[str, BaseInstrumentor] = {}

    def register(self, package_name: str, spec: InstrumentorSpec) -> None:
        self._specs[package_name] = spec

    def get_spec(self, package_name: str) -> Optional[InstrumentorSpec]:
        return self._specs.get(package_name)

    def get_or_create(self, package_name: str) -> Optional[BaseInstrumentor]:
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

    def all_specs(self) -> Dict[str, InstrumentorSpec]:
        return dict(self._specs)

    def all_instances(self) -> Dict[str, BaseInstrumentor]:
        return dict(self._instances)

