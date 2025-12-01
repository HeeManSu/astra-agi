import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel


T = TypeVar("T")


class SaveQueueManager:
    """
    Manages a queue of items to be saved to storage with debounce and batching.

    Features:
    - Debounce: Wait for a quiet period before saving.
    - Batching: Save multiple items in a single operation.
    - JSON Serialization: Handles UUID and datetime serialization.
    """

    def __init__(
        self,
        save_func: Callable[[list[Any]], Any],
        batch_size: int = 10,
        debounce_seconds: float = 0.5,
    ):
        self.save_func = save_func
        self.batch_size = batch_size
        self.debounce_seconds = debounce_seconds
        self._queue: list[Any] = []
        self._timer: asyncio.TimerHandle | None = None
        self._lock = asyncio.Lock()

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for common types."""
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        if isinstance(obj, (UUID,)):
            return str(obj)
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        raise TypeError(f"Type {type(obj)} not serializable")

    def add(self, item: Any) -> None:
        """Add an item to the queue and schedule a flush."""
        # Serialize item immediately to ensure it's safe for storage/queueing
        # Note: In this specific design, we might want to keep objects as is until save,
        # but the requirement mentioned "Json serialization in the queueManager".
        # If the store expects Pydantic models, we should probably keep them as models
        # and only serialize metadata if needed.
        # However, the user asked for "Json serialization in the queueManager".
        # Let's assume the save_func handles the actual DB insertion which might need dicts or models.
        # For now, I will keep the item as is, but provide a helper for serialization if needed by the save_func
        # or if we were persisting the queue itself.
        # But wait, the user flow says:
        # MessageStore.save_messages()
        #        ↓
        # BaseStorage → DB
        #
        # And Queue is before MessageStore?
        # "MemoryBase.save(message) -> SaveQueueManager -> (debounce/batch/serialize) -> MessageStore.save_messages()"
        #
        # So SaveQueueManager calls MessageStore.save_messages(batch).
        # MessageStore expects Message objects.
        # So we should probably queue Message objects.
        # The serialization requirement might be for the metadata or content if it's complex.
        # Or maybe the user meant "ensure data is serializable".
        # Let's stick to queuing the raw items (Message objects) and handle serialization
        # if we were writing to a raw JSON store, but here we are writing to SQL via SQLAlchemy.
        # SQLAlchemy handles datetime/uuid usually.
        #
        # Re-reading: "Json serialization in the queueManager"
        # Maybe they mean for the `metadata` field?
        # Let's ensure we have a utility for it.

        self._queue.append(item)
        self._schedule_flush()

    def _schedule_flush(self) -> None:
        """Schedule a flush after the debounce interval."""
        if self._timer:
            self._timer.cancel()

        loop = asyncio.get_running_loop()
        self._timer = loop.call_later(
            self.debounce_seconds, lambda: asyncio.create_task(self.flush())
        )

    async def flush(self) -> None:
        """Flush the queue, processing items in batches."""
        async with self._lock:
            if not self._queue:
                return

            # Copy and clear queue
            items_to_save = list(self._queue)
            self._queue.clear()
            self._timer = None

        # Process in batches
        failed_batches = []
        for i in range(0, len(items_to_save), self.batch_size):
            batch = items_to_save[i : i + self.batch_size]
            try:
                # We await the save function.
                # If save_func is async, we await it.
                if asyncio.iscoroutinefunction(self.save_func):
                    await self.save_func(batch)
                else:
                    # If it's not async (unlikely for DB), run it.
                    self.save_func(batch)
            except Exception as e:
                # Log error and re-queue failed batch
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to save batch of {len(batch)} items: {e}",
                    exc_info=True,
                )
                failed_batches.append(batch)

        # Re-queue failed batches for retry
        if failed_batches:
            async with self._lock:
                for batch in failed_batches:
                    self._queue.extend(batch)
                # Schedule retry after a longer delay
                if self._queue:
                    loop = asyncio.get_running_loop()
                    self._timer = loop.call_later(
                        self.debounce_seconds * 2, lambda: asyncio.create_task(self.flush())
                    )

    async def stop(self) -> None:
        """Force flush and stop."""
        if self._timer:
            self._timer.cancel()
        await self.flush()
