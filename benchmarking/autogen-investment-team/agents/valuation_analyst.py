"""
Valuation Analyst — AutoGen version.

Core backstory text is identical to the Astra/Agno/CrewAI sides. AutoGen
adds a small TEAM_CONTEXT footer (see settings.py) to restore parity with
the other frameworks' manager-driven query-reframing behavior, which
AutoGen's `SelectorGroupChat` does not provide.
"""

from autogen_agentchat.agents import AssistantAgent

from context import load_context
from tools.valuation_tools import VALUATION_ALL_TOOLS

from .settings import TEAM_CONTEXT, datetime_context, make_model_client


VALUATION_CONTEXT = load_context(["mandate.md", "process.md"])


SYSTEM_MESSAGE = (
    datetime_context()
    + VALUATION_CONTEXT
    + TEAM_CONTEXT
    + """
You are the Valuation Analyst for a $10M US equity fund.

You determine intrinsic value and margin of safety.

Do NOT:
- Analyze macro
- Analyze technicals
- Make portfolio decisions

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. DCF Valuation
2. Comparable Multiples
3. Fair Value (Bear / Base / Bull)
4. Margin of Safety
5. Valuation Risks
6. Final Valuation Verdict

--------------------------------------------------

Be structured.
Be concise.
Be numerical where possible.
"""
)


valuation_analyst = AssistantAgent(
    name="ValuationAnalyst",
    model_client=make_model_client(),
    tools=VALUATION_ALL_TOOLS,
    system_message=SYSTEM_MESSAGE,
    description="Determines intrinsic value and margin of safety via DCF and comparable multiples.",
    reflect_on_tool_use=True,
    max_tool_iterations=15,
)
