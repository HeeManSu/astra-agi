"""
HIL run state management and persistence.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from .models import RunStatus, PauseReason


class RunState(BaseModel):
    """
    Persistent run state for pause/resume.
    
    Stores all information needed to resume a paused execution,
    including the pause reason, tool call details, and execution context.
    
    This state survives agent restarts and allows humans to
    approve/provide input hours or days later.
    """
    run_id: str
    agent_id: str
    thread_id: Optional[str] = None
    status: RunStatus
    pause_reason: Optional[PauseReason] = None
    pause_data: Optional[Dict[str, Any]] = None  # Tool call details, suspend payload, etc.
    execution_context: Optional[Dict[str, Any]] = None  # Messages, model config, etc.
    created_at: datetime
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RunStateStorage:
    """
    Persistent storage for run states.
    
    Uses the agent's storage backend to persist run states
    in a dedicated table.
    """
    
    def __init__(self, storage: 'StorageBackend'):
        """
        Initialize run state storage.
        
        Args:
            storage: Storage backend (e.g., SQLiteStorage)
        """
        self.storage = storage
        
    async def initialize_schema(self) -> None:
        """Create run_states table if it doesn't exist."""
        await self.storage.connect()
        
        schema = """
        CREATE TABLE IF NOT EXISTS run_states (
            run_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            thread_id TEXT,
            status TEXT NOT NULL,
            pause_reason TEXT,
            pause_data TEXT,
            execution_context TEXT,
            created_at TEXT NOT NULL,
            paused_at TEXT,
            resumed_at TEXT,
            completed_at TEXT
        )
        """
        await self.storage.execute(schema)
        
    async def save(self, state: RunState) -> None:
        """
        Save run state to storage.
        
        Args:
            state: Run state to save
        """
        await self.initialize_schema()
        
        query = """
        INSERT OR REPLACE INTO run_states (
            run_id, agent_id, thread_id, status, pause_reason,
            pause_data, execution_context, created_at, paused_at,
            resumed_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = [
            state.run_id,
            state.agent_id,
            state.thread_id,
            state.status.value,
            state.pause_reason.value if state.pause_reason else None,
            json.dumps(state.pause_data) if state.pause_data else None,
            json.dumps(state.execution_context) if state.execution_context else None,
            state.created_at.isoformat(),
            state.paused_at.isoformat() if state.paused_at else None,
            state.resumed_at.isoformat() if state.resumed_at else None,
            state.completed_at.isoformat() if state.completed_at else None,
        ]
        
        await self.storage.execute(query, params)
        
    async def get(self, run_id: str) -> Optional[RunState]:
        """
        Get run state by ID.
        
        Args:
            run_id: Run ID to retrieve
            
        Returns:
            Run state if found, None otherwise
        """
        await self.initialize_schema()
        
        query = "SELECT * FROM run_states WHERE run_id = ?"
        row = await self.storage.fetch_one(query, [run_id])
        
        if not row:
            return None
            
        return RunState(
            run_id=row['run_id'],
            agent_id=row['agent_id'],
            thread_id=row['thread_id'],
            status=RunStatus(row['status']),
            pause_reason=PauseReason(row['pause_reason']) if row['pause_reason'] else None,
            pause_data=json.loads(row['pause_data']) if row['pause_data'] else None,
            execution_context=json.loads(row['execution_context']) if row['execution_context'] else None,
            created_at=datetime.fromisoformat(row['created_at']),
            paused_at=datetime.fromisoformat(row['paused_at']) if row['paused_at'] else None,
            resumed_at=datetime.fromisoformat(row['resumed_at']) if row['resumed_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
        )
        
    async def update_status(
        self,
        run_id: str,
        status: RunStatus,
        **kwargs
    ) -> None:
        """
        Update run status and optional fields.
        
        Args:
            run_id: Run ID to update
            status: New status
            **kwargs: Additional fields to update (paused_at, resumed_at, etc.)
        """
        await self.initialize_schema()
        
        # Build dynamic update query
        updates = ["status = ?"]
        params = [status.value]
        
        if 'paused_at' in kwargs:
            updates.append("paused_at = ?")
            params.append(kwargs['paused_at'].isoformat() if kwargs['paused_at'] else None)
            
        if 'resumed_at' in kwargs:
            updates.append("resumed_at = ?")
            params.append(kwargs['resumed_at'].isoformat() if kwargs['resumed_at'] else None)
            
        if 'completed_at' in kwargs:
            updates.append("completed_at = ?")
            params.append(kwargs['completed_at'].isoformat() if kwargs['completed_at'] else None)
            
        params.append(run_id)
        
        query = f"UPDATE run_states SET {', '.join(updates)} WHERE run_id = ?"
        await self.storage.execute(query, params)
