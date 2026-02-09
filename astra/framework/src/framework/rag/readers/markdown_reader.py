"""Markdown reader for RAG pipeline."""

from pathlib import Path
import re
from typing import Any

from framework.rag.readers.base import Reader
from framework.rag.vectordb.models import Document


class MarkdownReader(Reader):
    """Read Markdown files with optional section splitting.

    Example:
        reader = MarkdownReader()
        docs = await reader.read("/path/to/README.md")

        # Split by headers
        reader = MarkdownReader(split_by_headers=True)
        docs = await reader.read("/path/to/README.md")
    """

    def __init__(
        self,
        split_by_headers: bool = False,
        min_header_level: int = 1,
        max_header_level: int = 2,
    ):
        """Initialize Markdown reader.

        Args:
            split_by_headers: If True, split document by headers
            min_header_level: Minimum header level to split on (1 = #)
            max_header_level: Maximum header level to split on (2 = ##)
        """
        self.split_by_headers = split_by_headers
        self.min_header_level = min_header_level
        self.max_header_level = max_header_level

    def get_supported_formats(self) -> list[str]:
        """Return supported formats."""
        return [".md", ".markdown"]

    async def read(self, source: Any, name: str | None = None) -> list[Document]:
        """Read Markdown file.

        Args:
            source: Path to Markdown file or Markdown string
            name: Optional name for the document

        Returns:
            List of Document objects
        """
        # Handle file path or string content
        if isinstance(source, (str, Path)) and Path(source).exists():
            path = Path(source)
            doc_name = name or path.stem
            content = path.read_text(encoding="utf-8")
            source_path = str(path)
        else:
            content = str(source)
            doc_name = name or "markdown"
            source_path = "string"

        if self.split_by_headers:
            return self._split_by_headers(content, doc_name, source_path)

        # Return as single document
        return [
            Document(
                id=doc_name,
                content=content,
                metadata={
                    "source": source_path,
                    "name": doc_name,
                    "type": "markdown",
                },
            )
        ]

    def _split_by_headers(self, content: str, doc_name: str, source_path: str) -> list[Document]:
        """Split markdown content by headers."""
        documents: list[Document] = []

        # Build regex for header levels
        levels = "|".join("#" * i for i in range(self.min_header_level, self.max_header_level + 1))
        pattern = rf"^({levels})\s+(.+)$"

        sections: list[tuple[str, str]] = []
        current_header = ""
        current_content: list[str] = []

        for line in content.split("\n"):
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                # Save previous section
                if current_content:
                    sections.append((current_header, "\n".join(current_content)))
                current_header = match.group(2).strip()
                current_content = [line]
            else:
                current_content.append(line)

        # Don't forget the last section
        if current_content:
            sections.append((current_header, "\n".join(current_content)))

        for i, (header, section_content) in enumerate(sections):
            if not section_content.strip():
                continue

            section_id = header.lower().replace(" ", "_")[:50] if header else f"section_{i}"
            documents.append(
                Document(
                    id=f"{doc_name}_{section_id}",
                    content=section_content,
                    metadata={
                        "source": source_path,
                        "name": doc_name,
                        "section": header or f"Section {i}",
                        "section_index": i,
                        "type": "markdown",
                    },
                )
            )

        return documents
