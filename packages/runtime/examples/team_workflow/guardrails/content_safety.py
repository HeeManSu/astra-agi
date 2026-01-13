"""
Content Safety Guardrail.

Blocks harmful content and filters inappropriate language.
Prevents misinformation markers and ensures content safety.
"""

from typing import Any

from framework.guardrails import OutputGuardrail
from framework.guardrails.exceptions import OutputGuardrailError
from framework.middlewares import MiddlewareContext


class ContentSafetyGuardrail(OutputGuardrail):
    """
    Blocks harmful content and filters inappropriate language.
    Prevents misinformation markers and ensures content safety.
    """

    def __init__(
        self,
        blocklist: list[str] | None = None,
        strict_mode: bool = False,
    ):
        """
        Initialize content safety guardrail.

        Args:
            blocklist: List of words/phrases to block (default: common harmful terms)
            strict_mode: If True, blocks more aggressively (default: False)
        """
        # Default blocklist for harmful content
        self.blocklist = blocklist or [
            # Harmful content markers
            "kill yourself",
            "harm yourself",
            "illegal activities",
            # Misinformation markers (can be expanded)
            "proven false",
            "debunked",
            "hoax",
        ]

        # Extended blocklist for strict mode
        if strict_mode:
            self.blocklist.extend(
                [
                    "hate speech",
                    "discrimination",
                    "violence",
                ]
            )

        self.strict_mode = strict_mode

    async def validate(self, output: Any, context: MiddlewareContext) -> bool:
        """
        Validate output content.

        Args:
            output: ModelResponse or string to validate
            context: Middleware context

        Returns:
            True if valid

        Raises:
            OutputGuardrailError: If harmful content is detected
        """
        # Extract content
        content = ""
        if hasattr(output, "content"):
            content = output.content or ""
        elif isinstance(output, str):
            content = output
        else:
            return True

        content_lower = content.lower()

        # Check against blocklist
        for blocked_term in self.blocklist:
            if blocked_term.lower() in content_lower:
                raise OutputGuardrailError(
                    f"Content safety guardrail triggered: detected potentially harmful content "
                    f"('{blocked_term}'). Please revise your request."
                )

        # Additional checks in strict mode
        if self.strict_mode:
            # Check for excessive caps (potential spam/shouting)
            if len([c for c in content if c.isupper()]) > len(content) * 0.5 and len(content) > 50:
                raise OutputGuardrailError(
                    "Content safety guardrail triggered: excessive capitalization detected. "
                    "Please use normal capitalization."
                )

        return True

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        """
        Process output (validates and returns).

        Args:
            response: ModelResponse or string
            context: Middleware context

        Returns:
            Response if valid

        Raises:
            OutputGuardrailError: If validation fails
        """
        await self.validate(response, context)
        return response
