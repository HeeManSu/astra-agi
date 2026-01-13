"""
Fraud Detection Agent - E-commerce Order Fulfillment.

Analyzes orders for potential fraud indicators.
"""

from examples.team_workflow.db import db
from examples.team_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.team_workflow.models import get_model
from examples.team_workflow.tools.fraud_detection import check_fraud_risk
from framework.agents.agent import Agent
from framework.memory import AgentMemory


fraud_detection_agent = Agent(
    id="fraud-detection-agent",
    name="Fraud Detection Agent",
    description=(
        "Analyzes orders for potential fraud indicators and provides risk "
        "assessments for order approval"
    ),
    model=get_model(),
    instructions="""
You are a fraud detection specialist responsible for identifying potentially
fraudulent orders.

Your responsibilities:
- Analyze orders for fraud risk indicators
- Check for suspicious patterns (high value, address mismatch, etc.)
- Provide risk scores and recommendations
- Flag orders requiring manual review
- Identify payment method risks
- Assess customer behavior patterns

Guidelines:
- Be thorough in fraud analysis
- Flag suspicious patterns immediately
- Provide clear risk assessments
- Recommend manual review for medium/high risk orders
- Balance fraud prevention with customer experience
- Use multiple indicators for risk assessment
""",
    tools=[check_fraud_risk],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=False,  # Fraud detection needs complete analysis
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.2,  # Very low temperature for consistent fraud detection
    max_tokens=1024,
)
