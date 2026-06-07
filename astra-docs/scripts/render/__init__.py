"""Reference-generation toolchain.

Modules:
    ir       Intermediate-representation dataclasses produced by the walker
             and consumed by the MDX renderer.
    walker   griffe traversal that converts a loaded package into IR.
    mdx      IR -> MDX rendering via Jinja2 templates.
    nav      Emits ``mint.json``-compatible navigation fragments.
    xref     Symbol index ({qualname: mdx_path}) for cross-reference linking.
    filters  Visibility / deprecation predicates (skip _private, @deprecated).
"""

from .ir import ClassIR, FuncIR, ModuleIR, ParamIR

__all__ = ["ClassIR", "FuncIR", "ModuleIR", "ParamIR"]
