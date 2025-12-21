from __future__ import annotations

import functools
import logging
from typing import Callable, Any, Awaitable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

try:
    import wrapt  # type: ignore
except Exception:  # pragma: no cover
    wrapt = None


def wrap_function(func: F, wrapper: Callable[..., Any]) -> F:
    if wrapt is not None:
        return wrapt.FunctionWrapper(func, wrapper)  # type: ignore[return-value]
    @functools.wraps(func)
    def _wrapped(*args, **kwargs):
        return wrapper(func, args, kwargs)
    return _wrapped  # type: ignore[return-value]


def wrap_method(func: F, wrapper: Callable[..., Any]) -> F:
    return wrap_function(func, wrapper)


def wrap_async_function(func: F, wrapper: Callable[..., Awaitable[Any]]) -> F:
    if wrapt is not None:
        return wrapt.FunctionWrapper(func, wrapper)  # type: ignore[return-value]

    async def _wrapped(*args, **kwargs):
        return await wrapper(func, args, kwargs)
    return functools.wraps(func)(_wrapped)  # type: ignore[return-value]

