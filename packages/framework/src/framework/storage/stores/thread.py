import json
from datetime import datetime
from typing import List, Optional
from ..models import Thread
from .base import BaseStore

class ThreadStore(BaseStore[Thread]):
    """Store for managing conversation threads."""
    
    async def create(self, thread: Thread) -> None:
        """Create a new thread."""
        query = """
            INSERT INTO threads (id, title, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """
        await self.storage.execute(
            query,
            [
                thread.id,
                thread.title,
                thread.created_at.isoformat(),
                thread.updated_at.isoformat(),
                json.dumps(thread.metadata)
            ]
        )
        
    async def get(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID."""
        query = "SELECT * FROM threads WHERE id = ?"
        row = await self.storage.fetch_one(query, [thread_id])
        
        if not row:
            return None
            
        return Thread(
            id=row['id'],
            title=row['title'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )
        
    async def update(self, thread_id: str, title: Optional[str] = None, metadata: Optional[dict] = None) -> None:
        """Update a thread."""
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
            
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
            
        if not updates:
            return
            
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(thread_id)
        
        query = f"UPDATE threads SET {', '.join(updates)} WHERE id = ?"
        await self.storage.execute(query, params)
