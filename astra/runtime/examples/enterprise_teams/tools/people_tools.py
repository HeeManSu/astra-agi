"""People operations tools for enterprise teams."""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


class ScreenCandidateProfileInput(BaseModel):
    role: str = Field(description="Role title")
    years_experience: int = Field(description="Years of experience")
    skills: list[str] = Field(description="Candidate skills")


class ScreenCandidateProfileOutput(BaseModel):
    shortlist_score: int = Field(description="Fit score out of 100")
    decision: str = Field(description="advance, hold, or reject")
    notes: str = Field(description="Short screening notes")


SCREEN_CANDIDATE_PROFILE_SPEC = ToolSpec(
    name="screen_candidate_profile",
    description="Evaluate candidate fit for a role based on experience and skills",
    input_schema=ScreenCandidateProfileInput,
    output_schema=ScreenCandidateProfileOutput,
)


@bind_tool(SCREEN_CANDIDATE_PROFILE_SPEC)
async def screen_candidate_profile(
    input: ScreenCandidateProfileInput,
) -> ScreenCandidateProfileOutput:
    skill_bonus = min(len(input.skills) * 6, 30)
    exp_bonus = min(input.years_experience * 4, 40)
    score = min(100, 30 + skill_bonus + exp_bonus)

    if score >= 75:
        decision = "advance"
    elif score >= 55:
        decision = "hold"
    else:
        decision = "reject"

    notes = f"Role={input.role}; experience={input.years_experience}; skills={len(input.skills)}"
    return ScreenCandidateProfileOutput(
        shortlist_score=score,
        decision=decision,
        notes=notes,
    )


class PlanInterviewPanelInput(BaseModel):
    role: str = Field(description="Role title")
    seniority: str = Field(description="junior, mid, senior, or staff")


class PlanInterviewPanelOutput(BaseModel):
    panel_roles: list[str] = Field(description="Interview panel role list")
    rounds: int = Field(description="Recommended rounds")


PLAN_INTERVIEW_PANEL_SPEC = ToolSpec(
    name="plan_interview_panel",
    description="Recommend interview panel composition and number of rounds",
    input_schema=PlanInterviewPanelInput,
    output_schema=PlanInterviewPanelOutput,
)


@bind_tool(PLAN_INTERVIEW_PANEL_SPEC)
async def plan_interview_panel(input: PlanInterviewPanelInput) -> PlanInterviewPanelOutput:
    base_panel = ["Hiring Manager", "Functional Interviewer", "Cross-Functional Partner"]

    if input.seniority.lower() in {"senior", "staff"}:
        base_panel.append("Executive Interviewer")
        rounds = 5
    elif input.seniority.lower() == "mid":
        rounds = 4
    else:
        rounds = 3

    return PlanInterviewPanelOutput(panel_roles=base_panel, rounds=rounds)


class IdentifyTrainingGapsInput(BaseModel):
    team_name: str = Field(description="Team name")
    current_skills: list[str] = Field(description="Current known skills")
    required_skills: list[str] = Field(description="Skills required for next quarter")


class IdentifyTrainingGapsOutput(BaseModel):
    missing_skills: list[str] = Field(description="Missing skills")
    priority: str = Field(description="low, medium, or high")
    recommendation: str = Field(description="Suggested enablement plan")


IDENTIFY_TRAINING_GAPS_SPEC = ToolSpec(
    name="identify_training_gaps",
    description="Identify capability gaps and recommend upskilling priority",
    input_schema=IdentifyTrainingGapsInput,
    output_schema=IdentifyTrainingGapsOutput,
)


@bind_tool(IDENTIFY_TRAINING_GAPS_SPEC)
async def identify_training_gaps(
    input: IdentifyTrainingGapsInput,
) -> IdentifyTrainingGapsOutput:
    current = {skill.lower() for skill in input.current_skills}
    missing = [skill for skill in input.required_skills if skill.lower() not in current]

    if len(missing) >= 4:
        priority = "high"
    elif len(missing) >= 2:
        priority = "medium"
    else:
        priority = "low"

    recommendation = (
        f"Team {input.team_name} should run a 30-day enablement sprint on: "
        + (", ".join(missing) if missing else "no critical gaps")
    )

    return IdentifyTrainingGapsOutput(
        missing_skills=missing,
        priority=priority,
        recommendation=recommendation,
    )


class ComputeHiringVelocityInput(BaseModel):
    open_roles: int = Field(description="Open roles")
    hires_last_30_days: int = Field(description="Hires in last 30 days")


class ComputeHiringVelocityOutput(BaseModel):
    velocity: float = Field(description="Hires per open role")
    status: str = Field(description="fast, steady, or slow")


COMPUTE_HIRING_VELOCITY_SPEC = ToolSpec(
    name="compute_hiring_velocity",
    description="Compute hiring velocity from open roles and recent hires",
    input_schema=ComputeHiringVelocityInput,
    output_schema=ComputeHiringVelocityOutput,
)


@bind_tool(COMPUTE_HIRING_VELOCITY_SPEC)
async def compute_hiring_velocity(
    input: ComputeHiringVelocityInput,
) -> ComputeHiringVelocityOutput:
    velocity = round(input.hires_last_30_days / max(input.open_roles, 1), 3)
    status = "fast" if velocity >= 0.4 else "steady" if velocity >= 0.2 else "slow"
    return ComputeHiringVelocityOutput(velocity=velocity, status=status)


class EstimateOfferAcceptanceInput(BaseModel):
    role_level: str = Field(description="Role level")
    compensation_percentile: int = Field(description="Offer compensation percentile")


class EstimateOfferAcceptanceOutput(BaseModel):
    acceptance_probability: float = Field(description="Probability 0-1")
    risk_note: str = Field(description="Risk note")


ESTIMATE_OFFER_ACCEPTANCE_SPEC = ToolSpec(
    name="estimate_offer_acceptance",
    description="Estimate candidate offer acceptance probability",
    input_schema=EstimateOfferAcceptanceInput,
    output_schema=EstimateOfferAcceptanceOutput,
)


@bind_tool(ESTIMATE_OFFER_ACCEPTANCE_SPEC)
async def estimate_offer_acceptance(
    input: EstimateOfferAcceptanceInput,
) -> EstimateOfferAcceptanceOutput:
    base = 0.45 + (input.compensation_percentile / 200.0)
    if input.role_level.lower() in {"senior", "staff"}:
        base -= 0.08
    prob = max(0.05, min(0.95, round(base, 3)))
    return EstimateOfferAcceptanceOutput(
        acceptance_probability=prob,
        risk_note="Increase close plan rigor for offers below 0.65",
    )


class AssessAttritionRiskInput(BaseModel):
    avg_tenure_months: int = Field(description="Average tenure in months")
    engagement_score: int = Field(description="Engagement score 0-100")


class AssessAttritionRiskOutput(BaseModel):
    attrition_risk: str = Field(description="low, medium, or high")
    retention_action: str = Field(description="Recommended retention action")


ASSESS_ATTRITION_RISK_SPEC = ToolSpec(
    name="assess_attrition_risk",
    description="Assess attrition risk using tenure and engagement",
    input_schema=AssessAttritionRiskInput,
    output_schema=AssessAttritionRiskOutput,
)


@bind_tool(ASSESS_ATTRITION_RISK_SPEC)
async def assess_attrition_risk(input: AssessAttritionRiskInput) -> AssessAttritionRiskOutput:
    if input.engagement_score < 45 or input.avg_tenure_months < 12:
        risk = "high"
    elif input.engagement_score < 65:
        risk = "medium"
    else:
        risk = "low"
    action = "Manager 1:1 and growth plan" if risk != "low" else "Maintain recognition cadence"
    return AssessAttritionRiskOutput(attrition_risk=risk, retention_action=action)


class PlanHeadcountInput(BaseModel):
    current_team_size: int = Field(description="Current team size")
    projected_workload_growth_percent: float = Field(description="Projected workload growth percent")


class PlanHeadcountOutput(BaseModel):
    recommended_hires: int = Field(description="Recommended net-new hires")
    rationale: str = Field(description="Recommendation rationale")


PLAN_HEADCOUNT_SPEC = ToolSpec(
    name="plan_headcount",
    description="Recommend headcount change for projected workload growth",
    input_schema=PlanHeadcountInput,
    output_schema=PlanHeadcountOutput,
)


@bind_tool(PLAN_HEADCOUNT_SPEC)
async def plan_headcount(input: PlanHeadcountInput) -> PlanHeadcountOutput:
    hires = max(0, int(round((input.current_team_size * input.projected_workload_growth_percent) / 100.0)))
    return PlanHeadcountOutput(
        recommended_hires=hires,
        rationale=f"Projected growth of {input.projected_workload_growth_percent}% suggests {hires} hires",
    )


class EvaluateInterviewerLoadInput(BaseModel):
    scheduled_interviews: int = Field(description="Scheduled interviews")
    interviewer_count: int = Field(description="Interviewer count")


class EvaluateInterviewerLoadOutput(BaseModel):
    interviews_per_interviewer: float = Field(description="Average interviews per interviewer")


EVALUATE_INTERVIEWER_LOAD_SPEC = ToolSpec(
    name="evaluate_interviewer_load",
    description="Evaluate interviewer workload",
    input_schema=EvaluateInterviewerLoadInput,
    output_schema=EvaluateInterviewerLoadOutput,
)


@bind_tool(EVALUATE_INTERVIEWER_LOAD_SPEC)
async def evaluate_interviewer_load(
    input: EvaluateInterviewerLoadInput,
) -> EvaluateInterviewerLoadOutput:
    ratio = round(input.scheduled_interviews / max(input.interviewer_count, 1), 2)
    return EvaluateInterviewerLoadOutput(interviews_per_interviewer=ratio)


class ScoreRoleCompetitivenessInput(BaseModel):
    salary_percentile: int = Field(description="Salary percentile")
    remote_flexibility_score: int = Field(description="Remote flexibility score 0-100")


class ScoreRoleCompetitivenessOutput(BaseModel):
    competitiveness_score: int = Field(description="Competitiveness score 0-100")


SCORE_ROLE_COMPETITIVENESS_SPEC = ToolSpec(
    name="score_role_competitiveness",
    description="Score role competitiveness in hiring market",
    input_schema=ScoreRoleCompetitivenessInput,
    output_schema=ScoreRoleCompetitivenessOutput,
)


@bind_tool(SCORE_ROLE_COMPETITIVENESS_SPEC)
async def score_role_competitiveness(
    input: ScoreRoleCompetitivenessInput,
) -> ScoreRoleCompetitivenessOutput:
    score = max(0, min(100, int((input.salary_percentile * 0.6) + (input.remote_flexibility_score * 0.4))))
    return ScoreRoleCompetitivenessOutput(competitiveness_score=score)


class RecommendOnboardingPlanInput(BaseModel):
    role: str = Field(description="Role")


class RecommendOnboardingPlanOutput(BaseModel):
    plan: list[str] = Field(description="Onboarding plan")


RECOMMEND_ONBOARDING_PLAN_SPEC = ToolSpec(
    name="recommend_onboarding_plan",
    description="Recommend role-specific onboarding plan",
    input_schema=RecommendOnboardingPlanInput,
    output_schema=RecommendOnboardingPlanOutput,
)


@bind_tool(RECOMMEND_ONBOARDING_PLAN_SPEC)
async def recommend_onboarding_plan(
    input: RecommendOnboardingPlanInput,
) -> RecommendOnboardingPlanOutput:
    return RecommendOnboardingPlanOutput(
        plan=[
            f"Role overview for {input.role}",
            "Week-1 systems access and shadowing",
            "30-day goals and success metrics",
        ]
    )


class DetectSkillsCoverageInput(BaseModel):
    required_skill_count: int = Field(description="Required skills")
    covered_skill_count: int = Field(description="Covered skills")


class DetectSkillsCoverageOutput(BaseModel):
    coverage_percent: float = Field(description="Coverage percentage")


DETECT_SKILLS_COVERAGE_SPEC = ToolSpec(
    name="detect_skills_coverage",
    description="Compute skills coverage percentage",
    input_schema=DetectSkillsCoverageInput,
    output_schema=DetectSkillsCoverageOutput,
)


@bind_tool(DETECT_SKILLS_COVERAGE_SPEC)
async def detect_skills_coverage(input: DetectSkillsCoverageInput) -> DetectSkillsCoverageOutput:
    coverage = round((input.covered_skill_count / max(input.required_skill_count, 1)) * 100.0, 2)
    return DetectSkillsCoverageOutput(coverage_percent=coverage)


class SummarizePeopleKpisInput(BaseModel):
    hiring_velocity: float = Field(description="Hiring velocity")
    attrition_risk: str = Field(description="Attrition risk")


class SummarizePeopleKpisOutput(BaseModel):
    summary: str = Field(description="People KPI summary")


SUMMARIZE_PEOPLE_KPIS_SPEC = ToolSpec(
    name="summarize_people_kpis",
    description="Create compact people KPI summary",
    input_schema=SummarizePeopleKpisInput,
    output_schema=SummarizePeopleKpisOutput,
)


@bind_tool(SUMMARIZE_PEOPLE_KPIS_SPEC)
async def summarize_people_kpis(input: SummarizePeopleKpisInput) -> SummarizePeopleKpisOutput:
    return SummarizePeopleKpisOutput(
        summary=f"Hiring velocity={input.hiring_velocity}, attrition risk={input.attrition_risk}"
    )
