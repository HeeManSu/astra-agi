#!/usr/bin/env python3
"""Sync `astra/CHANGELOG.md` (Keep a Changelog format) into `changelog.mdx`.

Reads the upstream changelog from the monorepo and rewrites
`astra-docs/changelog.mdx` using Mintlify `<Update>` blocks per release.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable


HEADING_RE = re.compile(r"^##\s+\[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?", re.MULTILINE)


def parse_changelog(text: str) -> list[tuple[str, str | None, str]]:
    """Return a list of (version, date, body) tuples in source order."""
    matches = list(HEADING_RE.finditer(text))
    entries: list[tuple[str, str | None, str]] = []
    for idx, match in enumerate(matches):
        version = match.group(1)
        date = match.group(2)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        entries.append((version, date, body))
    return entries


def render_mdx(entries: Iterable[tuple[str, str | None, str]]) -> str:
    out: list[str] = [
        "---",
        'title: "Changelog"',
        'description: "Release notes for astra-framework, astra-runtime, and astra-observability."',
        'icon: "list"',
        "---",
        "",
        (
            "Astra ships frequently. Subscribe to the "
            "[GitHub releases feed](https://github.com/astra-dev/astra/releases.atom) "
            "for instant updates."
        ),
        "",
    ]
    for version, date, body in entries:
        label = version
        description = date or ""
        out.append(f'<Update label="{label}" description="{description}">')
        out.append("")
        out.append(body)
        out.append("")
        out.append("</Update>")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Path to upstream CHANGELOG.md (default: <repo>/astra/CHANGELOG.md).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "changelog.mdx",
    )
    args = parser.parse_args()

    docs_root = Path(__file__).resolve().parent.parent
    repo_root = docs_root.parent
    source = args.source or repo_root / "astra" / "CHANGELOG.md"

    if not source.exists():
        print(f"No upstream changelog at {source}; skipping sync.", file=sys.stderr)
        return 0

    text = source.read_text(encoding="utf-8")
    entries = parse_changelog(text)
    if not entries:
        print("Upstream changelog has no recognizable headings; nothing to sync.", file=sys.stderr)
        return 0

    args.out.write_text(render_mdx(entries), encoding="utf-8")
    print(f"Wrote {args.out} ({len(entries)} release entries).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
