from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OperationKind = Literal["generate", "tokens"]


@dataclass(frozen=True)
class OperationSpec:
    name: str
    method_name: str
    span_name: str
    kind: OperationKind
    streaming: bool = False
    asynchronous: bool = False

