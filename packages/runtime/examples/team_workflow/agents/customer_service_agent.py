"""
Customer Service Agent - E-commerce Order Fulfillment.

Handles customer inquiries and sends order notifications.
"""

from examples.team_workflow.db import db
from examples.team_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.team_workflow.models import get_model
from examples.team_workflow.tools.customer_service import (
    send_notification,
    update_order_status,
)
from framework.agents.agent import Agent
from framework.memory import AgentMemory


customer_service_agent = Agent(
    id="customer-service-agent",
    name="Customer Service Agent",
    description=(
        "Handles customer inquiries, sends notifications, and updates order "
        "status for customer communication"
    ),
    model=get_model(),
    instructions="""
You are a customer service specialist focused on providing excellent customer support.

Your responsibilities:
- Send order confirmation notifications
- Send shipping and delivery updates
- Update order status in the system
- Handle customer inquiries about orders
- Provide order tracking information
- Communicate order issues to customers

Guidelines:
- Send notifications promptly at each order stage
- Use clear, friendly communication
- Keep customers informed about order progress
- Update order status accurately
- Provide helpful information when customers ask
- Maintain professional and empathetic tone
""",
    tools=[send_notification, update_order_status],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.7,  # Higher temperature for natural customer communication
    max_tokens=2048,
)
