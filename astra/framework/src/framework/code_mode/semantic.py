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


# Return Schema
@dataclass
class ReturnSchema:
    """
    Schema for a tool's return type.

    Extracted from Pydantic output model.

    Attributes:
        type: Return type as string (e.g., "ValidateOrderOutput")
        description: Description of what is returned
        fields: Dict of field names to their descriptions (from output model)

    Example:
        ReturnSchema(
            type="ValidateOrderOutput",
            description="Order validation result",
            fields={"is_valid": "Whether the order is valid", "total_value": "Total order value"},
        )
    """

    type: str
    description: str
    fields: dict[str, str] = field(default_factory=dict)


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
                                "fields": t.returns.fields,
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

    Args:
        input_schema: Pydantic BaseModel class

    Returns:
        List of ParamSchema for each field
    """
    params = []
    for field_name, field_info in input_schema.model_fields.items():
        # Get type annotation as string
        annotation = input_schema.model_fields[field_name].annotation
        type_str = getattr(annotation, "__name__", str(annotation))

        # Check if required (no default)
        is_required = field_info.is_required()

        # Get description from Field
        description = field_info.description or ""

        # Get default value
        default = None if is_required else field_info.default

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


def _extract_return_schema(output_schema: type) -> ReturnSchema:
    """
    Extract return schema from a Pydantic model.

    Args:
        output_schema: Pydantic BaseModel class

    Returns:
        ReturnSchema with type and field info
    """
    fields = {}
    for field_name, field_info in output_schema.model_fields.items():
        fields[field_name] = field_info.description or ""

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
    tools = [_build_tool_schema(tool) for tool in (agent.tools or [])]

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


"""
{
  "team_id": "order-processing-team",
  "team_name": "Order Processing Team",
  "team_description": "Coordinates complete order fulfillment workflow",

  "domains": [
    {
      "id": "order_validator",
      "name": "Order Validator",
      "description": "Validates order details and customer information",
      "tools": [
        {
          "name": "validate_order",
          "description": "Validate order details including customer information, items, and shipping address. Returns validation status and any errors.",
          "parameters": [
            {"name": "order_id", "type": "str", "required": true, "description": "Unique order identifier"},
            {"name": "customer_id", "type": "str", "required": true, "description": "Customer ID"},
            {"name": "items", "type": "list[dict]", "required": true, "description": "List of items with product_id, quantity, price"},
            {"name": "shipping_address", "type": "dict", "required": true, "description": "Shipping address dictionary"},
            {"name": "payment_method", "type": "str", "required": false, "default": null, "description": "Optional payment method"}
          ],
          "return_type": "str",
          "return_description": "JSON string with validation status and errors",
          "example_call": "order_validator.validate_order('ORD-123', 'CUST-456', [{'product_id': 'PROD-001', 'quantity': 2, 'price': 99.99}], {'country': 'US', 'city': 'NYC'})",
          "example_result": "{\"status\": \"valid\", \"is_valid\": true, \"total_value\": 199.98}"
        }
      ]
    },

    {
      "id": "inventory",
      "name": "Inventory Manager",
      "description": "Checks stock and reserves items for orders",
      "tools": [
        {
          "name": "check_inventory",
          "description": "Check stock availability for products. Returns available quantity and stock status.",
          "parameters": [
            {"name": "product_ids", "type": "list[str]", "required": true, "description": "List of product IDs to check"}
          ],
          "return_type": "str",
          "return_description": "JSON string with inventory status for each product",
          "example_call": "inventory.check_inventory(['PROD-001', 'PROD-002'])",
          "example_result": "{\"products\": [{\"product_id\": \"PROD-001\", \"available\": 45, \"in_stock\": true}]}"
        },
        {
          "name": "reserve_items",
          "description": "Reserve items for an order to prevent overselling.",
          "parameters": [
            {"name": "order_id", "type": "str", "required": true, "description": "Order ID"},
            {"name": "items", "type": "list[dict]", "required": true, "description": "Items to reserve with product_id and quantity"}
          ],
          "return_type": "str",
          "return_description": "JSON string with reservation status",
          "example_call": "inventory.reserve_items('ORD-123', [{'product_id': 'PROD-001', 'quantity': 2}])",
          "example_result": "{\"reservation_id\": \"RES-ABC\", \"status\": \"reserved\"}"
        }
      ]
    },

    {
      "id": "payment",
      "name": "Payment Processor",
      "description": "Processes payments for orders",
      "tools": [
        {
          "name": "process_payment",
          "description": "Process payment for an order. Returns payment ID and transaction status.",
          "parameters": [
            {"name": "order_id", "type": "str", "required": true, "description": "Order ID"},
            {"name": "amount", "type": "float", "required": true, "description": "Payment amount"},
            {"name": "payment_method", "type": "str", "required": true, "description": "Payment method (credit_card, debit_card, paypal)"},
            {"name": "customer_id", "type": "str", "required": true, "description": "Customer ID"},
            {"name": "currency", "type": "str", "required": false, "default": "USD", "description": "Currency code"}
          ],
          "return_type": "str",
          "return_description": "JSON string with payment status and transaction ID",
          "example_call": "payment.process_payment('ORD-123', 199.98, 'credit_card', 'CUST-456')",
          "example_result": "{\"payment_id\": \"PAY-ABC\", \"status\": \"completed\", \"transaction_id\": \"TXN-123\"}"
        },
        {
          "name": "refund_payment",
          "description": "Process refund for a payment.",
          "parameters": [
            {"name": "payment_id", "type": "str", "required": true, "description": "Original payment ID"},
            {"name": "amount", "type": "float", "required": true, "description": "Refund amount"},
            {"name": "reason", "type": "str", "required": false, "default": null, "description": "Reason for refund"}
          ],
          "return_type": "str",
          "return_description": "JSON string with refund status",
          "example_call": "payment.refund_payment('PAY-ABC', 50.00, 'Partial return')",
          "example_result": "{\"refund_id\": \"REF-XYZ\", \"status\": \"completed\"}"
        }
      ]
    },

    {
      "id": "shipping",
      "name": "Shipping Coordinator",
      "description": "Calculates shipping and generates labels",
      "tools": [
        {
          "name": "calculate_shipping",
          "description": "Calculate shipping costs and estimated delivery times.",
          "parameters": [
            {"name": "destination_country", "type": "str", "required": true, "description": "Destination country code (US, CA, UK)"},
            {"name": "weight_kg", "type": "float", "required": true, "description": "Package weight in kilograms"},
            {"name": "shipping_method", "type": "str", "required": false, "default": "standard", "description": "Shipping method (standard, express, overnight)"}
          ],
          "return_type": "str",
          "return_description": "JSON string with shipping cost and delivery estimate",
          "example_call": "shipping.calculate_shipping('US', 2.5, 'express')",
          "example_result": "{\"total_cost\": 15.99, \"estimated_delivery_days\": 2}"
        },
        {
          "name": "generate_label",
          "description": "Generate shipping label for an order.",
          "parameters": [
            {"name": "order_id", "type": "str", "required": true, "description": "Order ID"},
            {"name": "shipping_address", "type": "dict", "required": true, "description": "Shipping address"},
            {"name": "shipping_method", "type": "str", "required": true, "description": "Selected shipping method"}
          ],
          "return_type": "str",
          "return_description": "JSON string with label and tracking number",
          "example_call": "shipping.generate_label('ORD-123', {'country': 'US', 'city': 'NYC'}, 'express')",
          "example_result": "{\"label_id\": \"LBL-123\", \"tracking_number\": \"1Z999AA10123456784\"}"
        }
      ]
    },

    {
      "id": "customer_service",
      "name": "Customer Service",
      "description": "Sends notifications and updates order status",
      "tools": [
        {
          "name": "send_notification",
          "description": "Send notification to customer via email or SMS.",
          "parameters": [
            {"name": "customer_id", "type": "str", "required": true, "description": "Customer ID"},
            {"name": "notification_type", "type": "str", "required": true, "description": "Type (order_confirmed, shipped, delivered)"},
            {"name": "message", "type": "str", "required": true, "description": "Notification message"},
            {"name": "channel", "type": "str", "required": false, "default": "email", "description": "Channel (email, sms, push)"},
            {"name": "order_id", "type": "str", "required": false, "default": null, "description": "Optional order ID"}
          ],
          "return_type": "str",
          "return_description": "JSON string with notification status",
          "example_call": "customer_service.send_notification('CUST-456', 'order_confirmed', 'Your order is confirmed!', order_id='ORD-123')",
          "example_result": "{\"notification_id\": \"NOTIF-ABC\", \"status\": \"sent\"}"
        },
        {
          "name": "update_order_status",
          "description": "Update order status in the system.",
          "parameters": [
            {"name": "order_id", "type": "str", "required": true, "description": "Order ID"},
            {"name": "status", "type": "str", "required": true, "description": "New status"},
            {"name": "notes", "type": "str", "required": false, "default": null, "description": "Status notes"}
          ],
          "return_type": "str",
          "return_description": "JSON string with status update confirmation",
          "example_call": "customer_service.update_order_status('ORD-123', 'shipped', 'Label generated')",
          "example_result": "{\"order_id\": \"ORD-123\", \"new_status\": \"shipped\"}"
        }
      ]
    }
  ],

  "metadata": {
    "total_domains": 5,
    "total_tools": 9
  }
}
"""
