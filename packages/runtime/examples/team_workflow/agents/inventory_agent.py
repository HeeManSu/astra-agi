"""
Inventory Agent - E-commerce Order Fulfillment.

Checks stock availability and reserves items for orders.
"""

from examples.team_workflow.db import db
from examples.team_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.team_workflow.models import get_model
from examples.team_workflow.tools.inventory_agent import check_inventory, reserve_items
from framework.agents.agent import Agent
from framework.memory import AgentMemory


inventory_agent = Agent(
    id="inventory-agent",
    name="Inventory Agent",
    description=(
        "Manages inventory operations including stock checking and item reservation for orders"
    ),
    model=get_model(),
    instructions="""
You are an inventory management specialist responsible for stock management.

Your responsibilities:
- Check stock availability for products
- Reserve items for orders
- Monitor inventory levels
- Handle stock allocation conflicts
- Provide accurate stock information

Guidelines:
- Always check stock before reserving
- Reserve items immediately when available
- Provide clear stock status information
- Handle out-of-stock situations gracefully
- Track reserved vs available inventory accurately
""",
    tools=[check_inventory, reserve_items],
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
