"""Rag - High-level RAG orchestrator.

The Rag class provides a user-friendly API for RAG operations,
using two internal pipelines for ingestion and query.

Example:
    context = RagContext(
        embedder=HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2"),
        vector_db=LanceDB(uri="./my_kb"),
    )

    ingest_pipeline = Pipeline(
        name="ingest",
        stages=[ReadStage(), ChunkStage(...), EmbedStage(), StoreStage()],
    )

    query_pipeline = Pipeline(
        name="query",
        stages=[RetrieveStage(top_k=5)],
    )

    rag = Rag(
        context=context,
        ingest_pipeline=ingest_pipeline,
        query_pipeline=query_pipeline,
    )

    await rag.ingest("./docs")
    results = await rag.query("How does Astra handle agent memory?")
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from framework.rag.context import RagContext, StageState
from framework.rag.exceptions import (
    RagIngestionError,
    RagQueryError,
)
from observability import (
    LogLevel,
    is_debug_mode,
    log,
    preview,
    span,
    update_span,
)


if TYPE_CHECKING:
    from framework.rag.stages.base import Stage


class Pipeline:
    """Generic pipeline that executes stages sequentially.

    A Pipeline wraps a list of stages and executes them in order,
    passing both the StageState (mutable data) and RagContext
    (shared dependencies) to each stage.
    """

    def __init__(self, name: str, stages: list["Stage"]):
        """Initialize Pipeline.

        Args:
            name: Human-readable name for this pipeline (e.g., "ingest", "query")
            stages: List of Stage instances to execute in order
        """
        self.name = name
        self.stages = stages

    async def execute(self, stage_state: StageState, rag_context: RagContext) -> StageState:
        """Execute all stages sequentially, injecting shared context."""
        async with span(
            f"rag.pipeline.{self.name}",
            attributes={"pipeline_name": self.name, "stage_count": len(self.stages)},
        ):
            for stage in self.stages:
                async with span(
                    f"rag.stage.{stage.name}",
                    attributes={"stage_name": stage.name, "pipeline": self.name},
                ):
                    stage_state = await stage.process(stage_state, rag_context)
                    stage_state.mark_stage_complete(stage.name)
                    update_span(
                        {
                            "result_count": len(getattr(stage_state, "results", []) or []),
                            "error_count": len(getattr(stage_state, "errors", []) or []),
                        }
                    )
            return stage_state

    def __repr__(self) -> str:
        stage_names = [s.name for s in self.stages]
        return f"Pipeline(name='{self.name}', stages={stage_names})"


class Rag:
    """High-level RAG orchestrator.

    Rag wraps two internal pipelines (ingest and query) and
    provides a simple API for RAG operations.
    """

    def __init__(
        self,
        context: RagContext,
        ingest_pipeline: Pipeline,
        query_pipeline: Pipeline,
    ):
        """Initialize Rag.

        Args:
            context: Shared dependencies (embedder, vector_db, config)
            ingest_pipeline: Pipeline for ingestion stages
            query_pipeline: Pipeline for query stages
        """
        self.context = context
        self.ingest_pipeline = ingest_pipeline
        self.query_pipeline = query_pipeline
        self.max_results = context.config.get("default_top_k", 5)

    async def ingest(
        self,
        path: str | Path | None = None,
        url: str | None = None,
        text: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Ingest content into the pipeline.

        Args:
            path: File path to ingest
            url: URL to fetch and ingest
            text: Raw text to ingest
            name: Name for the content
            metadata: Additional metadata

        Returns:
            Content ID
        """
        # Determine source
        if path:
            source = str(path)
        elif url:
            source = url
        elif text:
            source = "text"
        else:
            raise ValueError("Must provide path, url, or text")

        debug = is_debug_mode()
        async with span(
            "rag.ingest",
            attributes={
                "source": source,
                "source_type": "path" if path else ("url" if url else "text"),
                "name": name or "",
                "content_length": len(text or ""),
            },
        ):
            stage_state = StageState(
                source=source,
                raw_content=text,
                metadata=metadata or {},
            )

            if name:
                stage_state.metadata["name"] = name

            try:
                stage_state = await self.ingest_pipeline.execute(stage_state, self.context)
                if stage_state.has_errors():
                    error_details = "; ".join(stage_state.errors)
                    await log(LogLevel.ERROR, "RAG ingestion failed", {"errors": error_details})
                    raise RagIngestionError(
                        f"Ingestion failed: {error_details}",
                        suggestion=f"Check the source content at: {source}",
                    )
            except RagIngestionError:
                raise
            except Exception as e:
                await log(LogLevel.ERROR, f"RAG ingestion unexpected error: {e}")
                raise RagIngestionError(
                    f"Unexpected error during ingestion: {e!s}",
                    suggestion="Check logs for more details",
                ) from e

            content_id = stage_state.metadata.get("content_id", "unknown")
            update_span(
                {
                    "content_id": content_id,
                    "stage_count": len(self.ingest_pipeline.stages),
                    **(
                        {"raw_content_preview": preview(text or "")}
                        if debug and text
                        else {}
                    ),
                }
            )
            await log(LogLevel.INFO, "RAG ingest complete", {"content_id": content_id})
            return content_id

    async def ingest_batch(self, items: list[dict[str, Any]]) -> list[str]:
        """Ingest multiple items in batch."""
        content_ids = []
        for item in items:
            try:
                content_id = await self.ingest(**item)
                content_ids.append(content_id)
            except Exception as e:
                content_ids.append(f"error: {e}")
        return content_ids

    async def ingest_directory(
        self,
        directory: str | Path,
        pattern: str = "*.txt",
        recursive: bool = False,
    ) -> list[str]:
        """Ingest all files in a directory."""
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            raise ValueError(f"Directory not found: {directory}")

        files = dir_path.rglob(pattern) if recursive else dir_path.glob(pattern)
        items = [{"path": str(f), "name": f.name} for f in files if f.is_file()]

        return await self.ingest_batch(items)

    async def query(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Query the pipeline.

        Args:
            query: Query string
            top_k: Number of results (default: max_results from config)
            filters: Optional metadata filters

        Returns:
            List of matching documents
        """
        debug = is_debug_mode()
        async with span(
            "rag.query",
            attributes={
                "query_text_preview": preview(query),
                "top_k": top_k or self.max_results,
                "filter_count": len(filters or {}),
                **({"query_text_full": query} if debug else {}),
            },
        ):
            stage_state = StageState(
                query=query,
                metadata={
                    "top_k": top_k or self.max_results,
                    "filters": filters or {},
                },
            )

            try:
                stage_state = await self.query_pipeline.execute(stage_state, self.context)
                if stage_state.has_errors():
                    error_details = "; ".join(stage_state.errors)
                    await log(LogLevel.ERROR, "RAG query failed", {"errors": error_details})
                    raise RagQueryError(
                        f"Query failed: {error_details}",
                        suggestion="Ensure content has been ingested before querying",
                    )
            except RagQueryError:
                raise
            except Exception as e:
                await log(LogLevel.ERROR, f"RAG query unexpected error: {e}")
                raise RagQueryError(
                    f"Unexpected error during query: {e!s}",
                    suggestion="Check logs for more details",
                ) from e

            update_span(
                {
                    "result_count": len(stage_state.results or []),
                    **(
                        {"top_results_preview": preview(stage_state.results[:3])}
                        if debug and stage_state.results
                        else {}
                    ),
                }
            )
            await log(
                LogLevel.INFO,
                "RAG query complete",
                {"result_count": len(stage_state.results or [])},
            )
            return stage_state.results
