"""
Payment Agent - E-commerce Order Fulfillment.

Processes payments and handles refunds for orders.
"""

from examples.team_workflow.db import db
from examples.team_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.team_workflow.models import get_model
from examples.team_workflow.tools.payment_agent import process_payment, refund_payment
from framework.agents.agent import Agent
from framework.memory import AgentMemory


payment_agent = Agent(
    id="payment-agent",
    name="Payment Agent",
    description=(
        "Processes payments and handles refunds for orders using payment gateway integration"
    ),
    model=get_model(),
    instructions="""
You are a payment processing specialist responsible for handling financial transactions.

Your responsibilities:
- Process payments for orders
- Handle payment failures and retries
- Process refunds when needed
- Verify payment methods
- Handle high-value payment verification
- Maintain transaction records

Guidelines:
- Always verify payment amounts before processing
- Handle payment failures gracefully
- Process refunds accurately and promptly
- Flag suspicious payment patterns
- Maintain clear transaction records
- Ensure payment security and compliance
""",
    tools=[process_payment, refund_payment],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.2,  # Very low temperature for financial accuracy
    max_tokens=1024,
)
