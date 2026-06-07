"""Emit ``mint.json``-compatible navigation fragments.

Mintlify's navigation is a JSON tree with ``group`` + ``pages``; ``pages``
may be a string (page URL) or another nested group. We emit one group per
package, with each module getting its own page.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .ir import ModuleIR


def build_group(package: str, modules: Iterable[ModuleIR]) -> dict:
    """Return a single ``{"group": ..., "pages": [...]}`` dict."""

    pages: list[object] = [f"reference/{package}/index"]
    for m in modules:
        leaf = m.qualname.split(".")[-1]
        pages.append(f"reference/{package}/{leaf}")
    return {"group": package, "pages": pages}


def build_fragment(per_package: dict[str, list[ModuleIR]]) -> dict:
    """Return the umbrella ``API Reference`` group containing each package."""

    groups: list[object] = ["reference/index"]
    for package, modules in per_package.items():
        groups.append(build_group(package, modules))
    return {"group": "API Reference", "pages": groups}


def write_fragment(path: Path, fragment: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fragment, indent=2))
