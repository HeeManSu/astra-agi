"""
PII detection and redaction filter.
"""

from enum import Enum
import re
from typing import Any, ClassVar

from framework.guardrails.base import InputGuardrail, OutputGuardrail
from framework.guardrails.exceptions import InputGuardrailError, OutputGuardrailError
from framework.middlewares import MiddlewareContext


class PIIAction(str, Enum):
    """Action to take when PII is detected."""

    BLOCK = "block"
    REDACT = "redact"


class PIIBase:
    """Base logic for PII detection."""

    # Regex patterns for common PII
    PATTERNS: ClassVar[dict[str, str]] = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(\+?1?[-.]?)?\(?[2-9]\d{2}\)?[-.]?\d{3}[-.]?\d{4}\b",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    }

    def __init__(self, action: PIIAction = PIIAction.REDACT, types: list[str] | None = None):
        self.action = action
        self.types = types or list(self.PATTERNS.keys())

        self.compiled_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.PATTERNS.items()
            if name in self.types
        }

    def _check_text(self, text: str) -> tuple[bool, str]:
        """
        Check text for PII.
        Returns: (found_pii, processed_text)
        """
        found = False
        processed = text

        for name, pattern in self.compiled_patterns.items():
            if pattern.search(processed):
                found = True
                if self.action == PIIAction.BLOCK:
                    return True, text
                elif self.action == PIIAction.REDACT:
                    processed = pattern.sub(f"[REDACTED: {name.upper()}]", processed)

        return found, processed


class InputPIIFilter(InputGuardrail, PIIBase):
    """
    Detects and handles PII in user input.

    This guardrail scans user messages for sensitive information like email addresses,
    phone numbers, credit card numbers, and SSNs. It can either block the message
    or redact the sensitive information before it reaches the model.

    Example:
        ```python
        # Redact PII in input
        agent = Agent(input_middlewares=[InputPIIFilter(action=PIIAction.REDACT)])
        ```
    """

    def __init__(self, action: PIIAction = PIIAction.REDACT, types: list[str] | None = None):
        PIIBase.__init__(self, action, types)

    async def validate(self, messages: list[dict[str, Any]], context: MiddlewareContext) -> bool:
        for msg in messages:
            content = str(msg.get("content", ""))
            found, _ = self._check_text(content)

            if found and self.action == PIIAction.BLOCK:
                raise InputGuardrailError("PII detected in input message")

        return True

    async def process(
        self, messages: list[dict[str, Any]], context: MiddlewareContext
    ) -> list[dict[str, Any]]:
        if self.action == PIIAction.BLOCK:
            await self.validate(messages, context)
            return messages

        for msg in messages:
            content = str(msg.get("content", ""))
            _, processed = self._check_text(content)
            msg["content"] = processed

        return messages


class OutputPIIFilter(OutputGuardrail, PIIBase):
    """
    Detects and handles PII in agent output.

    This guardrail scans the agent's response for sensitive information like email addresses,
    phone numbers, credit card numbers, and SSNs. It can either block the response
    or redact the sensitive information before it is returned to the user.

    Example:
        ```python
        # Block PII in output
        agent = Agent(output_middlewares=[OutputPIIFilter(action=PIIAction.BLOCK)])
        ```
    """

    def __init__(self, action: PIIAction = PIIAction.REDACT, types: list[str] | None = None):
        PIIBase.__init__(self, action, types)

    async def validate(self, output: Any, context: MiddlewareContext) -> bool:
        content = ""
        if hasattr(output, "content"):
            content = output.content or ""
        elif isinstance(output, str):
            content = output
        else:
            return True

        found, _ = self._check_text(content)

        if found and self.action == PIIAction.BLOCK:
            raise OutputGuardrailError("PII detected in output")

        return True

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        if self.action == PIIAction.BLOCK:
            await self.validate(response, context)
            return response

        if hasattr(response, "content") and response.content:
            _, processed = self._check_text(response.content)
            response.content = processed
        elif isinstance(response, str):
            _, processed = self._check_text(response)
            return processed

        return response
