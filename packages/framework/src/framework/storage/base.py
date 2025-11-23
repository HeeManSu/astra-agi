from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the storage backend."""
        pass
        
    @abstractmethod
    async def execute(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> None:
        """Execute a write query (INSERT, UPDATE, DELETE)."""
        pass
        
    @abstractmethod
    async def fetch_all(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Execute a read query and return all results."""
        pass
        
    @abstractmethod
    async def fetch_one(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """Execute a read query and return a single result."""
        pass
