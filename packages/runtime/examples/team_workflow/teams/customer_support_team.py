"""
Customer Support Team - Route Mode.

Routes customer inquiries to the appropriate specialist.
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


customer_support_team = Team(
    id="customer-support-team",
    name="Customer Support Team",
    description="Routes customer inquiries to the appropriate specialist",
    model=get_model(),
    execution_mode="route",
    members=[
        TeamMember(
            id="customer-service-agent",
            name="Customer Service",
            description="General customer inquiries, order status, account questions",
            agent=customer_service_agent,
        ),
        TeamMember(
            id="order-validator-agent",
            name="Order Validator",
            description="Order validation questions, order requirements",
            agent=order_validator_agent,
        ),
        TeamMember(
            id="inventory-agent",
            name="Inventory Specialist",
            description="Stock availability, product availability questions",
            agent=inventory_agent,
        ),
        TeamMember(
            id="payment-agent",
            name="Payment Specialist",
            description="Payment issues, refunds, payment method questions",
            agent=payment_agent,
        ),
        TeamMember(
            id="shipping-agent",
            name="Shipping Specialist",
            description="Shipping costs, delivery times, tracking questions",
            agent=shipping_agent,
        ),
    ],
    instructions="""
You are a customer support router. Your job is to analyze customer inquiries
and route them to the single best specialist who can handle the request.

Available specialists:
- customer-service-agent: General customer inquiries, order status, account questions
- order-validator-agent: Order validation questions, order requirements
- inventory-agent: Stock availability, product availability questions
- payment-agent: Payment issues, refunds, payment method questions
- shipping-agent: Shipping costs, delivery times, tracking questions

Analyze the customer's request and delegate to exactly ONE specialist who can
best handle it.
""",
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    timeout=300.0,
    member_timeout=60.0,
    max_delegations=5,
)
