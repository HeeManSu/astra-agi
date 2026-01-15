"""Text file reader."""

from pathlib import Path
from typing import Any

from framework.rag.readers.base import Reader
from framework.rag.vectordb.models import Document


class TextReader(Reader):
    """Reader for plain text files and raw text content."""

    async def read(self, source: Any, name: str | None = None) -> list[Document]:
        """
        Read text content from source.

        Args:
            source: File path (Path or str) or raw text content (str)
            name: Optional name for the content

        Returns:
            List containing a single Document
        """
        if isinstance(source, Path):
            # Explicit Path object - read from file
            if not source.exists():
                raise FileNotFoundError(f"File not found: {source}")
            content = source.read_text(encoding="utf-8")
            doc_name = name or source.name
            doc_source = str(source)
        elif isinstance(source, str):
            # String could be file path or raw text - check if it's a valid path
            if self._is_file_path(source):
                path = Path(source)
                content = path.read_text(encoding="utf-8")
                doc_name = name or path.name
                doc_source = source
            else:
                # Treat as raw text content
                content = source
                doc_name = name or "text_content"
                # Truncate source for long text content
                doc_source = source[:100] + "..." if len(source) > 100 else source
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")

        return [
            Document(
                content=content,
                name=doc_name,
                source=doc_source,
                metadata={"type": "text"},
            )
        ]

    def _is_file_path(self, source: str) -> bool:
        """Check if source string is a valid file path."""
        # Quick checks to avoid OS errors on long strings
        if len(source) > 260:  # Max path length on most systems
            return False
        if "\n" in source or "\r" in source:  # Text content typically has newlines
            return False
        try:
            return Path(source).exists()
        except OSError:
            return False

    def get_supported_formats(self) -> list[str]:
        """Get supported formats."""
        return [".txt", ".text", "text/plain"]
