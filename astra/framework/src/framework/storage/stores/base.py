"""
Base store abstractions for Astra storage layer.

Provides a generic BaseStore that:
- Wraps an StorageBackend backend
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Table

from framework.storage.base import StorageBackend
from framework.storage.databases.mongodb import MongoDBStorage


TModel = TypeVar("TModel", bound=BaseModel)


class BaseStore(Generic[TModel]):
    """
    Generic base store for a single data domain (threads, messages, etc).

    Responsibilities:
    - Provide CRUD helpers on top of StorageBackend
    - Convert DB rows → Pydantic models
    - Handle database-agnostic operations
    """

    def __init__(
        self,
        storage: StorageBackend,
        model_cls: type[TModel],
        collection_name: str,
        table: Table | None = None,
    ) -> None:
        self._storage = storage
        self._table = table
        self._model_cls = model_cls
        self._collection_name = collection_name

    @property
    def storage(self) -> StorageBackend:
        return self._storage

    @property
    def table(self) -> Table | None:
        """SQLAlchemy Table object and None for MongoDB."""
        return self._table

    @property
    def model_cls(self) -> type[TModel]:
        return self._model_cls

    @property
    def collection_name(self) -> str:
        """Database-agnostic collection/table name."""
        return self._collection_name

    def _row_to_model(self, row: dict[str, Any]) -> TModel:
        """
        Convert a DB row dict → Pydantic model.

        Handles database-specific conversions:
        - MongoDB: Converts _id (ObjectId) to id (string)
        - SQL: Keeps id as is
        """
        row_data = dict(row)

        # MongoDB uses _id as primary key, convert to id for our models
        if "_id" in row_data:
            row_data["id"] = str(row_data.pop("_id"))

        if "metadata" in row_data and row_data["metadata"] is None:
            row_data["metadata"] = {}

        return self._model_cls(**row_data)

    def _prepare_document(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare document for insertion.

        For MongoDB: Remove id field, let MongoDB auto-generate _id
        For SQL: Keep id as is
        """
        doc = dict(data)

        if isinstance(self._storage, MongoDBStorage):
            # MongoDB auto-generates _id, so remove any id field
            doc.pop("id", None)
            doc.pop("_id", None)

        return doc
