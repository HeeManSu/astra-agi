from dataclasses import dataclass, field
import enum
import uuid


class NodeType(str, enum.Enum):
    ACTION = "action"
    TRANSFORM = "transform"
    RESPOND = "respond"
    BRANCH = "branch"
    LOOP = "loop"


@dataclass
class Node:
    """Base for every node in the plan builder.

    Attributes:
        type: The type of the node.
        label: The human-readable name of the node.
        description: The description of the node.
        id: The unique identifier of the node.
        inputs: The inputs of the node.
        outputs: The outputs of the node.
    """

    type: NodeType
    label: str = ""
    description: str = ""
    id: str = field(default_factory=lambda: f"n_{uuid.uuid4().hex[:8]}")

    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)


@dataclass
class ActionNode(Node):
    """Call an external tool.

    Attributes:
        tool: The tool to call.
    """

    type: NodeType = field(default=NodeType.ACTION, init=False)
    tool: str = ""


@dataclass
class TransformNode(Node):
    """Data transformation node.

    Attributes:
        expression: The Python expression to evaluate.
        assign_to: The variable name to assign the evaluated result.
    """

    type: NodeType = field(default=NodeType.TRANSFORM, init=False)
    expression: str = ""
    assign_to: str = ""


@dataclass
class RespondNode(Node):
    """Return the final result to the caller.

    Attributes:
        message: The expression or template for the response.
    """

    type: NodeType = field(default=NodeType.RESPOND, init=False)
    message: str = ""


@dataclass
class BranchNode(Node):
    """Conditional routing (if / else / switch).

    Attributes:
        condition: The condition to evaluate.
    """

    type: NodeType = field(default=NodeType.BRANCH, init=False)
    condition: str = ""


@dataclass
class LoopNode(Node):
    """Iterate over a collection with a body sub-graph.

    Attributes:
        over: The path to the collection to iterate over.
        as_var: The variable name to use for the current element.
        max_iterations: The maximum number of iterations to perform.
    """

    type: NodeType = field(default=NodeType.LOOP, init=False)
    over: str = ""
    as_var: str = "item"
    max_iterations: int = 1000


NODE_MAP: dict[NodeType, type[Node]] = {
    NodeType.ACTION: ActionNode,
    NodeType.TRANSFORM: TransformNode,
    NodeType.RESPOND: RespondNode,
    NodeType.BRANCH: BranchNode,
    NodeType.LOOP: LoopNode,
}


def action_node(
    tool: str,
    label: str,
    inputs: dict[str, str] | None = None,
    outputs: dict[str, str] | None = None,
) -> ActionNode:
    return ActionNode(tool=tool, label=label, inputs=inputs or {}, outputs=outputs or {})


def transform_node(
    expression: str,
    assign_to: str,
    label: str,
) -> TransformNode:
    return TransformNode(expression=expression, assign_to=assign_to, label=label)


def respond_node(message: str) -> RespondNode:
    return RespondNode(label="respond", message=message)


def branch_node(condition: str, label: str = "") -> BranchNode:
    return BranchNode(label=label, condition=condition)


def loop_node(over: str, as_var: str = "item", label: str = "") -> LoopNode:
    return LoopNode(label=label, over=over, as_var=as_var)
