"""
Base store abstractions for Astra storage layer.

Provides a generic BaseStore that:
- Wraps an StorageBackend backend
- Knows which SQLAlchemy table to use
- Knows how to hydrate Pydantic models from DB rows
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from framework.storage.base import StorageBackend


TModel = TypeVar("TModel", bound=BaseModel)


class BaseStore(Generic[TModel]):
    """
    Generic base store for a single data domain (threads, messages, etc).

    Responsibilities:
    - Provide CRUD helpers on top of StorageBackend
    - Convert DB rows → Pydantic models
    """

    def __init__(
        self,
        storage: StorageBackend,
        model_cls: type[TModel],
    ) -> None:
        self._storage = storage
        self._model_cls = model_cls

    @property
    def storage(self) -> StorageBackend:
        return self._storage

    @property
    def model_cls(self) -> type[TModel]:
        return self._model_cls

    def _row_to_model(self, row: dict[str, Any]) -> TModel:
        """Convert a DB row dict → Pydantic model."""
        # Handle None metadata (convert to empty dict)
        row_data = dict(row)
        if "metadata" in row_data and row_data["metadata"] is None:
            row_data["metadata"] = {}
        return self._model_cls(**row_data)
