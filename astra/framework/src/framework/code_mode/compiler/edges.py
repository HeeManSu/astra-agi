from dataclasses import dataclass, field
import enum
import uuid


class EdgeType(str, enum.Enum):
    """Defines exactly how control flows between nodes.

    Attributes:
        SEQUENTIAL: A → B
        BRANCH_IF: A → B if condition is true
        BRANCH_ELSE: A → B if condition is false and there is an else block
        BRANCH_DEFAULT: A → B if condition is false and there is no else block
        LOOP_BODY: A → B inside a loop (first iteration)
        LOOP_BACK: B → A inside a loop (next iteration)
    """

    SEQUENTIAL = "sequential"
    BRANCH_IF = "branch_if"
    BRANCH_ELSE = "branch_else"
    BRANCH_DEFAULT = "branch_default"
    LOOP_BODY = "loop_body"
    LOOP_BACK = "loop_back"


@dataclass
class Edge:
    source: str
    target: str
    type: EdgeType
    condition: str | None = None
    id: str = field(default_factory=lambda: f"e_{uuid.uuid4().hex[:8]}")


def sequential(source: str, target: str) -> Edge:
    return Edge(source=source, target=target, type=EdgeType.SEQUENTIAL)


def branch_if(source: str, target: str, condition: str) -> Edge:
    return Edge(source=source, target=target, type=EdgeType.BRANCH_IF, condition=condition)


def branch_else(source: str, target: str) -> Edge:
    return Edge(source=source, target=target, type=EdgeType.BRANCH_ELSE)


def branch_default(source: str, target: str) -> Edge:
    return Edge(source=source, target=target, type=EdgeType.BRANCH_DEFAULT)


def loop_body(source: str, target: str) -> Edge:
    return Edge(source=source, target=target, type=EdgeType.LOOP_BODY)


def loop_back(source: str, target: str) -> Edge:
    return Edge(source=source, target=target, type=EdgeType.LOOP_BACK)
