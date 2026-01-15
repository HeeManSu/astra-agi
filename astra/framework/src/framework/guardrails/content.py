"""
Content safety and moderation filter.
"""

from enum import Enum
import re
from typing import Any

from framework.guardrails.base import InputGuardrail, OutputGuardrail
from framework.guardrails.exceptions import InputGuardrailError, OutputGuardrailError
from framework.middlewares import MiddlewareContext


class ContentAction(str, Enum):
    """Action to take when unsafe content is detected."""

    BLOCK = "block"
    REDACT = "redact"


class ContentBase:
    """Base logic for content filtering."""

    def __init__(
        self,
        blocklist: list[str] | None = None,
        allowlist: list[str] | None = None,
        action: ContentAction = ContentAction.BLOCK,
        case_sensitive: bool = False,
    ):
        self.blocklist = set(blocklist or [])
        self.allowlist = set(allowlist or [])
        self.action = action
        self.case_sensitive = case_sensitive

        # Compile blocklist patterns (simple word boundaries)
        flags = 0 if case_sensitive else re.IGNORECASE
        self.compiled_patterns = [
            re.compile(rf"\b{re.escape(word)}\b", flags) for word in self.blocklist
        ]

    def _check_text(self, text: str) -> tuple[bool, str]:
        """
        Check text for unsafe content.
        Returns: (found_unsafe, processed_text)
        """
        found = False
        processed = text

        for pattern in self.compiled_patterns:
            if pattern.search(processed):
                found = True
                if self.action == ContentAction.BLOCK:
                    return True, text
                elif self.action == ContentAction.REDACT:
                    processed = pattern.sub("[UNSAFE]", processed)

        return found, processed


class InputContentFilter(InputGuardrail, ContentBase):
    """
    Filters unsafe content in user input.

    This guardrail checks user messages against a blocklist of forbidden words/phrases
    or an allowlist of permitted terms. It can be used for basic content moderation,
    profanity filtering, or topic restriction.

    Example:
        ```python
        # Block messages containing "unsafe"
        agent = Agent(input_middlewares=[InputContentFilter(blocklist=["unsafe"])])
        ```
    """

    def __init__(
        self,
        blocklist: list[str] | None = None,
        allowlist: list[str] | None = None,
        action: ContentAction = ContentAction.BLOCK,
        case_sensitive: bool = False,
    ):
        ContentBase.__init__(self, blocklist, allowlist, action, case_sensitive)

    async def validate(self, messages: list[dict[str, Any]], context: MiddlewareContext) -> bool:
        for msg in messages:
            content = str(msg.get("content", ""))
            found, _ = self._check_text(content)

            if found and self.action == ContentAction.BLOCK:
                raise InputGuardrailError("Unsafe content detected in input")

        return True

    async def process(
        self, messages: list[dict[str, Any]], context: MiddlewareContext
    ) -> list[dict[str, Any]]:
        if self.action == ContentAction.BLOCK:
            await self.validate(messages, context)
            return messages

        for msg in messages:
            content = str(msg.get("content", ""))
            _, processed = self._check_text(content)
            msg["content"] = processed

        return messages


class OutputContentFilter(OutputGuardrail, ContentBase):
    """
    Filters unsafe content in agent output.

    This guardrail checks the agent's response against a blocklist of forbidden words/phrases
    or an allowlist of permitted terms. It ensures the agent does not generate
    inappropriate or restricted content.

    Example:
        ```python
        # Redact "internal_only" from output
        agent = Agent(
            output_middlewares=[
                OutputContentFilter(blocklist=["internal_only"], action=ContentAction.REDACT)
            ]
        )
        ```
    """

    def __init__(
        self,
        blocklist: list[str] | None = None,
        allowlist: list[str] | None = None,
        action: ContentAction = ContentAction.BLOCK,
        case_sensitive: bool = False,
    ):
        ContentBase.__init__(self, blocklist, allowlist, action, case_sensitive)

    async def validate(self, output: Any, context: MiddlewareContext) -> bool:
        content = ""
        if hasattr(output, "content"):
            content = output.content or ""
        elif isinstance(output, str):
            content = output
        else:
            return True

        found, _ = self._check_text(content)

        if found and self.action == ContentAction.BLOCK:
            raise OutputGuardrailError("Unsafe content detected in output")

        return True

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        if self.action == ContentAction.BLOCK:
            await self.validate(response, context)
            return response

        if hasattr(response, "content") and response.content:
            _, processed = self._check_text(response.content)
            response.content = processed
        elif isinstance(response, str):
            _, processed = self._check_text(response)
            return processed

        return response
