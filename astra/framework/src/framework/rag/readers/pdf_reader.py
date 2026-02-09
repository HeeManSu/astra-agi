"""PDF reader for RAG pipeline."""

from pathlib import Path
from typing import Any

from framework.rag.readers.base import Reader
from framework.rag.vectordb.models import Document


class PDFReader(Reader):
    """Read PDF files and extract text content.

    Example:
        reader = PDFReader()
        docs = await reader.read("/path/to/document.pdf")
    """

    def get_supported_formats(self) -> list[str]:
        """Return supported formats."""
        return [".pdf"]

    async def read(self, source: Any, name: str | None = None) -> list[Document]:
        """Read PDF file and extract text.

        Args:
            source: Path to PDF file
            name: Optional name for the document

        Returns:
            List of Document objects (one per page or entire document)
        """
        try:
            import pypdf
        except ImportError as e:
            raise ImportError("pypdf not installed. Run: pip install pypdf") from e

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {source}")

        doc_name = name or path.stem
        documents: list[Document] = []

        # Use BytesIO to avoid blocking open() in async context
        from io import BytesIO

        pdf_bytes = path.read_bytes()
        pdf = pypdf.PdfReader(BytesIO(pdf_bytes))

        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                documents.append(
                    Document(
                        id=f"{doc_name}_page_{page_num}",
                        content=text,
                        metadata={
                            "source": str(path),
                            "name": doc_name,
                            "page": page_num,
                            "total_pages": len(pdf.pages),
                            "type": "pdf",
                        },
                    )
                )

        return documents
