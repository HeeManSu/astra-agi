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
    from framework.code_mode.semantic import build_team_semantic_layer

    team = Team(...)
    semantic = build_team_semantic_layer(team)
    stubs = generate_stubs(semantic)  # In stub_generator.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


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
        slug: Stable tool identifier (preferred execution identifier)
        name: Tool function name (e.g., "validate_order")
        description: Tool description
        parameters: List of parameter schemas
        returns: Return type schema
        example: Optional example for few-shot learning

    Example:
        ToolSchema(
            slug="validate-order",
            name="validate_order",
            description="Validate order details",
            parameters=[ParamSchema(name="order_id", type="str", ...)],
            returns=ReturnSchema(type="ValidateOrderOutput", ...),
            example=ExampleSchema(input={...}, output={...}),
        )
    """

    slug: str
    name: str
    description: str
    parameters: list[ParamSchema]
    returns: ReturnSchema
    example: ExampleSchema | None = None


# Domain Schema (Agent)
@dataclass
class DomainSchema:
    """
    Schema for a domain (Agent, MCP toolkit, or nested Team).

    Each domain becomes a Python class in the generated stubs.

    Attributes:
        id: Unique identifier (stable ID/slug)
        name: Display name (agent.name)
        description: Domain description (agent.description)
        tools: List of tools in this domain
        instructions: Optional agent instructions (included in stub docstring)

    Example:
        DomainSchema(
            id="inventory",
            name="Inventory Manager",
            description="Checks stock and reserves items for orders",
            tools=[ToolSchema(name="check_inventory", ...), ToolSchema(name="reserve_items", ...)],
            instructions="You manage inventory levels and...",
        )
    """

    id: str
    name: str
    description: str
    tools: list[ToolSchema]
    instructions: str | None = None


# Entity Semantic Layer (Root)
@dataclass
class EntitySemanticLayer:
    """
    Root container for the semantic layer.

    Represents the entity's (Agent, Team, Workflow) API surface in a structured format.

    Attributes:
        provider_id: Unique identifier
        provider_name: Display name
        provider_description: Description
        provider_instructions: Instructions (workflow hints for LLM)
        domains: List of domain schemas (one per agent/nested team/workflow phase)
        metadata: Additional metadata for extensions

    Example:
        EntitySemanticLayer(
            provider_id="order-team",
            provider_name="Order Processing Team",
            provider_description="Handles order processing workflow",
            provider_instructions="Process orders in the following way: ...",
            domains=[DomainSchema(...), DomainSchema(...)],
            metadata={...},
        )
    """

    provider_id: str
    provider_name: str
    provider_description: str
    provider_instructions: str
    domains: list[DomainSchema]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_description": self.provider_description,
            "provider_instructions": self.provider_instructions,
            # Domain represents a subteam or agent
            "domains": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "instructions": d.instructions,
                    "tools": [
                        {
                            "name": t.name,
                            "slug": t.slug,
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

    def get_planner_context(self) -> dict:
        """Build structured context for the planner LLM.

        Returns a dict with provider metadata and an agents_section string
        that includes each agent's role (extracted from instructions) and tools.
        This gives the planner enough context to distinguish agents that share
        the same tools but serve different roles.
        """
        planner_context = {
            "provider_name": self.provider_name,
            "provider_description": self.provider_description or "",
            "provider_instructions": self.provider_instructions or "",
            "agents": [],
        }

        for domain in self.domains:
            planner_context["agents"].append(
                {
                    "id": domain.id,
                    "name": domain.name,
                    "description": domain.description,
                    "instructions": domain.instructions,
                    "tools": [
                        {
                            "name": tool.name,
                            "slug": tool.slug,
                            "description": tool.description,
                        }
                        for tool in domain.tools
                    ],
                }
            )

        return planner_context

    def get_tool_stubs_by_tool_slugs(self, allowed_slugs: set[str]) -> EntitySemanticLayer:
        """Returns a new semantic layer containing only the specified tools."""
        from copy import deepcopy

        filtered_domains = []
        for domain in self.domains:
            # We assume allowed_slugs contains strings like "agent.tool_slug"
            filtered_tools = [t for t in domain.tools if f"{domain.id}.{t.slug}" in allowed_slugs]
            if filtered_tools:
                d = deepcopy(domain)
                d.tools = filtered_tools
                filtered_domains.append(d)

        return EntitySemanticLayer(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_description=self.provider_description,
            provider_instructions=self.provider_instructions,
            domains=filtered_domains,
            metadata=dict(self.metadata),
        )


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

    Handles special case for RootModel: when the output schema is a RootModel,
    the actual return type is the inner 'root' field type (e.g., list or dict),
    NOT a dict with a 'root' field.

    Args:
        output_schema: Pydantic BaseModel class

    Returns:
        ReturnSchema with type and field info including types
    """
    from pydantic import RootModel

    # Handle RootModel specially: Pydantic's RootModel wraps a single value and
    # serializes to just that value (not a dict with 'root' key).
    #
    # Example definition:
    #   class ListOutput(RootModel):
    #       root: list[Any]
    #
    # ListOutput(root=[1,2,3]) serializes to [1,2,3], not {"root": [1,2,3]}
    #
    # Without this, the semantic layer would report "dict with fields: root (list)"
    # causing the LLM to generate incorrect code like result.get('root').
    # This fix correctly reports "list" so the LLM iterates directly.
    if issubclass(output_schema, RootModel):
        root_field = output_schema.model_fields.get("root")
        if root_field:
            annotation = root_field.annotation
            type_str = _annotation_to_type_string(annotation)
            return ReturnSchema(
                type=type_str,
                description=output_schema.__doc__ or f"Returns {type_str}",
                fields=[],
            )

    # Standard Pydantic model - extract all fields
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

    # Defaults from code
    description = tool.description

    # Note: Tool descriptions can be enriched from cached ToolDefinitions
    # at the route/request level using per-agent lazy caching.

    raw_tool_slug = getattr(tool, "slug", None)
    tool_slug = _normalize_slug(raw_tool_slug) if raw_tool_slug else _normalize_slug(tool.name)

    return ToolSchema(
        slug=tool_slug,
        name=tool.name,
        description=description,
        parameters=params,
        returns=returns,
        example=example,
    )


def build_domain_schema(
    id: str,
    name: str,
    description: str | None,
    tools: list[Any],
    instructions: str | None = None,
) -> DomainSchema:
    """
    Build DomainSchema from raw domain properties.

    Args:
        id: Domain identifier
        name: Domain name
        description: Domain description
        tools: List of tool objects
        instructions: Optional agent instructions for LLM context

    Returns:
        DomainSchema representing the domain
    """
    tool_schemas = [_build_tool_schema(tool) for tool in tools]

    # Convert name to snake_case for class id if id not provided
    class_id = id if id else name.lower().replace(" ", "_").replace("-", "_")

    return DomainSchema(
        id=class_id,
        name=name,
        description=description or f"Domain: {name}",
        tools=tool_schemas,
        instructions=instructions,
    )


def _normalize_slug(value: str) -> str:
    """Normalize any identifier into a stable slug."""
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "unknown"


def build_entity_semantic_layer(
    provider_id: str,
    provider_name: str,
    provider_description: str,
    provider_instructions: str,
    domains: list[DomainSchema],
    metadata: dict[str, Any] | None = None,
) -> EntitySemanticLayer:
    """
    Build a complete EntitySemanticLayer from raw components.

    This is the core factory for the semantic layer. It is agnostic to
    whether the source is an Agent, Team, or Workflow.

    Args:
        provider_id: Unique identifier for the provider
        provider_name: Display name
        provider_description: Description
        provider_instructions: Instructions/Workflow hints
        domains: List of domain schemas
        metadata: Optional additional metadata

    Returns:
        Configured EntitySemanticLayer
    """
    return EntitySemanticLayer(
        provider_id=provider_id,
        provider_name=provider_name,
        provider_description=provider_description,
        provider_instructions=provider_instructions,
        domains=domains,
        metadata=metadata
        or {
            "total_domains": len(domains),
            "total_tools": sum(len(d.tools) for d in domains),
        },
    )


def build_mcp_tool_schemas(
    mcp_slug: str,
    tool_definitions: dict[str, Any] | None,
) -> list[ToolSchema]:
    """
    Extract ToolSchema list for an MCP toolkit from tool_definitions.

    Lower-level helper used to merge MCP tools into a parent agent's domain
    instead of creating a separate domain. Callers that need full DomainSchema
    should use build_mcp_domain_schema() instead.

    Args:
        mcp_slug: Stable MCP slug identifier
        tool_definitions: Dict of ToolDefinition objects from DB (slug -> ToolDef)

    Returns:
        List of ToolSchema for the MCP toolkit (empty if none found)
    """
    if not tool_definitions:
        return []

    mcp_source = f"mcp:{mcp_slug}"
    slug_prefix = f"{mcp_source}-"
    tool_schemas: list[ToolSchema] = []

    for tool_def in tool_definitions.values():
        if hasattr(tool_def, "source") and tool_def.source == mcp_source:
            # Build params from input_schema
            params: list[ParamSchema] = []
            if hasattr(tool_def, "input_schema") and tool_def.input_schema:
                input_schema = tool_def.input_schema
                props = input_schema.get("properties", {})
                required = input_schema.get("required", [])
                for name, prop in props.items():
                    params.append(
                        ParamSchema(
                            name=name,
                            type=prop.get("type", "any"),
                            required=name in required,
                            description=prop.get("description", ""),
                        )
                    )

            raw_tool_slug = getattr(tool_def, "slug", "")
            parsed_slug = ""
            if isinstance(raw_tool_slug, str) and raw_tool_slug.startswith(slug_prefix):
                parsed_slug = raw_tool_slug[len(slug_prefix) :]
            tool_slug = _normalize_slug(parsed_slug or tool_def.name)

            return_type = "Any"
            if hasattr(tool_def, "output_schema") and isinstance(tool_def.output_schema, dict):
                output_schema_type = tool_def.output_schema.get("type")
                if isinstance(output_schema_type, str) and output_schema_type:
                    return_type = output_schema_type

            tool_schemas.append(
                ToolSchema(
                    slug=tool_slug,
                    name=tool_def.name,
                    description=tool_def.description or "",
                    parameters=params,
                    returns=ReturnSchema(type=return_type, description="MCP tool result"),
                )
            )

    return tool_schemas


def build_mcp_domain_schema(
    mcp_slug: str,
    mcp_name: str,
    tool_definitions: dict[str, Any] | None,
) -> DomainSchema | None:
    """
    Build a standalone DomainSchema for an MCP toolkit.

    Kept for backward compatibility. Prefer build_mcp_tool_schemas() when
    merging MCP tools into a parent agent's domain.

    Args:
        mcp_slug: Stable MCP slug identifier
        mcp_name: Display name of the MCP toolkit
        tool_definitions: Dict of ToolDefinition objects from DB (slug -> ToolDef)

    Returns:
        DomainSchema for the MCP toolkit, or None if no tools found
    """
    tool_schemas = build_mcp_tool_schemas(mcp_slug, tool_definitions)
    if not tool_schemas:
        return None
    return DomainSchema(
        id=mcp_slug,
        name=mcp_name,
        description=f"MCP tools from {mcp_name}",
        tools=tool_schemas,
    )
