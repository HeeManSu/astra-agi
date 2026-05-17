"""
Macro Strategist node — LangGraph version.

Analyzes macroeconomic regime and market-wide risk conditions.
System-message instruction text is byte-identical to the Agno/CrewAI sides.
"""

from context import load_context
from tools.macro_tools import MACRO_ALL_TOOLS

from ._tool_loop import run_analyst
from .settings import datetime_context, make_llm


MACRO_CONTEXT = load_context(["mandate.md", "risk_policy.md"])


# Byte-identical to agno-investment-team/agents/macro_strategist.py `instructions`.
INSTRUCTIONS = (
    datetime_context()
    + MACRO_CONTEXT
    + """
You are the Macro Strategist for a $10M US equity fund.

Your role is to assess the current macro regime and define the overall equity risk environment.

You:
- Analyze macroeconomic conditions only
- Do NOT analyze individual stocks
- Do NOT make allocation decisions

Use the provided macro data tools to determine:

- Monetary policy stance
- Inflation direction
- Growth momentum
- Liquidity conditions
- Yield curve signal

--------------------------------------------------

OUTPUT FORMAT

1. Macro Summary
2. Monetary Policy Assessment
3. Inflation & Growth Assessment
4. Liquidity & Credit Conditions
5. Yield Curve Interpretation
6. Equity Risk Regime (Risk-On / Neutral / Risk-Off)
7. Confidence Score (1-10)

Be structured.
Be concise.
Use numbers when relevant.
No company-specific commentary.
"""
)


def macro_node(state: dict) -> dict:
    """Run the macro analyst on state['query'] and return {'macro_output': str}."""
    # Keep the prompt focused on the macro scope — downstream analysts use the
    # ticker. Mentioning the ticker here makes the macro analyst refuse
    # (over-literal about 'no company-specific commentary'). Instead we tell
    # it explicitly this is the upstream step for a research report.
    user_prompt = (
        "Produce the macro-regime and equity-risk-environment assessment. "
        "This is the upstream step of a multi-analyst research report. "
        "Downstream analysts will handle the specific ticker; you should "
        "focus strictly on current macroeconomic conditions per your output "
        f"format. (For downstream reference only, the target is: {state['query']})"
    )
    output = run_analyst(
        llm=make_llm(),
        system_prompt=INSTRUCTIONS,
        user_prompt=user_prompt,
        tools=MACRO_ALL_TOOLS,
    )
    return {"macro_output": output}
