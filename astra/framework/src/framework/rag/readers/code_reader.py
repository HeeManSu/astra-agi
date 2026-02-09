"""CodeReader - Reads code files and extracts semantic units using tree-sitter."""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Parser
import tree_sitter_python as tspython

from framework.rag.readers.base import Reader
from framework.rag.vectordb.models import Document


PY_LANGUAGE = Language(tspython.language())


class CodeReader(Reader):
    """Reads Python files and splits into semantic units (functions, classes)."""

    def __init__(self):
        self.parser = Parser(PY_LANGUAGE)

    async def read(self, source: str, name: str | None = None) -> list[Document]:
        """Read a Python file and extract functions/classes as documents.

        Args:
            source: File path to read
            name: Optional name override

        Returns:
            List of Documents, one per function/class
        """
        path = Path(source)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8")
        tree = self.parser.parse(content.encode())

        documents: list[Document] = []
        file_name = name or path.name

        # Extract functions and classes
        for node in self._walk_tree(tree.root_node):
            if node.type in ("function_definition", "class_definition"):
                doc = self._node_to_document(node, content, path, file_name)
                if doc:
                    documents.append(doc)

        # If no functions/classes, return whole file as one document
        if not documents:
            documents.append(
                Document(
                    content=content,
                    name=file_name,
                    source=str(path),
                    metadata={"type": "file", "file_path": str(path)},
                )
            )

        return documents

    def _walk_tree(self, node: Any):
        """Walk tree and yield function/class nodes."""
        yield node
        for child in node.children:
            yield from self._walk_tree(child)

    def _node_to_document(
        self, node: Any, content: str, path: Path, file_name: str
    ) -> Document | None:
        """Convert AST node to Document."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        node_content = content[start_byte:end_byte]

        # Get name
        name_node = node.child_by_field_name("name")
        symbol_name = name_node.text.decode() if name_node else "unknown"

        # Get line range
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        # Extract calls for index
        calls = self._extract_calls(node)

        return Document(
            content=node_content,
            name=f"{file_name}:{symbol_name}",
            source=str(path),
            metadata={
                "type": node.type.replace("_definition", ""),
                "symbol_name": symbol_name,
                "file_path": str(path),
                "line_start": start_line,
                "line_end": end_line,
                "calls": calls,
            },
        )

    def _extract_calls(self, node: Any) -> list[str]:
        """Extract function calls from a node."""
        calls = []
        for child in self._walk_tree(node):
            if child.type == "call":
                func = child.child_by_field_name("function")
                if func:
                    calls.append(func.text.decode())
        return list(set(calls))
