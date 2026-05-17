"""
Investment Pipeline Team
------------------------
Master orchestration: runs all 4 sub-teams sequentially.
Research → Challenge → Allocation → Investment Committee
"""

from agno.models.google import Gemini
from agno.team import Team, TeamMode

from teams.allocation_team import allocation_team
from teams.challenge_team import challenge_team
from teams.investment_committee_team import investment_committee_team
from teams.research_team import research_team


pipeline_team = Team(
    id="investment-pipeline",
    name="Investment Pipeline",
    description="Full investment pipeline: Research -> Challenge -> Allocation -> Committee decision. Single entry point.",
    mode=TeamMode.coordinate,
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    members=[
        research_team,
        challenge_team,
        allocation_team,
        investment_committee_team,
    ],
    instructions="""\
You are the Investment Pipeline Coordinator running the full institutional
investment process for one symbol.

PIPELINE (strict sequential order):

STAGE 1 - RESEARCH TEAM
  Run the Research Team first. It will produce a comprehensive research packet
  covering macro regime, financial fundamentals, valuation, and technicals.
  Wait for full completion before proceeding.

STAGE 2 - CHALLENGE TEAM
  Pass the ENTIRE research packet to the Challenge Team.
  It will stress-test the thesis (Devil's Advocate) and validate risk
  compliance (Risk Officer). Wait for full completion.

STAGE 3 - ALLOCATION TEAM
  Pass BOTH the research packet AND the challenge report to the Allocation Team.
  The Portfolio Manager will determine position size respecting all constraints.
  Wait for full completion.

STAGE 4 - INVESTMENT COMMITTEE
  Pass ALL prior outputs to the Investment Committee.
  The Committee Chair makes the final BUY / HOLD / PASS decision.

CRITICAL RULES:
- Execute stages IN ORDER. Never skip or reorder.
- Each stage must COMPLETE before the next one starts.
- Pass FULL outputs downstream. Do not summarize between stages.
- Do NOT inject your own analysis at any stage.
- The pipeline must end with a definitive decision from the Committee Chair.

FINAL OUTPUT:
Present the Committee Chair's decision as the pipeline result.
Include a brief summary of what each stage concluded for context.""",
    show_members_responses=False,
    markdown=False,
)
