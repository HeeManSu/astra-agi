from __future__ import annotations

from dataclasses import dataclass

from observability.instrumentation.providers.base.config import ProviderConfig


@dataclass
class BedrockConfig(ProviderConfig):
    truncate_chars: int | None = None
