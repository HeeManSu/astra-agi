from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Mapping
import logging

logger = logging.getLogger(__name__)


@dataclass
class InstrumentorConfig:
    auto_instrument: bool = True
    instrument_llm_calls: bool = True
    privacy_truncate_chars: int = 2000
    fail_safe: bool = True
    provider_options: Optional[Dict[str, Any]] = None
    provider_configs: Mapping[str, Any] = field(default_factory=dict)


class BaseInstrumentor:
    _is_instrumented: bool
    _config: Optional[InstrumentorConfig]

    def __init__(self) -> None:
        self._is_instrumented = False
        self._config = None

    @property
    def is_instrumented(self) -> bool:
        return self._is_instrumented

    @property
    def target_packages(self) -> tuple[str, ...]:
        raise NotImplementedError

    def instrument(self, module: Any, config: InstrumentorConfig) -> None:
        if self._is_instrumented:
            logger.debug("%s already instrumented", self.__class__.__name__)
            return
        self._config = config
        try:
            self._do_instrument(module)
            self._is_instrumented = True
            logger.info("%s instrumented successfully", self.__class__.__name__)
        except Exception as e:
            self._is_instrumented = False
            if config.fail_safe:
                logger.exception("Instrumentation failed for %s: %s", self.__class__.__name__, e)
            else:
                raise

    def uninstrument(self) -> None:
        if not self._is_instrumented:
            return
        try:
            self._do_uninstrument()
        finally:
            self._is_instrumented = False
            logger.info("%s uninstrumented", self.__class__.__name__)

    def _do_instrument(self, module: Any) -> None:
        raise NotImplementedError

    def _do_uninstrument(self) -> None:
        pass
