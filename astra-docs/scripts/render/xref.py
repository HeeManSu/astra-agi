"""Symbol -> MDX path index.

The walker registers each documented symbol's fully-qualified name with the
MDX path that will host it (and the anchor within that page). The renderer
looks symbols up by short name when emitting type annotations so that, e.g.,
``Agent`` in a signature can be turned into a markdown link to
``/reference/framework/agents#agent``.

The index is persisted as JSON next to the generated MDX so subsequent
package builds can resolve cross-package references.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class XrefIndex:
    """Symbol index storing ``qualname -> (mdx_url, anchor)`` mappings."""

    entries: dict[str, tuple[str, str]] = field(default_factory=dict)
    # short-name -> list of qualnames; used as a fallback when only a leaf
    # name like ``Agent`` appears in a type annotation.
    _by_short: dict[str, list[str]] = field(default_factory=dict)

    def register(self, qualname: str, mdx_url: str, anchor: str) -> None:
        """Register a symbol. ``mdx_url`` should be the docs URL path."""

        self.entries[qualname] = (mdx_url, anchor)
        short = qualname.rsplit(".", 1)[-1]
        self._by_short.setdefault(short, []).append(qualname)

    def resolve(self, ref: str) -> str | None:
        """Return a markdown link target for ``ref`` or ``None`` if unknown."""

        if ref in self.entries:
            url, anchor = self.entries[ref]
            return f"{url}#{anchor}" if anchor else url
        candidates = self._by_short.get(ref, [])
        if len(candidates) == 1:
            url, anchor = self.entries[candidates[0]]
            return f"{url}#{anchor}" if anchor else url
        return None

    # ------------------------------------------------------------------
    # Linkifying type expressions
    # ------------------------------------------------------------------

    _IDENT = re.compile(r"\b([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*)\b")

    def linkify(self, type_str: str | None) -> str:
        """Wrap known identifiers inside a rendered type string in MD links."""

        if not type_str:
            return ""

        def _sub(match: "re.Match[str]") -> str:
            ident = match.group(1)
            target = self.resolve(ident)
            if not target:
                return ident
            return f"[{ident}]({target})"

        return self._IDENT.sub(_sub, type_str)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {q: list(v) for q, v in self.entries.items()}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    @classmethod
    def load(cls, path: Path) -> "XrefIndex":
        idx = cls()
        if not path.exists():
            return idx
        payload = json.loads(path.read_text())
        for q, (url, anchor) in payload.items():
            idx.register(q, url, anchor)
        return idx
