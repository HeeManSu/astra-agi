"""E-commerce Order Fulfillment Teams."""

# Import in order: base teams first, then hierarchical team that depends on them
from examples.team_workflow.teams.customer_support_team import customer_support_team
from examples.team_workflow.teams.fraud_detection_team import fraud_detection_team

# Import operations_team last since it depends on other teams
from examples.team_workflow.teams.operations_team import operations_team
from examples.team_workflow.teams.order_processing_team import order_processing_team


__all__ = [
    "customer_support_team",
    "fraud_detection_team",
    "operations_team",
    "order_processing_team",
]
