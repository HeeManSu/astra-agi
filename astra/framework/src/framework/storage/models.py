from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Thread(BaseModel):
    """Represents a conversation thread."""

    id: str | None = None  # Auto-assigned by database
    resource_type: str  # "agent" | "team" | "stepper" | "workflow"
    resource_id: str  # The ID of the resource
    resource_name: str  # Human-readable name for display
    title: str  # Auto-set from first user message
    message_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_archived: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    """Represents a single message in a thread."""

    id: str | None = None  # Auto-assigned by database
    thread_id: str
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    sequence: int = 0
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "assistant", "system", "tool"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


# @TODO: Himanshu. PersistentFacts disabled for V1 release. Will be enabled later.
# class MemoryScope(str, Enum):
#     """
#     Memory scoping levels for persistent facts.
#
#     Scoping determines who can access and modify facts:
#
#     - USER: User-specific facts (most common)
#       Example: "User prefers dark mode", "User's name is John"
#       Scoped to: user_id (e.g., "[email protected]")
#       Persists: Across all sessions for that user
#
#     - SESSION: Session-specific facts (temporary)
#       Example: "Current task: writing report", "Session started at 2pm"
#       Scoped to: session_id or thread_id
#       Persists: Only within current session/thread
#
#     - AGENT: Agent-specific facts (shared across users)
#       Example: "Last maintenance: 2024-01-15", "Agent version: 1.0"
#       Scoped to: agent_id
#       Persists: Shared by all users of this agent
#
#     - GLOBAL: System-wide facts (shared by all)
#       Example: "System version: 1.0.0", "Maintenance window: Sundays"
#       Scoped to: None (global)
#       Persists: Shared by all agents and users
#     """
#
#     USER = "user"  # User-specific facts (e.g., preferences)
#     SESSION = "session"  # Session-specific facts (temporary)
#     AGENT = "agent"  # Agent-specific facts (shared across users)
#     GLOBAL = "global"  # System-wide facts (shared by all)
#
#
# class Fact(BaseModel):
#     """A single persistent fact."""
#
#     id: str
#     key: str
#     value: Any  # JSON-serializable value
#     scope: MemoryScope
#     scope_id: str | None = None  # user_id, session_id, agent_id, etc.
#     schema_type: str | None = None  # Optional schema name for validation
#     tags: list[str] = Field(default_factory=list)
#     metadata: dict[str, Any] = Field(default_factory=dict)
#     created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
#     updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
#     expires_at: datetime | None = None
#     deleted_at: datetime | None = None


class TeamAuth(BaseModel):
    """Team authentication credentials for playground access.

    Single row table - one email/password for the entire team.
    """

    id: str | None = None  # Auto-assigned by database
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None


class ToolDefinition(BaseModel):
    """
    Individual tool definition - stored per tool, not per source.

    Editable via UI, can be LLM-enriched.
    Keyed by (name, source) for uniqueness.
    """

    id: str | None = None  # Auto-assigned by database

    # Identity
    slug: str  # Tool name (e.g., "get_stock_price")
    name: str  # Tool name (e.g., "get_stock_price")
    source: str  # Human-readable source name
    is_active: bool = True

    # Schema - flexible to support any tool source format
    description: str
    input_schema: Any = None  # Typically: list[{name, type, required, description, default}]
    output_schema: Any = None  # Typically: {type, description, fields}
    required_fields: list[str] = Field(default_factory=list)
    example: Any = None  # Typically: {input: {...}, output: {...}}

    # Content hash for change detection
    hash: str | None = None

    # Improvement tracking
    is_improved: bool = False
    improved_by: str | None = None  # "user" or "llm"
    version: str = "1.0.0"

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NodeExecution(BaseModel):
    """Execution state of a single node within a workflow run."""

    node_id: str
    node_type: str  # "action" | "transform" | "branch" | "loop" | "respond" | ...
    label: str = ""
    status: str = "pending"  # pending | running | ok | error | skipped | waiting
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    retry_attempt: int = 0


class WorkflowInstance(BaseModel):
    """Represents a single execution run of a DSL workflow.

    Persisted per-run for observability, debugging, crash recovery, and audit.
    Node-level tracking is embedded in node_status_map (not a separate collection).
    """

    id: str | None = None  # Auto-assigned by database

    # Identity
    agent_id: str = ""  # which agent/team triggered this
    conversation_id: str = ""  # link to conversation thread
    plan_id: str = ""  # DslWorkflow.workflow_id
    plan_version: str = "1.0.0"  # DslWorkflow.version

    # Execution state
    status: str = "RUNNING"  # RUNNING | FAILED | WAITING | COMPLETED | CANCELLED
    current_node_ids: list[str] = Field(default_factory=list)  # cursor(s)
    state_snapshot: dict[str, Any] = Field(default_factory=dict)  # workflow state
    node_status_map: dict[str, NodeExecution] = Field(
        default_factory=dict
    )  # node_id → NodeExecution
    retry_counts: dict[str, int] = Field(default_factory=dict)  # node_id → count

    # Results
    response: str | None = None  # final RespondNode output
    error: str | None = None  # last error message
    execution_log: list[dict[str, Any]] = Field(default_factory=list)  # journal entries

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None  # first node started
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None  # terminal time
    duration_ms: int | None = None  # total wall-clock
