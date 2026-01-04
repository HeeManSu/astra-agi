"""
AgentStorage facade for Astra.

Provides a simple, high-level interface over:
- ThreadStore
- MessageStore

Used by agents to:
- Create/load threads
- Append messages
- Fetch conversation history
"""

from typing import Any
from uuid import uuid4

from framework.storage.base import StorageBackend
from framework.storage.models import Message, Thread
from framework.storage.queue import SaveQueueManager
from framework.storage.stores.message import MessageStore
from framework.storage.stores.thread import ThreadStore


class AgentStorage:
    """
    High-level storage interface for agents.

    Responsibilities:
    - Create and retrieve threads
    - Append messages to threads
    - Return recent conversation history
    - Soft delete threads and messages

    Automatically filters out soft-deleted records in all queries.
    """

    def __init__(
        self,
        storage: StorageBackend,
        max_messages: int = 50,
        batch_size: int = 10,
        debounce_seconds: float = 0.5,
    ) -> None:
        self.storage = storage
        self.threads = ThreadStore(storage)
        self.messages = MessageStore(storage)
        self.max_messages = max_messages

        # Initialize Queue Manager
        self.queue = SaveQueueManager(
            save_func=self._save_messages_batch,
            batch_size=batch_size,
            debounce_seconds=debounce_seconds,
        )

    async def _save_messages_batch(self, messages: list[Message]) -> None:
        """Callback for QueueManager to save a batch of messages."""
        # Use bulk insert for better performance
        await self.messages.bulk_add(messages)

    async def create_thread(
        self,
        thread_id: str | None = None,
        agent_name: str | None = None,
        resource_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Thread:
        """
        Create a new thread.

        If thread_id is not provided, a random one is generated.
        """
        thread_id = thread_id or f"thread-{uuid4().hex[:10]}"
        thread = Thread(
            id=thread_id,
            agent_name=agent_name,
            resource_id=resource_id,
            title=title,
            metadata=metadata or {},
            # is_archived, created_at, updated_at are either defaulted in model or DB
        )
        return await self.threads.create(thread)

    async def get_thread(self, thread_id: str) -> Thread | None:
        """Fetch thread by ID."""
        return await self.threads.get(thread_id)

    async def list_threads(
        self,
        agent_name: str | None = None,
        limit: int = 50,
    ) -> list[Thread]:
        """
        List threads, optionally filtered by agent_name.

        Args:
            agent_name: Optional agent name to filter by
            limit: Maximum number of threads to return

        Returns:
            List of Thread objects, ordered by updated_at desc
        """
        filter_dict: dict = {"deleted_at": None}
        if agent_name:
            filter_dict["agent_name"] = agent_name

        query = self.storage.build_select_query(
            collection="astra_threads",
            filter_dict=filter_dict,
            sort=[("updated_at", -1)],
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        return [self.threads._row_to_model(row) for row in rows]

    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Append a message to a thread via the queue.

        Args:
            thread_id: Thread identifier
            role: Message role (user, assistant, system, tool)
            content: Message content
            tool_calls: Tool calls for assistant messages (list of {"name": str, "arguments": dict})
            tool_call_id: Tool call ID for tool messages (links tool result to tool call)
            metadata: Additional metadata

        Auto-assigns sequence using MessageStore.get_next_sequence().
        Messages are queued and saved in batches for performance.
        """
        # Auto-create thread if it doesn't exist (prevents foreign key errors)
        thread = await self.get_thread(thread_id)
        if thread is None:
            await self.create_thread(thread_id=thread_id)

        sequence = await self.messages.get_next_sequence(thread_id)

        # Build metadata with tool_calls and tool_call_id
        msg_metadata = metadata or {}
        if tool_calls:
            msg_metadata["tool_calls"] = tool_calls
        if tool_call_id:
            msg_metadata["tool_call_id"] = tool_call_id

        message = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=msg_metadata,
            sequence=sequence,
        )

        # Add to queue for batched persistence
        self.queue.add(message)

    async def get_history(
        self,
        thread_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        """
        Get recent conversation history for a thread.

        Args:
            thread_id: Thread identifier
            limit: Optional override for number of messages.
                   Defaults to self.max_messages.

        Returns:
            List of Message objects with tool_calls in metadata (if present)
        """
        # Auto-create thread if it doesn't exist
        thread = await self.get_thread(thread_id)
        if thread is None:
            await self.create_thread(thread_id=thread_id)

        effective_limit = limit or self.max_messages
        return await self.messages.get_recent(thread_id, limit=effective_limit)

    async def soft_delete_thread(self, thread_id: str) -> None:
        """
        Soft delete a thread by setting deleted_at timestamp.

        Args:
            thread_id: Thread identifier to soft delete

        Note: Soft-deleted threads are automatically filtered out from queries.
        Messages in the thread remain accessible but the thread itself is hidden.
        """
        await self.threads.soft_delete(thread_id)

    async def soft_delete_message(self, message_id: str) -> None:
        """
        Soft delete a message by setting deleted_at timestamp.

        Args:
            message_id: Message identifier to soft delete

        Note: Soft-deleted messages are automatically filtered out from queries.
        """
        await self.messages.soft_delete(message_id)

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        """
        Convert Message to dict format for LLM context.

        Reconstructs proper message format with tool_calls if present.

        Args:
            message: Message object from storage

        Returns:
            Dict in format: {"role": str, "content": str, "tool_calls": list, "name": str}
        """
        msg_dict: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }

        # Add tool_calls for assistant messages
        if message.role == "assistant" and message.metadata.get("tool_calls"):
            msg_dict["tool_calls"] = message.metadata["tool_calls"]

        # Add name for tool messages
        if message.role == "tool":
            tool_call_id = message.metadata.get("tool_call_id")
            tool_name = message.metadata.get("tool_name")
            if tool_call_id:
                msg_dict["tool_call_id"] = tool_call_id
            if tool_name:
                msg_dict["name"] = tool_name

        return msg_dict

    async def stop(self) -> None:
        """Stop the queue manager."""
        await self.queue.stop()

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to storage backend."""
        return getattr(self.storage, name)
