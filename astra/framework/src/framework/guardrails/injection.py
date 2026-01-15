"""
Prompt injection detection filter.
"""

import re
from typing import ClassVar

from framework.guardrails.base import InputGuardrail
from framework.guardrails.exceptions import InputGuardrailError
from framework.middlewares import MiddlewareContext


class PromptInjectionFilter(InputGuardrail):
    """
    Detects and blocks prompt injection attempts.

    Prompt injection is when users try to manipulate the agent by injecting
    instructions into their input (e.g., "Ignore previous instructions and...").

    Example:
        ```python
        agent = Agent(
            name="SafeAgent", model=Gemini("1.5-flash"), input_middlewares=[PromptInjectionFilter()]
        )
        ```
    """

    # Common prompt injection patterns
    INJECTION_PATTERNS: ClassVar[list[str]] = [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"forget\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"new\s+instructions?:",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"act\s+as\s+(if\s+)?you\s+are",
        r"pretend\s+(to\s+be|you\s+are)",
        r"roleplay\s+as",
        r"simulate\s+(being|a)",
        r"override\s+your",
        r"bypass\s+your",
        r"reveal\s+your\s+(system|instructions|prompt)",
        r"what\s+(are|is)\s+your\s+(system|instructions|prompt)",
    ]

    def __init__(self, custom_patterns: list[str] | None = None, case_sensitive: bool = False):
        """
        Initialize prompt injection detector.

        Args:
            custom_patterns: Additional regex patterns to check
            case_sensitive: Whether pattern matching is case-sensitive
        """
        self.patterns = self.INJECTION_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)

        self.case_sensitive = case_sensitive

        # Compile patterns
        flags = 0 if case_sensitive else re.IGNORECASE
        self.compiled_patterns = [re.compile(pattern, flags) for pattern in self.patterns]

    def _is_injection_attempt(self, text: str) -> bool:
        """Check if text contains injection patterns."""
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        return False

    async def validate(self, messages: list[dict[str, str]], context: MiddlewareContext) -> bool:
        """
        Validate that input doesn't contain prompt injection attempts.

        Raises:
            InputGuardrailError: If injection attempt detected
        """
        for msg in messages:
            content = str(msg.get("content", ""))
            if self._is_injection_attempt(content):
                raise InputGuardrailError(
                    f"Prompt injection attempt detected in message: {content[:100]}..."
                )

        return True
