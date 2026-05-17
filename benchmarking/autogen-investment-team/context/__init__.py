"""
Context Loader
--------------
Loads markdown context documents for agent instructions.
"""

from pathlib import Path

_DIR = Path(__file__).parent


def load_context(files: list[str]) -> str:
    """Return concatenated context text for the listed file names."""
    sections = []
    for f in files:
        p = _DIR / f
        if p.exists():
            sections.append(p.read_text().strip())
    return "\n\n---\n\n".join(sections)
