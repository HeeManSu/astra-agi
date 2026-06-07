# Limca: Code Intelligence Agent

Limca is a deterministic code intelligence engine that uses static analysis (Tree-sitter) to build symbol tables and call graphs, enabling LLMs to navigate codebases accurately without hallucinations.

## Architecture

```
User Query → LLM Planner → AST Analysis / Graph Traversal → LLM Synthesis → Answer
```

- **No Embeddings**: Uses real code structure, not vector similarity.
- **Symbol Resolution**: Resolves `self.method` to fully qualified names (FQNs).
- **Multi-hop Traversal**: Traces execution flow across files.

## Directory Structure

```
limca/
├── agent.py                 # Agent definition
├── core/
│   ├── parser.py            # AST parsing (Python/JS/TS)
│   ├── indexer.py           # Indexing orchestration
│   ├── resolver.py          # Symbol resolution logic
│   ├── symbols.py           # Symbol table
│   ├── call_graph.py        # Call graph
│   ├── import_graph.py      # Import graph
│   └── traversal.py         # Graph traversal
├── sources/
│   └── local.py             # Local file loader
└── tools/
    └── code_tools.py        # Agent tools
```

## Setup & usage

1. **Install dependencies**:

   ```bash
   uv pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript
   ```

2. **Run Verification**:

   ```bash
   # From examples/limca directory
   uv run test_limca_full.py
   ```

3. **Use Agent**:

   ```python
   from limca.agent import limca_agent

   # Index a codebase
   await limca_agent.run("Index the current directory")

   # Ask questions
   await limca_agent.run("Trace the flow of index_codebase function")
   ```
