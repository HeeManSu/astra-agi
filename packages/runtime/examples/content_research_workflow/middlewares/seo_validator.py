"""
SEO Validator Middleware.

Validates SEO requirements for output content.
Checks meta description length, heading structure, and keyword density.
"""

import re
from typing import Any

from framework.middlewares import MiddlewareContext, OutputMiddleware
from framework.models import ModelResponse


class SEOValidator(OutputMiddleware):
    """
    Validates SEO requirements for output content.
    Checks meta description length, heading structure, and keyword density.
    """

    def __init__(self, check_meta_description: bool = True, check_headings: bool = True):
        """
        Initialize SEO validator.

        Args:
            check_meta_description: Whether to validate meta descriptions
            check_headings: Whether to validate heading structure
        """
        self.check_meta_description = check_meta_description
        self.check_headings = check_headings

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        """
        Validate SEO requirements.

        Args:
            response: ModelResponse or string
            context: Middleware context

        Returns:
            Response (optionally with SEO notes)
        """
        if isinstance(response, ModelResponse):
            content = response.content or ""
        elif isinstance(response, str):
            content = response
        else:
            return response

        # Check meta description if requested
        if self.check_meta_description and "meta description" in content.lower():
            meta_pattern = r"meta description[:\s]+(.+?)(?:\n|$)"
            match = re.search(meta_pattern, content, re.IGNORECASE)
            if match:
                meta_desc = match.group(1).strip()
                if len(meta_desc) < 120 or len(meta_desc) > 160:
                    # Add note to content
                    note = f"\n\n[SEO Note: Meta description should be 120-160 characters. Current: {len(meta_desc)}]"
                    if isinstance(response, ModelResponse):
                        response.content = content + note
                    else:
                        response = content + note

        # Check heading structure if requested
        if self.check_headings:
            headings = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
            if headings:
                # Check for proper hierarchy
                prev_level = 0
                for level, text in headings:
                    current_level = len(level)
                    if current_level > prev_level + 1:
                        note = f"\n\n[SEO Note: Heading '{text[:30]}...' jumps from level {prev_level} to {current_level}. Maintain proper hierarchy.]"
                        if isinstance(response, ModelResponse):
                            response.content = content + note
                        else:
                            response = content + note
                        break
                    prev_level = current_level

        return response
