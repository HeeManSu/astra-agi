"""
Custom middlewares for Market Research Agent.
"""

from framework.middleware import MiddlewareCategory, MiddlewareContext, MiddlewareStage, middleware


@middleware(
    stages=[MiddlewareStage.INPUT],
    category=MiddlewareCategory.FORMATTING,
    name="spoon_to_kitchen",
)
async def spoon_to_kitchen(ctx: MiddlewareContext) -> MiddlewareContext:
    """INPUT: Replaces 'spoon' with 'kitchen' in user input."""
    if isinstance(ctx.data, str):
        ctx.data = ctx.data.replace("spoon", "kitchen").replace("Spoon", "Kitchen")
    return ctx


@middleware(
    stages=[MiddlewareStage.OUTPUT],
    category=MiddlewareCategory.FORMATTING,
    name="executive_replacer",
)
async def executive_replacer(ctx: MiddlewareContext) -> MiddlewareContext:
    """OUTPUT: Replaces 'executive' with 'non-executive' in output."""
    if isinstance(ctx.data, str):
        ctx.data = ctx.data.replace("executive", "non-executive").replace(
            "Executive", "Non-Executive"
        )
    return ctx
