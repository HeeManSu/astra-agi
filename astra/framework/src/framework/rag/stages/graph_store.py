"""Graph storage stage for RAG pipeline."""

from typing import Any

from framework.rag.stages.base import Stage


class GraphStoreStage(Stage):
    """Store documents and relationships in graph database.

    This stage runs after vectordb storage to add graph structure.

    Example:
        from framework.rag.graphdb import KuzuGraphDB

        graph_db = KuzuGraphDB("./graph")
        await graph_db.connect()

        pipeline = Pipeline(
            name="ingest",
            stages=[
                ReadStage(),
                ChunkStage(),
                EmbedStage(),
                StoreStage(),
                GraphStoreStage(graph_db),  # Add graph storage
            ]
        )
    """

    def __init__(self, graph_db: Any, extract_relations: bool = False):
        """Initialize GraphStoreStage.

        Args:
            graph_db: GraphDB instance
            extract_relations: Whether to extract entity relations (requires LLM)
        """
        from framework.rag.graphdb.base import GraphDB

        if not isinstance(graph_db, GraphDB):
            raise TypeError("graph_db must be a GraphDB instance")

        self.graph_db = graph_db
        self.extract_relations = extract_relations

    async def process(self, state: Any) -> Any:
        """Store documents as graph nodes with relationships."""
        from framework.rag.graphdb.base import Edge, Node

        for doc in state.documents:
            # 1. Store document node
            doc_node = Node(
                id=doc.id,
                label="Document",
                properties={
                    "name": doc.name,
                    "source": getattr(doc, "source", None),
                    "metadata": doc.metadata,
                },
            )
            await self.graph_db.add_node(doc_node)

            # 2. Store each chunk as node with CONTAINS edge
            chunks = getattr(doc, "chunks", [])
            prev_chunk_id = None

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.id}_chunk_{i}"
                chunk_node = Node(
                    id=chunk_id,
                    label="Chunk",
                    properties={
                        "content": getattr(chunk, "content", str(chunk)),
                        "index": i,
                        "doc_id": doc.id,
                    },
                )
                await self.graph_db.add_node(chunk_node)

                # Document -> Chunk (CONTAINS)
                await self.graph_db.add_edge(
                    Edge(
                        source_id=doc.id,
                        target_id=chunk_id,
                        label="CONTAINS",
                        properties={"index": i},
                    )
                )

                # Chunk -> Chunk (NEXT) for sequential access
                if prev_chunk_id:
                    await self.graph_db.add_edge(
                        Edge(
                            source_id=prev_chunk_id,
                            target_id=chunk_id,
                            label="NEXT",
                            properties={},
                        )
                    )
                prev_chunk_id = chunk_id

        return state
