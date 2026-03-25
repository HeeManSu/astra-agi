"""Debug artifact persistence.

Saves generated artifacts to .debug/ in the project root for quick inspection.
"""

from __future__ import annotations

import os


def save_debug_artifact(filename: str, content: str) -> None:
    """Save a debug artifact to .debug/ (always overwrites)."""
    os.makedirs(".debug", exist_ok=True)
    with open(f".debug/{filename}", "w") as f:
        f.write(content)
