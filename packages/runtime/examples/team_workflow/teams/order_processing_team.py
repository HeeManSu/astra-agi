"""
Order Processing Team - Coordinate Mode.

Coordinates the complete order fulfillment workflow:
Order → Validate → Inventory → Payment → Shipping → Notification
"""

from examples.team_workflow.agents import (
    customer_service_agent,
    inventory_agent,
    order_validator_agent,
    payment_agent,
    shipping_agent,
)
from examples.team_workflow.db import db
from examples.team_workflow.models import get_model
from framework.memory import AgentMemory
from framework.team import Team, TeamMember


order_processing_team = Team(
    id="order-processing-team",
    name="Order Processing Team",
    description="Coordinates complete order fulfillment workflow",
    model=get_model(),
    execution_mode="coordinate",
    members=[
        TeamMember(
            id="order-validator-agent",
            name="Order Validator",
            description="Validates order details and customer information",
            agent=order_validator_agent,
        ),
        TeamMember(
            id="inventory-agent",
            name="Inventory Manager",
            description="Checks stock and reserves items for orders",
            agent=inventory_agent,
        ),
        TeamMember(
            id="payment-agent",
            name="Payment Processor",
            description="Processes payments for orders",
            agent=payment_agent,
        ),
        TeamMember(
            id="shipping-agent",
            name="Shipping Coordinator",
            description="Calculates shipping and generates labels",
            agent=shipping_agent,
        ),
        TeamMember(
            id="customer-service-agent",
            name="Customer Service",
            description="Sends notifications and updates order status",
            agent=customer_service_agent,
        ),
    ],
    instructions="""
You are coordinating a complete order fulfillment workflow. Decompose order
requests into subtasks and delegate to specialists in sequence.

Workflow:
1. Validation phase: Delegate to order-validator-agent to validate order details
2. Inventory phase: Delegate to inventory-agent to check stock and reserve items
3. Payment phase: Delegate to payment-agent to process payment
4. Shipping phase: Delegate to shipping-agent to calculate shipping and generate label
5. Notification phase: Delegate to customer-service-agent to send confirmation

You can run validation and inventory check in parallel for efficiency.
After all phases complete, synthesize the final order confirmation.
""",
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    allow_parallel=True,
    max_parallel=2,
    timeout=600.0,  # Longer timeout for complete order processing
    member_timeout=120.0,
    max_delegations=15,
)
