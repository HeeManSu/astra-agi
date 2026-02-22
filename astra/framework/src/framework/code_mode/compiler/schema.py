"""Top-level DSL workflow schema for Astra.

A ``DslWorkflow`` is the complete, serializable representation of a
workflow graph.  It holds:

  - Typed state schema (what data flows through the graph)
  - Ordered list of nodes
  - Ordered list of edges
  - Entry point, global config, and version metadata

This is the unit that gets validated, serialized to JSON, persisted,
and handed to the deterministic executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from framework.code_mode.compiler.edges import DslEdge, EdgeRole, EdgeType
from framework.code_mode.compiler.nodes import DslNode


# ── State schema
@dataclass
class StateField:
    """A single field in the workflow's typed state schema.

    Attributes:
        name:     Field name (must be a valid Python identifier).
        type:     Type tag — "string", "number", "boolean", "list", "dict", "any".
        required: Whether the field must be present at workflow start.
        default:  Default value if not provided.
    """

    name: str
    type: str = "any"  # "string" | "number" | "boolean" | "list" | "dict" | "any"
    required: bool = False
    default: Any = None


# ── Workflow config
@dataclass
class WorkflowConfig:
    """Global configuration for a workflow execution.

    Attributes:
        max_execution_seconds: Hard cap on total workflow wall-clock time.
        max_nodes:             Safety limit on total node visits (journal entries).
                               Loop-heavy workflows need this higher than graph size
                               because visits = loop_count x items x body_nodes.
        max_visits_per_node:   Max times a single node can be visited.  Catches true
                               infinite loops (same node re-entered) without false-
                               positiving on valid large workflows.  0 = unlimited.
        checkpoint_strategy:   When to auto-checkpoint — "on_gate", "every_node", "manual".
        allow_replan:          Whether ReplanNodes are permitted to fire.
        max_replans:           Global cap on total re-plan invocations.
        state_size_limit_mb:   Warn at 80 %, hard-fail above 100 % of this limit.
                               Set to 0 to disable the check.
    """

    max_execution_seconds: int = 300
    max_nodes: int = 10_000  # total visits (was 100 — too blunt for loops)
    max_visits_per_node: int = 5_000  # per-node visit cap (0 = unlimited)
    checkpoint_strategy: str = "on_gate"  # "on_gate" | "every_node" | "manual"
    allow_replan: bool = True
    max_replans: int = 2
    state_size_limit_mb: int = 50  # 0 = unlimited


# ── Top-level workflow
@dataclass
class DslWorkflow:
    """Complete DSL workflow graph — the unit of validation and execution.

    Attributes:
        workflow_id: Unique identifier for this workflow definition.
        version:     Semver string for versioning.
        name:        Human-readable workflow name.
        description: What this workflow does.
        state:       Typed state schema — fields that flow through the graph.
        nodes:       Ordered list of all nodes in the graph.
        edges:       Ordered list of all edges connecting the nodes.
        entry:       Node ID where execution begins.
        config:      Global execution config (timeouts, limits, checkpoints).
    """

    name: str = ""
    description: str = ""
    workflow_id: str = field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    version: str = "1.0.0"

    # Graph structure
    state: list[StateField] = field(default_factory=list)
    nodes: list[DslNode] = field(default_factory=list)
    edges: list[DslEdge] = field(default_factory=list)
    entry: str = ""  # node id where execution starts

    # Config
    config: WorkflowConfig = field(default_factory=WorkflowConfig)

    # ── Node lookup helpers
    def get_node(self, node_id: str) -> DslNode | None:
        """Find a node by id, or None."""
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def node_ids(self) -> set[str]:
        """Return the set of all node IDs in this workflow."""
        return {n.id for n in self.nodes}

    # ── Edge lookup helpers
    def outgoing_edges(self, node_id: str) -> list[DslEdge]:
        """All edges leaving a node, sorted by priority."""
        return sorted(
            [e for e in self.edges if e.source == node_id],
            key=lambda e: e.priority,
        )

    def incoming_edges(self, node_id: str) -> list[DslEdge]:
        """All edges arriving at a node."""
        return [e for e in self.edges if e.target == node_id]

    def edge_by_role(self, node_id: str, role: EdgeRole) -> DslEdge | None:
        """Find outgoing edge with a specific role from a node.

        Returns the first matching edge, or None if no edge with that
        role exists for the given node.
        """
        for e in self.outgoing_edges(node_id):
            if e.role == role:
                return e
        return None

    # ── Structural queries
    def terminal_nodes(self) -> list[DslNode]:
        """Nodes with no outgoing edges (graph sinks)."""
        sources_with_edges = {e.source for e in self.edges}
        return [n for n in self.nodes if n.id not in sources_with_edges]

    def root_nodes(self) -> list[DslNode]:
        """Nodes with no incoming edges (graph sources)."""
        targets_with_edges = {e.target for e in self.edges}
        return [n for n in self.nodes if n.id not in targets_with_edges]

    # ── Validation helpers
    def validate_structure(self) -> list[str]:
        """Run basic structural checks and return a list of error messages.

        Checks:
          1. Entry node exists
          2. All edge sources/targets reference existing nodes
          3. No duplicate node IDs
          4. At least one RespondNode or TerminateNode exists
          5. All nodes are reachable from entry
        """
        errors: list[str] = []
        ids = self.node_ids()

        # 1. Entry node
        if not self.entry:
            errors.append("No entry node specified")
        elif self.entry not in ids:
            errors.append(f"Entry node '{self.entry}' does not exist")

        # 2. Edge references
        for edge in self.edges:
            if edge.source not in ids:
                errors.append(f"Edge '{edge.id}' references unknown source '{edge.source}'")
            if edge.target not in ids:
                errors.append(f"Edge '{edge.id}' references unknown target '{edge.target}'")
            # Conditional edges must have a condition
            if edge.type == EdgeType.CONDITIONAL and not edge.condition:
                errors.append(f"Conditional edge '{edge.id}' is missing a condition expression")

        # 3. Duplicate IDs
        seen: set[str] = set()
        for n in self.nodes:
            if n.id in seen:
                errors.append(f"Duplicate node ID: '{n.id}'")
            seen.add(n.id)

        # 4. Terminal node check
        from framework.code_mode.compiler.nodes import NodeType

        has_terminal = any(n.type in (NodeType.RESPOND, NodeType.TERMINATE) for n in self.nodes)
        if not has_terminal:
            errors.append("Workflow must have at least one RespondNode or TerminateNode")

        # 5. Reachability from entry
        if self.entry and self.entry in ids:
            reachable = self._reachable_from(self.entry)
            unreachable = ids - reachable
            errors.extend(f"Node '{uid}' is not reachable from entry" for uid in unreachable)

        return errors

    def _reachable_from(self, start: str) -> set[str]:
        """BFS to find all nodes reachable from ``start``."""
        visited: set[str] = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(
                edge.target
                for edge in self.edges
                if edge.source == current and edge.target not in visited
            )
        return visited

    def summary(self) -> str:
        """One-line summary for logs and debugging."""
        return (
            f"DslWorkflow('{self.name}', "
            f"{len(self.nodes)} nodes, "
            f"{len(self.edges)} edges, "
            f"entry='{self.entry}')"
        )
