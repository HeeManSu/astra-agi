"""Intermediate representation (IR) dataclasses.

The walker produces these dataclasses from griffe objects; the MDX renderer
consumes them. Keeping the IR purely declarative means templates never touch
griffe internals and tests can fabricate IR instances directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParamIR:
    """A single parameter on a callable.

    Attributes:
        name: Parameter identifier as it appears in the signature.
        type_str: Rendered type annotation, or ``None`` if unannotated.
        default: Repr of the default value, or ``None`` if required.
        description: Docstring text for this parameter (from the Args section).
        required: ``True`` if no default value is provided.
    """

    name: str
    type_str: str | None
    default: str | None
    description: str
    required: bool


@dataclass
class FuncIR:
    """A function, method, or ``__init__``."""

    name: str
    qualname: str
    signature: str
    description: str
    params: list[ParamIR] = field(default_factory=list)
    returns_type: str | None = None
    returns_desc: str = ""
    raises: list[tuple[str, str]] = field(default_factory=list)
    source_url: str = ""
    is_async: bool = False


@dataclass
class ClassIR:
    """A class. ``init`` holds the ``__init__`` as a ``FuncIR`` if defined."""

    name: str
    qualname: str
    description: str
    init: FuncIR | None = None
    methods: list[FuncIR] = field(default_factory=list)
    source_url: str = ""


@dataclass
class ModuleIR:
    """A module page. ``submodules`` lists qualnames of nested public modules."""

    name: str
    qualname: str
    description: str
    classes: list[ClassIR] = field(default_factory=list)
    functions: list[FuncIR] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
