import asyncio
from collections.abc import Callable
from typing import Any, TypeVar


T = TypeVar("T")


class SaveQueueManager:
    """
    Manages a queue of items to be saved to storage with debounce and batching.

    Features:
    - Debounce: Wait for a quiet period before saving.
    - Batching: Save multiple items in a single operation.
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

    def add(self, item: Any) -> None:
        """Add an item to the queue and schedule a flush."""
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
