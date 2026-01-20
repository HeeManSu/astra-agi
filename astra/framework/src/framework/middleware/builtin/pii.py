"""
PII detection and redaction guardrail.
"""

from enum import Enum
import re
from typing import Any, ClassVar

from framework.middleware import (
    Middleware,
    MiddlewareCategory,
    MiddlewareContext,
    MiddlewareStage,
)


class PIIAction(str, Enum):
    """Action to take when PII is detected."""

    BLOCK = "block"
    REDACT = "redact"


class PIIGuardrail(Middleware):
    """
    Detects and handles Personally Identifiable Information (PII)
    in input and/or output.

    Supported PII types:
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - SSNs

    Behavior:
    - BLOCK  → stop execution if PII is found
    - REDACT → replace detected PII with placeholders
    """

    stages: ClassVar[set[MiddlewareStage]] = {MiddlewareStage.INPUT, MiddlewareStage.OUTPUT}
    category: ClassVar[MiddlewareCategory] = MiddlewareCategory.SAFETY
    name: ClassVar[str] = "pii_guardrail"

    # Regex patterns for common PII (reasonably strict, low false positives)
    PATTERNS: ClassVar[dict[str, str]] = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "phone": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    }

    def __init__(
        self,
        *,
        action: PIIAction = PIIAction.REDACT,
        types: list[str] | None = None,
        stages: set[MiddlewareStage] | None = None,
    ):
        """
        Args:
            action: BLOCK to reject, REDACT to mask PII
            types: Subset of PII types to detect (defaults to all)
            stages: Override default execution stages
        """
        self.action = action
        self.types = types or list(self.PATTERNS.keys())

        # Store effective stages (allows per-instance override)
        self._effective_stages = stages if stages else self.__class__.stages

        self.compiled_patterns: dict[str, re.Pattern] = {
            name: re.compile(pattern)
            for name, pattern in self.PATTERNS.items()
            if name in self.types
        }

    # Detection
    def _detect_pii(self, text: str) -> set[str]:
        """Return the set of detected PII types in the text."""
        detected: set[str] = set()
        for name, pattern in self.compiled_patterns.items():
            if pattern.search(text):
                detected.add(name)
        return detected

    # Transformation
    def _redact(self, text: str, detected: set[str]) -> str:
        """Redact detected PII types from text."""
        for name in detected:
            pattern = self.compiled_patterns[name]
            text = pattern.sub(f"[REDACTED:{name.upper()}]", text)
        return text

    # Data extraction / update helpers
    def _extract_text(self, data: Any) -> str:
        """Extract text from common data shapes."""
        if isinstance(data, str):
            return data

        if isinstance(data, list):
            # Message list (OpenAI / chat style)
            parts = [str(msg.get("content", "")) for msg in data if isinstance(msg, dict)]
            return "\n".join(parts)

        if hasattr(data, "content"):
            return str(getattr(data, "content", ""))

        return str(data)

    def _update_data(self, data: Any, processed: str) -> Any:
        """Write redacted text back into the original data shape."""
        if isinstance(data, str):
            return processed

        if isinstance(data, list):
            # Update most recent user message
            for msg in reversed(data):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    msg["content"] = processed
                    break
            return data

        if hasattr(data, "content"):
            data.content = processed
            return data

        return processed

    # ---------------------------------------------------------------------
    # Middleware entry point
    # ---------------------------------------------------------------------

    async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """
        Execute PII detection and handling.

        Policy-first flow:
        1. Extract text
        2. Detect PII
        3. Apply action (block or redact)
        """
        text = self._extract_text(ctx.data)
        detected = self._detect_pii(text)

        if not detected:
            return ctx

        if self.action == PIIAction.BLOCK:
            ctx.reject("PII detected in message")
            return ctx

        # REDACT
        redacted = self._redact(text, detected)
        ctx.data = self._update_data(ctx.data, redacted)

        return ctx
