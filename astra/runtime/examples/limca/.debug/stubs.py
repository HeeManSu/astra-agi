# ═══════════════════════════════════════════════════════════════════════════════
# AVAILABLE TOOLS - Limca
# ═══════════════════════════════════════════════════════════════════════════════

class limca:
    """Repository Q/A agent with wiki-grounded responses"""

    @staticmethod
    def index_codebase(path: str) -> dict:
        """
        Parse a codebase and build symbol table, call graph, and import graph for code analysis

        Args:
            path: Path to the codebase - can be an absolute local path (e.g., '/path/to/project') OR a GitHub URL (e.g., 'https://github.com/user/repo'). GitHub repos will be cloned automatically. (required)

        Returns:
            dict with fields:
            - path (str): Path that was indexed
            - files_indexed (int): Number of files parsed
            - symbols_count (int): Number of symbols extracted
            - calls_count (int): Number of call edges found
            - unresolved_calls (int): Number of unresolved calls
            - parse_errors (int): Number of parse errors
        """
        ...

    @staticmethod
    def find_symbol(query: str) -> dict:
        """
        Find symbols matching a query by name or fully qualified name

        Args:
            query: Symbol name or FQN to search for (e.g., 'LoginView', 'auth.views') (required)

        Returns:
            dict with fields:
            - symbols (list): Matching symbols
        """
        ...

    @staticmethod
    def trace_calls(symbol: str, depth: int = 3) -> dict:
        """
        Trace call graph from a symbol, showing what functions/methods are called

        Args:
            symbol: Symbol name or FQN to trace from (required)
            depth: How many levels to traverse (max 5) (default: 3, required)

        Returns:
            dict with fields:
            - entry (str): Entry symbol FQN
            - tree (dict): Call tree structure
            - files (list): Files touched
            - symbols_visited (int): Number of symbols visited
            - truncated (bool): True if traversal hit limits
            - error (str | None): Error message if failed
        """
        ...

    @staticmethod
    def find_references(symbol: str) -> dict:
        """
        Find all usages of a symbol - shows where this function/method/class is called

        Args:
            symbol: Symbol name or FQN to find references for (required)

        Returns:
            dict with fields:
            - symbol (str): Symbol searched
            - references (list): List of references
            - count (int): Number of references
            - error (str | None): Error message if failed
        """
        ...

    @staticmethod
    def get_file_snippet(
        file: str,
        start_line: int,
        end_line: int | None | None = None,
    ) -> dict:
        """
        Get a code snippet from a file with line numbers

        Args:
            file: Relative file path from codebase root (required)
            start_line: Starting line number (1-indexed) (required)
            end_line: Ending line number (default: start_line + 20)

        Returns:
            dict with fields:
            - file (str): File path
            - start_line (int): Start line
            - end_line (int): End line
            - content (str): Code snippet with line numbers
            - error (str | None): Error message if failed
        """
        ...

    @staticmethod
    def get_class_hierarchy(class_name: str) -> dict:
        """
        Get inheritance hierarchy for a class - shows parent, children, and methods

        Args:
            class_name: Class name or FQN to analyze (required)

        Returns:
            dict with fields:
            - class_info (dict): Class details
            - parent (str | None): Parent class FQN
            - children (list): Child classes
            - methods (list): Methods in the class
            - error (str | None): Error message if failed
        """
        ...

    @staticmethod
    def find_imports(target: str) -> dict:
        """
        Find what modules a file or symbol depends on (imports)

        Args:
            target: File path or symbol name to find imports for (required)

        Returns:
            dict with fields:
            - target (str): Target analyzed
            - target_type (str): 'file' or 'symbol'
            - imports (list): Direct imports
            - all_dependencies (list): All transitive dependencies
            - error (str | None): Error message if failed
        """
        ...

    @staticmethod
    def generate_diagram(diagram_type: str, target: str | None | None = None) -> dict:
        """
        Generate a Mermaid visualization diagram - supports class hierarchies, call graphs, import dependencies, and architecture overviews

        Args:
            diagram_type: Type of diagram: 'class' (class hierarchy), 'call' (call graph), 'imports' (dependencies), 'overview' (architecture) (required)
            target: Optional target symbol/file for focused diagrams

        Returns:
            dict with fields:
            - diagram_type (str): Type of diagram generated
            - mermaid (str): Mermaid diagram code (render in markdown)
            - error (str | None): Error message if failed
        """
        ...

    @staticmethod
    def generate_wiki(repo_path: str, output_dir: str | None | None = None) -> dict:
        """
        Generate hierarchical wiki documentation for an indexed codebase. Creates markdown pages with architecture diagrams and source citations.

        Args:
            repo_path: Path to the repository (must be indexed first) (required)
            output_dir: Output directory for wiki pages (defaults to .limca/wiki/)

        Returns:
            dict with fields:
            - pages_generated (int): Number of wiki pages created
            - output_dir (str): Directory where pages were written
            - pages (list): List of generated page titles
            - error (str | None): Error message if failed
        """
        ...

