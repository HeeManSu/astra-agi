"""Base class for RAG pipeline stages."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

from framework.rag.context import StageState


if TYPE_CHECKING:
    from framework.rag.context import RagContext


class Stage(ABC):
    """Base class for RAG pipeline stages.

    Stages can be used for ingestion (read, chunk, embed, store) or
    query (retrieve, rerank).

    Each stage receives:
    - StageState: Mutable data passed between stages
    - RagContext: Shared dependencies (embedder, vector_db, config)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this stage."""

    @property
    @abstractmethod
    def stage_type(self) -> Literal["ingestion", "query", "both"]:
        """What operations this stage supports."""

    @abstractmethod
    async def process(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Process data and return updated state."""

    async def __call__(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Allow stages to be called directly."""
        result = await self.process(state, rag_context)
        result.mark_stage_complete(self.name)
        return result
