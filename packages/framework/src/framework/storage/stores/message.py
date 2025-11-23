import json
from datetime import datetime
from typing import List
from ..models import Message
from .base import BaseStore

class MessageStore(BaseStore[Message]):
    """Store for managing messages."""
    
    async def add(self, message: Message) -> None:
        """Add a single message to a thread."""
        await self.add_many([message])

    async def add_many(self, messages: List[Message]) -> None:
        """Add multiple messages to a thread efficiently."""
        if not messages:
            return
            
        query = """
            INSERT INTO messages (id, thread_id, role, content, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = [
            (
                msg.id,
                msg.thread_id,
                msg.role,
                msg.content,
                msg.created_at.isoformat(),
                json.dumps(msg.metadata)
            )
            for msg in messages
        ]
        # Use executemany if available, otherwise loop (StorageBackend needs update for executemany)
        # For now, we'll just loop in execute or update StorageBackend.
        # Let's update StorageBackend to support batch execution properly later.
        # For now, we will just iterate.
        for param in params:
             await self.storage.execute(query, list(param))
        
    async def get_by_thread(self, thread_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """Get messages for a thread."""
        query = """
            SELECT * FROM messages 
            WHERE thread_id = ? 
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
        """
        rows = await self.storage.fetch_all(query, [thread_id, limit, offset])
        
        return [
            Message(
                id=row['id'],
                thread_id=row['thread_id'],
                role=row['role'],
                content=row['content'],
                created_at=datetime.fromisoformat(row['created_at']),
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            )
            for row in rows
        ]
