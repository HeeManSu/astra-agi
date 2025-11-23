from typing import Generic, TypeVar
from ..base import StorageBackend

T = TypeVar("T")

class BaseStore(Generic[T]):
    """Base class for domain stores."""
    
    def __init__(self, storage: StorageBackend):
        self.storage = storage
