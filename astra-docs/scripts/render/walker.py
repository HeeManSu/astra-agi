"""griffe traversal -> IR.

We load packages with :func:`griffe.load` in **static mode** by default --
griffe will parse source files via the ``ast`` module without executing them.
This avoids importing Astra at build time (which would otherwise require
every optional dependency to be installed in CI just to read docstrings).

Google-style docstrings are parsed via griffe's docstring parser into a list
of typed sections (``Text``, ``Args``, ``Returns``, ``Raises``, ``Examples``,
``Notes``, ``Warnings``). We render those sections into MDX-ready strings
while building the IR.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import griffe

from .filters import is_deprecated, is_private_name, should_render
from .ir import ClassIR, FuncIR, ModuleIR, ParamIR
from .xref import XrefIndex

# ``griffe.docstrings.google.parse`` was relocated across griffe versions; we
# import via the top-level ``griffe`` namespace where possible and fall back.
try:  # griffe >= 0.49 keeps the parser under ``griffe.docstrings``
    from griffe.docstrings.google import parse as parse_google  # type: ignore
except Exception:  # pragma: no cover - older or newer layout
    parse_google = None  # type: ignore[assignment]


GITHUB_BASE = "https://github.com/astra-dev/astra/blob/main"


# ---------------------------------------------------------------------------
# Type-annotation rendering
# ---------------------------------------------------------------------------


def render_annotation(ann: Any) -> str | None:
    """Render a griffe annotation (``Expr`` or ``str``) into a readable string.

    griffe's ``Expr`` objects implement ``__str__`` already; we just normalise
    whitespace and unwrap missing values to ``None``.
    """

    if ann is None:
        return None
    if isinstance(ann, str):
        return ann.strip() or None
    # griffe.expressions.Expr and subclasses
    try:
        text = str(ann)
    except Exception:
        return None
    text = " ".join(text.split())
    return text or None


# ---------------------------------------------------------------------------
# Docstring section unpacking
# ---------------------------------------------------------------------------


def _parsed_sections(docstring: Any) -> list[Any]:
    """Return the list of parsed sections for a griffe ``Docstring``.

    Tries the cached ``parsed`` attribute first; otherwise calls the Google
    parser directly. Returns ``[]`` if no docstring.
    """

    if docstring is None:
        return []
    parsed = getattr(docstring, "parsed", None)
    if parsed:
        return list(parsed)
    if parse_google is not None:
        try:
            return list(parse_google(docstring))
        except Exception:
            return []
    return []


def _section_kind(section: Any) -> str:
    """Normalise the kind of a docstring section to a lowercase string."""

    kind = getattr(section, "kind", "")
    return str(getattr(kind, "value", kind)).lower()


def _section_value(section: Any) -> Any:
    return getattr(section, "value", "")


def _split_doc(
    docstring: Any,
) -> tuple[
    str, dict[str, str], list[tuple[str, str | None, str]], list[tuple[str, str]], str | None
]:
    """Unpack a docstring into (description, arg_docs, raises, returns).

    Returns:
        description: First text section, joined as a single string.
        arg_docs: ``{param_name: description}`` from the Args section.
        return_info: ``(type_str, description)`` for Returns (each may be empty).
        raises: list of ``(exception_type, description)``.
        examples_md: pre-rendered examples block (or ``None``).
    """

    sections = _parsed_sections(docstring)
    description_parts: list[str] = []
    arg_docs: dict[str, str] = {}
    raises: list[tuple[str, str]] = []
    returns_type: str | None = None
    returns_desc = ""
    examples_md_parts: list[str] = []

    for section in sections:
        kind = _section_kind(section)
        value = _section_value(section)
        if kind in ("text", "description"):
            description_parts.append(str(value).strip())
        elif kind in ("parameters", "arguments", "args"):
            for p in value or []:
                name = getattr(p, "name", "")
                desc = getattr(p, "description", "") or ""
                if name:
                    arg_docs[name] = desc.strip()
        elif kind in ("returns", "return"):
            # Returns section is a list of returned values; we collapse them.
            descs: list[str] = []
            for r in value or []:
                ann = getattr(r, "annotation", None)
                if returns_type is None and ann is not None:
                    returns_type = render_annotation(ann)
                d = getattr(r, "description", "") or ""
                if d:
                    descs.append(d.strip())
            returns_desc = "\n\n".join(descs)
        elif kind == "raises":
            for r in value or []:
                ann = render_annotation(getattr(r, "annotation", None)) or "Exception"
                desc = getattr(r, "description", "") or ""
                raises.append((ann, desc.strip()))
        elif kind in ("examples", "example"):
            # Examples value can be a string or a list of (kind, text) pairs.
            if isinstance(value, str):
                examples_md_parts.append(value.strip())
            else:
                for item in value or []:
                    if isinstance(item, tuple) and len(item) == 2:
                        examples_md_parts.append(str(item[1]).strip())
                    else:
                        examples_md_parts.append(str(item).strip())
        elif kind in ("notes", "note"):
            description_parts.append(f"\n\n<Note>\n{str(value).strip()}\n</Note>")
        elif kind in ("warnings", "warning"):
            description_parts.append(f"\n\n<Warning>\n{str(value).strip()}\n</Warning>")

    description = "\n\n".join(p for p in description_parts if p).strip()
    examples_md = (
        "\n\n```python\n" + "\n\n".join(examples_md_parts) + "\n```" if examples_md_parts else None
    )
    if examples_md:
        description = (description + "\n\n**Examples**\n" + examples_md).strip()
    return description, arg_docs, raises, returns_type, returns_desc


# ---------------------------------------------------------------------------
# Source URLs
# ---------------------------------------------------------------------------


def _source_url(obj: Any, repo_root: Path) -> str:
    """Build a GitHub blob URL for the symbol's defining file + line."""

    filepath = getattr(obj, "filepath", None)
    if filepath is None:
        return ""
    try:
        rel = Path(filepath).resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:
        # Fall back to the basename if the path is outside the repo root.
        rel = Path(filepath).name
    lineno = getattr(obj, "lineno", None) or 1
    return f"{GITHUB_BASE}/{rel}#L{lineno}"


# ---------------------------------------------------------------------------
# Function / class / module conversion
# ---------------------------------------------------------------------------


def _build_signature(func: Any) -> str:
    """Render the function signature as a Python-ish string."""

    parts: list[str] = []
    for p in getattr(func, "parameters", []) or []:
        name = getattr(p, "name", "")
        ann = render_annotation(getattr(p, "annotation", None))
        default = getattr(p, "default", None)
        piece = name
        if ann:
            piece += f": {ann}"
        if default is not None:
            piece += f" = {default}"
        parts.append(piece)
    sig = ", ".join(parts)
    name = getattr(func, "name", "")
    ret_ann = render_annotation(getattr(func, "returns", None))
    suffix = f" -> {ret_ann}" if ret_ann else ""
    prefix = "async def " if getattr(func, "is_async", False) else "def "
    return f"{prefix}{name}({sig}){suffix}"


def _params_for(func: Any, arg_docs: dict[str, str]) -> list[ParamIR]:
    out: list[ParamIR] = []
    for p in getattr(func, "parameters", []) or []:
        name = getattr(p, "name", "")
        if name in ("self", "cls"):
            continue
        ann = render_annotation(getattr(p, "annotation", None))
        default = getattr(p, "default", None)
        default_str = None if default is None else str(default)
        required = default is None
        out.append(
            ParamIR(
                name=name,
                type_str=ann,
                default=default_str,
                description=arg_docs.get(name, ""),
                required=required,
            )
        )
    return out


def func_to_ir(func: Any, repo_root: Path) -> FuncIR:
    description, arg_docs, raises, returns_type, returns_desc = _split_doc(
        getattr(func, "docstring", None)
    )
    inferred_return = render_annotation(getattr(func, "returns", None))
    return FuncIR(
        name=func.name,
        qualname=func.canonical_path,
        signature=_build_signature(func),
        description=description,
        params=_params_for(func, arg_docs),
        returns_type=returns_type or inferred_return,
        returns_desc=returns_desc,
        raises=raises,
        source_url=_source_url(func, repo_root),
        is_async=bool(getattr(func, "is_async", False)),
    )


def class_to_ir(cls: Any, repo_root: Path) -> ClassIR:
    description, _arg_docs, _raises, _rt, _rd = _split_doc(getattr(cls, "docstring", None))
    init_ir: FuncIR | None = None
    methods: list[FuncIR] = []
    members = getattr(cls, "members", {}) or {}
    for name, member in members.items():
        if not _is_function(member):
            continue
        if is_deprecated(member):
            continue
        if name == "__init__":
            init_ir = func_to_ir(member, repo_root)
            continue
        if is_private_name(name):
            continue
        methods.append(func_to_ir(member, repo_root))
    methods.sort(key=lambda f: f.name)
    return ClassIR(
        name=cls.name,
        qualname=cls.canonical_path,
        description=description,
        init=init_ir,
        methods=methods,
        source_url=_source_url(cls, repo_root),
    )


def _is_function(obj: Any) -> bool:
    kind = getattr(obj, "kind", None)
    return str(getattr(kind, "value", kind)).lower() == "function"


def _is_class(obj: Any) -> bool:
    kind = getattr(obj, "kind", None)
    return str(getattr(kind, "value", kind)).lower() == "class"


def _is_module(obj: Any) -> bool:
    kind = getattr(obj, "kind", None)
    return str(getattr(kind, "value", kind)).lower() == "module"


def _module_all(mod: Any) -> list[str] | None:
    """Return the module's declared ``__all__`` or ``None`` if undeclared."""

    exports = getattr(mod, "exports", None)
    if exports is None:
        return None
    out: list[str] = []
    for e in exports:
        name = getattr(e, "name", None) or getattr(e, "value", None) or str(e)
        out.append(str(name).strip("'\""))
    return out


def module_to_ir(mod: Any, repo_root: Path) -> ModuleIR:
    description, *_ = _split_doc(getattr(mod, "docstring", None))
    all_list = _module_all(mod)
    classes: list[ClassIR] = []
    functions: list[FuncIR] = []
    submodules: list[str] = []
    for name, member in (getattr(mod, "members", {}) or {}).items():
        if _is_module(member):
            if not is_private_name(name):
                submodules.append(member.canonical_path)
            continue
        if not should_render(member, all_list):
            continue
        if _is_class(member):
            classes.append(class_to_ir(member, repo_root))
        elif _is_function(member):
            functions.append(func_to_ir(member, repo_root))
    classes.sort(key=lambda c: c.name)
    functions.sort(key=lambda f: f.name)
    submodules.sort()
    return ModuleIR(
        name=mod.name,
        qualname=mod.canonical_path,
        description=description,
        classes=classes,
        functions=functions,
        submodules=submodules,
    )


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------


def load_package(package: str, search_paths: Iterable[str | Path]) -> Any:
    """Wrapper over :func:`griffe.load` using static parsing."""

    return griffe.load(
        package,
        search_paths=[str(p) for p in search_paths],
        # static is the default but we set it explicitly for clarity.
        # ``allow_inspection=False`` keeps us from importing user code.
        allow_inspection=False,
    )


def walk_package(
    package_obj: Any,
    repo_root: Path,
    xref: XrefIndex,
    package_url_root: str,
) -> list[ModuleIR]:
    """Walk a loaded griffe package, returning a list of ``ModuleIR``.

    One IR per public submodule. The xref index is populated as a side
    effect so subsequent packages can resolve cross-references.
    """

    out: list[ModuleIR] = []
    _visit(package_obj, repo_root, xref, package_url_root, out)
    return out


def _visit(
    mod: Any,
    repo_root: Path,
    xref: XrefIndex,
    package_url_root: str,
    out: list[ModuleIR],
) -> None:
    if not _is_module(mod):
        return
    if is_private_name(mod.name) and mod.name != mod.canonical_path.split(".")[0]:
        return

    ir = module_to_ir(mod, repo_root)
    # Only emit a page if the module has something to show or it's the root.
    if ir.classes or ir.functions or mod.name == mod.canonical_path.split(".")[0]:
        page_url = f"{package_url_root}/{ir.name}"
        for c in ir.classes:
            xref.register(c.qualname, page_url, c.name.lower())
            if c.init is not None:
                xref.register(c.init.qualname, page_url, c.name.lower())
            for m in c.methods:
                xref.register(m.qualname, page_url, f"{c.name.lower()}-{m.name.lower()}")
        for f in ir.functions:
            xref.register(f.qualname, page_url, f.name.lower())
        out.append(ir)

    for name, member in (getattr(mod, "members", {}) or {}).items():
        if _is_module(member) and not is_private_name(name):
            _visit(member, repo_root, xref, package_url_root, out)


# ---------------------------------------------------------------------------
# Docstring-coverage auditing
# ---------------------------------------------------------------------------


def collect_missing_docstrings(modules: list[ModuleIR]) -> list[str]:
    """Return qualnames of public symbols without a non-empty description."""

    missing: list[str] = []
    for m in modules:
        if not m.description:
            missing.append(m.qualname)
        for c in m.classes:
            if not c.description:
                missing.append(c.qualname)
            if c.init and not c.init.description:
                missing.append(f"{c.qualname}.__init__")
            for meth in c.methods:
                if not meth.description:
                    missing.append(meth.qualname)
        for f in m.functions:
            if not f.description:
                missing.append(f.qualname)
    return missing
