import uuid
from typing import List, Optional, Dict, Any
from .base import StorageBackend
from .models import Thread, Message
from .stores.thread import ThreadStore
from .base import StorageBackend
from .models import Thread, Message
from .stores.thread import ThreadStore
from .stores.message import MessageStore
from .queue import SaveQueueManager

class AgentMemory:
    """
    Facade for agent memory operations.
    Handles interaction with ThreadStore and MessageStore.
    Integrates SaveQueueManager for optimized writes.
    
    Flow:
    - Reads: Direct access to Stores (ThreadStore, MessageStore) -> StorageBackend.
    - Writes: Buffered via SaveQueueManager -> Batch Write -> StorageBackend.
    
    This ensures low latency for the agent loop while persisting data efficiently.
    """
    
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.threads = ThreadStore(storage)
        self.messages = MessageStore(storage)
        self.queue = SaveQueueManager()
        
    async def start(self) -> None:
        """Start the memory system (queue worker)."""
        await self.queue.start()
        
    async def stop(self) -> None:
        """Stop the memory system and flush queue."""
        await self.queue.stop()
        
    async def create_thread(self, thread_id: Optional[str] = None, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Thread:
        """Create a new conversation thread."""
        thread = Thread(
            id=thread_id or str(uuid.uuid4()),
            title=title,
            metadata=metadata or {}
        )
        # Threads are usually created rarely, so we can save directly or queue
        # For safety/consistency, let's save directly for now to ensure it exists before messages
        await self.threads.create(thread)
        return thread
        
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID."""
        return await self.threads.get(thread_id)
        
    async def add_message(self, thread_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add a message to a thread."""
        # Ensure thread exists (this check might be slow, maybe cache?)
        # For now, assume thread exists or check efficiently.
        # If we queue message, we assume thread exists.
        
        # Optimization: If we just created the thread in this session, we know it exists.
        # But for stateless requests, we might need to check.
        # Let's check for now.
        thread = await self.get_thread(thread_id)
        if not thread:
            await self.create_thread(thread_id=thread_id)
            
        message = Message(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        # Enqueue for saving
        await self.queue.enqueue(self.messages.add_many, message)
        return message
        
    async def get_history(self, thread_id: str, limit: int = 100) -> List[Message]:
        """Get conversation history for a thread."""
        return await self.messages.get_by_thread(thread_id, limit=limit)
