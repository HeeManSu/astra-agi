"""CSV reader for RAG pipeline."""

import csv
from io import StringIO
from pathlib import Path
from typing import Any

from framework.rag.readers.base import Reader
from framework.rag.vectordb.models import Document


class CSVReader(Reader):
    """Read CSV files and convert rows to documents.

    Example:
        reader = CSVReader()
        docs = await reader.read("/path/to/data.csv")

        # With custom options
        reader = CSVReader(row_as_document=True)
        docs = await reader.read("/path/to/data.csv")
    """

    def __init__(
        self,
        row_as_document: bool = True,
        delimiter: str = ",",
        include_headers: bool = True,
    ):
        """Initialize CSV reader.

        Args:
            row_as_document: If True, each row becomes a document.
                            If False, entire CSV becomes one document.
            delimiter: CSV delimiter character
            include_headers: Include header names with values
        """
        self.row_as_document = row_as_document
        self.delimiter = delimiter
        self.include_headers = include_headers

    def get_supported_formats(self) -> list[str]:
        """Return supported formats."""
        return [".csv", ".tsv"]

    async def read(self, source: Any, name: str | None = None) -> list[Document]:
        """Read CSV file.

        Args:
            source: Path to CSV file or CSV string
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
            doc_name = name or "csv_data"
            source_path = "string"

        documents: list[Document] = []
        reader = csv.DictReader(
            StringIO(content),
            delimiter=self.delimiter if self.delimiter != "\t" else "\t",
        )

        if self.row_as_document:
            # Each row becomes a document
            for row_num, row in enumerate(reader):
                if self.include_headers:
                    row_text = "\n".join(f"{k}: {v}" for k, v in row.items() if v)
                else:
                    row_text = " | ".join(v for v in row.values() if v)

                documents.append(
                    Document(
                        id=f"{doc_name}_row_{row_num}",
                        content=row_text,
                        metadata={
                            "source": source_path,
                            "name": doc_name,
                            "row": row_num,
                            "type": "csv",
                            "columns": list(row.keys()),
                        },
                    )
                )
        else:
            # Entire CSV as one document
            all_rows = []
            for row in reader:
                if self.include_headers:
                    row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                else:
                    row_text = " | ".join(v for v in row.values() if v)
                all_rows.append(row_text)

            documents.append(
                Document(
                    id=doc_name,
                    content="\n".join(all_rows),
                    metadata={
                        "source": source_path,
                        "name": doc_name,
                        "total_rows": len(all_rows),
                        "type": "csv",
                    },
                )
            )

        return documents
