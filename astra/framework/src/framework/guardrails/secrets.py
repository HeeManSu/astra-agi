"""
Secret leakage detection filter.
"""

from enum import Enum
import re
from typing import Any, ClassVar

from framework.guardrails.base import OutputGuardrail
from framework.guardrails.exceptions import OutputGuardrailError
from framework.middlewares import MiddlewareContext


class SecretAction(str, Enum):
    """Action to take when secret is detected."""

    BLOCK = "block"
    REDACT = "redact"


class SecretLeakageFilter(OutputGuardrail):
    """
    Detects and blocks/redacts secrets in agent output.

    This guardrail scans the agent's output for potential secret leakage, including
    API keys (OpenAI, AWS, Google, GitHub, Slack) and private keys. It helps prevent
    accidental exposure of sensitive credentials.

    Example:
        ```python
        # Block secrets in output
        agent = Agent(output_middlewares=[SecretLeakageFilter(action=SecretAction.BLOCK)])
        ```
    """

    # Regex patterns for common secrets
    PATTERNS: ClassVar[dict[str, str]] = {
        "openai_key": r"sk-[a-zA-Z0-9]{48}",
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret_key": r"[0-9a-zA-Z/+]{40}",
        "google_api_key": r"AIza[0-9A-Za-z-_]{35}",
        "github_token": r"gh[pousr]_[a-zA-Z0-9]{36}",
        "slack_token": r"xox[baprs]-([0-9a-zA-Z]{10,48})?",
        "private_key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
    }

    def __init__(
        self,
        action: SecretAction = SecretAction.BLOCK,
        custom_patterns: dict[str, str] | None = None,
    ):
        """
        Initialize secret filter.

        Args:
            action: Action to take (BLOCK or REDACT)
            custom_patterns: Dict of {name: regex} for additional secrets
        """
        self.action = action
        self.patterns = self.PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

        self.compiled_patterns = {
            name: re.compile(pattern) for name, pattern in self.patterns.items()
        }

    def _check_text(self, text: str) -> tuple[bool, str]:
        """
        Check text for secrets.
        Returns: (found_secret, processed_text)
        """
        found = False
        processed = text

        for name, pattern in self.compiled_patterns.items():
            if pattern.search(processed):
                found = True
                if self.action == SecretAction.BLOCK:
                    return True, text
                elif self.action == SecretAction.REDACT:
                    processed = pattern.sub(f"[REDACTED: {name.upper()}]", processed)

        return found, processed

    async def validate(self, output: Any, context: MiddlewareContext) -> bool:
        """Validate output."""
        content = ""
        if hasattr(output, "content"):
            content = output.content or ""
        elif isinstance(output, str):
            content = output
        else:
            return True

        found, _ = self._check_text(content)

        if found and self.action == SecretAction.BLOCK:
            raise OutputGuardrailError("Secret detected in output")

        return True

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        """Process output (redact if configured)."""
        if self.action == SecretAction.BLOCK:
            await self.validate(response, context)
            return response

        if hasattr(response, "content") and response.content:
            _, processed = self._check_text(response.content)
            response.content = processed
        elif isinstance(response, str):
            _, processed = self._check_text(response)
            return processed

        return response
