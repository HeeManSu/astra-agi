"""
Output Formatter Middleware.

Formats output by cleaning up markdown, normalizing spacing,
and ensuring proper structure.
"""

import re
from typing import Any

from framework.middlewares import MiddlewareContext, OutputMiddleware
from framework.models import ModelResponse


class OutputFormatter(OutputMiddleware):
    """
    Formats output by cleaning up markdown, normalizing spacing,
    and ensuring proper structure.
    """

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        """
        Format output response.

        Args:
            response: ModelResponse or string
            context: Middleware context

        Returns:
            Formatted response
        """
        if isinstance(response, ModelResponse):
            if response.content:
                content = response.content

                # Normalize line breaks
                content = re.sub(r"\n{3,}", "\n\n", content)

                # Fix spacing around headings
                content = re.sub(r"\n(#{1,6})\s+", r"\n\n\1 ", content)

                # Ensure proper spacing after headings
                content = re.sub(r"(#{1,6}\s+.+)\n([^\n#])", r"\1\n\n\2", content)

                # Clean up excessive spaces
                content = re.sub(r" +", " ", content)

                # Update response
                response.content = content.strip()

        elif isinstance(response, str):
            # Apply same formatting to string
            content = response
            content = re.sub(r"\n{3,}", "\n\n", content)
            content = re.sub(r"\n(#{1,6})\s+", r"\n\n\1 ", content)
            content = re.sub(r"(#{1,6}\s+.+)\n([^\n#])", r"\1\n\n\2", content)
            content = re.sub(r" +", " ", content)
            return content.strip()

        return response
