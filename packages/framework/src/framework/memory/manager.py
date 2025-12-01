from typing import Any

from framework.memory.memory import AgentMemory
from framework.models import Model
from framework.storage.memory import AgentStorage


class MemoryManager:
    """
    Manages short-term conversation context and summarization.

    Uses AgentMemory configuration to:
    1. Retrieve recent messages (sliding window)
    2. Summarize older messages (if enabled)
    3. Maintain context within LLM limits
    """

    def __init__(self, memory: AgentMemory, model: Model):
        self.memory = memory
        self.model = model
        self._summary_cache: dict[str, str] = {}  # Cache summaries by thread_id

    async def get_context(self, thread_id: str, storage: AgentStorage) -> list[dict[str, Any]]:
        """
        Get recent conversation context for the current turn.

        Args:
            thread_id: Thread ID to load context from
            storage: AgentStorage instance for storage access

        Returns:
            List of message dicts in format: [{"role": "user", "content": "..."}]
            If summary enabled, first message will be a system message with summary
            Returns empty list if add_history_to_messages is False
        """
        # If history loading is disabled, return empty context
        if not self.memory.add_history_to_messages:
            return []

        # Load recent messages based on config
        limit = self.memory.num_history_responses * 2  # *2 because user+assistant = 1 turn
        recent_messages = await storage.get_history(thread_id, limit=limit)

        context = []

        # Add summary if enabled and there are older messages
        if self.memory.create_session_summary:
            # Check if there are more messages beyond our window
            # If we got exactly 'limit' messages, there might be more older messages to summarize
            if len(recent_messages) >= limit:
                # Generate or retrieve summary
                summary = await self._get_summary(thread_id, storage)
                if summary:
                    context.append(
                        {"role": "system", "content": f"Previous conversation summary: {summary}"}
                    )

        # Add recent messages
        # Use AgentStorage's _message_to_dict method for proper reconstruction
        for msg in recent_messages:
            msg_dict = storage._message_to_dict(msg)
            context.append(msg_dict)

        return context

    async def _get_summary(self, thread_id: str, storage: AgentStorage) -> str | None:
        """
        Get or generate summary of old messages.
        """
        # Fetch a reasonable amount of history to summarize (e.g., last 100 messages)
        # TODO: Optimize this to fetch only needed messages or use a dedicated summary store
        all_messages = await storage.get_history(thread_id, limit=100)

        # We want to summarize everything EXCEPT the recent window
        window_size = self.memory.num_history_responses * 2

        if len(all_messages) <= window_size:
            return None

        # Since get_history returns [oldest, ..., newest],
        # the messages to summarize are at the beginning of the list.
        to_summarize = all_messages[:-window_size]

        if not to_summarize:
            return None

        # Format messages for summarization
        text = "\n".join([f"{msg.role}: {msg.content}" for msg in to_summarize])
        prompt = f"{self.memory.summary_prompt}\n\n{text}"

        try:
            # Use the agent's model to generate summary
            # We create a temporary context for the summary generation
            # TODO: Consider using a separate model or lighter model for summarization
            response = await self.model.invoke([{"role": "user", "content": prompt}])
            return response.content
        except Exception:
            # If summarization fails, return None (graceful degradation)
            return None
