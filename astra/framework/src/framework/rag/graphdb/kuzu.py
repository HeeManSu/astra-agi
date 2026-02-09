"""KuzuDB implementation of GraphDB."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from framework.rag.graphdb.base import Edge, GraphDB, Node


if TYPE_CHECKING:
    import kuzu


class KuzuGraphDB(GraphDB):
    """KuzuDB-based graph database for RAG.

    KuzuDB is an embedded graph database (like SQLite for graphs).
    No server needed - data stored locally.

    Example:
        graph = KuzuGraphDB("./my_graph")
        await graph.connect()

        await graph.add_node(Node(id="doc1", label="Document", properties={"name": "README"}))
        await graph.add_node(Node(id="chunk1", label="Chunk", properties={"content": "..."}))
        await graph.add_edge(Edge(source_id="doc1", target_id="chunk1", label="CONTAINS"))

        neighbors = await graph.get_neighbors("doc1", direction="out")
    """

    NODE_TABLES: ClassVar[list[str]] = ["Document", "Chunk", "Entity"]
    EDGE_TYPES: ClassVar[list[str]] = ["CONTAINS", "MENTIONS", "RELATES_TO", "NEXT", "REFERENCES"]

    def __init__(self, db_path: str):
        """Initialize KuzuDB.

        Args:
            db_path: Path to database directory
        """
        self.db_path = db_path
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None
        self._initialized = False

    @property
    def conn(self) -> kuzu.Connection:
        """Get connection, raising if not connected."""
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    async def connect(self) -> None:
        """Initialize database and create schema."""
        try:
            import kuzu
        except ImportError as e:
            raise ImportError("kuzu not installed. Run: pip install kuzu") from e

        self._db = kuzu.Database(self.db_path)
        self._conn = kuzu.Connection(self._db)
        self._init_schema()
        self._initialized = True

    def _execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute query and return single QueryResult.

        Handles the case where execute() returns QueryResult | list[QueryResult].
        """
        result = self.conn.execute(query, params or {})
        # execute() can return list for multi-statement queries
        if isinstance(result, list):
            return result[0] if result else None
        return result

    def _init_schema(self) -> None:
        """Create node and edge tables if they don't exist."""
        conn = self.conn

        # Create node tables
        for table in self.NODE_TABLES:
            self._try_create_node_table(conn, table)

        # Create edge tables for all combinations
        for edge in self.EDGE_TYPES:
            for src in self.NODE_TABLES:
                for tgt in self.NODE_TABLES:
                    self._try_create_edge_table(conn, edge, src, tgt)

    def _try_create_node_table(self, conn: kuzu.Connection, table: str) -> None:
        """Try to create a node table, ignoring if exists."""
        try:
            conn.execute(f"""
                CREATE NODE TABLE IF NOT EXISTS {table} (
                    id STRING PRIMARY KEY,
                    properties STRING
                )
            """)
        except Exception:
            pass  # Table might already exist

    def _try_create_edge_table(self, conn: kuzu.Connection, edge: str, src: str, tgt: str) -> None:
        """Try to create an edge table, ignoring if exists."""
        try:
            conn.execute(f"""
                CREATE REL TABLE IF NOT EXISTS {edge}_{src}_{tgt} (
                    FROM {src} TO {tgt},
                    properties STRING
                )
            """)
        except Exception:
            pass  # Table might already exist

    async def close(self) -> None:
        """Close database connection."""
        self._conn = None
        self._db = None
        self._initialized = False

    def _ensure_connected(self) -> None:
        """Ensure database is connected."""
        if not self._initialized or self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

    async def add_node(self, node: Node) -> str:
        """Add a node to the graph."""
        self._ensure_connected()
        conn = self.conn
        props_json = json.dumps(node.properties)

        try:
            conn.execute(
                f"CREATE (:{node.label} {{id: $id, properties: $props}})",
                {"id": node.id, "props": props_json},
            )
        except Exception:
            # Node might exist - update it
            conn.execute(
                f"MATCH (n:{node.label} {{id: $id}}) SET n.properties = $props",
                {"id": node.id, "props": props_json},
            )

        return node.id

    async def add_edge(self, edge: Edge) -> str:
        """Add an edge between two nodes."""
        self._ensure_connected()
        conn = self.conn
        props_json = json.dumps(edge.properties)

        # Find source and target node tables
        src_table = await self._find_node_table(edge.source_id)
        tgt_table = await self._find_node_table(edge.target_id)

        if not src_table or not tgt_table:
            raise ValueError(f"Source or target node not found: {edge.source_id}, {edge.target_id}")

        rel_table = f"{edge.label}_{src_table}_{tgt_table}"

        conn.execute(
            f"MATCH (a:{src_table} {{id: $src}}), (b:{tgt_table} {{id: $tgt}}) "
            f"CREATE (a)-[:{rel_table} {{properties: $props}}]->(b)",
            {"src": edge.source_id, "tgt": edge.target_id, "props": props_json},
        )

        return f"{edge.source_id}->{edge.target_id}"

    async def _find_node_table(self, node_id: str) -> str | None:
        """Find which table a node belongs to."""
        for table in self.NODE_TABLES:
            result = self._execute(
                f"MATCH (n:{table} {{id: $id}}) RETURN n.id",
                {"id": node_id},
            )
            if result and result.has_next():
                return table
        return None

    async def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        self._ensure_connected()

        for table in self.NODE_TABLES:
            result = self._execute(
                f"MATCH (n:{table} {{id: $id}}) RETURN n.id, n.properties",
                {"id": node_id},
            )
            if result and result.has_next():
                row = result.get_next()
                return Node(
                    id=str(row[0]),
                    label=table,
                    properties=json.loads(str(row[1])) if row[1] else {},
                )
        return None

    async def get_neighbors(
        self,
        node_id: str,
        edge_label: str | None = None,
        direction: str = "both",
    ) -> list[Node]:
        """Get neighboring nodes."""
        self._ensure_connected()

        src_table = await self._find_node_table(node_id)
        if not src_table:
            return []

        neighbors: list[Node] = []

        for tgt_table in self.NODE_TABLES:
            if edge_label:
                rel_out = f"{edge_label}_{src_table}_{tgt_table}"
                rel_in = f"{edge_label}_{tgt_table}_{src_table}"
            else:
                rel_out = ""
                rel_in = ""

            try:
                if direction in ("out", "both"):
                    rel_pattern = f":{rel_out}" if rel_out else ""
                    query = (
                        f"MATCH (a:{src_table} {{id: $id}})-[r{rel_pattern}]->(b:{tgt_table}) "
                        f"RETURN b.id, b.properties"
                    )
                    result = self._execute(query, {"id": node_id})
                    if result:
                        while result.has_next():
                            row = result.get_next()
                            neighbors.append(
                                Node(
                                    id=str(row[0]),
                                    label=tgt_table,
                                    properties=json.loads(str(row[1])) if row[1] else {},
                                )
                            )

                if direction in ("in", "both"):
                    rel_pattern = f":{rel_in}" if rel_in else ""
                    query = (
                        f"MATCH (a:{src_table} {{id: $id}})<-[r{rel_pattern}]-(b:{tgt_table}) "
                        f"RETURN b.id, b.properties"
                    )
                    result = self._execute(query, {"id": node_id})
                    if result:
                        while result.has_next():
                            row = result.get_next()
                            neighbors.append(
                                Node(
                                    id=str(row[0]),
                                    label=tgt_table,
                                    properties=json.loads(str(row[1])) if row[1] else {},
                                )
                            )
            except Exception:
                continue  # Skip if relation table doesn't exist

        return neighbors

    async def query(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query."""
        self._ensure_connected()

        result = self._execute(cypher, params)
        rows: list[dict[str, Any]] = []
        if result:
            while result.has_next():
                row = result.get_next()
                # Convert list to dict with string keys
                rows.append({str(i): v for i, v in enumerate(row)})
        return rows

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges."""
        self._ensure_connected()
        conn = self.conn

        table = await self._find_node_table(node_id)
        if not table:
            return False

        conn.execute(
            f"MATCH (n:{table} {{id: $id}}) DETACH DELETE n",
            {"id": node_id},
        )
        return True

    async def clear(self) -> None:
        """Clear all nodes and edges."""
        self._ensure_connected()
        conn = self.conn

        for table in self.NODE_TABLES:
            self._try_clear_table(conn, table)

    def _try_clear_table(self, conn: kuzu.Connection, table: str) -> None:
        """Try to clear a table, ignoring errors."""
        try:
            conn.execute(f"MATCH (n:{table}) DETACH DELETE n")
        except Exception:
            pass
