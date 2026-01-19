"""
Semantic Layer Schema for Code Mode.

This module defines the data structures for representing a Team's configuration
in a structured format that can be used for:
1. Generating Python stubs for LLM code generation
2. Building API documentation
3. Validating team configurations

Architecture:
    Team → TeamSemanticLayer
         → DomainSchema (one per Agent)
              → ToolSchema (one per tool)
                   → ParamSchema (one per parameter)
                   → ReturnSchema (output info)
                   → ExampleSchema (example usage)

Usage:
    from framework.code_mode.semantic import build_semantic_layer

    team = Team(...)
    semantic = build_semantic_layer(team)
    stubs = generate_stubs(semantic)  # In stub_generator.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from framework.agents.agent import Agent
    from framework.team.team import Team


# Parameter Schema
@dataclass
class ParamSchema:
    """
    Schema for a single tool parameter.

    Extracted from Pydantic Field definitions on the tool's input model.

    Attributes:
        name: Parameter name (e.g., "order_id")
        type: Type as string (e.g., "str", "list[dict]")
        required: Whether the parameter is required
        description: Description from Pydantic Field
        default: Default value if not required (None if required)

    Example:
        ParamSchema(
            name="order_id",
            type="str",
            required=True,
            description="Unique order identifier",
            default=None,
        )
    """

    name: str
    type: str
    required: bool
    description: str
    default: Any = None


# Field Schema (for return type fields)
@dataclass
class FieldSchema:
    """
    Schema for a single field in a return type.

    Attributes:
        name: Field name
        type: Field type as string (e.g., "str", "float")
        description: Field description
    """

    name: str
    type: str
    description: str


# Return Schema
@dataclass
class ReturnSchema:
    """
    Schema for a tool's return type.

    Extracted from Pydantic output model.

    Attributes:
        type: Return type as string (e.g., "ValidateOrderOutput")
        description: Description of what is returned
        fields: List of FieldSchema objects with name, type, and description

    Example:
        ReturnSchema(
            type="ValidateOrderOutput",
            description="Order validation result",
            fields=[
                FieldSchema(name="is_valid", type="bool", description="Whether the order is valid"),
                FieldSchema(name="total_value", type="float", description="Total order value"),
            ],
        )
    """

    type: str
    description: str
    fields: list[FieldSchema] = field(default_factory=list)


# Example Schema
@dataclass
class ExampleSchema:
    """
    Schema for tool usage example.

    Used for few-shot learning in LLM prompts.

    Attributes:
        input: Example input as dict
        output: Example output as dict

    Example:
        ExampleSchema(
            input={"order_id": "ORD-123", "items": [{"product_id": "P1", "quantity": 2}]},
            output={"is_valid": True, "total_value": 199.98},
        )
    """

    input: dict[str, Any]
    output: dict[str, Any]


# Tool Schema
@dataclass
class ToolSchema:
    """
    Schema for a single tool.

    Contains all information needed to generate a Python stub.

    Attributes:
        name: Tool function name (e.g., "validate_order")
        description: Tool description
        parameters: List of parameter schemas
        returns: Return type schema
        example: Optional example for few-shot learning

    Example:
        ToolSchema(
            name="validate_order",
            description="Validate order details",
            parameters=[ParamSchema(name="order_id", type="str", ...)],
            returns=ReturnSchema(type="ValidateOrderOutput", ...),
            example=ExampleSchema(input={...}, output={...}),
        )
    """

    name: str
    description: str
    parameters: list[ParamSchema]
    returns: ReturnSchema
    example: ExampleSchema | None = None


# Domain Schema (Agent)
@dataclass
class DomainSchema:
    """
    Schema for a domain (Agent or nested Team).

    Each domain becomes a Python class in the generated stubs.

    Attributes:
        id: Unique identifier (agent.id converted to snake_case)
        name: Display name (agent.name)
        description: Domain description (agent.description)
        tools: List of tools in this domain

    Example:
        DomainSchema(
            id="inventory",
            name="Inventory Manager",
            description="Checks stock and reserves items for orders",
            tools=[ToolSchema(name="check_inventory", ...), ToolSchema(name="reserve_items", ...)],
        )
    """

    id: str
    name: str
    description: str
    tools: list[ToolSchema]


# Team Semantic Layer (Root)
@dataclass
class TeamSemanticLayer:
    """
    Root container for the semantic layer.

    Represents the entire Team's API surface in a structured format.

    Attributes:
        team_id: Team identifier
        team_name: Team display name
        team_description: Team description
        team_instructions: Team instructions (workflow hints for LLM)
        domains: List of domain schemas (one per agent/nested team)
        metadata: Additional metadata for extensions

    Example:
        TeamSemanticLayer(
            team_id="order-processing-team",
            team_name="Order Processing Team",
            team_description="Coordinates complete order fulfillment workflow",
            team_instructions="1. Validate order → 2. Check inventory → 3. Process payment",
            domains=[DomainSchema(id="inventory", ...), DomainSchema(id="payment", ...)],
            metadata={"total_domains": 2, "total_tools": 5},
        )
    """

    team_id: str
    team_name: str
    team_description: str
    team_instructions: str
    domains: list[DomainSchema]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "team_description": self.team_description,
            "team_instructions": self.team_instructions,
            # Domain represents a subteam or agent
            "domains": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "parameters": [
                                {
                                    "name": p.name,
                                    "type": p.type,
                                    "required": p.required,
                                    "description": p.description,
                                    "default": p.default,
                                }
                                for p in t.parameters
                            ],
                            "returns": {
                                "type": t.returns.type,
                                "description": t.returns.description,
                                "fields": {
                                    f.name: {"type": f.type, "description": f.description}
                                    for f in t.returns.fields
                                },
                            },
                            "example": (
                                {"input": t.example.input, "output": t.example.output}
                                if t.example
                                else None
                            ),
                        }
                        for t in d.tools
                    ],
                }
                for d in self.domains
            ],
            "metadata": self.metadata,
        }


# Builder Function
def _extract_params_from_pydantic(input_schema: type) -> list[ParamSchema]:
    """
    Extract parameter schemas from a Pydantic model.

    Required Logic:
        A parameter is considered "required" if:
        1. It has no default (Field(...)), OR
        2. It has a non-None default AND the type is NOT Optional (doesn't include None)

        A parameter is "optional" only if:
        - It has a default value AND the type includes None (e.g., str | None)

    Examples:
        query: str = Field(...)                    → required=True,  default=None
        domain: str = Field(default="in")          → required=True,  default="in"
        postal_code: str | None = Field(default=None) → required=False, default=None

    Args:
        input_schema: Pydantic BaseModel class

    Returns:
        List of ParamSchema for each field
    """
    import types
    from typing import Union, get_args, get_origin

    params = []
    for field_name, field_info in input_schema.model_fields.items():
        # Get type annotation
        annotation = input_schema.model_fields[field_name].annotation
        type_str = getattr(annotation, "__name__", str(annotation))

        # Check if type is Optional (includes None)
        # Handle Union types (including str | None syntax which is UnionType in Python 3.10+)
        origin = get_origin(annotation)
        is_optional_type = False
        if origin is Union or isinstance(annotation, types.UnionType):
            args = get_args(annotation)
            is_optional_type = type(None) in args

        # Pydantic's is_required() only checks for Field(...)
        pydantic_required = field_info.is_required()

        # New required logic:
        # - If Pydantic says required (no default) → required
        # - If has default AND type is NOT Optional → required (with default)
        # - If has default AND type IS Optional → optional
        if pydantic_required:
            is_required = True
            default = None
        elif is_optional_type:
            # Optional type with default → truly optional
            is_required = False
            default = field_info.default
        else:
            # Non-optional type with default → required (but has fallback default)
            is_required = True
            default = field_info.default

        # Get description from Field
        description = field_info.description or ""

        params.append(
            ParamSchema(
                name=field_name,
                type=type_str,
                required=is_required,
                description=description,
                default=default,
            )
        )
    return params


def _annotation_to_type_string(annotation: Any) -> str:
    """
    Convert a type annotation to a string representation.

    Args:
        annotation: Type annotation from Pydantic field

    Returns:
        Type as string (e.g., "str", "float", "list[str]")
    """
    if annotation is None:
        return "Any"
    # Handle simple types like str, int, float
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    # Handle generic types like list[str], dict[str, int]
    return str(annotation).replace("typing.", "")


def _extract_return_schema(output_schema: type) -> ReturnSchema:
    """
    Extract return schema from a Pydantic model.

    Args:
        output_schema: Pydantic BaseModel class

    Returns:
        ReturnSchema with type and field info including types
    """
    fields = []
    for field_name, field_info in output_schema.model_fields.items():
        # Get type string from annotation
        annotation = field_info.annotation
        type_str = _annotation_to_type_string(annotation)
        description = field_info.description or ""
        fields.append(FieldSchema(name=field_name, type=type_str, description=description))

    return ReturnSchema(
        type=output_schema.__name__,
        description=output_schema.__doc__ or "",
        fields=fields,
    )


def _build_tool_schema(tool: Any) -> ToolSchema:
    """
    Build ToolSchema from a Tool instance.

    Args:
        tool: Tool instance with Pydantic input/output schemas

    Returns:
        ToolSchema with all parameter and return info
    """
    # Extract parameters from input schema
    params = _extract_params_from_pydantic(tool.input_schema)

    # Extract return schema
    returns = _extract_return_schema(tool.output_schema)

    # Extract example if present
    example = None
    if tool.example:
        example = ExampleSchema(
            input=tool.example.get("input", {}),
            output=tool.example.get("output", {}),
        )

    return ToolSchema(
        name=tool.name,
        description=tool.description,
        parameters=params,
        returns=returns,
        example=example,
    )


def _build_domain_from_agent(agent: Agent) -> DomainSchema:
    """
    Build DomainSchema from an Agent.

    Args:
        agent: Agent instance

    Returns:
        DomainSchema representing the agent as a domain
    """
    agent_tools = agent.tools or []
    tools = [_build_tool_schema(tool) for tool in agent_tools]

    # Convert agent name to snake_case for class name
    class_id = agent.name.lower().replace(" ", "_").replace("-", "_")

    return DomainSchema(
        id=class_id,
        name=agent.name,
        description=agent.description or f"Agent: {agent.name}",
        tools=tools,
    )


def build_semantic_layer(team: Team) -> TeamSemanticLayer:
    """
    Build semantic layer from a Team.

    Traverses all team members (Agents or nested Teams) and builds
    a structured representation for code generation.

    Args:
        team: Team instance with members

    Returns:
        TeamSemanticLayer containing all domain and tool schemas

    Example:
        team = Team(
            id="order-team",
            name="Order Processing Team",
            members=[inventory_agent, payment_agent],
            ...
        )
        semantic = build_semantic_layer(team)
        print(semantic.to_dict())
    """
    from framework.agents.agent import Agent
    from framework.team.team import Team as TeamClass

    domains = []

    for member in team.members:
        # member is always TeamMember now
        agent_or_team = member.agent

        # @tTODO Change the className of the agent or team of the generated code from camelCase to snake_case

        if isinstance(agent_or_team, Agent):
            # Agent becomes a domain
            domains.append(_build_domain_from_agent(agent_or_team))
        elif isinstance(agent_or_team, TeamClass):
            # Nested team: recursively build and merge domains
            # Note: We flattens domains.
            # If we want to preserve hierarchy, we might need a different structure,
            # but for now, code mode sees a flat list of "agents" (domains).
            nested_semantic = build_semantic_layer(agent_or_team)
            domains.extend(nested_semantic.domains)

    return TeamSemanticLayer(
        team_id=team.id,
        team_name=team.name,
        team_description=team.description,
        team_instructions=team.instructions,
        domains=domains,
        metadata={
            "total_domains": len(domains),
            "total_tools": sum(len(d.tools) for d in domains),
        },
    )


def build_agent_semantic_layer(agent: Agent) -> TeamSemanticLayer:
    """
    Build semantic layer for a single Agent.

    Reuses TeamSemanticLayer structure with a single domain (the agent itself).
    This allows the agent to use the same Sandbox infrastructure as Team.

    Args:
        agent: Agent instance with tools

    Returns:
        TeamSemanticLayer with single domain containing all agent tools

    Example:
        agent = Agent(
            name="Market Analyst",
            model=model,
            tools=[analyze_stock, get_market_data],
            ...
        )
        semantic = build_agent_semantic_layer(agent)
        # semantic.domains[0] contains all tools
    """
    # Build single domain from the agent
    domain = _build_domain_from_agent(agent)

    return TeamSemanticLayer(
        team_id=agent.id,
        team_name=agent.name,
        team_description=agent.description or f"Agent: {agent.name}",
        team_instructions=agent.instructions,
        domains=[domain],  # Single domain for the agent
        metadata={
            "total_domains": 1,
            "total_tools": len(domain.tools),
            "is_agent": True,  # Flag to identify this is an agent, not a team
        },
    )
