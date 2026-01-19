"""
Research Tools for Finance Team.

Tools for retrieving earnings data, SEC filings, and competitor analysis.
"""

import random

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


# GET EARNINGS REPORT TOOL
class GetEarningsReportInput(BaseModel):
    """Input for earnings report retrieval."""

    symbol: str = Field(description="Stock ticker symbol (e.g., AAPL, GOOGL)")
    quarter: str = Field(default="Q4", description="Financial quarter (Q1, Q2, Q3, Q4)")


class GetEarningsReportOutput(BaseModel):
    """Output from earnings report retrieval."""

    symbol: str = Field(description="Stock ticker symbol")
    quarter: str = Field(description="Financial quarter")
    revenue_bn: float = Field(description="Revenue in billions")
    eps: float = Field(description="Earnings per share")
    guidance: str = Field(description="Guidance update (Raised, Lowered, Maintained)")
    highlights: str = Field(description="Key highlights from the report")


GET_EARNINGS_REPORT_SPEC = ToolSpec(
    name="get_earnings_report",
    description="Retrieve the latest earnings report summary for a company",
    input_model=GetEarningsReportInput,
    output_model=GetEarningsReportOutput,
    examples=[
        {
            "input": {"symbol": "AAPL", "quarter": "Q4"},
            "output": {
                "symbol": "AAPL",
                "quarter": "Q4",
                "revenue_bn": 89.5,
                "eps": 12.34,
                "guidance": "Raised",
                "highlights": "Strong performance in cloud segment for AAPL",
            },
        }
    ],
)


@bind_tool(GET_EARNINGS_REPORT_SPEC)
async def get_earnings_report(input: GetEarningsReportInput) -> GetEarningsReportOutput:
    """
    Retrieve earnings report summary.

    Constraints:
    - Returns simulated data for demo purposes
    - Real-time integration in production

    Notes:
    - Use for fundamental analysis
    - Includes revenue, EPS, and guidance updates

    Tags: earnings, financial-data, research
    """
    revenue = round(random.uniform(10, 100), 2)
    eps = round(random.uniform(1, 15), 2)
    guidance = random.choice(["Raised", "Lowered", "Maintained"])

    return GetEarningsReportOutput(
        symbol=input.symbol,
        quarter=input.quarter,
        revenue_bn=revenue,
        eps=eps,
        guidance=guidance,
        highlights=f"Strong performance in cloud segment for {input.symbol}",
    )


# SEARCH SEC FILINGS TOOL
class SearchSecFilingsInput(BaseModel):
    """Input for SEC filings search."""

    symbol: str = Field(description="Stock ticker symbol")
    doc_type: str = Field(default="10-K", description="Document type (10-K, 10-Q, 8-K)")


class SearchSecFilingsOutput(BaseModel):
    """Output from SEC filings search."""

    filings: str = Field(description="Summary of recent SEC filings")


SEARCH_SEC_FILINGS_SPEC = ToolSpec(
    name="search_sec_filings",
    description="Search for SEC filings for a specific company",
    input_model=SearchSecFilingsInput,
    output_model=SearchSecFilingsOutput,
    examples=[
        {
            "input": {"symbol": "AAPL", "doc_type": "10-K"},
            "output": {
                "filings": "Found 3 recent 10-K filings for AAPL: 1. 10-K (2024-02-15) - Annual Report, 2. 10-K (2023-02-10) - Annual Report"
            },
        }
    ],
)


@bind_tool(SEARCH_SEC_FILINGS_SPEC)
async def search_sec_filings(input: SearchSecFilingsInput) -> SearchSecFilingsOutput:
    """
    Search SEC EDGAR database for company filings.

    Constraints:
    - Limited to public companies
    - Returns most recent 3 filings

    Notes:
    - Use for regulatory compliance research
    - Real SEC EDGAR integration in production

    Tags: sec, regulatory, research
    """
    result = f"Found 3 recent {input.doc_type} filings for {input.symbol}: 1. {input.doc_type} (2024-02-15) - Annual Report, 2. {input.doc_type} (2023-02-10) - Annual Report"

    return SearchSecFilingsOutput(filings=result)


# GET COMPETITOR ANALYSIS TOOL
class GetCompetitorAnalysisInput(BaseModel):
    """Input for competitor analysis."""

    symbol: str = Field(description="Stock ticker symbol to analyze")


class GetCompetitorAnalysisOutput(BaseModel):
    """Output from competitor analysis."""

    analysis: str = Field(description="Competitor comparison summary")


GET_COMPETITOR_ANALYSIS_SPEC = ToolSpec(
    name="get_competitor_analysis",
    description="Identify key competitors and compare basic metrics",
    input_model=GetCompetitorAnalysisInput,
    output_model=GetCompetitorAnalysisOutput,
    examples=[
        {
            "input": {"symbol": "AAPL"},
            "output": {
                "analysis": "Competitor Analysis for AAPL:\\n1. Competitor A: Market Cap $200B, P/E 25\\n2. Competitor B: Market Cap $150B, P/E 18"
            },
        }
    ],
)


@bind_tool(GET_COMPETITOR_ANALYSIS_SPEC)
async def get_competitor_analysis(input: GetCompetitorAnalysisInput) -> GetCompetitorAnalysisOutput:
    """
    Analyze competitors and compare key valuation metrics.

    Constraints:
    - Limited to top 3 competitors
    - Metrics include Market Cap and P/E ratio

    Notes:
    - Use for relative valuation analysis
    - Real-time comparison in production

    Tags: competitive-analysis, valuation, research
    """
    result = f"Competitor Analysis for {input.symbol}:\\n1. Competitor A: Market Cap $200B, P/E 25\\n2. Competitor B: Market Cap $150B, P/E 18\\n3. Competitor C: Market Cap $90B, P/E 30"

    return GetCompetitorAnalysisOutput(analysis=result)
