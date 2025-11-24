"""
Output formatting middlewares.
"""
from ..base import OutputMiddleware
from ..context import MiddlewareContext


class TrimWhitespaceMiddleware(OutputMiddleware):
    """
    Trims leading/trailing whitespace from output.
    
    Example:
        ```python
        agent = Agent(
            name="CleanAgent",
            model=Gemini("1.5-flash"),
            output_middlewares=[TrimWhitespaceMiddleware()]
        )
        ```
    """
    
    async def process(
        self,
        output: str,
        context: MiddlewareContext
    ) -> str:
        """Trim whitespace."""
        return output.strip()


class OutputLengthLimiter(OutputMiddleware):
    """
    Limits output length by truncating.
    
    Example:
        ```python
        agent = Agent(
            name="BriefAgent",
            model=Gemini("1.5-flash"),
            output_middlewares=[OutputLengthLimiter(max_length=1000)]
        )
        ```
    """
    
    def __init__(self, max_length: int = 5000, suffix: str = "..."):
        """
        Initialize limiter.
        
        Args:
            max_length: Maximum output length
            suffix: Suffix to add when truncated
        """
        self.max_length = max_length
        self.suffix = suffix
    
    async def process(
        self,
        output: str,
        context: MiddlewareContext
    ) -> str:
        """Limit output length."""
        if len(output) > self.max_length:
            return output[:self.max_length - len(self.suffix)] + self.suffix
        return output
