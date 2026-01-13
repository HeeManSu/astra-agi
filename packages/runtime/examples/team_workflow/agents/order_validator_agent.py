"""
Order Validator Agent - E-commerce Order Fulfillment.

Validates order details, customer information, and order requirements.
"""

from examples.team_workflow.db import db
from examples.team_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.team_workflow.models import get_model
from examples.team_workflow.tools.order_validator import validate_order
from framework.agents.agent import Agent
from framework.memory import AgentMemory


order_validator_agent = Agent(
    id="order-validator-agent",
    name="Order Validator Agent",
    description=(
        "Validates order details, customer information, and order requirements "
        "to ensure orders meet business rules and standards"
    ),
    model=get_model(),
    instructions="""
You are an order validation specialist focused on ensuring all orders meet
business requirements before processing.

Your responsibilities:
- Validate order details (items, quantities, prices)
- Verify customer information is complete
- Check shipping address validity
- Ensure order value meets minimum/maximum requirements
- Validate payment method compatibility
- Flag orders that require manual review

Guidelines:
- Be thorough in validation checks
- Provide clear error messages when validation fails
- Flag high-value orders for additional review
- Ensure all required fields are present
- Check country/region shipping restrictions
""",
    tools=[validate_order],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.3,  # Lower temperature for consistent validation
    max_tokens=1024,
)
