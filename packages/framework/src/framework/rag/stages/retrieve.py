"""RetrieveStage - Retrieves relevant documents from vector database."""

from typing import TYPE_CHECKING, Literal

from framework.rag.context import StageState
from framework.rag.stages.base import Stage


if TYPE_CHECKING:
    from framework.rag.context import RagContext


class RetrieveStage(Stage):
    """Stage for retrieving documents (embedder/vector_db from RagContext)."""

    def __init__(self, top_k: int = 10, search_type: str = "vector"):
        self.top_k = top_k
        self.search_type = search_type

    @property
    def name(self) -> str:
        return "RetrieveStage"

    @property
    def stage_type(self) -> Literal["ingestion", "query", "both"]:
        return "query"

    async def process(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Retrieve relevant documents."""
        vector_db = rag_context.vector_db
        embedder = rag_context.embedder

        if not state.query:
            state.add_error("No query provided")
            return state

        # Get query embedding if not already done
        if state.query_embedding is None:
            embeddings = await embedder.embed([state.query])
            if embeddings:
                state.query_embedding = embeddings[0]

        # Get top_k from state metadata or use stage default
        top_k = state.metadata.get("top_k", self.top_k)

        # Query vector database
        results = await vector_db.search(query=state.query, limit=top_k)

        state.results = results
        return state
