"""Storage abstraction layer for Limca."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageProvider(Protocol):
    """Protocol for storage providers.

    Storage providers handle persistence for different data types:
    - index: Symbol tables, call graphs, import graphs
    - wiki: Generated wiki pages and cache
    - embeddings: Vector embeddings for semantic search
    """

    async def get(self, key: str) -> Any | None:
        """Retrieve a value by key."""
        ...

    async def set(self, key: str, value: Any) -> None:
        """Store a value by key."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete a value by key. Returns True if deleted."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix filter."""
        ...


class InMemoryStorage:
    """Simple in-memory storage for development/testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def list_keys(self, prefix: str = "") -> list[str]:
        return [k for k in self._data if k.startswith(prefix)]


class FileStorage:
    """File-based storage using JSON files."""

    def __init__(self, base_path: str) -> None:
        import os

        self._base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        import os

        # Sanitize key to be filesystem-safe
        safe_key = key.replace("/", "_").replace("\\", "_")
        return os.path.join(self._base_path, f"{safe_key}.json")

    async def get(self, key: str) -> Any | None:
        import json
        import os

        path = self._key_to_path(key)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    async def set(self, key: str, value: Any) -> None:
        import json

        path = self._key_to_path(key)
        with open(path, "w") as f:
            json.dump(value, f, indent=2)

    async def delete(self, key: str) -> bool:
        import os

        path = self._key_to_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def exists(self, key: str) -> bool:
        import os

        return os.path.exists(self._key_to_path(key))

    async def list_keys(self, prefix: str = "") -> list[str]:
        import os

        keys = []
        for fname in os.listdir(self._base_path):
            if fname.endswith(".json"):
                key = fname[:-5]  # Remove .json
                if key.startswith(prefix):
                    keys.append(key)
        return keys
