"""Token counting utility for conversation buffer.

Implements token counting:
- Uses tiktoken for accurate counting
- Includes message overhead (TOKENS_PER_MESSAGE)
- Includes conversation overhead (TOKENS_PER_CONVERSATION)
- Falls back to character-based estimation if tiktoken unavailable
"""

from typing import Any

import tiktoken


class TokenCounter:
    """
    Token counter with caching.

    Features:
    - Accurate token counting using tiktoken
    - Message overhead calculation (3.8 tokens per message)
    - Conversation overhead (24 tokens per conversation)
    - Caching for performance
    - Fallback to character-based estimation
    """

    TOKENS_PER_MESSAGE = 3.8  # Overhead per message
    TOKENS_PER_CONVERSATION = 24  # Overhead for conversation

    def __init__(self, encoding: str = "cl100k_base"):
        """
        Initialize token counter.

        Args:
            encoding: Tokenizer encoding (default: cl100k_base for GPT-4/3.5)
        """
        self.encoding = encoding
        self._encoder = None
        self._cache: dict[str, int] = {}

        if tiktoken is not None:
            try:
                self._encoder = tiktoken.get_encoding(self.encoding)
            except Exception:
                self._encoder = None

    def count(self, text: str) -> int:
        """
        Count tokens in text (with caching).

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if text in self._cache:
            return self._cache[text]

        if self._encoder is not None:
            tokens = len(self._encoder.encode(text))
        else:
            # Fallback: character-based estimation (1 token = 4 chars)
            tokens = len(text) // 4

        self._cache[text] = tokens
        return tokens

    def count_message(self, message: dict[str, Any]) -> int:
        """
        Count tokens in a message.

        Includes:
        - Content tokens
        - Role tokens
        - Message overhead (TOKENS_PER_MESSAGE)

        Args:
            message: Message dict with 'role' and 'content'

        Returns:
            Token count including overhead
        """
        # Extract role and content
        role = message.get("role", "")
        content = message.get("content", "")

        token_string = role + str(content)

        content_tokens = self.count(token_string)

        # Add message overhead
        total_tokens = content_tokens + int(self.TOKENS_PER_MESSAGE)

        return total_tokens

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """
        Count total tokens in a list of messages.

        Includes:
        - All message tokens
        - Message overhead per message
        - Conversation overhead (once per conversation)

        Args:
            messages: List of message dicts

        Returns:
            Total token count including all overhead
        """
        if not messages:
            return 0

        message_tokens = sum(self.count_message(msg) for msg in messages)

        total_tokens = message_tokens + int(self.TOKENS_PER_CONVERSATION)

        return total_tokens

    def count_input_messages(
        self, messages: list[dict[str, Any]], include_conversation_overhead: bool = True
    ) -> int:
        """
        Count tokens for input messages (used for context window limiting).

        This is the method used by MemoryManager to check if messages fit within token limit.

        Args:
            messages: List of message dicts
            include_conversation_overhead: Whether to include conversation overhead

        Returns:
            Total token count
        """
        if not messages:
            return 0

        message_tokens = sum(self.count_message(msg) for msg in messages)

        if include_conversation_overhead:
            total_tokens = message_tokens + int(self.TOKENS_PER_CONVERSATION)
        else:
            total_tokens = message_tokens

        return total_tokens
