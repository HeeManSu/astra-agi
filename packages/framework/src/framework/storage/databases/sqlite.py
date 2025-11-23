import json
import os
from typing import Any, Dict, List, Optional, Union
import aiosqlite
from ..base import StorageBackend

class SQLiteStorage(StorageBackend):
    """
    SQLite implementation of StorageBackend.
    Supports local files and LibSQL file URLs.
    """
    
    def __init__(self, db_path: str = "storage.db"):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to the database file (e.g., "storage.db", "file:./storage.db")
        """
        # Handle "file:" prefix for LibSQL compatibility
        if db_path.startswith("file:"):
            db_path = db_path.replace("file:", "")
            
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        
    async def connect(self) -> None:
        """Establish connection and enable foreign keys."""
        if not self._conn:
            # Ensure directory exists
            directory = os.path.dirname(self.db_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA foreign_keys = ON;")
            
            # Initialize schema
            await self._init_schema()
            
    async def disconnect(self) -> None:
        """Close connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            
    async def execute(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> None:
        """Execute a write query."""
        if not self._conn:
            await self.connect()
        assert self._conn is not None
        
        await self._conn.execute(query, params or [])
        await self._conn.commit()
        
    async def fetch_all(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Execute a read query and return all results."""
        if not self._conn:
            await self.connect()
        assert self._conn is not None
        
        async with self._conn.execute(query, params or []) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    async def fetch_one(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """Execute a read query and return a single result."""
        if not self._conn:
            await self.connect()
        assert self._conn is not None
        
        async with self._conn.execute(query, params or []) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _init_schema(self) -> None:
        """Initialize database schema."""
        # Threads table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                metadata TEXT
            );
        """)
        
        # Messages table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
            );
        """)
        
        # Create indexes
        await self.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);")
