"""Reader factory for automatic reader selection."""

from pathlib import Path

from framework.rag.readers.base import Reader
from framework.rag.readers.text_reader import TextReader


class ReaderFactory:
    """Factory for creating and selecting appropriate readers."""

    _readers: dict[str, type[Reader]] = {}

    @classmethod
    def register(cls, extension: str, reader_class: type[Reader]) -> None:
        """
        Register a reader for a file extension.

        Args:
            extension: File extension (e.g., ".pdf", ".txt")
            reader_class: Reader class
        """
        cls._readers[extension.lower()] = reader_class

    @classmethod
    def get_reader_for_path(cls, path: str | Path) -> Reader:
        """
        Get appropriate reader for a file path.

        Args:
            path: File path

        Returns:
            Reader instance
        """
        path_obj = Path(path)
        extension = path_obj.suffix.lower()

        if extension in cls._readers:
            return cls._readers[extension]()

        return TextReader()

    @classmethod
    def get_reader_for_url(cls, url: str) -> Reader:
        """
        Get appropriate reader for a URL.

        Args:
            url: URL string

        Returns:
            Reader instance (defaults to TextReader for now)
        """
        return TextReader()

    @classmethod
    def get_reader_for_text(cls) -> Reader:
        """Get reader for plain text content."""
        return TextReader()


# Register default readers
ReaderFactory.register(".txt", TextReader)
ReaderFactory.register(".text", TextReader)
