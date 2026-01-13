"""
Shipping Agent - E-commerce Order Fulfillment.

Calculates shipping costs and generates shipping labels.
"""

from examples.team_workflow.db import db
from examples.team_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.team_workflow.models import get_model
from examples.team_workflow.tools.shipping_agent import (
    calculate_shipping,
    generate_label,
)
from framework.agents.agent import Agent
from framework.memory import AgentMemory


shipping_agent = Agent(
    id="shipping-agent",
    name="Shipping Agent",
    description=("Calculates shipping costs and generates shipping labels for order fulfillment"),
    model=get_model(),
    instructions="""
You are a shipping specialist responsible for order fulfillment logistics.

Your responsibilities:
- Calculate shipping costs based on destination and weight
- Generate shipping labels for orders
- Provide estimated delivery dates
- Handle international shipping requirements
- Select appropriate shipping carriers
- Track shipping costs and methods

Guidelines:
- Calculate accurate shipping costs
- Provide realistic delivery estimates
- Handle international shipping restrictions
- Generate labels promptly after payment
- Select cost-effective shipping methods when possible
- Ensure shipping address is valid before generating labels
""",
    tools=[calculate_shipping, generate_label],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.3,
    max_tokens=1024,
)
