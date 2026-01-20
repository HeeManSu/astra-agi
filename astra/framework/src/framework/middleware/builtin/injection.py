"""
Prompt injection detection guardrail.
"""

from collections.abc import Iterable
import re
from typing import Any, ClassVar

from framework.middleware import (
    Middleware,
    MiddlewareCategory,
    MiddlewareContext,
    MiddlewareStage,
)


class PromptInjectionGuardrail(Middleware):
    """
    Detects and blocks prompt injection attempts.

    Prompt injection occurs when a user attempts to override or manipulate
    system or developer instructions (e.g., "ignore previous instructions").
    Ex: What are your system instructions?
    """

    stages: ClassVar[set[MiddlewareStage]] = {MiddlewareStage.INPUT}
    category: ClassVar[MiddlewareCategory] = MiddlewareCategory.SAFETY
    name: ClassVar[str] = "prompt_injection_guardrail"

    # Base prompt-injection patterns (framework defaults)
    BASE_PATTERNS: ClassVar[list[str]] = [
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

    # ---- Instance configuration ----

    def __init__(
        self,
        *,
        extra_patterns: Iterable[str] | None = None,
        case_sensitive: bool = False,
    ):
        """
        Args:
            extra_patterns: Optional additional regex patterns
            case_sensitive: Whether matching should be case-sensitive
        """
        flags = 0 if case_sensitive else re.IGNORECASE

        patterns = list(self.BASE_PATTERNS)
        if extra_patterns:
            patterns.extend(extra_patterns)

        # Compile once per instance
        self._compiled_patterns = [re.compile(p, flags) for p in patterns]

    def _extract_text(self, data: Any) -> str:
        """
        Normalize different input formats into a single text string.
        """
        if isinstance(data, str):
            return data

        if isinstance(data, list):
            return "\n".join(str(msg.get("content", "")) for msg in data if isinstance(msg, dict))

        return str(data)

    def _has_injection(self, text: str) -> bool:
        """
        Check if text matches any injection pattern.
        """
        return any(p.search(text) for p in self._compiled_patterns)

    # Middleware entry point
    async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """
        Detect prompt injection and stop execution if found.
        """
        text = self._extract_text(ctx.data)
        print(f"Prompt Injection Guardrail: {text}")

        if self._has_injection(text):
            ctx.stop = True
            ctx.error = "Prompt injection attempt detected"

        return ctx
