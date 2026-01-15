"""EmbedStage - Generates embeddings for chunks."""

from typing import TYPE_CHECKING, Literal

from framework.rag.context import StageState
from framework.rag.stages.base import Stage


if TYPE_CHECKING:
    from framework.rag.context import RagContext


class EmbedStage(Stage):
    """Stage for generating embeddings (from RagContext)."""

    @property
    def name(self) -> str:
        return "EmbedStage"

    @property
    def stage_type(self) -> Literal["ingestion", "query", "both"]:
        return "both"

    async def process(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Generate embeddings using embedder from RagContext."""
        embedder = rag_context.embedder

        # Handle query embedding
        if state.query and not state.query_embedding:
            embeddings = await embedder.embed([state.query])
            if embeddings:
                state.query_embedding = embeddings[0]
            return state

        # Handle chunk embedding
        if not state.chunks:
            state.add_error("No chunks to embed")
            return state

        embeddings = []
        for chunk in state.chunks:
            result = await embedder.embed([chunk.content])
            if result:
                embedding = result[0]
                embeddings.append(embedding)
                chunk.embedding = embedding

        state.embeddings = embeddings
        return state
