"""
Observability Instrumentation

Entry point for auto-instrumentation of LLM providers and agentic libraries.
Initializes import monitoring and instruments already-imported modules when enabled.
"""
import logging
from typing import Optional

from observability.instrumentation.core.base_instrumentor import InstrumentorConfig
from observability.instrumentation.core.import_monitor import ImportMonitor
from observability.instrumentation.core.registry import InstrumentationRegistry, InstrumentorSpec
from observability.instrumentation.core.version_checker import VersionChecker
from observability.instrumentation.providers.registry import register_builtin_providers


logger = logging.getLogger(__name__)

_registry = InstrumentationRegistry()
_import_monitor: ImportMonitor | None = None
_is_initialized: bool = False


def init(auto_instrument: bool = True, config: InstrumentorConfig | None = None) -> None:
    """
    Initialize auto-instrumentation system.
    - Registers built-in instrumentors
    - Hooks into Python import system
    - Instruments already-imported target modules
    """
    global _import_monitor, _is_initialized
    if _is_initialized:
        return

    cfg = config or InstrumentorConfig()
    cfg.auto_instrument = auto_instrument

    # Register built-in providers using the central registry catalog
    register_builtin_providers(_registry)

    _import_monitor = ImportMonitor(
        registry=_registry,
        version_checker=VersionChecker(),
        config=cfg,
    )

    if cfg.auto_instrument:
        _import_monitor.attach()

    _import_monitor.instrument_already_imported()
    _is_initialized = True
    logger.info("Observability Instrumentation initialized (auto_instrument=%s)", cfg.auto_instrument)


def shutdown() -> None:
    """Detach import hooks and uninstrument all instrumentors."""
    global _import_monitor, _is_initialized
    if _import_monitor is not None:
        _import_monitor.detach()
        _import_monitor.uninstrument_all()
    _is_initialized = False


