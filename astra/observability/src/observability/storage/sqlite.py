"""
SQLite storage backend for Astra Observability.

Uses aiosqlite for async SQLite operations.
Suitable for development and single-node deployments.
"""

from datetime import datetime
import json

import aiosqlite

from observability.logs.model import Log, LogLevel
from observability.tracing.span import Span, SpanKind, SpanStatus
from observability.tracing.trace import Trace, TraceStatus

from .base import StorageBackend


class TelemetrySQLite(StorageBackend):
    """
    SQLite-based storage for traces and spans.

    Usage:
        storage = TelemetrySQLite("observability.db")
        await storage.init()
        await storage.save_trace(trace)
        await storage.close()
    """

    def __init__(self, db_path: str = "observability.db"):
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Create tables if they don't exist."""
        self._conn = await aiosqlite.connect(self.db_path)

        # Enable WAL mode for better concurrency
        await self._conn.execute("PRAGMA journal_mode=WAL")

        # Create traces table
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                attributes TEXT NOT NULL DEFAULT '{}',
                total_tokens INTEGER DEFAULT 0,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                thoughts_tokens INTEGER DEFAULT 0,
                model TEXT
            )
        """)

        # Create spans table
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                parent_span_id TEXT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_ms INTEGER,
                attributes TEXT NOT NULL DEFAULT '{}',
                error TEXT,
                FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
            )
        """)

        # Create logs table
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                span_id TEXT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                attributes TEXT NOT NULL DEFAULT '{}',
                timestamp TEXT NOT NULL,
                FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
            )
        """)

        # Create indexes
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_spans_trace_id ON spans(trace_id)")
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_traces_start_time ON traces(start_time DESC)"
        )
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_span_id ON logs(span_id)")

        await self._conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    # Trace operations

    async def save_trace(self, trace: Trace) -> None:
        """Save or update a trace (upsert)."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        await self._conn.execute(
            """
            INSERT INTO traces (
                trace_id, name, status, start_time, end_time, attributes,
                total_tokens, input_tokens, output_tokens, thoughts_tokens, model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trace_id) DO UPDATE SET
                status = excluded.status,
                end_time = excluded.end_time,
                attributes = excluded.attributes,
                total_tokens = excluded.total_tokens,
                input_tokens = excluded.input_tokens,
                output_tokens = excluded.output_tokens,
                thoughts_tokens = excluded.thoughts_tokens,
                model = excluded.model
            """,
            (
                trace.trace_id,
                trace.name,
                trace.status.value,
                trace.start_time.isoformat(),
                trace.end_time.isoformat() if trace.end_time else None,
                json.dumps(trace.attributes),
                trace.total_tokens,
                trace.input_tokens,
                trace.output_tokens,
                trace.thoughts_tokens,
                trace.model,
            ),
        )
        await self._conn.commit()

    async def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        async with self._conn.execute(
            """
            SELECT trace_id, name, status, start_time, end_time, attributes,
                   total_tokens, input_tokens, output_tokens, thoughts_tokens, model
            FROM traces WHERE trace_id = ?
            """,
            (trace_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        return Trace(
            trace_id=row[0],
            name=row[1],
            status=TraceStatus(row[2]),
            start_time=datetime.fromisoformat(row[3]),
            end_time=datetime.fromisoformat(row[4]) if row[4] else None,
            attributes=json.loads(row[5]),
            total_tokens=row[6],
            input_tokens=row[7],
            output_tokens=row[8],
            thoughts_tokens=row[9],
            model=row[10],
        )

    async def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trace]:
        """List traces with pagination, ordered by start_time DESC."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        async with self._conn.execute(
            """
            SELECT trace_id, name, status, start_time, end_time, attributes,
                   total_tokens, input_tokens, output_tokens, thoughts_tokens, model
            FROM traces
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            Trace(
                trace_id=row[0],
                name=row[1],
                status=TraceStatus(row[2]),
                start_time=datetime.fromisoformat(row[3]),
                end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                attributes=json.loads(row[5]),
                total_tokens=row[6],
                input_tokens=row[7],
                output_tokens=row[8],
                thoughts_tokens=row[9],
                model=row[10],
            )
            for row in rows
        ]

    # Span operations

    async def save_span(self, span: Span) -> None:
        """Save or update a span (upsert)."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        await self._conn.execute(
            """
            INSERT INTO spans (
                span_id, trace_id, parent_span_id, name, kind, status,
                start_time, end_time, duration_ms, attributes, error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(span_id) DO UPDATE SET
                status = excluded.status,
                end_time = excluded.end_time,
                duration_ms = excluded.duration_ms,
                attributes = excluded.attributes,
                error = excluded.error
            """,
            (
                span.span_id,
                span.trace_id,
                span.parent_span_id,
                span.name,
                span.kind.value,
                span.status.value,
                span.start_time.isoformat(),
                span.end_time.isoformat() if span.end_time else None,
                span.duration_ms,
                json.dumps(span.attributes),
                span.error,
            ),
        )
        await self._conn.commit()

    async def get_spans_for_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace, ordered by start_time."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        async with self._conn.execute(
            """
            SELECT span_id, trace_id, parent_span_id, name, kind, status,
                   start_time, end_time, duration_ms, attributes, error
            FROM spans
            WHERE trace_id = ?
            ORDER BY start_time ASC
            """,
            (trace_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            Span(
                span_id=row[0],
                trace_id=row[1],
                parent_span_id=row[2],
                name=row[3],
                kind=SpanKind(row[4]),
                status=SpanStatus(row[5]),
                start_time=datetime.fromisoformat(row[6]),
                end_time=datetime.fromisoformat(row[7]) if row[7] else None,
                duration_ms=row[8],
                attributes=json.loads(row[9]),
                error=row[10],
            )
            for row in rows
        ]

    # Log operations

    async def save_log(self, log: Log) -> None:
        """Save a log entry."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        await self._conn.execute(
            """
            INSERT INTO logs (
                id, trace_id, span_id, level, message, attributes, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log.id,
                log.trace_id,
                log.span_id,
                log.level.value,
                log.message,
                json.dumps(log.attributes),
                log.timestamp.isoformat(),
            ),
        )
        await self._conn.commit()

    async def list_logs(
        self,
        trace_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Log]:
        """List logs for a trace, ordered by timestamp ASC."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")

        async with self._conn.execute(
            """
            SELECT id, trace_id, span_id, level, message, attributes, timestamp
            FROM logs
            WHERE trace_id = ?
            ORDER BY timestamp ASC
            LIMIT ? OFFSET ?
            """,
            (trace_id, limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            Log(
                id=row[0],
                trace_id=row[1],
                span_id=row[2],
                level=LogLevel(row[3]),
                message=row[4],
                attributes=json.loads(row[5]),
                timestamp=datetime.fromisoformat(row[6]),
            )
            for row in rows
        ]
