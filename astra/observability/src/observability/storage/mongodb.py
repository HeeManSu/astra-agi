"""
MongoDB storage backend for Astra Observability.

Uses motor for async MongoDB operations.
Suitable for production and multi-node deployments.
"""

from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from observability.logs.model import Log, LogLevel
from observability.tracing.span import Span, SpanKind, SpanStatus
from observability.tracing.trace import Trace, TraceStatus

from .base import StorageBackend


class TelemetryMongoDB(StorageBackend):
    """
    MongoDB-based storage for traces and spans.

    Usage:
        storage = TelemetryMongoDB(
            url="mongodb://localhost:27017",
            db_name="astra_observability"
        )
        await storage.init()
        await storage.save_trace(trace)
        await storage.close()
    """

    def __init__(self, url: str, db_name: str = "astra_observability"):
        """
        Initialize MongoDB storage.

        Args:
            url: MongoDB connection URL
            db_name: Database name to use
        """
        self.url = url
        self.db_name = db_name
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None
        self._initialized: bool = False

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self._db is None:
            raise RuntimeError("Database not connected. Call init() first.")
        return self._db

    async def init(self) -> None:
        """Initialize the storage (create collections and indexes)."""
        if self._initialized:
            return

        self._client = AsyncIOMotorClient(self.url)
        self._db = self._client[self.db_name]

        # Test connection
        try:
            await self._client.admin.command("ping")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to MongoDB: {e}") from e

        # Create indexes for traces collection
        traces_collection = self._db["astra_obs_traces"]
        await traces_collection.create_index("start_time", background=True)
        await traces_collection.create_index("status", background=True)

        # Create indexes for spans collection
        spans_collection = self._db["astra_obs_spans"]
        await spans_collection.create_index("trace_id", background=True)
        await spans_collection.create_index([("trace_id", 1), ("start_time", 1)], background=True)

        # Create indexes for logs collection
        logs_collection = self._db["astra_obs_logs"]
        await logs_collection.create_index("trace_id", background=True)
        await logs_collection.create_index("span_id", background=True)
        await logs_collection.create_index([("trace_id", 1), ("timestamp", 1)], background=True)

        self._initialized = True

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._initialized = False

    # Trace operations

    async def save_trace(self, trace: Trace) -> None:
        """Save or update a trace (upsert)."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        doc = {
            "_id": trace.trace_id,
            "trace_id": trace.trace_id,
            "name": trace.name,
            "status": trace.status.value,
            "start_time": trace.start_time.isoformat(),
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "duration_ms": trace.duration_ms,
            "attributes": trace.attributes,
            # Token metrics
            "total_tokens": trace.total_tokens,
            "input_tokens": trace.input_tokens,
            "output_tokens": trace.output_tokens,
            "thoughts_tokens": trace.thoughts_tokens,
            "model": trace.model,
        }

        await self.db["astra_obs_traces"].replace_one({"_id": trace.trace_id}, doc, upsert=True)

    async def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        doc = await self.db["astra_obs_traces"].find_one({"_id": trace_id})

        if not doc:
            return None

        return self._doc_to_trace(doc)

    async def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trace]:
        """List traces with pagination, ordered by start_time DESC."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        cursor = self.db["astra_obs_traces"].find().sort("start_time", -1).skip(offset).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [self._doc_to_trace(doc) for doc in docs]

    # Span operations

    async def save_span(self, span: Span) -> None:
        """Save or update a span (upsert)."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        doc = {
            "_id": span.span_id,
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "parent_span_id": span.parent_span_id,
            "name": span.name,
            "kind": span.kind.value,
            "status": span.status.value,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "duration_ms": span.duration_ms,
            "attributes": span.attributes,
            "error": span.error,
        }

        await self.db["astra_obs_spans"].replace_one({"_id": span.span_id}, doc, upsert=True)

    async def get_spans_for_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace, ordered by start_time."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        cursor = self.db["astra_obs_spans"].find({"trace_id": trace_id}).sort("start_time", 1)

        docs = await cursor.to_list(length=None)
        return [self._doc_to_span(doc) for doc in docs]

    # Log operations

    async def save_log(self, log: Log) -> None:
        """Save a log entry (upsert)."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        doc = {
            "_id": log.id,
            "id": log.id,
            "trace_id": log.trace_id,
            "span_id": log.span_id,
            "level": log.level.value,
            "message": log.message,
            "attributes": log.attributes,
            "timestamp": log.timestamp.isoformat(),
        }

        await self.db["astra_obs_logs"].replace_one({"_id": log.id}, doc, upsert=True)

    async def list_logs(self, trace_id: str, limit: int = 100, offset: int = 0) -> list[Log]:
        """List logs for a trace."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call init() first.")

        cursor = (
            self.db["astra_obs_logs"]
            .find({"trace_id": trace_id})
            .sort("timestamp", 1)
            .skip(offset)
            .limit(limit)
        )

        docs = await cursor.to_list(length=limit)
        return [self._doc_to_log(doc) for doc in docs]

    # Helper methods

    def _doc_to_trace(self, doc: dict[str, Any]) -> Trace:
        """Convert a MongoDB document to a Trace object."""
        return Trace(
            trace_id=doc["trace_id"],
            name=doc["name"],
            status=TraceStatus(doc["status"]),
            start_time=datetime.fromisoformat(doc["start_time"]),
            end_time=datetime.fromisoformat(doc["end_time"]) if doc.get("end_time") else None,
            attributes=doc.get("attributes", {}),
            # Token metrics
            total_tokens=doc.get("total_tokens", 0) or 0,
            input_tokens=doc.get("input_tokens", 0) or 0,
            output_tokens=doc.get("output_tokens", 0) or 0,
            thoughts_tokens=doc.get("thoughts_tokens", 0) or 0,
            model=doc.get("model"),
        )

    def _doc_to_span(self, doc: dict[str, Any]) -> Span:
        """Convert a MongoDB document to a Span object."""
        return Span(
            span_id=doc["span_id"],
            trace_id=doc["trace_id"],
            parent_span_id=doc.get("parent_span_id"),
            name=doc["name"],
            kind=SpanKind(doc["kind"]),
            status=SpanStatus(doc["status"]),
            start_time=datetime.fromisoformat(doc["start_time"]),
            end_time=datetime.fromisoformat(doc["end_time"]) if doc.get("end_time") else None,
            duration_ms=doc.get("duration_ms"),
            attributes=doc.get("attributes", {}),
            error=doc.get("error"),
        )

    def _doc_to_log(self, doc: dict[str, Any]) -> Log:
        """Convert a MongoDB document to a Log object."""
        return Log(
            id=doc["id"],
            trace_id=doc["trace_id"],
            span_id=doc.get("span_id"),
            level=LogLevel(doc["level"]),
            message=doc["message"],
            attributes=doc.get("attributes", {}),
            timestamp=datetime.fromisoformat(doc["timestamp"]),
        )
