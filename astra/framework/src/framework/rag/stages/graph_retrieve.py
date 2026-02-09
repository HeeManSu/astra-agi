"""Graph retrieval stage for RAG pipeline."""

from typing import Any

from framework.rag.stages.base import Stage


class GraphRetrieveStage(Stage):
    """Expand retrieval results using graph relationships.

    After vector similarity retrieval, uses graph to find related content.

    Example:
        query_pipeline = Pipeline(
            name="query",
            stages=[
                RetrieveStage(top_k=5),           # Vector search
                GraphRetrieveStage(graph_db, hops=1),  # Expand via graph
            ]
        )
    """

    def __init__(self, graph_db: Any, hops: int = 1, include_content: bool = True):
        """Initialize GraphRetrieveStage.

        Args:
            graph_db: GraphDB instance
            hops: Number of graph traversal hops
            include_content: Whether to include neighbor content in results
        """
        from framework.rag.graphdb.base import GraphDB

        if not isinstance(graph_db, GraphDB):
            raise TypeError("graph_db must be a GraphDB instance")

        self.graph_db = graph_db
        self.hops = hops
        self.include_content = include_content

    async def process(self, state: Any) -> Any:
        """Expand results with graph-connected nodes."""
        expanded = []
        seen_ids = set()

        # Get IDs from retrieved documents
        for doc in state.documents:
            seen_ids.add(doc.id)

        # Traverse graph for each retrieved doc
        for doc in state.documents:
            neighbors = await self._get_neighbors_recursive(doc.id, self.hops, seen_ids)
            expanded.extend(neighbors)

        # Add expanded content to state context
        state.context["graph_expanded"] = [
            {
                "id": node.id,
                "label": node.label,
                "content": node.properties.get("content", ""),
                "source": node.properties.get("doc_id", ""),
            }
            for node in expanded
        ]

        return state

    async def _get_neighbors_recursive(
        self,
        node_id: str,
        remaining_hops: int,
        seen: set,
    ) -> list:
        """Recursively get neighbors up to N hops."""
        if remaining_hops <= 0:
            return []

        neighbors = await self.graph_db.get_neighbors(node_id, direction="both")
        result = []

        for neighbor in neighbors:
            if neighbor.id not in seen:
                seen.add(neighbor.id)
                result.append(neighbor)

                if remaining_hops > 1:
                    deeper = await self._get_neighbors_recursive(
                        neighbor.id, remaining_hops - 1, seen
                    )
                    result.extend(deeper)

        return result
