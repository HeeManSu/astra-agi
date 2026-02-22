"""Marketing domain tools for enterprise teams."""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


class ProfileAudienceSegmentInput(BaseModel):
    product: str = Field(description="Product or solution name")
    region: str = Field(description="Target region")


class ProfileAudienceSegmentOutput(BaseModel):
    segment_name: str = Field(description="Suggested segment label")
    primary_channel: str = Field(description="Best-performing channel")
    conversion_assumption: float = Field(description="Expected conversion percentage")


PROFILE_AUDIENCE_SEGMENT_SPEC = ToolSpec(
    name="profile_audience_segment",
    description="Recommend a target audience segment and primary acquisition channel",
    input_schema=ProfileAudienceSegmentInput,
    output_schema=ProfileAudienceSegmentOutput,
)


@bind_tool(PROFILE_AUDIENCE_SEGMENT_SPEC)
async def profile_audience_segment(
    input: ProfileAudienceSegmentInput,
) -> ProfileAudienceSegmentOutput:
    segment = f"{input.region.title()} SMB Decision Makers"
    channel = "LinkedIn" if input.region.lower() in {"us", "north america", "global"} else "Search"
    conversion = 4.2 if channel == "LinkedIn" else 3.4

    return ProfileAudienceSegmentOutput(
        segment_name=segment,
        primary_channel=channel,
        conversion_assumption=conversion,
    )


class BuildCampaignBriefInput(BaseModel):
    objective: str = Field(description="Campaign objective")
    target_segment: str = Field(description="Audience segment")
    budget: float = Field(description="Budget in USD")


class BuildCampaignBriefOutput(BaseModel):
    headline: str = Field(description="Campaign headline")
    key_message: str = Field(description="Primary message")
    cta: str = Field(description="Call to action")


BUILD_CAMPAIGN_BRIEF_SPEC = ToolSpec(
    name="build_campaign_brief",
    description="Create a concise campaign brief with headline, message, and CTA",
    input_schema=BuildCampaignBriefInput,
    output_schema=BuildCampaignBriefOutput,
)


@bind_tool(BUILD_CAMPAIGN_BRIEF_SPEC)
async def build_campaign_brief(input: BuildCampaignBriefInput) -> BuildCampaignBriefOutput:
    headline = f"{input.objective.title()} for {input.target_segment}"
    key_message = (
        f"Deliver clear value for {input.target_segment} while staying within "
        f"${input.budget:,.0f} budget."
    )
    cta = "Book a demo"

    return BuildCampaignBriefOutput(
        headline=headline,
        key_message=key_message,
        cta=cta,
    )


class EstimateCampaignROIInput(BaseModel):
    spend: float = Field(description="Campaign spend in USD")
    expected_leads: int = Field(description="Expected leads")
    close_rate_percent: float = Field(description="Expected close rate in percent")
    avg_deal_size: float = Field(description="Average deal size in USD")


class EstimateCampaignROIOutput(BaseModel):
    expected_revenue: float = Field(description="Projected revenue in USD")
    roi_percent: float = Field(description="Projected ROI percentage")
    confidence: str = Field(description="low, medium, or high confidence")


ESTIMATE_CAMPAIGN_ROI_SPEC = ToolSpec(
    name="estimate_campaign_roi",
    description="Estimate expected campaign ROI from simple funnel assumptions",
    input_schema=EstimateCampaignROIInput,
    output_schema=EstimateCampaignROIOutput,
)


@bind_tool(ESTIMATE_CAMPAIGN_ROI_SPEC)
async def estimate_campaign_roi(input: EstimateCampaignROIInput) -> EstimateCampaignROIOutput:
    won_deals = input.expected_leads * (input.close_rate_percent / 100.0)
    revenue = round(won_deals * input.avg_deal_size, 2)
    roi = round(((revenue - input.spend) / max(input.spend, 1.0)) * 100.0, 2)

    if input.expected_leads >= 500:
        confidence = "high"
    elif input.expected_leads >= 200:
        confidence = "medium"
    else:
        confidence = "low"

    return EstimateCampaignROIOutput(
        expected_revenue=revenue,
        roi_percent=roi,
        confidence=confidence,
    )


class GenerateContentCalendarInput(BaseModel):
    campaign_name: str = Field(description="Campaign name")
    weeks: int = Field(default=4, description="Number of weeks")


class GenerateContentCalendarOutput(BaseModel):
    calendar: list[str] = Field(description="Planned weekly content slots")


GENERATE_CONTENT_CALENDAR_SPEC = ToolSpec(
    name="generate_content_calendar",
    description="Generate a simple weekly content calendar",
    input_schema=GenerateContentCalendarInput,
    output_schema=GenerateContentCalendarOutput,
)


@bind_tool(GENERATE_CONTENT_CALENDAR_SPEC)
async def generate_content_calendar(
    input: GenerateContentCalendarInput,
) -> GenerateContentCalendarOutput:
    items = [f"Week {i + 1}: {input.campaign_name} primary content" for i in range(max(1, input.weeks))]
    return GenerateContentCalendarOutput(calendar=items)


class ScoreChannelMixInput(BaseModel):
    paid_percent: float = Field(description="Paid channel budget percent")
    organic_percent: float = Field(description="Organic channel budget percent")


class ScoreChannelMixOutput(BaseModel):
    mix_score: int = Field(description="Score 0-100")
    recommendation: str = Field(description="Channel-mix recommendation")


SCORE_CHANNEL_MIX_SPEC = ToolSpec(
    name="score_channel_mix",
    description="Score paid/organic channel mix balance",
    input_schema=ScoreChannelMixInput,
    output_schema=ScoreChannelMixOutput,
)


@bind_tool(SCORE_CHANNEL_MIX_SPEC)
async def score_channel_mix(input: ScoreChannelMixInput) -> ScoreChannelMixOutput:
    gap = abs(input.paid_percent - input.organic_percent)
    score = max(0, 100 - int(gap))
    rec = "Balanced mix" if gap <= 20 else "Rebalance toward weaker channel"
    return ScoreChannelMixOutput(mix_score=score, recommendation=rec)


class EstimateCACInput(BaseModel):
    marketing_spend: float = Field(description="Marketing spend")
    acquired_customers: int = Field(description="Acquired customers")


class EstimateCACOutput(BaseModel):
    cac: float = Field(description="Customer acquisition cost")
    efficiency_band: str = Field(description="efficient, acceptable, or high")


ESTIMATE_CAC_SPEC = ToolSpec(
    name="estimate_cac",
    description="Estimate customer acquisition cost and efficiency band",
    input_schema=EstimateCACInput,
    output_schema=EstimateCACOutput,
)


@bind_tool(ESTIMATE_CAC_SPEC)
async def estimate_cac(input: EstimateCACInput) -> EstimateCACOutput:
    cac = round(input.marketing_spend / max(input.acquired_customers, 1), 2)
    band = "efficient" if cac < 200 else "acceptable" if cac < 600 else "high"
    return EstimateCACOutput(cac=cac, efficiency_band=band)


class EvaluateBrandSentimentInput(BaseModel):
    positive_mentions: int = Field(description="Positive mentions")
    neutral_mentions: int = Field(description="Neutral mentions")
    negative_mentions: int = Field(description="Negative mentions")


class EvaluateBrandSentimentOutput(BaseModel):
    sentiment_index: float = Field(description="Sentiment index -1 to 1")
    trend: str = Field(description="positive, neutral, or negative")


EVALUATE_BRAND_SENTIMENT_SPEC = ToolSpec(
    name="evaluate_brand_sentiment",
    description="Compute a simple brand sentiment index",
    input_schema=EvaluateBrandSentimentInput,
    output_schema=EvaluateBrandSentimentOutput,
)


@bind_tool(EVALUATE_BRAND_SENTIMENT_SPEC)
async def evaluate_brand_sentiment(
    input: EvaluateBrandSentimentInput,
) -> EvaluateBrandSentimentOutput:
    total = max(input.positive_mentions + input.neutral_mentions + input.negative_mentions, 1)
    index = round((input.positive_mentions - input.negative_mentions) / total, 3)
    trend = "positive" if index > 0.2 else "negative" if index < -0.2 else "neutral"
    return EvaluateBrandSentimentOutput(sentiment_index=index, trend=trend)


class ForecastPipelineFromMqlInput(BaseModel):
    mql_count: int = Field(description="MQL count")
    mql_to_sql_percent: float = Field(description="MQL to SQL conversion percent")
    sql_to_win_percent: float = Field(description="SQL to win conversion percent")


class ForecastPipelineFromMqlOutput(BaseModel):
    expected_wins: float = Field(description="Expected won deals")


FORECAST_PIPELINE_FROM_MQL_SPEC = ToolSpec(
    name="forecast_pipeline_from_mql",
    description="Forecast won deals from MQL funnel",
    input_schema=ForecastPipelineFromMqlInput,
    output_schema=ForecastPipelineFromMqlOutput,
)


@bind_tool(FORECAST_PIPELINE_FROM_MQL_SPEC)
async def forecast_pipeline_from_mql(
    input: ForecastPipelineFromMqlInput,
) -> ForecastPipelineFromMqlOutput:
    wins = input.mql_count * (input.mql_to_sql_percent / 100.0) * (input.sql_to_win_percent / 100.0)
    return ForecastPipelineFromMqlOutput(expected_wins=round(wins, 2))


class RecommendCreativeVariantInput(BaseModel):
    audience: str = Field(description="Audience segment")
    objective: str = Field(description="Campaign objective")


class RecommendCreativeVariantOutput(BaseModel):
    variant: str = Field(description="Recommended creative variant")


RECOMMEND_CREATIVE_VARIANT_SPEC = ToolSpec(
    name="recommend_creative_variant",
    description="Recommend creative variant by objective and audience",
    input_schema=RecommendCreativeVariantInput,
    output_schema=RecommendCreativeVariantOutput,
)


@bind_tool(RECOMMEND_CREATIVE_VARIANT_SPEC)
async def recommend_creative_variant(
    input: RecommendCreativeVariantInput,
) -> RecommendCreativeVariantOutput:
    variant = f"{input.objective.title()} / {input.audience} proof-point creative"
    return RecommendCreativeVariantOutput(variant=variant)


class AssessLandingPageQualityInput(BaseModel):
    load_time_seconds: float = Field(description="Page load time")
    cta_clarity_score: int = Field(description="CTA clarity score 0-100")


class AssessLandingPageQualityOutput(BaseModel):
    quality_score: int = Field(description="Quality score 0-100")


ASSESS_LANDING_PAGE_QUALITY_SPEC = ToolSpec(
    name="assess_landing_page_quality",
    description="Score landing page quality from speed and CTA clarity",
    input_schema=AssessLandingPageQualityInput,
    output_schema=AssessLandingPageQualityOutput,
)


@bind_tool(ASSESS_LANDING_PAGE_QUALITY_SPEC)
async def assess_landing_page_quality(
    input: AssessLandingPageQualityInput,
) -> AssessLandingPageQualityOutput:
    speed_penalty = int(max(0.0, (input.load_time_seconds - 2.0) * 10))
    score = max(0, min(100, input.cta_clarity_score - speed_penalty))
    return AssessLandingPageQualityOutput(quality_score=score)


class AllocateChannelBudgetInput(BaseModel):
    total_budget: float = Field(description="Total budget")
    channels: list[str] = Field(description="Channel list")


class AllocateChannelBudgetOutput(BaseModel):
    per_channel_budget: float = Field(description="Equal channel allocation")


ALLOCATE_CHANNEL_BUDGET_SPEC = ToolSpec(
    name="allocate_channel_budget",
    description="Allocate campaign budget evenly across channels",
    input_schema=AllocateChannelBudgetInput,
    output_schema=AllocateChannelBudgetOutput,
)


@bind_tool(ALLOCATE_CHANNEL_BUDGET_SPEC)
async def allocate_channel_budget(input: AllocateChannelBudgetInput) -> AllocateChannelBudgetOutput:
    per = round(input.total_budget / max(len(input.channels), 1), 2)
    return AllocateChannelBudgetOutput(per_channel_budget=per)


class SummarizeCampaignKpisInput(BaseModel):
    roi_percent: float = Field(description="ROI percent")
    cac: float = Field(description="CAC")


class SummarizeCampaignKpisOutput(BaseModel):
    summary: str = Field(description="Campaign KPI summary")


SUMMARIZE_CAMPAIGN_KPIS_SPEC = ToolSpec(
    name="summarize_campaign_kpis",
    description="Create compact campaign KPI summary",
    input_schema=SummarizeCampaignKpisInput,
    output_schema=SummarizeCampaignKpisOutput,
)


@bind_tool(SUMMARIZE_CAMPAIGN_KPIS_SPEC)
async def summarize_campaign_kpis(input: SummarizeCampaignKpisInput) -> SummarizeCampaignKpisOutput:
    return SummarizeCampaignKpisOutput(summary=f"ROI={input.roi_percent}%, CAC=${input.cac}")
