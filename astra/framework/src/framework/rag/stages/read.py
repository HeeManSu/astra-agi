"""ReadStage - Reads content from various sources."""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from framework.rag.context import StageState
from framework.rag.stages.base import Stage


if TYPE_CHECKING:
    from framework.rag.context import RagContext


class ReadStage(Stage):
    """Stage for reading content from files, URLs, or text."""

    def __init__(self, formats: list[str] | None = None):
        self.formats = formats or ["txt", "md", "pdf"]

    @property
    def name(self) -> str:
        return "ReadStage"

    @property
    def stage_type(self) -> Literal["ingestion", "query", "both"]:
        return "ingestion"

    async def process(self, state: StageState, rag_context: "RagContext") -> StageState:
        """Read content from source."""
        from framework.rag.readers.factory import ReaderFactory

        source = state.source
        raw_content = state.raw_content

        if source == "text" and raw_content:
            from framework.rag.readers import TextReader

            reader = TextReader()
            documents = await reader.read(
                source=raw_content,
                name=state.metadata.get("name", "text_content"),
            )
        elif source:
            path = Path(source) if not source.startswith(("http://", "https://")) else None

            if path and path.exists():
                reader = ReaderFactory.get_reader_for_path(str(path))
                documents = await reader.read(
                    source=str(path),
                    name=state.metadata.get("name", path.name),
                )
            else:
                from framework.rag.readers import TextReader

                reader = TextReader()
                documents = await reader.read(
                    source=source,
                    name=state.metadata.get("name", "content"),
                )
        else:
            state.add_error("No source provided to ReadStage")
            return state

        state.documents = documents
        return state
