#!/usr/bin/env python3
"""Audit MDX pages that instantiate a model directly without using the provider snippet.

The shared snippet at `snippets/provider-tabs.mdx` shows the five-tab
`<CodeGroup>` (Gemini, Bedrock, Anthropic/OpenAI/Ollama "Coming in v0.2").
Pages that build an `Agent` or call `Gemini(...)` / `Bedrock(...)` should
import that snippet rather than inlining a bespoke provider example.

Exit code:
  0 - all model-instantiating pages import ProviderTabs (or are explicitly exempt)
  1 - at least one page builds a model inline without the shared snippet
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MODEL_CTOR_RE = re.compile(r"\b(?:Gemini|Bedrock|Anthropic|OpenAI|Ollama)\s*\(")
PROVIDER_TABS_IMPORT_RE = re.compile(
    r"import\s+ProviderTabs\s+from\s+['\"]/snippets/provider-tabs\.mdx['\"]"
)

EXEMPT_BASENAMES = {
    "provider-tabs.mdx",
    # Reference pages are auto-generated and document the model class itself.
}


def is_exempt(path: Path, docs_root: Path) -> bool:
    if path.name in EXEMPT_BASENAMES:
        return True
    parts = path.relative_to(docs_root).parts
    return parts[0] == "reference" or parts[0] == "snippets"


def audit_file(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not MODEL_CTOR_RE.search(text):
        return None
    if PROVIDER_TABS_IMPORT_RE.search(text):
        return None
    return (
        f"{path}: model constructor present but does not "
        "import ProviderTabs from '/snippets/provider-tabs.mdx'."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Docs root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit 1 if any page is non-compliant (default: warn only).",
    )
    args = parser.parse_args()

    root: Path = args.root
    mdx_files = sorted(p for p in root.rglob("*.mdx") if not is_exempt(p, root))

    misses: list[str] = []
    for path in mdx_files:
        miss = audit_file(path)
        if miss:
            misses.append(miss)

    if misses:
        print(f"CodeGroup audit found {len(misses)} non-compliant page(s):\n", file=sys.stderr)
        for m in misses:
            print(f"  - {m}", file=sys.stderr)
        return 1 if args.fail_on_missing else 0

    print(f"CodeGroup audit clean across {len(mdx_files)} pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
