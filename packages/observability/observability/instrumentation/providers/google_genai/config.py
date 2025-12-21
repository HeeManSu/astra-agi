from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from observability.instrumentation.providers.base.config import ProviderConfig


@dataclass
class GoogleGenAIConfig(ProviderConfig):
    truncate_chars: Optional[int] = None

