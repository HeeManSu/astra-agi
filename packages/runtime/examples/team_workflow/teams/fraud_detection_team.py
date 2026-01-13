"""
Fraud Detection Team - Collaborate Mode.

Multiple fraud analysts review the same order simultaneously for comprehensive
fraud risk assessment.
"""

from examples.team_workflow.agents import fraud_detection_agent
from examples.team_workflow.db import db
from examples.team_workflow.models import get_model
from framework.memory import AgentMemory
from framework.team import Team, TeamMember


# Create multiple fraud analyst instances with different perspectives
# In a real scenario, these would be different agents, but for this example
# we'll use the same agent with different IDs and descriptions
fraud_analyst_1 = fraud_detection_agent
fraud_analyst_2 = fraud_detection_agent
fraud_analyst_3 = fraud_detection_agent

fraud_detection_team = Team(
    id="fraud-detection-team",
    name="Fraud Detection Team",
    description=(
        "Multiple fraud analysts review the same order simultaneously for "
        "comprehensive fraud risk assessment"
    ),
    model=get_model(),
    execution_mode="collaborate",
    members=[
        TeamMember(
            id="fraud-analyst-1",
            name="Fraud Analyst 1",
            description=(
                "Fraud analyst focusing on payment method and transaction pattern analysis"
            ),
            agent=fraud_analyst_1,
        ),
        TeamMember(
            id="fraud-analyst-2",
            name="Fraud Analyst 2",
            description=(
                "Fraud analyst focusing on address verification and geographic risk assessment"
            ),
            agent=fraud_analyst_2,
        ),
        TeamMember(
            id="fraud-analyst-3",
            name="Fraud Analyst 3",
            description=(
                "Fraud analyst focusing on customer behavior and order value risk assessment"
            ),
            agent=fraud_analyst_3,
        ),
    ],
    instructions="""
You are coordinating a collaborative fraud detection session. All fraud analysts
work on the same order simultaneously to provide comprehensive fraud risk assessment.

Delegate the SAME order to all fraud analysts, then synthesize their different
risk assessments into a unified fraud analysis with consensus recommendation.
""",
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    timeout=600.0,
    member_timeout=120.0,
    max_delegations=5,
)
