from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderConfig:
    enabled: bool = True
    name: Optional[str] = None

