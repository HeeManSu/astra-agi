"""Shared LLM factory for the LangGraph side.

`make_llm()` returns a deterministic `ChatGoogleGenerativeAI` with Gemini
thinking explicitly OFF. Same posture as Astra / Agno / CrewAI:

    temperature=0.0
    thinking_budget=0
    include_thoughts=False

The thinking kwargs are load-bearing — `ChatGoogleGenerativeAI` defaults to
thinking ON on gemini-2.5+ (verified during Phase 0 probe: baseline returned
`reasoning=25/26` output tokens). Without these, the benchmark would unfairly
advantage LangGraph's call count with hidden thinking tokens.
"""

from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI


def make_llm() -> ChatGoogleGenerativeAI:
    """One LLM per node (LangGraph doesn't track per-agent state, but we
    match the per-agent-LLM pattern for symmetry with the other sides)."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        thinking_budget=0,
        include_thoughts=False,
    )


def datetime_context() -> str:
    """Matches Agno's add_datetime_to_context=True — a dated header so agents
    know what 'today' means. Identical format to the Astra/Agno/CrewAI helpers."""
    return f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y %H:%M %Z')}\n\n"
