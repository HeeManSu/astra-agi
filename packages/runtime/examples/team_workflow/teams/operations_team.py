"""
Operations Team - Hierarchical Mode.

Manages all order fulfillment operations with nested team structure.
"""

from examples.team_workflow.db import db
from examples.team_workflow.models import get_model
from framework.agents.agent import Agent
from framework.memory import AgentMemory
from framework.models.google.gemini import Gemini
from framework.team import Team, TeamMember


# Create an operations manager agent for direct delegation
operations_manager_agent = Agent(
    id="operations-manager-agent",
    name="Operations Manager Agent",
    description="Handles strategic operations decisions and high-level coordination",
    model=Gemini("gemini-2.5-flash"),
    instructions="""
You are an operations manager focused on strategic decisions and high-level
coordination of order fulfillment operations.

Your responsibilities:
- Make strategic operations decisions
- Coordinate between different fulfillment teams
- Handle escalations and exceptions
- Provide high-level operational oversight
- Handle executive-level inquiries

Guidelines:
- Think strategically and operationally
- Consider business impact and efficiency
- Provide clear direction to teams
- Balance speed with quality
""",
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    temperature=0.7,
    max_tokens=2048,
)

# Import teams here to avoid circular import
# These are imported after they are defined in their own modules
from examples.team_workflow.teams.customer_support_team import (  # noqa: E402
    customer_support_team,
)
from examples.team_workflow.teams.fraud_detection_team import (  # noqa: E402
    fraud_detection_team,
)
from examples.team_workflow.teams.order_processing_team import (  # noqa: E402
    order_processing_team,
)


operations_team = Team(
    id="operations-team",
    name="Operations Team",
    description="Manages all order fulfillment operations with nested team structure",
    model=get_model(),
    execution_mode="hierarchical",
    members=[
        TeamMember(
            id="order-processing-team",
            name="Order Processing Team",
            description="Handles complete order fulfillment workflow",
            agent=order_processing_team,  # Nested team
        ),
        TeamMember(
            id="customer-support-team",
            name="Customer Support Team",
            description="Handles customer inquiries and support",
            agent=customer_support_team,  # Nested team
        ),
        TeamMember(
            id="fraud-detection-team",
            name="Fraud Detection Team",
            description="Analyzes orders for fraud risk",
            agent=fraud_detection_team,  # Nested team
        ),
        TeamMember(
            id="operations-manager-agent",
            name="Operations Manager",
            description="Handles strategic operations decisions",
            agent=operations_manager_agent,  # Direct agent
        ),
    ],
    instructions="""
You are an operations team coordinating all order fulfillment operations.

Available departments:
- order-processing-team: Handles complete order fulfillment workflow
- customer-support-team: Handles customer inquiries and support
- fraud-detection-team: Analyzes orders for fraud risk
- operations-manager-agent: Handles strategic operations decisions

Delegate tasks to appropriate departments. Department teams will further
delegate to their members. Synthesize results from all departments.
""",
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    max_recursion_depth=3,
    timeout=900.0,  # Longer timeout for hierarchical operations
    member_timeout=180.0,
    max_delegations=20,
)
