"""
Shared SQLite database used by every agent and team registered with AgentOS.

Holds session history, memories, and metrics so the AgentOS UI can replay
prior runs.
"""

from pathlib import Path

from agno.db.sqlite import SqliteDb


_DB_FILE = str(Path(__file__).resolve().parent / "agentos.db")

db = SqliteDb(
    db_file=_DB_FILE,
    session_table="sessions",
    memory_table="user_memories",
    metrics_table="metrics",
    eval_table="eval_runs",
)
