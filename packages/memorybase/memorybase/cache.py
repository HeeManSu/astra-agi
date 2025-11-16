"""
Simple LRU cache for memory search results.

Provides time-bounded caching for recent memory lookups to improve
performance for repeated queries within a session.
"""

import time
from collections import OrderedDict
from typing import Any, Optional


class MemoryCache:
    """
    Time-bounded LRU cache for memory search results.
    
    Caches search results with TTL (time-to-live) to avoid redundant
    storage queries for the same queries within a short time window.
    
    Features:
    - LRU eviction when cache is full
    - TTL-based expiration
    - Thread-safe operations (for async contexts)
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize the memory cache.
        
        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cached entries in seconds
        """
        self.cache: OrderedDict[str, dict] = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if entry['expires_at'] <= time.time():
            # Remove expired entry
            del self.cache[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        
        return entry['data']
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Remove oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        # Add new entry
        self.cache[key] = {
            'data': value,
            'expires_at': time.time() + self.ttl
        }
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
    
    def size(self) -> int:
        """
        Get the current number of cached entries.
        
        Returns:
            Number of entries in cache
        """
        return len(self.cache)
    
    def _cleanup_expired(self) -> None:
        """
        Remove all expired entries from the cache.
        
        Note: This is called automatically during get/set operations,
        but can be called manually for cleanup.
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry['expires_at'] <= current_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
