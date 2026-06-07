#!/usr/bin/env python3
"""Generate Mintlify MDX reference pages for one Astra package.

Usage:
    python astra-docs/scripts/build-reference.py --package framework
    python astra-docs/scripts/build-reference.py --package runtime --check
    python astra-docs/scripts/build-reference.py --package observability \\
        --emit-nav astra-docs/reference/observability/_nav.json

Design notes
------------
We use ``griffe.load`` in **static mode** (``allow_inspection=False``) so the
build does not need to import the package; that keeps CI lightweight and
deterministic and avoids spurious failures when an optional dependency is
missing on the build host.

The walker produces a list of :class:`ModuleIR`; we render one MDX file per
public submodule. Cross-references are routed through :class:`XrefIndex`,
which is persisted alongside the generated MDX so a downstream package can
link to symbols defined in a previously-built one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make sibling ``render`` package importable when this file is executed
# directly (``python astra-docs/scripts/build-reference.py ...``).
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from render import nav  # noqa: E402
from render.mdx import Renderer  # noqa: E402
from render.walker import (  # noqa: E402
    collect_missing_docstrings,
    load_package,
    walk_package,
)
from render.xref import XrefIndex  # noqa: E402


PACKAGES = {
    "framework": "astra_framework",
    "runtime": "astra_runtime",
    "observability": "astra_observability",
}


def _default_src(package: str, repo_root: Path) -> Path:
    """Default source path: ``astra/<pkg>/src/<dist_name>``."""

    dist = PACKAGES[package]
    return repo_root / "astra" / package / "src" / dist


def _repo_root() -> Path:
    """Walk up from this script until we find ``astra-docs/``'s parent."""

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "astra-docs").is_dir() and (parent / "astra").is_dir():
            return parent
    return here.parents[2]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate MDX reference pages for an Astra package.",
    )
    p.add_argument(
        "--package",
        required=True,
        choices=sorted(PACKAGES),
        help="Which Astra package to render.",
    )
    p.add_argument(
        "--src",
        type=Path,
        default=None,
        help="Source root (defaults to astra/<pkg>/src/<dist_name>).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (defaults to astra-docs/reference/<pkg>).",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any public symbol lacks a docstring; print misses.",
    )
    p.add_argument(
        "--emit-nav",
        type=Path,
        default=None,
        help="Write a mint.json-compatible nav fragment to this path.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    repo_root = _repo_root()
    docs_root = repo_root / "astra-docs"
    templates_dir = docs_root / "templates"

    package = args.package
    dist = PACKAGES[package]
    src = args.src or _default_src(package, repo_root)
    out_dir = args.out or (docs_root / "reference" / package)
    xref_path = docs_root / "reference" / "_xref.json"

    if not src.exists():
        print(f"[build-reference] source path does not exist: {src}", file=sys.stderr)
        return 2

    # Load package with griffe (static mode).
    print(f"[build-reference] loading {dist} from {src}")
    pkg_obj = load_package(dist, search_paths=[src.parent])

    xref = XrefIndex.load(xref_path)
    package_url_root = f"/reference/{package}"
    modules = walk_package(pkg_obj, repo_root=repo_root, xref=xref, package_url_root=package_url_root)
    print(f"[build-reference] discovered {len(modules)} modules")

    # --check mode: report missing docstrings and exit.
    if args.check:
        missing = collect_missing_docstrings(modules)
        if missing:
            print(
                f"[build-reference] {len(missing)} public symbols lack docstrings:",
                file=sys.stderr,
            )
            for q in missing:
                print(f"  - {q}", file=sys.stderr)
            return 1
        print("[build-reference] all public symbols have docstrings.")
        return 0

    # Render MDX.
    renderer = Renderer(templates_dir=templates_dir, xref=xref)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for module in modules:
        # Skip the package's top-level module file (we keep the hand-written
        # ``index.mdx`` landing page for each package).
        if module.qualname == dist:
            continue
        path = renderer.write_module(module, out_dir, package)
        written.append(path)
    print(f"[build-reference] wrote {len(written)} MDX pages to {out_dir}")

    # Persist xref index for cross-package linking.
    xref.save(xref_path)

    # Emit nav fragment if requested.
    if args.emit_nav:
        fragment = nav.build_group(package, modules)
        args.emit_nav.parent.mkdir(parents=True, exist_ok=True)
        args.emit_nav.write_text(json.dumps(fragment, indent=2))
        print(f"[build-reference] wrote nav fragment to {args.emit_nav}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
