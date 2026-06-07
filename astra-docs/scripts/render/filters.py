"""Visibility filters.

A symbol is "public" for documentation purposes when:
  * its name does not start with ``_`` (with the dunder allow-list below), AND
  * it is not marked ``@deprecated``, AND
  * if a parent module defines ``__all__``, the symbol is in it.

``__init__`` and a small set of useful dunders are always kept on classes.
"""

from __future__ import annotations

from typing import Iterable

# Dunders we want to surface even though they start with an underscore.
_ALLOWED_DUNDERS: frozenset[str] = frozenset(
    {
        "__init__",
        "__call__",
        "__iter__",
        "__aiter__",
        "__next__",
        "__anext__",
        "__enter__",
        "__exit__",
        "__aenter__",
        "__aexit__",
        "__len__",
        "__getitem__",
        "__contains__",
    }
)


def is_private_name(name: str) -> bool:
    """Return ``True`` for names we should hide.

    Hidden:
      * Leading underscore (``_foo``, ``_Helper``), unless it is in
        :data:`_ALLOWED_DUNDERS`.
    """

    if not name.startswith("_"):
        return False
    return name not in _ALLOWED_DUNDERS


def is_deprecated(obj: object) -> bool:
    """Return ``True`` if the griffe object is marked deprecated.

    Recognises ``@deprecated`` decorator names and a ``deprecated`` label
    that griffe attaches when it sees one.
    """

    labels = getattr(obj, "labels", None) or set()
    if "deprecated" in labels:
        return True
    decorators = getattr(obj, "decorators", None) or []
    for dec in decorators:
        name = getattr(dec, "value", "") or ""
        if "deprecated" in str(name).lower():
            return True
    return False


def in_public_api(name: str, all_list: Iterable[str] | None) -> bool:
    """If ``__all__`` is defined, only its entries are public; else infer.

    When ``all_list`` is ``None`` the module did not declare ``__all__`` and
    we fall back to "non-underscore is public".
    """

    if all_list is None:
        return not is_private_name(name)
    return name in set(all_list)


def should_render(obj: object, all_list: Iterable[str] | None = None) -> bool:
    """Composite predicate: keep iff public name, not deprecated, in __all__."""

    name = getattr(obj, "name", "")
    if is_private_name(name):
        return False
    if is_deprecated(obj):
        return False
    if not in_public_api(name, all_list):
        return False
    return True
