#!/usr/bin/env python3
"""Generate ``llms.txt`` and ``llms-full.txt`` from the Mintlify docs.

Walks every page declared in ``astra-docs/mint.json``'s navigation, reads
the matching MDX file, strips YAML frontmatter and the most common MDX
component noise (``import`` statements and self-closing JSX tags), and
concatenates the cleaned text.

Outputs:
    astra-docs/llms-full.txt   Full Markdown body of every page.
    astra-docs/llms.txt        URL index (one path per page).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable


FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
IMPORT_RE = re.compile(r"^\s*import\s+.+?from\s+['\"].+?['\"];?\s*$", re.MULTILINE)
EXPORT_RE = re.compile(r"^\s*export\s+.+?;\s*$", re.MULTILINE)
SELF_CLOSE_RE = re.compile(r"<([A-Z][A-Za-z0-9]*)([^>]*)/>")
JSX_PAIR_RE = re.compile(r"<([A-Z][A-Za-z0-9]*)([^>]*)>(.*?)</\1>", re.DOTALL)


def _iter_pages(nav: list, prefix: str = "") -> Iterable[str]:
    """Yield every page path from a Mintlify ``navigation`` list."""

    for entry in nav:
        if isinstance(entry, str):
            yield entry
        elif isinstance(entry, dict):
            pages = entry.get("pages", [])
            yield from _iter_pages(pages, prefix)


def _strip_mdx(text: str) -> str:
    text = FRONTMATTER_RE.sub("", text, count=1)
    text = IMPORT_RE.sub("", text)
    text = EXPORT_RE.sub("", text)
    # Replace paired JSX components with their inner text.
    prev = None
    while prev != text:
        prev = text
        text = JSX_PAIR_RE.sub(lambda m: m.group(3), text)
    text = SELF_CLOSE_RE.sub("", text)
    # Collapse runs of blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main() -> int:
    docs_root = Path(__file__).resolve().parent.parent
    mint_json = docs_root / "mint.json"
    if not mint_json.exists():
        print(f"[build-llms-txt] mint.json not found at {mint_json}", file=sys.stderr)
        return 2

    config = json.loads(mint_json.read_text())
    nav = config.get("navigation", [])
    pages = list(_iter_pages(nav))

    full_parts: list[str] = []
    url_lines: list[str] = []
    site_url = config.get("openapi", {}).get("baseUrl") or "https://docs.astra.dev"

    for page in pages:
        mdx_path = docs_root / f"{page}.mdx"
        if not mdx_path.exists():
            continue
        raw = mdx_path.read_text()
        body = _strip_mdx(raw)
        full_parts.append(f"# /{page}\n\n{body}\n")
        url_lines.append(f"{site_url.rstrip('/')}/{page}")

    (docs_root / "llms-full.txt").write_text("\n".join(full_parts))
    (docs_root / "llms.txt").write_text("\n".join(url_lines) + "\n")
    print(f"[build-llms-txt] wrote {len(full_parts)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
