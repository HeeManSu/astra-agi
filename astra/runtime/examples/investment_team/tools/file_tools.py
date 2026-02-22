"""
File Tools for Astra Framework.

Wraps filesystem operations as Astra Tool instances, scoped to a configurable base directory.
Matches Agno's FileTools functionality used by knowledge_agent and memo_writer.

Integration: These are pure Python tools — no API keys needed.
They use pathlib to read/write/list/search files on the local filesystem,
restricted to a base_dir for safety (prevents path traversal).

IMPORTANT: Each call to make_file_tools() must use a unique `prefix` so that
tool slugs remain unique across agents (the server enforces global slug uniqueness).
Example:
    knowledge_agent tools: "knowledge_read_file", "knowledge_list_files", ...
    memo_writer tools:     "memo_read_file",      "memo_list_files", ...
"""

import json
from pathlib import Path

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# 1. read_file
# ──────────────────────────────────────────────


class ReadFileInput(BaseModel):
    file_name: str = Field(description="Name or relative path of the file to read")


class ReadFileOutput(BaseModel):
    result: str = Field(description="File contents or error message")


def make_read_file(base_dir: Path, prefix: str):
    """Create a read_file tool scoped to a specific directory."""
    resolved_base = base_dir.resolve()
    spec = ToolSpec(
        name=f"{prefix}_read_file",
        description="Reads the contents of a file and returns them. Use this to read memos and documents.",
        input_schema=ReadFileInput,
        output_schema=ReadFileOutput,
    )

    @bind_tool(spec)
    def read_file(input: ReadFileInput) -> ReadFileOutput:
        try:
            file_path = (resolved_base / input.file_name).resolve()
            if not str(file_path).startswith(str(resolved_base)):
                return ReadFileOutput(result="Error: path traversal not allowed")
            if not file_path.exists():
                return ReadFileOutput(result=f"File not found: {input.file_name}")
            contents = file_path.read_text(encoding="utf-8")
            return ReadFileOutput(result=contents)
        except Exception as e:
            return ReadFileOutput(result=f"Error reading file: {e}")

    return read_file


# ──────────────────────────────────────────────
# 2. list_files
# ──────────────────────────────────────────────


class ListFilesInput(BaseModel):
    directory: str = Field(default=".", description="Subdirectory to list (default: root)")


class ListFilesOutput(BaseModel):
    result: str = Field(description="JSON list of file names or error message")


def make_list_files(base_dir: Path, prefix: str):
    """Create a list_files tool scoped to a specific directory."""
    resolved_base = base_dir.resolve()
    spec = ToolSpec(
        name=f"{prefix}_list_files",
        description="Returns a list of files in the directory. Use this to see what memos are available.",
        input_schema=ListFilesInput,
        output_schema=ListFilesOutput,
    )

    @bind_tool(spec)
    def list_files(input: ListFilesInput) -> ListFilesOutput:
        try:
            target = (resolved_base / input.directory).resolve()
            if not str(target).startswith(str(resolved_base)):
                return ListFilesOutput(result="Error: path traversal not allowed")
            if not target.exists():
                return ListFilesOutput(result=f"Directory not found: {input.directory}")
            files = [str(p.relative_to(resolved_base)) for p in target.iterdir()]
            return ListFilesOutput(result=json.dumps(files, indent=2))
        except Exception as e:
            return ListFilesOutput(result=f"Error listing files: {e}")

    return list_files


# ──────────────────────────────────────────────
# 3. search_files
# ──────────────────────────────────────────────


class SearchFilesInput(BaseModel):
    pattern: str = Field(description='Glob pattern to search for, e.g. "*.md", "nvda*"')


class SearchFilesOutput(BaseModel):
    result: str = Field(description="JSON with matching file paths or error message")


def make_search_files(base_dir: Path, prefix: str):
    """Create a search_files tool scoped to a specific directory."""
    resolved_base = base_dir.resolve()
    spec = ToolSpec(
        name=f"{prefix}_search_files",
        description="Searches for files matching a glob pattern. Use this to find specific memos.",
        input_schema=SearchFilesInput,
        output_schema=SearchFilesOutput,
    )

    @bind_tool(spec)
    def search_files(input: SearchFilesInput) -> SearchFilesOutput:
        try:
            if not input.pattern or not input.pattern.strip():
                return SearchFilesOutput(result="Error: pattern cannot be empty")
            matches = list(resolved_base.glob(input.pattern))
            file_paths = [str(p.relative_to(resolved_base)) for p in matches]
            result = {
                "pattern": input.pattern,
                "matches_found": len(file_paths),
                "files": file_paths,
            }
            return SearchFilesOutput(result=json.dumps(result, indent=2))
        except Exception as e:
            return SearchFilesOutput(result=f"Error searching files: {e}")

    return search_files


# ──────────────────────────────────────────────
# 4. save_file
# ──────────────────────────────────────────────


class SaveFileInput(BaseModel):
    file_name: str = Field(description="Name or relative path of the file to save")
    contents: str = Field(description="Contents to write to the file")
    overwrite: bool = Field(default=True, description="Overwrite if file already exists")


class SaveFileOutput(BaseModel):
    result: str = Field(description="File name if successful, error message otherwise")


def make_save_file(base_dir: Path, prefix: str):
    """Create a save_file tool scoped to a specific directory."""
    resolved_base = base_dir.resolve()
    spec = ToolSpec(
        name=f"{prefix}_save_file",
        description="Saves contents to a file. Use this to write investment memos.",
        input_schema=SaveFileInput,
        output_schema=SaveFileOutput,
    )

    @bind_tool(spec)
    def save_file(input: SaveFileInput) -> SaveFileOutput:
        try:
            file_path = (resolved_base / input.file_name).resolve()
            if not str(file_path).startswith(str(resolved_base)):
                return SaveFileOutput(result="Error: path traversal not allowed")
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.exists() and not input.overwrite:
                return SaveFileOutput(result=f"File {input.file_name} already exists")
            file_path.write_text(input.contents, encoding="utf-8")
            return SaveFileOutput(result=str(input.file_name))
        except Exception as e:
            return SaveFileOutput(result=f"Error saving file: {e}")

    return save_file


def make_file_tools(base_dir: Path, prefix: str, writable: bool = False) -> list:
    """
    Create a set of file tools scoped to base_dir with a unique prefix.

    Args:
        base_dir: Root directory for file operations
        prefix:   Agent-specific prefix to namespace tool slugs (e.g. "knowledge", "memo")
                  This MUST be unique per agent to avoid duplicate slug errors.
        writable: If True, includes save_file. If False, read-only.

    Returns:
        List of bound tool functions ready to pass to an Agent
    """
    tools = [
        make_read_file(base_dir, prefix),
        make_list_files(base_dir, prefix),
        make_search_files(base_dir, prefix),
    ]
    if writable:
        tools.append(make_save_file(base_dir, prefix))
    return tools
