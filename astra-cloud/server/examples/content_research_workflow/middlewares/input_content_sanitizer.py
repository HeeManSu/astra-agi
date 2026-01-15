"""
Input Content Sanitizer Middleware.

Sanitizes input content by removing HTML tags, normalizing whitespace,
and validating input length.
"""

import re
from typing import Any

from framework.middlewares import InputMiddleware, MiddlewareContext


class InputContentSanitizer(InputMiddleware):
    """
    Sanitizes input content by removing HTML tags, normalizing whitespace,
    and validating input length.
    """

    def __init__(self, max_length: int = 100000):
        """
        Initialize input sanitizer.

        Args:
            max_length: Maximum allowed input length (default: 100000)
        """
        self.max_length = max_length

    async def process(
        self, messages: list[dict[str, Any]], context: MiddlewareContext
    ) -> list[dict[str, Any]]:
        """
        Sanitize input messages.

        Args:
            messages: List of message dicts
            context: Middleware context

        Returns:
            Sanitized messages
        """
        sanitized = []

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Remove HTML tags
                content = re.sub(r"<[^>]+>", "", content)

                # Normalize whitespace
                content = re.sub(r"\s+", " ", content)
                content = content.strip()

                # Validate length
                if len(content) > self.max_length:
                    content = content[: self.max_length] + "... [truncated]"

                # Update message
                sanitized_msg = msg.copy()
                sanitized_msg["content"] = content
                sanitized.append(sanitized_msg)
            else:
                sanitized.append(msg)

        return sanitized
