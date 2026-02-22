"""IT operations tools for enterprise teams."""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


class ClassifyIncidentSeverityInput(BaseModel):
    affected_users: int = Field(description="Number of affected users")
    revenue_impact_per_hour: float = Field(description="Revenue impact per hour in USD")
    data_loss: bool = Field(description="Whether data loss is observed")


class ClassifyIncidentSeverityOutput(BaseModel):
    severity: str = Field(description="SEV1, SEV2, or SEV3")
    response_sla_minutes: int = Field(description="Response SLA in minutes")
    rationale: str = Field(description="Classification rationale")


CLASSIFY_INCIDENT_SEVERITY_SPEC = ToolSpec(
    name="classify_incident_severity",
    description="Classify incident criticality and response SLA",
    input_schema=ClassifyIncidentSeverityInput,
    output_schema=ClassifyIncidentSeverityOutput,
)


@bind_tool(CLASSIFY_INCIDENT_SEVERITY_SPEC)
async def classify_incident_severity(
    input: ClassifyIncidentSeverityInput,
) -> ClassifyIncidentSeverityOutput:
    if input.data_loss or input.revenue_impact_per_hour >= 10000 or input.affected_users >= 5000:
        sev = "SEV1"
        sla = 10
    elif input.revenue_impact_per_hour >= 2000 or input.affected_users >= 500:
        sev = "SEV2"
        sla = 30
    else:
        sev = "SEV3"
        sla = 120

    rationale = (
        f"affected_users={input.affected_users}, impact=${input.revenue_impact_per_hour}/h, "
        f"data_loss={input.data_loss}"
    )
    return ClassifyIncidentSeverityOutput(severity=sev, response_sla_minutes=sla, rationale=rationale)


class GenerateRunbookTasksInput(BaseModel):
    service_name: str = Field(description="Service name")
    incident_type: str = Field(description="Incident type")


class GenerateRunbookTasksOutput(BaseModel):
    tasks: list[str] = Field(description="Ordered runbook tasks")
    rollback_needed: bool = Field(description="Whether rollback is likely needed")


GENERATE_RUNBOOK_TASKS_SPEC = ToolSpec(
    name="generate_runbook_tasks",
    description="Generate first-response runbook tasks for a service incident",
    input_schema=GenerateRunbookTasksInput,
    output_schema=GenerateRunbookTasksOutput,
)


@bind_tool(GENERATE_RUNBOOK_TASKS_SPEC)
async def generate_runbook_tasks(
    input: GenerateRunbookTasksInput,
) -> GenerateRunbookTasksOutput:
    rollback_needed = "deploy" in input.incident_type.lower() or "release" in input.incident_type.lower()
    tasks = [
        f"Declare incident for {input.service_name}",
        "Collect logs, traces, and recent deploy metadata",
        "Mitigate user impact with failover or feature flags",
        "Prepare stakeholder update with ETA",
    ]
    if rollback_needed:
        tasks.append("Execute controlled rollback and verify service health")

    return GenerateRunbookTasksOutput(tasks=tasks, rollback_needed=rollback_needed)


class ValidateChangeWindowInput(BaseModel):
    start_utc: str = Field(description="Planned UTC start timestamp")
    duration_minutes: int = Field(description="Duration in minutes")
    peak_traffic_expected: bool = Field(description="True if peak traffic expected")


class ValidateChangeWindowOutput(BaseModel):
    approved: bool = Field(description="Approval result")
    reason: str = Field(description="Decision reason")
    suggested_window: str = Field(description="Suggested fallback window")


VALIDATE_CHANGE_WINDOW_SPEC = ToolSpec(
    name="validate_change_window",
    description="Validate maintenance window against traffic and risk constraints",
    input_schema=ValidateChangeWindowInput,
    output_schema=ValidateChangeWindowOutput,
)


@bind_tool(VALIDATE_CHANGE_WINDOW_SPEC)
async def validate_change_window(
    input: ValidateChangeWindowInput,
) -> ValidateChangeWindowOutput:
    long_change = input.duration_minutes > 90

    if input.peak_traffic_expected and long_change:
        return ValidateChangeWindowOutput(
            approved=False,
            reason="Duration too long for predicted peak-traffic window",
            suggested_window="Next off-peak window (02:00-04:00 UTC)",
        )

    if input.peak_traffic_expected:
        return ValidateChangeWindowOutput(
            approved=True,
            reason="Approved with enhanced monitoring during peak window",
            suggested_window=input.start_utc,
        )

    return ValidateChangeWindowOutput(
        approved=True,
        reason="Approved for off-peak execution",
        suggested_window=input.start_utc,
    )


class CalculateErrorBudgetInput(BaseModel):
    slo_target_percent: float = Field(description="SLO target percent")
    observed_uptime_percent: float = Field(description="Observed uptime percent")


class CalculateErrorBudgetOutput(BaseModel):
    budget_remaining_percent: float = Field(description="Remaining error budget percent")
    burn_status: str = Field(description="healthy, warning, or exhausted")


CALCULATE_ERROR_BUDGET_SPEC = ToolSpec(
    name="calculate_error_budget",
    description="Calculate remaining error budget against SLO",
    input_schema=CalculateErrorBudgetInput,
    output_schema=CalculateErrorBudgetOutput,
)


@bind_tool(CALCULATE_ERROR_BUDGET_SPEC)
async def calculate_error_budget(input: CalculateErrorBudgetInput) -> CalculateErrorBudgetOutput:
    allowed = max(0.0, 100.0 - input.slo_target_percent)
    used = max(0.0, input.slo_target_percent - input.observed_uptime_percent)
    remaining = round(max(0.0, allowed - used), 3)
    status = "healthy" if remaining > (allowed * 0.5) else "warning" if remaining > 0 else "exhausted"
    return CalculateErrorBudgetOutput(budget_remaining_percent=remaining, burn_status=status)


class AssessReleaseRiskInput(BaseModel):
    changed_services: int = Field(description="Number of services changed")
    rollback_tested: bool = Field(description="Whether rollback path was tested")


class AssessReleaseRiskOutput(BaseModel):
    release_risk: str = Field(description="low, medium, or high")
    recommendation: str = Field(description="Recommended control action")


ASSESS_RELEASE_RISK_SPEC = ToolSpec(
    name="assess_release_risk",
    description="Assess release risk from blast radius and rollback readiness",
    input_schema=AssessReleaseRiskInput,
    output_schema=AssessReleaseRiskOutput,
)


@bind_tool(ASSESS_RELEASE_RISK_SPEC)
async def assess_release_risk(input: AssessReleaseRiskInput) -> AssessReleaseRiskOutput:
    if input.changed_services >= 5 and not input.rollback_tested:
        risk = "high"
    elif input.changed_services >= 3:
        risk = "medium"
    else:
        risk = "low"
    rec = "Require staged rollout and approval" if risk != "low" else "Proceed with standard checks"
    return AssessReleaseRiskOutput(release_risk=risk, recommendation=rec)


class EstimateCapacityHeadroomInput(BaseModel):
    current_utilization_percent: float = Field(description="Current utilization percent")
    projected_peak_percent: float = Field(description="Projected peak utilization percent")


class EstimateCapacityHeadroomOutput(BaseModel):
    headroom_percent: float = Field(description="Capacity headroom percent")
    action: str = Field(description="Capacity action recommendation")


ESTIMATE_CAPACITY_HEADROOM_SPEC = ToolSpec(
    name="estimate_capacity_headroom",
    description="Estimate capacity headroom before projected peak",
    input_schema=EstimateCapacityHeadroomInput,
    output_schema=EstimateCapacityHeadroomOutput,
)


@bind_tool(ESTIMATE_CAPACITY_HEADROOM_SPEC)
async def estimate_capacity_headroom(
    input: EstimateCapacityHeadroomInput,
) -> EstimateCapacityHeadroomOutput:
    headroom = round(100.0 - max(input.current_utilization_percent, input.projected_peak_percent), 2)
    action = "Scale up capacity" if headroom < 15 else "Capacity sufficient"
    return EstimateCapacityHeadroomOutput(headroom_percent=headroom, action=action)


class DraftPostmortemSummaryInput(BaseModel):
    incident_id: str = Field(description="Incident identifier")
    root_cause: str = Field(description="Root cause summary")


class DraftPostmortemSummaryOutput(BaseModel):
    summary: str = Field(description="Postmortem summary")


DRAFT_POSTMORTEM_SUMMARY_SPEC = ToolSpec(
    name="draft_postmortem_summary",
    description="Draft concise postmortem summary for incident records",
    input_schema=DraftPostmortemSummaryInput,
    output_schema=DraftPostmortemSummaryOutput,
)


@bind_tool(DRAFT_POSTMORTEM_SUMMARY_SPEC)
async def draft_postmortem_summary(
    input: DraftPostmortemSummaryInput,
) -> DraftPostmortemSummaryOutput:
    return DraftPostmortemSummaryOutput(
        summary=f"Incident {input.incident_id}: root cause={input.root_cause}. Preventive actions scheduled."
    )


class MapIncidentDependenciesInput(BaseModel):
    impacted_service_count: int = Field(description="Impacted service count")


class MapIncidentDependenciesOutput(BaseModel):
    dependency_depth: int = Field(description="Estimated dependency depth")


MAP_INCIDENT_DEPENDENCIES_SPEC = ToolSpec(
    name="map_incident_dependencies",
    description="Estimate dependency depth for incident scope",
    input_schema=MapIncidentDependenciesInput,
    output_schema=MapIncidentDependenciesOutput,
)


@bind_tool(MAP_INCIDENT_DEPENDENCIES_SPEC)
async def map_incident_dependencies(
    input: MapIncidentDependenciesInput,
) -> MapIncidentDependenciesOutput:
    depth = 1 if input.impacted_service_count <= 2 else 2 if input.impacted_service_count <= 5 else 3
    return MapIncidentDependenciesOutput(dependency_depth=depth)


class EvaluateMonitoringCoverageInput(BaseModel):
    monitored_endpoints: int = Field(description="Monitored endpoints")
    total_endpoints: int = Field(description="Total endpoints")


class EvaluateMonitoringCoverageOutput(BaseModel):
    coverage_percent: float = Field(description="Coverage percent")


EVALUATE_MONITORING_COVERAGE_SPEC = ToolSpec(
    name="evaluate_monitoring_coverage",
    description="Evaluate service monitoring coverage",
    input_schema=EvaluateMonitoringCoverageInput,
    output_schema=EvaluateMonitoringCoverageOutput,
)


@bind_tool(EVALUATE_MONITORING_COVERAGE_SPEC)
async def evaluate_monitoring_coverage(
    input: EvaluateMonitoringCoverageInput,
) -> EvaluateMonitoringCoverageOutput:
    coverage = round((input.monitored_endpoints / max(input.total_endpoints, 1)) * 100.0, 2)
    return EvaluateMonitoringCoverageOutput(coverage_percent=coverage)


class PrioritizeRemediationItemsInput(BaseModel):
    item_scores: list[int] = Field(description="Remediation scores")


class PrioritizeRemediationItemsOutput(BaseModel):
    top_indices: list[int] = Field(description="Top remediation indices")


PRIORITIZE_REMEDIATION_ITEMS_SPEC = ToolSpec(
    name="prioritize_remediation_items",
    description="Prioritize remediation backlog items",
    input_schema=PrioritizeRemediationItemsInput,
    output_schema=PrioritizeRemediationItemsOutput,
)


@bind_tool(PRIORITIZE_REMEDIATION_ITEMS_SPEC)
async def prioritize_remediation_items(
    input: PrioritizeRemediationItemsInput,
) -> PrioritizeRemediationItemsOutput:
    ranked = sorted(range(len(input.item_scores)), key=lambda i: input.item_scores[i], reverse=True)
    return PrioritizeRemediationItemsOutput(top_indices=ranked[:5])


class EstimateMttrImprovementInput(BaseModel):
    current_mttr_minutes: int = Field(description="Current MTTR")
    automation_gain_percent: float = Field(description="Expected automation gain percent")


class EstimateMttrImprovementOutput(BaseModel):
    projected_mttr_minutes: float = Field(description="Projected MTTR")


ESTIMATE_MTTR_IMPROVEMENT_SPEC = ToolSpec(
    name="estimate_mttr_improvement",
    description="Estimate MTTR improvement from automation",
    input_schema=EstimateMttrImprovementInput,
    output_schema=EstimateMttrImprovementOutput,
)


@bind_tool(ESTIMATE_MTTR_IMPROVEMENT_SPEC)
async def estimate_mttr_improvement(
    input: EstimateMttrImprovementInput,
) -> EstimateMttrImprovementOutput:
    projected = round(input.current_mttr_minutes * (1 - input.automation_gain_percent / 100.0), 2)
    return EstimateMttrImprovementOutput(projected_mttr_minutes=max(projected, 1.0))


class SummarizeServiceReliabilityInput(BaseModel):
    sev1_count: int = Field(description="SEV1 count")
    error_budget_remaining: float = Field(description="Remaining error budget")


class SummarizeServiceReliabilityOutput(BaseModel):
    summary: str = Field(description="Reliability summary")


SUMMARIZE_SERVICE_RELIABILITY_SPEC = ToolSpec(
    name="summarize_service_reliability",
    description="Create concise reliability summary",
    input_schema=SummarizeServiceReliabilityInput,
    output_schema=SummarizeServiceReliabilityOutput,
)


@bind_tool(SUMMARIZE_SERVICE_RELIABILITY_SPEC)
async def summarize_service_reliability(
    input: SummarizeServiceReliabilityInput,
) -> SummarizeServiceReliabilityOutput:
    return SummarizeServiceReliabilityOutput(
        summary=f"SEV1={input.sev1_count}, error budget remaining={input.error_budget_remaining}%"
    )
