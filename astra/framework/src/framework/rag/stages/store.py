"""StoreStage - Stores chunks and embeddings in vector database."""

from typing import TYPE_CHECKING, Literal
import uuid

from framework.rag.context import StageState
from framework.rag.stages.base import Stage


if TYPE_CHECKING:
    from framework.rag.context import RagContext


class StoreStage(Stage):
    """Stage for storing embeddings in vector database (from RagContext)."""

    @property
    def name(self) -> str:
        return "StoreStage"

    @property
    def stage_type(self) -> Literal["ingestion", "query", "both"]:
        return "ingestion"

    async def process(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Store chunks in vector database."""
        vector_db = rag_context.vector_db

        if not state.chunks:
            state.add_error("No chunks to store")
            return state

        # Generate content ID
        content_id = str(uuid.uuid4())
        state.metadata["content_id"] = content_id

        # Add content_id to each chunk
        for chunk in state.chunks:
            chunk.content_id = content_id

        # Store in vector database
        await vector_db.insert(state.chunks)

        return state
