"""Customer success domain tools for enterprise teams."""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


class PrioritizeSupportTicketInput(BaseModel):
    impact: str = Field(description="low, medium, or high")
    urgency: str = Field(description="low, medium, or high")
    customer_tier: str = Field(description="standard, growth, or enterprise")


class PrioritizeSupportTicketOutput(BaseModel):
    priority: str = Field(description="P1, P2, P3, or P4")
    sla_hours: int = Field(description="Target SLA in hours")
    escalation_required: bool = Field(description="Whether escalation is required")


PRIORITIZE_SUPPORT_TICKET_SPEC = ToolSpec(
    name="prioritize_support_ticket",
    description="Classify ticket priority and SLA based on impact, urgency, and tier",
    input_schema=PrioritizeSupportTicketInput,
    output_schema=PrioritizeSupportTicketOutput,
)


@bind_tool(PRIORITIZE_SUPPORT_TICKET_SPEC)
async def prioritize_support_ticket(
    input: PrioritizeSupportTicketInput,
) -> PrioritizeSupportTicketOutput:
    key = (input.impact.lower(), input.urgency.lower(), input.customer_tier.lower())

    if "high" in key and key[2] == "enterprise":
        return PrioritizeSupportTicketOutput(priority="P1", sla_hours=1, escalation_required=True)
    if "high" in key or key[2] == "enterprise":
        return PrioritizeSupportTicketOutput(priority="P2", sla_hours=4, escalation_required=True)
    if "medium" in key:
        return PrioritizeSupportTicketOutput(priority="P3", sla_hours=12, escalation_required=False)
    return PrioritizeSupportTicketOutput(priority="P4", sla_hours=24, escalation_required=False)


class DraftResolutionStepsInput(BaseModel):
    issue_type: str = Field(description="Issue category")
    system_name: str = Field(description="System/service name")


class DraftResolutionStepsOutput(BaseModel):
    owner_team: str = Field(description="Recommended owner team")
    steps: list[str] = Field(description="Suggested resolution sequence")


DRAFT_RESOLUTION_STEPS_SPEC = ToolSpec(
    name="draft_resolution_steps",
    description="Generate an actionable first-response resolution checklist",
    input_schema=DraftResolutionStepsInput,
    output_schema=DraftResolutionStepsOutput,
)


@bind_tool(DRAFT_RESOLUTION_STEPS_SPEC)
async def draft_resolution_steps(input: DraftResolutionStepsInput) -> DraftResolutionStepsOutput:
    owner = "Platform" if "api" in input.system_name.lower() else "Support Engineering"
    steps = [
        f"Confirm customer impact for {input.system_name}",
        f"Reproduce the {input.issue_type} issue with latest logs",
        "Apply known workaround or rollback",
        "Document root cause hypothesis and next update ETA",
    ]
    return DraftResolutionStepsOutput(owner_team=owner, steps=steps)


class ComputeCustomerHealthInput(BaseModel):
    nps_score: int = Field(description="NPS score from -100 to 100")
    open_tickets: int = Field(description="Count of open tickets")
    renewal_days: int = Field(description="Days until renewal")


class ComputeCustomerHealthOutput(BaseModel):
    health_score: int = Field(description="Health score from 0 to 100")
    health_band: str = Field(description="green, amber, or red")
    action: str = Field(description="Next best action")


COMPUTE_CUSTOMER_HEALTH_SPEC = ToolSpec(
    name="compute_customer_health",
    description="Calculate customer health score and recommended action",
    input_schema=ComputeCustomerHealthInput,
    output_schema=ComputeCustomerHealthOutput,
)


@bind_tool(COMPUTE_CUSTOMER_HEALTH_SPEC)
async def compute_customer_health(
    input: ComputeCustomerHealthInput,
) -> ComputeCustomerHealthOutput:
    base = 60 + int(input.nps_score * 0.2)
    penalty = min(input.open_tickets * 5, 35)
    renewal_modifier = -10 if input.renewal_days < 30 else 0
    score = max(0, min(100, base - penalty + renewal_modifier))

    if score >= 75:
        band = "green"
        action = "Proceed with expansion conversation"
    elif score >= 50:
        band = "amber"
        action = "Run success check-in and close critical tickets"
    else:
        band = "red"
        action = "Escalate to retention plan with leadership"

    return ComputeCustomerHealthOutput(
        health_score=score,
        health_band=band,
        action=action,
    )


class ClassifyChurnRiskInput(BaseModel):
    health_score: int = Field(description="Current health score")
    unresolved_p1_count: int = Field(description="Unresolved P1 tickets")


class ClassifyChurnRiskOutput(BaseModel):
    churn_risk: str = Field(description="low, medium, or high")
    note: str = Field(description="Reasoning note")


CLASSIFY_CHURN_RISK_SPEC = ToolSpec(
    name="classify_churn_risk",
    description="Classify churn risk from health and unresolved critical incidents",
    input_schema=ClassifyChurnRiskInput,
    output_schema=ClassifyChurnRiskOutput,
)


@bind_tool(CLASSIFY_CHURN_RISK_SPEC)
async def classify_churn_risk(input: ClassifyChurnRiskInput) -> ClassifyChurnRiskOutput:
    if input.health_score < 45 or input.unresolved_p1_count >= 2:
        risk = "high"
    elif input.health_score < 70 or input.unresolved_p1_count == 1:
        risk = "medium"
    else:
        risk = "low"
    return ClassifyChurnRiskOutput(risk=risk, note=f"health={input.health_score}, p1={input.unresolved_p1_count}")


class EstimateResolutionEffortInput(BaseModel):
    affected_components: int = Field(description="Number of affected components")
    dependency_teams: int = Field(description="Number of dependency teams")


class EstimateResolutionEffortOutput(BaseModel):
    effort_hours: int = Field(description="Estimated effort in hours")
    complexity: str = Field(description="low, medium, or high")


ESTIMATE_RESOLUTION_EFFORT_SPEC = ToolSpec(
    name="estimate_resolution_effort",
    description="Estimate support resolution effort and complexity",
    input_schema=EstimateResolutionEffortInput,
    output_schema=EstimateResolutionEffortOutput,
)


@bind_tool(ESTIMATE_RESOLUTION_EFFORT_SPEC)
async def estimate_resolution_effort(
    input: EstimateResolutionEffortInput,
) -> EstimateResolutionEffortOutput:
    effort = int((input.affected_components * 2) + (input.dependency_teams * 3))
    cx = "high" if effort >= 18 else "medium" if effort >= 8 else "low"
    return EstimateResolutionEffortOutput(effort_hours=effort, complexity=cx)


class GenerateQBROutlineInput(BaseModel):
    account_name: str = Field(description="Account name")
    quarter: str = Field(description="Quarter label")


class GenerateQBROutlineOutput(BaseModel):
    sections: list[str] = Field(description="QBR section headings")


GENERATE_QBR_OUTLINE_SPEC = ToolSpec(
    name="generate_qbr_outline",
    description="Generate a standard QBR outline",
    input_schema=GenerateQBROutlineInput,
    output_schema=GenerateQBROutlineOutput,
)


@bind_tool(GENERATE_QBR_OUTLINE_SPEC)
async def generate_qbr_outline(input: GenerateQBROutlineInput) -> GenerateQBROutlineOutput:
    return GenerateQBROutlineOutput(
        sections=[
            f"{input.account_name} {input.quarter} Executive Summary",
            "Adoption and Value Metrics",
            "Open Risks and Escalations",
            "Growth Opportunities and Action Plan",
        ]
    )


class SuggestSuccessPlaybookInput(BaseModel):
    issue_pattern: str = Field(description="Recurring issue pattern")


class SuggestSuccessPlaybookOutput(BaseModel):
    playbook_steps: list[str] = Field(description="Suggested playbook steps")


SUGGEST_SUCCESS_PLAYBOOK_SPEC = ToolSpec(
    name="suggest_success_playbook",
    description="Suggest a repeatable customer-success playbook",
    input_schema=SuggestSuccessPlaybookInput,
    output_schema=SuggestSuccessPlaybookOutput,
)


@bind_tool(SUGGEST_SUCCESS_PLAYBOOK_SPEC)
async def suggest_success_playbook(
    input: SuggestSuccessPlaybookInput,
) -> SuggestSuccessPlaybookOutput:
    return SuggestSuccessPlaybookOutput(
        playbook_steps=[
            f"Detect early signal for {input.issue_pattern}",
            "Trigger proactive outreach within 24 hours",
            "Run guided remediation checklist",
            "Track improvement for 2 renewal cycles",
        ]
    )


class RouteTicketQueueInput(BaseModel):
    ticket_type: str = Field(description="Ticket type")


class RouteTicketQueueOutput(BaseModel):
    queue: str = Field(description="Assigned support queue")


ROUTE_TICKET_QUEUE_SPEC = ToolSpec(
    name="route_ticket_queue",
    description="Route ticket to the appropriate support queue",
    input_schema=RouteTicketQueueInput,
    output_schema=RouteTicketQueueOutput,
)


@bind_tool(ROUTE_TICKET_QUEUE_SPEC)
async def route_ticket_queue(input: RouteTicketQueueInput) -> RouteTicketQueueOutput:
    queue = "integrations" if "api" in input.ticket_type.lower() else "general-support"
    return RouteTicketQueueOutput(queue=queue)


class PredictSlaBreachInput(BaseModel):
    backlog_items: int = Field(description="Current backlog items")
    avg_handle_time_minutes: float = Field(description="Average handle time")
    sla_minutes: int = Field(description="SLA target")


class PredictSlaBreachOutput(BaseModel):
    breach_risk: str = Field(description="low, medium, or high")


PREDICT_SLA_BREACH_SPEC = ToolSpec(
    name="predict_sla_breach",
    description="Predict SLA breach risk from queue pressure",
    input_schema=PredictSlaBreachInput,
    output_schema=PredictSlaBreachOutput,
)


@bind_tool(PREDICT_SLA_BREACH_SPEC)
async def predict_sla_breach(input: PredictSlaBreachInput) -> PredictSlaBreachOutput:
    projected = input.backlog_items * input.avg_handle_time_minutes
    ratio = projected / max(input.sla_minutes, 1)
    risk = "high" if ratio > 1.4 else "medium" if ratio > 0.8 else "low"
    return PredictSlaBreachOutput(breach_risk=risk)


class ComputeBacklogPressureInput(BaseModel):
    opened: int = Field(description="Tickets opened")
    closed: int = Field(description="Tickets closed")


class ComputeBacklogPressureOutput(BaseModel):
    net_backlog_change: int = Field(description="Net backlog change")


COMPUTE_BACKLOG_PRESSURE_SPEC = ToolSpec(
    name="compute_backlog_pressure",
    description="Compute net backlog pressure",
    input_schema=ComputeBacklogPressureInput,
    output_schema=ComputeBacklogPressureOutput,
)


@bind_tool(COMPUTE_BACKLOG_PRESSURE_SPEC)
async def compute_backlog_pressure(
    input: ComputeBacklogPressureInput,
) -> ComputeBacklogPressureOutput:
    return ComputeBacklogPressureOutput(net_backlog_change=input.opened - input.closed)


class SuggestEscalationPathInput(BaseModel):
    priority: str = Field(description="Ticket priority")


class SuggestEscalationPathOutput(BaseModel):
    path: list[str] = Field(description="Escalation path")


SUGGEST_ESCALATION_PATH_SPEC = ToolSpec(
    name="suggest_escalation_path",
    description="Suggest escalation path for ticket priority",
    input_schema=SuggestEscalationPathInput,
    output_schema=SuggestEscalationPathOutput,
)


@bind_tool(SUGGEST_ESCALATION_PATH_SPEC)
async def suggest_escalation_path(
    input: SuggestEscalationPathInput,
) -> SuggestEscalationPathOutput:
    if input.priority.upper() == "P1":
        steps = ["IC", "Support Lead", "Engineering Lead", "Executive On-Call"]
    else:
        steps = ["Support Lead", "Engineering Manager"]
    return SuggestEscalationPathOutput(path=steps)


class SummarizeAccountRisksInput(BaseModel):
    account_name: str = Field(description="Account name")
    churn_risk: str = Field(description="Churn risk")


class SummarizeAccountRisksOutput(BaseModel):
    summary: str = Field(description="Account risk summary")


SUMMARIZE_ACCOUNT_RISKS_SPEC = ToolSpec(
    name="summarize_account_risks",
    description="Create concise account risk summary",
    input_schema=SummarizeAccountRisksInput,
    output_schema=SummarizeAccountRisksOutput,
)


@bind_tool(SUMMARIZE_ACCOUNT_RISKS_SPEC)
async def summarize_account_risks(
    input: SummarizeAccountRisksInput,
) -> SummarizeAccountRisksOutput:
    return SummarizeAccountRisksOutput(summary=f"{input.account_name} churn risk is {input.churn_risk}")
