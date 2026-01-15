"""ChunkStage - Splits documents into smaller chunks."""

from typing import TYPE_CHECKING, Any, Literal

from framework.rag.context import StageState
from framework.rag.stages.base import Stage


if TYPE_CHECKING:
    from framework.rag.context import RagContext


class ChunkStage(Stage):
    """Stage for chunking documents."""

    def __init__(
        self,
        strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._chunker: Any = None

    @property
    def name(self) -> str:
        return "ChunkStage"

    @property
    def stage_type(self) -> Literal["ingestion", "query", "both"]:
        return "ingestion"

    def _get_chunker(self) -> Any:
        """Get or create chunker instance."""
        if self._chunker is None:
            from framework.rag.chunking.recursive import RecursiveChunking

            self._chunker = RecursiveChunking(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        return self._chunker

    async def process(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Chunk documents."""
        if not state.documents:
            state.add_error("No documents to chunk")
            return state

        chunker = self._get_chunker()
        all_chunks = []

        for doc in state.documents:
            chunks = await chunker.chunk(doc)
            all_chunks.extend(chunks)

        state.chunks = all_chunks
        return state
