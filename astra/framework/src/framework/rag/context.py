"""Context classes for RAG pipeline.

RagContext: Shared dependencies (embedder, vector_db, config) injected into all stages.
StageState: Data passed between stages during pipeline execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RagContext:
    """Shared context containing all cross-cutting dependencies.

    This is the single source of truth for embedder, vector_db, and config.
    Stages read from this context instead of having their own instances.

    Example:
        context = RagContext(
            embedder=HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2"),
            vector_db=LanceDB(uri="./my_kb"),
            config={"default_top_k": 5},
        )
    """

    embedder: Any
    vector_db: Any
    config: Any


@dataclass
class StageState:
    """State passed between stages in the RAG pipeline.

    This state object carries data through the pipeline, allowing
    each stage to read from and write to shared state.
    """

    # === Ingestion State ===
    source: str | None = None  # Path, URL, or "text"
    raw_content: str | None = None
    documents: list[Any] = field(default_factory=list)
    chunks: list[Any] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)

    # === Query State ===
    query: str | None = None
    query_embedding: list[float] | None = None
    results: list[Any] = field(default_factory=list)

    # === Metadata ===
    metadata: dict[str, Any] = field(default_factory=dict)
    stages_completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def mark_stage_complete(self, stage_name: str) -> None:
        """Mark a stage as completed."""
        self.stages_completed.append(stage_name)

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
