"""Contents database implementations."""

from framework.KnowledgeBase.contents_db.base import ContentsDB
from framework.KnowledgeBase.contents_db.in_memory import InMemoryContentsDB


__all__ = ["ContentsDB", "InMemoryContentsDB"]
