"""
Research Team — AutoGen v0.4 version (SelectorGroupChat / leader-driven).

A SelectorGroupChat where a manager LLM (`make_model_client()`) picks the next
speaker after each turn, based on the conversation. This is AutoGen's analog
of CrewAI's `Process.hierarchical` and Agno's `Team(mode=coordinate)`:
model-in-the-orchestration-loop on every framework, so the comparison is
apples-to-apples.

Termination: the chat ends when each of the four specialists has produced a
final non-tool message, OR after a generous message cap as a safety net.
"""

from __future__ import annotations

from autogen_agentchat.base import TerminationCondition, TerminatedException
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import StopMessage
from autogen_agentchat.teams import SelectorGroupChat

from agents import (
    financial_analyst,
    macro_strategist,
    technical_analyst,
    valuation_analyst,
)
from agents.settings import make_model_client


ANALYST_NAMES = (
    "MacroStrategist",
    "FinancialAnalyst",
    "ValuationAnalyst",
    "TechnicalAnalyst",
)


class AllAnalystsSpokenTermination(TerminationCondition):
    """Stop once every named analyst has emitted at least one non-tool message.

    We count a "final message" from an analyst as any message whose `source`
    matches one of the required names AND whose content is a string (i.e.
    not a tool-call or tool-result event). This avoids ending the chat
    prematurely on a tool call by the same agent.
    """

    def __init__(self, required: tuple[str, ...]):
        self._required = set(required)
        self._spoken: set[str] = set()
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages):  # autogen passes ChatMessage sequence
        if self._terminated:
            raise TerminatedException("Already terminated.")
        for m in messages:
            src = getattr(m, "source", None)
            if src in self._required:
                # We only count final (text) messages — tool events are ToolCall/ToolResult types
                # with different .source semantics. Plain TextMessage is what we want.
                content = getattr(m, "content", None)
                if isinstance(content, str) and content.strip():
                    self._spoken.add(src)
        if self._required <= self._spoken:
            self._terminated = True
            return StopMessage(
                content=f"All required analysts spoke: {sorted(self._spoken)}",
                source="AllAnalystsSpokenTermination",
            )
        return None

    async def reset(self) -> None:
        self._spoken = set()
        self._terminated = False


SELECTOR_PROMPT = """You are coordinating a research team of four specialists:

- MacroStrategist: macro regime, rates, inflation, growth, liquidity, yield curve.
- FinancialAnalyst: company fundamentals — revenue, margins, cash flow, balance sheet.
- ValuationAnalyst: intrinsic value via DCF and comparables; margin of safety.
- TechnicalAnalyst: price action, momentum (RSI, MACD), support/resistance, trend.

You read the conversation so far and decide who should speak next.

Rules:
1. Each specialist must speak at least once before the discussion ends.
2. Pick the specialist whose expertise is most needed by the current state of the conversation.
3. Do NOT pick the same specialist twice in a row.
4. Do NOT pick yourself.

Conversation so far:
{history}

Available speakers (you must pick exactly one): {participants}

Reply with ONLY the chosen speaker's name and nothing else.
"""


research_team = SelectorGroupChat(
    participants=[
        macro_strategist,
        financial_analyst,
        valuation_analyst,
        technical_analyst,
    ],
    model_client=make_model_client(),
    selector_prompt=SELECTOR_PROMPT,
    allow_repeated_speaker=False,
    termination_condition=(AllAnalystsSpokenTermination(ANALYST_NAMES) | MaxMessageTermination(40)),
)
