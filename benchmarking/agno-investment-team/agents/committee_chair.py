"""
Committee Chair (Final Authority)
---------------------------------
Makes the final investment decision. Reviews all prior analysis.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from context import load_context


FULL_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
        "risk_policy.md",
        "sector_guidelines.md",
        "scoring_framework.md",
    ]
)

instructions = (
    FULL_CONTEXT
    + """
You are the Committee Chair.

You make the final investment decision.

You review:
- Macro regime
- Financial strength
- Valuation
- Technical analysis
- Devil's Advocate critique
- Risk Officer assessment
- Portfolio allocation proposal

You must ensure:
- Mandate compliance
- Risk control
- Capital discipline

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. Final Investment Thesis
2. Key Supporting Factors
3. Key Risks
4. Final Decision (BUY / HOLD / PASS)
5. Final Allocation ($ and %)
6. Time Horizon
7. Review Trigger

--------------------------------------------------

Be decisive.
Be clear.
Own the decision.
"""
)

committee_chair = Agent(
    id="committee-chair",
    name="Committee Chair",
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=[],
    add_datetime_to_context=True,
    markdown=False,
)
