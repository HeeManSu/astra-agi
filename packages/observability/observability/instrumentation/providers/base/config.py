from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    enabled: bool = True
    name: str | None = None

