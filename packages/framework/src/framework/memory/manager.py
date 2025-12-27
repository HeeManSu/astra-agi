from typing import Any

from framework.memory.memory import AgentMemory
from framework.memory.token_counter import TokenCounter
from framework.models import Model
from framework.storage.memory import AgentStorage


class MemoryManager:
    """
    Manages short-term conversation history.

    Features:
    - Token-aware windowing (primary) or message count (fallback)
    - Automatic overflow handling with summarization
    - System message filtering
    - Efficient message trimming
    """

    def __init__(self, memory: AgentMemory, model: Model):
        """
        Initialize memory manager.

        Args:
            memory: Memory configuration
            model: Model instance for summarization
        """
        self.memory = memory
        self.model = model
        self._summary_cache: dict[str, str] = {}  # Cache summaries by thread_id
        self._token_counter = TokenCounter()  # Token counter with caching

    async def get_context(
        self, thread_id: str, storage: AgentStorage, max_tokens: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get recent conversation context for the current turn.

        Args:
            thread_id: Thread ID to load context from
            storage: AgentStorage instance for storage access
            max_tokens: Maximum tokens allowed (model context window - safety margin)

        Returns:
            List of message dicts in format: [{"role": "user", "content": "..."}]
            Returns empty list if add_history_to_messages is False
        """
        if not self.memory.add_history_to_messages:
            return []

        # Determine window size (use window_size, fallback to num_history_responses for backward compat)
        message_limit = self.memory.window_size
        if message_limit == 20 and self.memory.num_history_responses != 10:
            # User set num_history_responses but not window_size, use * 2 calculation
            message_limit = self.memory.num_history_responses * 2

        # Load messages (load more than needed for token-aware trimming)
        # Load up to 2x limit to have buffer for token-aware selection
        recent_messages = await storage.get_history(thread_id, limit=message_limit * 2)

        context = []
        for msg in recent_messages:
            msg_dict = storage._message_to_dict(msg)
            context.append(msg_dict)

        # Filter tool calls if disabled (default: exclude tool calls to reduce noise)
        if not self.memory.include_tool_calls:
            context = [msg for msg in context if msg.get("role") != "tool"]

        # Apply token-aware windowing if token_limit is set
        if self.memory.token_limit and max_tokens:
            context = await self._apply_token_limiting(context, max_tokens)
        else:
            # Apply message count limiting
            context = self._apply_message_limiting(context, message_limit)

        return context

    def _apply_message_limiting(
        self, messages: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        """
        Apply message count limiting.

        Args:
            messages: List of messages (oldest to newest)
            limit: Maximum number of messages to keep

        Returns:
            Trimmed list of messages (keeping newest)
        """
        # Filter system messages if needed
        if not self.memory.include_system_messages:
            # Count only non-system messages
            non_system = [msg for msg in messages if msg.get("role") != "system"]
            system = [msg for msg in messages if msg.get("role") == "system"]

            # Keep all system messages + limit non-system messages
            trimmed_non_system = non_system[-limit:] if len(non_system) > limit else non_system

            # Combine: system messages first, then trimmed non-system
            result = system + trimmed_non_system
            # Sort by original order (messages are already in chronological order)
            return sorted(
                result, key=lambda m: messages.index(m) if m in messages else len(messages)
            )
        else:
            # Count all messages including system
            return messages[-limit:] if len(messages) > limit else messages

    async def _apply_token_limiting(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """
        Apply token-aware limiting with overflow handling.

        Args:
            messages: List of messages (oldest to newest)
            max_tokens: Maximum tokens allowed

        Returns:
            Trimmed list of messages that fit within token limit
        """
        # Reserve tokens for summary if overflow handling is enabled
        summary_reserve = 200 if self.memory.summarize_overflow else 0
        available_tokens = max_tokens - summary_reserve

        # Filter system messages if needed
        system_messages = []
        non_system_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                if self.memory.include_system_messages:
                    system_messages.append(msg)
            else:
                non_system_messages.append(msg)

        # Count system message tokens (without conversation overhead for individual groups)
        system_tokens = sum(self._token_counter.count_message(msg) for msg in system_messages)

        # Calculate available tokens for non-system messages
        non_system_budget = available_tokens - system_tokens
        if non_system_budget <= 0:
            # System messages alone exceed limit, return only system messages
            return system_messages

        # Trim non-system messages
        trimmed = []
        current_tokens = 0

        for msg in reversed(non_system_messages):
            msg_tokens = self._token_counter.count_message(msg)
            if current_tokens + msg_tokens <= non_system_budget:
                trimmed.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        # Check if we need overflow handling
        all_messages = system_messages + non_system_messages
        total_tokens = self._token_counter.count_input_messages(all_messages)

        if total_tokens > max_tokens and self.memory.summarize_overflow:
            # Get summary for overflow messages
            summary = await self._get_summary_for_overflow(all_messages, trimmed, max_tokens)
            if summary:
                summary_msg = {
                    "role": "system",
                    "content": f"Previous conversation summary: {summary}",
                }
                # Check if summary + trimmed messages fit
                summary_tokens = self._token_counter.count_message(summary_msg)
                if summary_tokens + current_tokens + system_tokens <= max_tokens:
                    return [*system_messages, summary_msg, *trimmed]

        # Return system messages + trimmed non-system messages
        return system_messages + trimmed

    async def _get_summary_for_overflow(
        self,
        all_messages: list[dict[str, Any]],
        kept_messages: list[dict[str, Any]],
        max_tokens: int,
    ) -> str | None:
        """
        Generate summary for messages that were trimmed due to overflow.

        Args:
            all_messages: All messages in conversation
            kept_messages: Messages that were kept in context
            max_tokens: Token limit

        Returns:
            Summary string or None if summarization fails
        """
        # Find messages that were excluded
        kept_set = {id(msg.get("content", "")) for msg in kept_messages}
        excluded = [msg for msg in all_messages if id(msg.get("content", "")) not in kept_set]

        if not excluded:
            return None

        cache_key = f"{hash(str(excluded))}"
        if cache_key in self._summary_cache:
            return self._summary_cache[cache_key]

        # Format messages for summarization
        text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in excluded]
        )
        prompt = f"{self.memory.summary_prompt}\n\n{text}"

        try:
            # Use summary model if specified, else use agent's model
            # For now, use agent's model (summary_model can be implemented later)
            response = await self.model.invoke([{"role": "user", "content": prompt}])
            summary = response.content

            # Cache summary
            self._summary_cache[cache_key] = summary
            return summary
        except Exception:
            return None
