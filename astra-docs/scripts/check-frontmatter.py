#!/usr/bin/env python3
"""Verify every MDX page has the required frontmatter fields.

Exits non-zero if any page is missing `title` or `description`, or sets `noindex: true`.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    raw = match.group(1)
    out: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if not fm:
        errors.append(f"{path}: missing frontmatter")
        return errors
    if not fm.get("title"):
        errors.append(f"{path}: missing 'title'")
    if not fm.get("description"):
        errors.append(f"{path}: missing 'description'")
    if fm.get("noindex", "").lower() == "true":
        errors.append(f"{path}: noindex is set; remove if unintentional")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Docs root (default: parent of scripts/).",
    )
    args = parser.parse_args()

    root: Path = args.root
    mdx_files = sorted(
        p
        for p in root.rglob("*.mdx")
        if "snippets" not in p.parts and "node_modules" not in p.parts
    )

    all_errors: list[str] = []
    for path in mdx_files:
        all_errors.extend(check_file(path))

    if all_errors:
        print(f"Frontmatter check failed on {len(all_errors)} page(s):\n", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"Frontmatter OK across {len(mdx_files)} pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
