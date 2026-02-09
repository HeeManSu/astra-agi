# ruff: noqa: TID252
"""Code intelligence tools for Limca agent."""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


# ============ INDEX CODEBASE ============
class IndexCodebaseInput(BaseModel):
    """Input for indexing a codebase."""

    path: str = Field(
        description="Path to the codebase - can be an absolute local path (e.g., '/path/to/project') "
        "OR a GitHub URL (e.g., 'https://github.com/user/repo'). GitHub repos will be cloned automatically."
    )


class IndexCodebaseOutput(BaseModel):
    """Output from codebase indexing."""

    path: str = Field(description="Path that was indexed")
    files_indexed: int = Field(description="Number of files parsed")
    symbols_count: int = Field(description="Number of symbols extracted")
    calls_count: int = Field(description="Number of call edges found")
    unresolved_calls: int = Field(description="Number of unresolved calls")
    parse_errors: int = Field(description="Number of parse errors")


INDEX_CODEBASE_SPEC = ToolSpec(
    name="index_codebase",
    description="Parse a codebase and build symbol table, call graph, and import graph for code analysis",
    input_schema=IndexCodebaseInput,
    output_schema=IndexCodebaseOutput,
)


@bind_tool(INDEX_CODEBASE_SPEC)
def index_codebase(input: IndexCodebaseInput) -> IndexCodebaseOutput:
    """Index a codebase from a local path."""
    from ..core.indexer import index_codebase as _index

    result = _index(input.path)
    return IndexCodebaseOutput(**result)


# ============ FIND SYMBOL ============
class FindSymbolInput(BaseModel):
    """Input for finding symbols."""

    query: str = Field(
        description="Symbol name or FQN to search for (e.g., 'LoginView', 'auth.views')"
    )


class SymbolInfo(BaseModel):
    """Information about a symbol."""

    fqn: str = Field(description="Fully qualified name")
    name: str = Field(description="Short name")
    type: str = Field(description="Symbol type: class, function, method")
    file: str = Field(description="File path")
    line_start: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")


class FindSymbolOutput(BaseModel):
    """Output from symbol search."""

    symbols: list[SymbolInfo] = Field(description="Matching symbols")


FIND_SYMBOL_SPEC = ToolSpec(
    name="find_symbol",
    description="Find symbols matching a query by name or fully qualified name",
    input_schema=FindSymbolInput,
    output_schema=FindSymbolOutput,
)


@bind_tool(FIND_SYMBOL_SPEC)
def find_symbol(input: FindSymbolInput) -> FindSymbolOutput:
    """Find symbols matching a query."""
    from ..core.indexer import find_symbol as _find

    results = _find(input.query)
    return FindSymbolOutput(symbols=[SymbolInfo(**s) for s in results])


# ============ TRACE CALLS ============
class TraceCallsInput(BaseModel):
    """Input for tracing call graph."""

    symbol: str = Field(description="Symbol name or FQN to trace from")
    depth: int = Field(default=3, description="How many levels to traverse (max 5)")


class TraceCallsOutput(BaseModel):
    """Output from call tracing."""

    entry: str = Field(description="Entry symbol FQN")
    tree: dict = Field(description="Call tree structure")
    files: list[str] = Field(description="Files touched")
    symbols_visited: int = Field(description="Number of symbols visited")
    truncated: bool = Field(description="True if traversal hit limits")
    error: str | None = Field(default=None, description="Error message if failed")


TRACE_CALLS_SPEC = ToolSpec(
    name="trace_calls",
    description="Trace call graph from a symbol, showing what functions/methods are called",
    input_schema=TraceCallsInput,
    output_schema=TraceCallsOutput,
)


@bind_tool(TRACE_CALLS_SPEC)
def trace_calls(input: TraceCallsInput) -> TraceCallsOutput:
    """Trace call graph from a symbol."""
    from ..core.indexer import trace_calls as _trace

    result = _trace(input.symbol, input.depth)
    if "error" in result:
        return TraceCallsOutput(
            entry="",
            tree={},
            files=[],
            symbols_visited=0,
            truncated=False,
            error=result["error"],
        )
    return TraceCallsOutput(
        entry=result["entry"],
        tree=result["tree"],
        files=result["files"],
        symbols_visited=result["symbols_visited"],
        truncated=result["truncated"],
    )


# ============ FIND REFERENCES ============
class FindReferencesInput(BaseModel):
    """Input for finding references."""

    symbol: str = Field(description="Symbol name or FQN to find references for")


class ReferenceInfo(BaseModel):
    """Information about a reference."""

    caller: str = Field(description="Caller FQN")
    file: str = Field(description="File path")
    line: int = Field(description="Line number")


class FindReferencesOutput(BaseModel):
    """Output from reference search."""

    symbol: str = Field(description="Symbol searched")
    references: list[ReferenceInfo] = Field(description="List of references")
    count: int = Field(description="Number of references")
    error: str | None = Field(default=None, description="Error message if failed")


FIND_REFERENCES_SPEC = ToolSpec(
    name="find_references",
    description="Find all usages of a symbol - shows where this function/method/class is called",
    input_schema=FindReferencesInput,
    output_schema=FindReferencesOutput,
)


@bind_tool(FIND_REFERENCES_SPEC)
def find_references(input: FindReferencesInput) -> FindReferencesOutput:
    """Find all usages of a symbol."""
    from ..core.indexer import find_references as _refs

    result = _refs(input.symbol)
    if "error" in result:
        return FindReferencesOutput(symbol="", references=[], count=0, error=result["error"])
    return FindReferencesOutput(
        symbol=result["symbol"],
        references=[ReferenceInfo(**r) for r in result["references"]],
        count=result["count"],
    )


# ============ GET FILE SNIPPET ============
class GetFileSnippetInput(BaseModel):
    """Input for getting code snippets."""

    file: str = Field(description="Relative file path from codebase root")
    start_line: int = Field(description="Starting line number (1-indexed)")
    end_line: int | None = Field(
        default=None, description="Ending line number (default: start_line + 20)"
    )


class GetFileSnippetOutput(BaseModel):
    """Output from snippet retrieval."""

    file: str = Field(description="File path")
    start_line: int = Field(description="Start line")
    end_line: int = Field(description="End line")
    content: str = Field(description="Code snippet with line numbers")
    error: str | None = Field(default=None, description="Error message if failed")


GET_FILE_SNIPPET_SPEC = ToolSpec(
    name="get_file_snippet",
    description="Get a code snippet from a file with line numbers",
    input_schema=GetFileSnippetInput,
    output_schema=GetFileSnippetOutput,
)


@bind_tool(GET_FILE_SNIPPET_SPEC)
def get_file_snippet(input: GetFileSnippetInput) -> GetFileSnippetOutput:
    """Get a code snippet from a file."""
    from ..core.indexer import get_file_snippet as _snippet

    result = _snippet(input.file, input.start_line, input.end_line)
    if "error" in result:
        return GetFileSnippetOutput(
            file="", start_line=0, end_line=0, content="", error=result["error"]
        )
    return GetFileSnippetOutput(
        file=result["file"],
        start_line=result["start_line"],
        end_line=result["end_line"],
        content=result["content"],
    )


# ============ GET CLASS HIERARCHY ============
class GetClassHierarchyInput(BaseModel):
    """Input for class hierarchy."""

    class_name: str = Field(description="Class name or FQN to analyze")


class GetClassHierarchyOutput(BaseModel):
    """Output from class hierarchy analysis."""

    class_info: dict = Field(description="Class details")
    parent: str | None = Field(description="Parent class FQN")
    children: list[dict] = Field(description="Child classes")
    methods: list[dict] = Field(description="Methods in the class")
    error: str | None = Field(default=None, description="Error message if failed")


GET_CLASS_HIERARCHY_SPEC = ToolSpec(
    name="get_class_hierarchy",
    description="Get inheritance hierarchy for a class - shows parent, children, and methods",
    input_schema=GetClassHierarchyInput,
    output_schema=GetClassHierarchyOutput,
)


@bind_tool(GET_CLASS_HIERARCHY_SPEC)
def get_class_hierarchy(input: GetClassHierarchyInput) -> GetClassHierarchyOutput:
    """Get class hierarchy."""
    from ..core.indexer import get_class_hierarchy as _hierarchy

    result = _hierarchy(input.class_name)
    if "error" in result:
        return GetClassHierarchyOutput(
            class_info={}, parent=None, children=[], methods=[], error=result["error"]
        )
    return GetClassHierarchyOutput(
        class_info=result["class"],
        parent=result["parent"],
        children=result["children"],
        methods=result["methods"],
    )


# ============ FIND IMPORTS ============
class FindImportsInput(BaseModel):
    """Input for finding imports."""

    target: str = Field(description="File path or symbol name to find imports for")


class FindImportsOutput(BaseModel):
    """Output from import analysis."""

    target: str = Field(description="Target analyzed")
    target_type: str = Field(description="'file' or 'symbol'")
    imports: list[str] = Field(description="Direct imports")
    all_dependencies: list[str] = Field(default=[], description="All transitive dependencies")
    error: str | None = Field(default=None, description="Error message if failed")


FIND_IMPORTS_SPEC = ToolSpec(
    name="find_imports",
    description="Find what modules a file or symbol depends on (imports)",
    input_schema=FindImportsInput,
    output_schema=FindImportsOutput,
)


@bind_tool(FIND_IMPORTS_SPEC)
def find_imports(input: FindImportsInput) -> FindImportsOutput:
    """Find imports for a target."""
    from ..core.indexer import find_imports as _imports

    result = _imports(input.target)
    if "error" in result:
        return FindImportsOutput(target="", target_type="", imports=[], error=result["error"])

    # Explicit type handling to satisfy type checker
    imports_list: list[str] = result.get("direct_imports") or result.get("imports") or []
    deps_list: list[str] = result.get("all_dependencies") or []

    return FindImportsOutput(
        target=result["target"],
        target_type=result["type"],
        imports=imports_list,
        all_dependencies=deps_list,
    )


# ============ GENERATE DIAGRAM ============
class GenerateDiagramInput(BaseModel):
    """Input for diagram generation."""

    diagram_type: str = Field(
        description="Type of diagram: 'class' (class hierarchy), 'call' (call graph), 'imports' (dependencies), 'overview' (architecture)"
    )
    target: str | None = Field(
        default=None, description="Optional target symbol/file for focused diagrams"
    )


class GenerateDiagramOutput(BaseModel):
    """Output from diagram generation."""

    diagram_type: str = Field(description="Type of diagram generated")
    mermaid: str = Field(description="Mermaid diagram code (render in markdown)")
    error: str | None = Field(default=None, description="Error message if failed")


GENERATE_DIAGRAM_SPEC = ToolSpec(
    name="generate_diagram",
    description="Generate a Mermaid visualization diagram - supports class hierarchies, call graphs, import dependencies, and architecture overviews",
    input_schema=GenerateDiagramInput,
    output_schema=GenerateDiagramOutput,
)


@bind_tool(GENERATE_DIAGRAM_SPEC)
def generate_diagram(input: GenerateDiagramInput) -> GenerateDiagramOutput:
    """Generate a Mermaid diagram."""
    from ..core.indexer import generate_diagram as _diagram

    result = _diagram(input.diagram_type, input.target)
    if "error" in result:
        return GenerateDiagramOutput(diagram_type="", mermaid="", error=result["error"])
    return GenerateDiagramOutput(
        diagram_type=result["diagram_type"],
        mermaid=result["mermaid"],
    )


# ============ GENERATE WIKI ============
class GenerateWikiInput(BaseModel):
    """Input for generating wiki documentation."""

    repo_path: str = Field(description="Path to the repository (must be indexed first)")
    output_dir: str | None = Field(
        default=None,
        description="Output directory for wiki pages (defaults to .limca/wiki/)",
    )


class GenerateWikiOutput(BaseModel):
    """Output from wiki generation."""

    pages_generated: int = Field(description="Number of wiki pages created")
    output_dir: str = Field(description="Directory where pages were written")
    pages: list[str] = Field(description="List of generated page titles")
    error: str | None = Field(default=None, description="Error message if failed")


GENERATE_WIKI_SPEC = ToolSpec(
    name="generate_wiki",
    description="Generate hierarchical wiki documentation for an indexed codebase. Creates markdown pages with architecture diagrams and source citations.",
    input_schema=GenerateWikiInput,
    output_schema=GenerateWikiOutput,
)


@bind_tool(GENERATE_WIKI_SPEC)
def generate_wiki(input: GenerateWikiInput) -> GenerateWikiOutput:
    """Generate wiki documentation from indexed codebase."""
    import os

    from ..config import load_config
    from ..core.indexer import get_index
    from ..wiki import WikiGenerator, WikiPlanner

    try:
        # Check if indexed
        index = get_index()
        if not index:
            return GenerateWikiOutput(
                pages_generated=0,
                output_dir="",
                pages=[],
                error="Codebase not indexed. Run index_codebase first.",
            )

        # Load config
        config = load_config(input.repo_path)

        # Plan pages
        planner = WikiPlanner(config.wiki)
        config_plans = planner.plan_from_config()
        auto_plans = planner.plan_from_index(index)
        plans = planner.merge_plans(config_plans, auto_plans)

        # Generate wiki
        output_dir = input.output_dir or os.path.join(input.repo_path, ".limca", "wiki")
        generator = WikiGenerator(
            output_dir=output_dir,
            index=index,
            repo_notes=[n.model_dump() for n in config.wiki.repo_notes],
        )

        generated_paths = generator.generate_all(plans)

        return GenerateWikiOutput(
            pages_generated=len(generated_paths),
            output_dir=output_dir,
            pages=[p.title for p in plans],
        )

    except Exception as e:
        return GenerateWikiOutput(
            pages_generated=0,
            output_dir="",
            pages=[],
            error=str(e),
        )
