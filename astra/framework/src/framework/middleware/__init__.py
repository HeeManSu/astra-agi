"""
Astra Middleware System.

Provides a unified pipeline for input/output processing with:
- Explicit stages (INPUT, OUTPUT)
- Semantic categories (SAFETY, VALIDATION, etc.)
- Guardrails as safety-focused middleware

Usage:
```python
from framework.middleware import (
    Middleware,
    MiddlewareContext,
    MiddlewareStage,
    MiddlewareCategory,
    middleware,
    run_middlewares,
)


# Using decorator
@middleware(stages=[MiddlewareStage.INPUT], category=MiddlewareCategory.LOGGING)
async def log_input(ctx):
    print(ctx.data)
    return ctx


# Using class
class MyGuardrail(Middleware):
    stages = {MiddlewareStage.INPUT}
    category = MiddlewareCategory.SAFETY

    async def run(self, ctx):
        # validate ctx.data
        return ctx
```
"""

from framework.middleware.base import (
    Middleware,
    MiddlewareContext,
    MiddlewareError,
    middleware,
    run_middlewares,
)
from framework.middleware.enums import MiddlewareCategory, MiddlewareStage


__all__ = [
    "Middleware",
    "MiddlewareCategory",
    "MiddlewareContext",
    "MiddlewareError",
    "MiddlewareStage",
    "middleware",
    "run_middlewares",
]
