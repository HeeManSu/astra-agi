"""Abstract base class for graph databases."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    """Graph node representing an entity."""

    id: str
    label: str  # Node type: "Document", "Chunk", "Entity"
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Graph edge representing a relationship."""

    source_id: str
    target_id: str
    label: str  # Edge type: "CONTAINS", "RELATES_TO", "REFERENCES"
    properties: dict[str, Any] = field(default_factory=dict)


class GraphDB(ABC):
    """Abstract base class for graph database implementations.

    Provides interface for storing and querying entity relationships.

    Example:
        graph = KuzuGraphDB("./graph_db")
        await graph.connect()

        # Add nodes
        await graph.add_node(Node(id="doc1", label="Document", properties={"name": "README"}))
        await graph.add_node(Node(id="chunk1", label="Chunk", properties={"content": "..."}))

        # Add relationship
        await graph.add_edge(Edge(source_id="doc1", target_id="chunk1", label="CONTAINS"))

        # Query neighbors
        chunks = await graph.get_neighbors("doc1", edge_label="CONTAINS", direction="out")
    """

    @abstractmethod
    async def connect(self) -> None:
        """Initialize database connection and schema."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""
        ...

    @abstractmethod
    async def add_node(self, node: Node) -> str:
        """Add a node to the graph.

        Args:
            node: Node to add

        Returns:
            Node ID
        """
        ...

    @abstractmethod
    async def add_edge(self, edge: Edge) -> str:
        """Add an edge between two nodes.

        Args:
            edge: Edge to add

        Returns:
            Edge identifier
        """
        ...

    @abstractmethod
    async def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        edge_label: str | None = None,
        direction: str = "both",
    ) -> list[Node]:
        """Get neighboring nodes.

        Args:
            node_id: Starting node ID
            edge_label: Filter by edge type (optional)
            direction: "in", "out", or "both"

        Returns:
            List of neighbor nodes
        """
        ...

    @abstractmethod
    async def query(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result rows
        """
        ...

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges.

        Args:
            node_id: Node to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all nodes and edges from the graph."""
        ...
