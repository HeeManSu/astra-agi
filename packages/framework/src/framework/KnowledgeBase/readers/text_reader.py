"""Text file reader."""

from pathlib import Path
from typing import Any

from framework.KnowledgeBase.models import Document
from framework.KnowledgeBase.readers.base import Reader


class TextReader(Reader):
    """Reader for plain text files."""

    async def read(self, source: Any, name: str | None = None) -> list[Document]:
        """
        Read text content from source.

        Args:
            source: File path (Path or str) or text content (str)
            name: Optional name for the content

        Returns:
            List containing a single Document
        """
        if isinstance(source, (Path, str)):
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            content = path.read_text(encoding="utf-8")
            doc_name = name or path.name
        elif isinstance(source, str):
            content = source
            doc_name = name or "text_content"
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")

        return [
            Document(
                content=content,
                name=doc_name,
                source=str(source) if isinstance(source, (Path, str)) else None,
                metadata={"type": "text"},
            )
        ]

    def get_supported_formats(self) -> list[str]:
        """Get supported formats."""
        return [".txt", ".text", "text/plain"]
