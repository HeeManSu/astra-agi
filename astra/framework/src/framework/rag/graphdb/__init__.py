"""
GraphDB - Graph database abstraction for RAG.

Provides storage for entity relationships alongside vector embeddings.
"""

from framework.rag.graphdb.base import Edge, GraphDB, Node
from framework.rag.graphdb.kuzu import KuzuGraphDB


__all__ = [
    "Edge",
    "GraphDB",
    "KuzuGraphDB",
    "Node",
]
