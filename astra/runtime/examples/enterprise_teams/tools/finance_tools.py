"""Finance domain tools for enterprise teams."""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


class EvaluateBudgetVarianceInput(BaseModel):
    planned_spend: float = Field(description="Planned spend in USD")
    actual_spend: float = Field(description="Actual spend in USD")


class EvaluateBudgetVarianceOutput(BaseModel):
    variance_amount: float = Field(description="Actual minus planned spend")
    variance_percent: float = Field(description="Variance percentage")
    status: str = Field(description="under_budget, on_track, or over_budget")


EVALUATE_BUDGET_VARIANCE_SPEC = ToolSpec(
    name="evaluate_budget_variance",
    description="Compare planned and actual spend and classify budget health",
    input_schema=EvaluateBudgetVarianceInput,
    output_schema=EvaluateBudgetVarianceOutput,
)


@bind_tool(EVALUATE_BUDGET_VARIANCE_SPEC)
async def evaluate_budget_variance(
    input: EvaluateBudgetVarianceInput,
) -> EvaluateBudgetVarianceOutput:
    variance = round(input.actual_spend - input.planned_spend, 2)
    baseline = input.planned_spend if input.planned_spend else 1.0
    variance_percent = round((variance / baseline) * 100.0, 2)

    if variance_percent > 5:
        status = "over_budget"
    elif variance_percent < -5:
        status = "under_budget"
    else:
        status = "on_track"

    return EvaluateBudgetVarianceOutput(
        variance_amount=variance,
        variance_percent=variance_percent,
        status=status,
    )


class ForecastCashFlowInput(BaseModel):
    current_cash: float = Field(description="Current cash balance in USD")
    monthly_revenue: float = Field(description="Average monthly revenue")
    monthly_burn: float = Field(description="Average monthly spend")
    months: int = Field(default=6, description="Forecast horizon in months")


class ForecastCashFlowOutput(BaseModel):
    ending_cash: float = Field(description="Projected ending cash")
    runway_months: float = Field(description="Estimated runway months")
    recommendation: str = Field(description="Liquidity recommendation")


FORECAST_CASH_FLOW_SPEC = ToolSpec(
    name="forecast_cash_flow",
    description="Forecast cash position and runway based on simple operating assumptions",
    input_schema=ForecastCashFlowInput,
    output_schema=ForecastCashFlowOutput,
)


@bind_tool(FORECAST_CASH_FLOW_SPEC)
async def forecast_cash_flow(input: ForecastCashFlowInput) -> ForecastCashFlowOutput:
    monthly_net = input.monthly_revenue - input.monthly_burn
    ending_cash = round(input.current_cash + (monthly_net * input.months), 2)

    if input.monthly_burn <= 0:
        runway = 120.0
    else:
        runway = round(max(ending_cash, 0) / input.monthly_burn, 2)

    if runway < 6:
        rec = "Reduce burn or secure financing within this quarter"
    elif runway < 12:
        rec = "Monitor spend weekly and defer non-critical initiatives"
    else:
        rec = "Liquidity healthy; continue planned execution"

    return ForecastCashFlowOutput(
        ending_cash=ending_cash,
        runway_months=runway,
        recommendation=rec,
    )


class AssessVendorRiskInput(BaseModel):
    vendor_name: str = Field(description="Vendor name")
    dependency_level: str = Field(description="low, medium, or high")
    sla_breaches_last_quarter: int = Field(
        ge=0, description="Count of SLA breaches in last quarter"
    )


class AssessVendorRiskOutput(BaseModel):
    vendor_name: str = Field(description="Vendor name")
    risk_score: int = Field(description="Risk score on 0-100")
    risk_tier: str = Field(description="low, medium, or high")
    summary: str = Field(description="Short risk summary")


ASSESS_VENDOR_RISK_SPEC = ToolSpec(
    name="assess_vendor_risk",
    description="Estimate vendor operational risk from dependency and SLA quality",
    input_schema=AssessVendorRiskInput,
    output_schema=AssessVendorRiskOutput,
)


@bind_tool(ASSESS_VENDOR_RISK_SPEC)
async def assess_vendor_risk(input: AssessVendorRiskInput) -> AssessVendorRiskOutput:
    dependency_weight = {"low": 20, "medium": 40, "high": 60}.get(
        input.dependency_level.lower(), 40
    )
    breach_penalty = min(input.sla_breaches_last_quarter * 8, 40)
    risk_score = max(0, min(dependency_weight + breach_penalty, 100))

    if risk_score >= 70:
        tier = "high"
    elif risk_score >= 40:
        tier = "medium"
    else:
        tier = "low"

    summary = (
        f"{input.vendor_name} risk={tier} (score={risk_score}) based on "
        f"dependency={input.dependency_level} and SLA breaches={input.sla_breaches_last_quarter}."
    )

    return AssessVendorRiskOutput(
        vendor_name=input.vendor_name,
        risk_score=risk_score,
        risk_tier=tier,
        summary=summary,
    )


class ComputeWorkingCapitalInput(BaseModel):
    current_assets: float = Field(description="Current assets")
    current_liabilities: float = Field(description="Current liabilities")


class ComputeWorkingCapitalOutput(BaseModel):
    working_capital: float = Field(description="Working capital")
    liquidity_band: str = Field(description="strong, moderate, or weak")


COMPUTE_WORKING_CAPITAL_SPEC = ToolSpec(
    name="compute_working_capital",
    description="Compute working capital and classify liquidity band",
    input_schema=ComputeWorkingCapitalInput,
    output_schema=ComputeWorkingCapitalOutput,
)


@bind_tool(COMPUTE_WORKING_CAPITAL_SPEC)
async def compute_working_capital(input: ComputeWorkingCapitalInput) -> ComputeWorkingCapitalOutput:
    wc = round(input.current_assets - input.current_liabilities, 2)
    band = "strong" if wc > 100000 else "moderate" if wc >= 0 else "weak"
    return ComputeWorkingCapitalOutput(working_capital=wc, liquidity_band=band)


class ScoreCreditExposureInput(BaseModel):
    receivable_amount: float = Field(ge=0, description="Total receivables")
    overdue_amount: float = Field(ge=0, description="Overdue receivables")


class ScoreCreditExposureOutput(BaseModel):
    exposure_ratio: float = Field(description="Overdue-to-total ratio")
    exposure_score: int = Field(description="Score 0-100 (higher is worse)")


SCORE_CREDIT_EXPOSURE_SPEC = ToolSpec(
    name="score_credit_exposure",
    description="Score credit exposure from overdue receivables",
    input_schema=ScoreCreditExposureInput,
    output_schema=ScoreCreditExposureOutput,
)


@bind_tool(SCORE_CREDIT_EXPOSURE_SPEC)
async def score_credit_exposure(input: ScoreCreditExposureInput) -> ScoreCreditExposureOutput:
    ratio = round(input.overdue_amount / max(input.receivable_amount, 1.0), 4)
    score = max(0, min(100, int(ratio * 140)))
    return ScoreCreditExposureOutput(exposure_ratio=ratio, exposure_score=score)


class DetectExpenseAnomalyInput(BaseModel):
    baseline_monthly_spend: float = Field(description="Baseline monthly spend")
    current_monthly_spend: float = Field(description="Current monthly spend")


class DetectExpenseAnomalyOutput(BaseModel):
    anomaly_detected: bool = Field(description="True if spend anomaly detected")
    delta_percent: float = Field(description="Spend delta in percent")


DETECT_EXPENSE_ANOMALY_SPEC = ToolSpec(
    name="detect_expense_anomaly",
    description="Detect month-over-month spend anomaly",
    input_schema=DetectExpenseAnomalyInput,
    output_schema=DetectExpenseAnomalyOutput,
)


@bind_tool(DETECT_EXPENSE_ANOMALY_SPEC)
async def detect_expense_anomaly(input: DetectExpenseAnomalyInput) -> DetectExpenseAnomalyOutput:
    delta = round(
        (
            (input.current_monthly_spend - input.baseline_monthly_spend)
            / max(input.baseline_monthly_spend, 1.0)
        )
        * 100.0,
        2,
    )
    return DetectExpenseAnomalyOutput(anomaly_detected=abs(delta) >= 12.0, delta_percent=delta)


class PlanCapexPriorityInput(BaseModel):
    project_name: str = Field(description="Project name")
    expected_roi_percent: float = Field(description="Expected ROI percent")
    compliance_required: bool = Field(description="Whether project is compliance-mandated")


class PlanCapexPriorityOutput(BaseModel):
    priority: str = Field(description="high, medium, or low")
    note: str = Field(description="Decision note")


PLAN_CAPEX_PRIORITY_SPEC = ToolSpec(
    name="plan_capex_priority",
    description="Assign capex priority from ROI and compliance context",
    input_schema=PlanCapexPriorityInput,
    output_schema=PlanCapexPriorityOutput,
)


@bind_tool(PLAN_CAPEX_PRIORITY_SPEC)
async def plan_capex_priority(input: PlanCapexPriorityInput) -> PlanCapexPriorityOutput:
    if input.compliance_required or input.expected_roi_percent >= 20:
        p = "high"
    elif input.expected_roi_percent >= 10:
        p = "medium"
    else:
        p = "low"
    return PlanCapexPriorityOutput(priority=p, note=f"{input.project_name} set to {p} priority")


class ModelRevenueScenarioInput(BaseModel):
    baseline_revenue: float = Field(description="Baseline monthly revenue")
    growth_percent: float = Field(description="Growth scenario percent")


class ModelRevenueScenarioOutput(BaseModel):
    projected_revenue: float = Field(description="Projected revenue")


MODEL_REVENUE_SCENARIO_SPEC = ToolSpec(
    name="model_revenue_scenario",
    description="Project revenue under a growth scenario",
    input_schema=ModelRevenueScenarioInput,
    output_schema=ModelRevenueScenarioOutput,
)


@bind_tool(MODEL_REVENUE_SCENARIO_SPEC)
async def model_revenue_scenario(input: ModelRevenueScenarioInput) -> ModelRevenueScenarioOutput:
    projected = round(input.baseline_revenue * (1 + input.growth_percent / 100.0), 2)
    return ModelRevenueScenarioOutput(projected_revenue=projected)


class ComputeProfitMarginInput(BaseModel):
    revenue: float = Field(description="Revenue")
    cost: float = Field(description="Cost")


class ComputeProfitMarginOutput(BaseModel):
    margin_percent: float = Field(description="Profit margin percent")


COMPUTE_PROFIT_MARGIN_SPEC = ToolSpec(
    name="compute_profit_margin",
    description="Compute profit margin from revenue and cost",
    input_schema=ComputeProfitMarginInput,
    output_schema=ComputeProfitMarginOutput,
)


@bind_tool(COMPUTE_PROFIT_MARGIN_SPEC)
async def compute_profit_margin(input: ComputeProfitMarginInput) -> ComputeProfitMarginOutput:
    margin = round(((input.revenue - input.cost) / max(input.revenue, 1.0)) * 100.0, 2)
    return ComputeProfitMarginOutput(margin_percent=margin)


class EvaluateCostCenterHealthInput(BaseModel):
    budget: float = Field(description="Cost center budget")
    actual: float = Field(description="Actual spend")


class EvaluateCostCenterHealthOutput(BaseModel):
    health: str = Field(description="healthy, watch, or critical")


EVALUATE_COST_CENTER_HEALTH_SPEC = ToolSpec(
    name="evaluate_cost_center_health",
    description="Classify cost center spending health",
    input_schema=EvaluateCostCenterHealthInput,
    output_schema=EvaluateCostCenterHealthOutput,
)


@bind_tool(EVALUATE_COST_CENTER_HEALTH_SPEC)
async def evaluate_cost_center_health(
    input: EvaluateCostCenterHealthInput,
) -> EvaluateCostCenterHealthOutput:
    ratio = input.actual / max(input.budget, 1.0)
    health = "critical" if ratio > 1.15 else "watch" if ratio > 1.0 else "healthy"
    return EvaluateCostCenterHealthOutput(health=health)


class RankInvestmentProjectsInput(BaseModel):
    project_scores: list[float] = Field(description="List of project scores")


class RankInvestmentProjectsOutput(BaseModel):
    ranked_indices: list[int] = Field(description="Project indices ranked high-to-low")


RANK_INVESTMENT_PROJECTS_SPEC = ToolSpec(
    name="rank_investment_projects",
    description="Rank projects by score",
    input_schema=RankInvestmentProjectsInput,
    output_schema=RankInvestmentProjectsOutput,
)


@bind_tool(RANK_INVESTMENT_PROJECTS_SPEC)
async def rank_investment_projects(
    input: RankInvestmentProjectsInput,
) -> RankInvestmentProjectsOutput:
    ranked = sorted(
        range(len(input.project_scores)), key=lambda i: input.project_scores[i], reverse=True
    )
    return RankInvestmentProjectsOutput(ranked_indices=ranked)


class SummarizeFinanceKpisInput(BaseModel):
    cash_runway_months: float = Field(description="Cash runway")
    margin_percent: float = Field(description="Margin percent")


class SummarizeFinanceKpisOutput(BaseModel):
    summary: str = Field(description="Finance KPI summary")


SUMMARIZE_FINANCE_KPIS_SPEC = ToolSpec(
    name="summarize_finance_kpis",
    description="Create a compact finance KPI summary",
    input_schema=SummarizeFinanceKpisInput,
    output_schema=SummarizeFinanceKpisOutput,
)


@bind_tool(SUMMARIZE_FINANCE_KPIS_SPEC)
async def summarize_finance_kpis(input: SummarizeFinanceKpisInput) -> SummarizeFinanceKpisOutput:
    text = f"Runway={input.cash_runway_months} months, margin={input.margin_percent}%"
    return SummarizeFinanceKpisOutput(summary=text)
