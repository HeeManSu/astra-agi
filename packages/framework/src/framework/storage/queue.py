import asyncio
from typing import List, Any, Callable, Awaitable, Dict, Tuple

class SaveQueueManager:
    """
    Manages asynchronous saving of data to storage.
    Implements batching and debouncing optimizations to reduce database load.
    
    Architecture:
    - Sits between MemoryBase (AgentMemory) and Domain Stores.
    - Buffers write operations in an in-memory queue.
    - A background worker flushes the queue periodically (flush_interval).
    - Groups items by their target function (e.g. MessageStore.add_many) to enable batch writes.
    
    Flow:
    1. AgentMemory calls enqueue(func, item).
    2. Item is added to internal list.
    3. Background worker wakes up every X seconds.
    4. Worker groups items by function.
    5. Worker calls func(items) with the batched list.
    """
    
    def __init__(self, batch_size: int = 10, flush_interval: float = 0.5):
        """
        Initialize the queue manager.
        
        Args:
            batch_size: Number of items to batch before flushing (soft limit)
            flush_interval: Seconds to wait before flushing
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Queue stores tuples of (save_function, item)
        self._queue: List[Tuple[Callable[[List[Any]], Awaitable[None]], Any]] = []
        self._lock = asyncio.Lock()
        self._worker_task: asyncio.Task | None = None
        self._running = False
        
    async def start(self) -> None:
        """Start the background worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        
    async def stop(self) -> None:
        """Stop the background worker and flush remaining items."""
        self._running = False
        if self._worker_task:
            try:
                # Wait for current sleep to finish or cancel?
                # Better to just wait for flush.
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
            except Exception:
                pass
        
        # Final flush
        await self.flush()
            
    async def enqueue(self, func: Callable[[List[Any]], Awaitable[None]], item: Any) -> None:
        """
        Add an item to the queue.
        
        Args:
            func: Async function that accepts a list of items (e.g., store.add_many)
            item: The item to save
        """
        async with self._lock:
            self._queue.append((func, item))
            
        # If queue is large, trigger flush immediately (optional optimization)
        if len(self._queue) >= self.batch_size:
            # We could trigger flush here, but for simplicity let the worker handle it
            # or spawn a flush task.
            pass
            
        # If not running (e.g. simple script usage without explicit start),
        # we might want to flush immediately or start the worker.
        # For safety, if not running, flush immediately to avoid data loss.
        if not self._running:
             await self.flush()

    async def _worker(self) -> None:
        """Background worker to flush queue periodically."""
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
            
    async def flush(self) -> None:
        """Flush the queue to storage."""
        async with self._lock:
            if not self._queue:
                return
            
            items_to_process = self._queue[:]
            self._queue.clear()
            
        # Group items by their save function
        grouped: Dict[Callable, List[Any]] = {}
        for func, item in items_to_process:
            if func not in grouped:
                grouped[func] = []
            grouped[func].append(item)
            
        # Execute batch saves
        for func, items in grouped.items():
            try:
                await func(items)
            except Exception as e:
                # In a real system, we might retry or log to a dead-letter queue
                print(f"Error saving batch with {func.__name__}: {e}")
