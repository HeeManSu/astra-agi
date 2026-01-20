"""
Middleware base classes, context, decorator, and execution engine.

This module provides the core middleware abstractions:
- MiddlewareContext: Data carrier through the pipeline
- Middleware: Base class for all middlewares
- middleware: Decorator for creating middlewares from functions
- run_middlewares: Execution engine
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar

from framework.middleware.enums import MiddlewareCategory, MiddlewareStage


class MiddlewareContext:
    """
    Context object passed through the middleware pipeline.

    Attributes:
        data: The payload being processed (message or response)
        stage: The current execution stage (INPUT, OUTPUT, etc.)
        metadata: Shared state across middlewares
        stop: If True, short-circuit execution
        error: Error message if stopped
    """

    def __init__(
        self,
        data: Any,
        *,
        stage: MiddlewareStage | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.data = data
        self.stage = stage
        self.metadata = metadata or {}
        self.stop = False
        self.error: str | None = None

    def reject(self, message: str) -> None:
        """
        Stop pipeline execution with an error.

        Usage:
        ```python
        ctx.reject("PII detected")
        ```

        This is equivalent to:
        ```python
        ctx.stop = True
        ctx.error = "PII detected"
        ```
        """
        self.stop = True
        self.error = message


class Middleware(ABC):
    """
    Base class for all middlewares.

    Subclass this to create a middleware:

    ```python
    class MyMiddleware(Middleware):
        stages = {MiddlewareStage.INPUT}
        category = MiddlewareCategory.CUSTOM

        async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
            # Process ctx.data
            return ctx
    ```

    Attributes:
        stages: Class-level default stages this middleware runs in.
        category: Semantic category for grouping/observability.
        name: Optional name for debugging.

    Notes on `stages` and `effective_stages`:
        - `stages` is a ClassVar (class-level default, shared by all instances)
        - To allow per-instance override, store custom stages in `_effective_stages`
        - The `effective_stages` property returns `_effective_stages` if set,
          otherwise falls back to the class-level `stages`

        Example allowing per-instance override:
        ```python
        class MyGuardrail(Middleware):
            stages = {MiddlewareStage.INPUT}  # Default

            def __init__(self, stages=None):
                # Allow caller to override stages
                self._effective_stages = stages if stages else self.__class__.stages
        ```
    """

    # Class-level default stages (which execution stages this middleware runs in)
    # Subclasses should override this. To allow per-instance override, set
    # `_effective_stages` in __init__ and use the `effective_stages` property.
    stages: ClassVar[set[MiddlewareStage]] = set()

    # Semantic category for grouping/filtering (does NOT affect execution order)
    category: MiddlewareCategory = MiddlewareCategory.CUSTOM

    # Optional name for debugging/logging
    name: str | None = None

    @property
    def effective_stages(self) -> set[MiddlewareStage]:
        """
        Get the effective stages this middleware instance runs in.

        Returns `_effective_stages` if the instance has it set (allowing
        per-instance customization), otherwise returns the class-level `stages`.

        This pattern allows:
        - Class-level defaults via `stages` ClassVar
        - Per-instance override via `_effective_stages` instance attribute
        - Linter-friendly code (ClassVar satisfies Pyright/Ruff)
        """
        return getattr(self, "_effective_stages", self.__class__.stages)

    @abstractmethod
    async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """
        Process the context.

        Args:
            ctx: The middleware context

        Returns:
            The (potentially modified) context
        """


def middleware(
    *,
    stages: list[MiddlewareStage] | set[MiddlewareStage],
    category: MiddlewareCategory = MiddlewareCategory.CUSTOM,
    name: str | None = None,
) -> Callable[[Callable], Middleware]:
    """
    Decorator to create a middleware from a function.

    Usage:
    ```python
    @middleware(stages=[MiddlewareStage.INPUT], category=MiddlewareCategory.LOGGING)
    async def log_input(ctx):
        print(f"Input: {ctx.data}")
        return ctx
    ```

    For configurable middleware, use a factory:
    ```python
    def pii_guardrail(mode="mask"):
        @middleware(stages=[MiddlewareStage.INPUT], category=MiddlewareCategory.SAFETY)
        async def _pii(ctx):
            if mode == "reject" and has_pii(ctx.data):
                ctx.stop = True
                ctx.error = "PII detected"
            else:
                ctx.data = mask_pii(ctx.data)
            return ctx

        return _pii
    ```
    """
    # Capture outer variables with different names to avoid shadowing
    _stages = set(stages) if isinstance(stages, list) else stages
    _category = category
    _name = name

    def decorator(fn: Callable) -> Middleware:
        class FnMiddleware(Middleware):
            stages = _stages
            category = _category
            name = _name or fn.__name__

            async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
                return await fn(ctx)

        # Store reference to original function
        FnMiddleware._fn = fn  # type: ignore

        return FnMiddleware()

    return decorator


async def run_middlewares(
    middlewares: list[Middleware],
    stage: MiddlewareStage,
    ctx: MiddlewareContext,
) -> MiddlewareContext:
    """
    Execute middlewares for a given stage.

    Args:
        middlewares: List of middleware instances
        stage: The stage to run (INPUT or OUTPUT)
        ctx: The context to process

    Returns:
        The processed context
    """
    # Set stage on context for debugging/logging
    ctx.stage = stage

    for mw in middlewares:
        if stage in mw.effective_stages:
            ctx = await mw.run(ctx)
            if ctx.stop:
                break
    return ctx


class MiddlewareError(Exception):
    """Raised when a middleware stops execution with an error."""

    def __init__(self, message: str, middleware_name: str | None = None):
        self.middleware_name = middleware_name
        super().__init__(message)
