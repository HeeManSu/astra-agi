"""
Shared agent settings for the CrewAI side.

The single most important thing here is the `make_llm()` helper — it creates
a `crewai.LLM` with Gemini thinking explicitly OFF (via google-genai's
ThinkingConfig), matching the `thinking_budget=0, include_thoughts=False`
posture used on the Astra and Agno sides. CrewAI's Gemini provider auto-
enables `ThinkingConfig(include_thoughts=True)` for gemini-2.5+ unless a
thinking_config is explicitly provided, so this is load-bearing for fairness.
"""

from datetime import datetime

from crewai import LLM
from google.genai.types import ThinkingConfig


THINKING_OFF = ThinkingConfig(thinking_budget=0, include_thoughts=False)


def make_llm() -> LLM:
    """One LLM per agent (CrewAI tracks per-agent state on the instance).

    Kept deterministic: temperature=0.0, thinking disabled. Stream off so the
    benchmark measures the same code path every time.
    """
    return LLM(
        model="gemini/gemini-2.5-flash",
        temperature=0.0,
        thinking_config=THINKING_OFF,
        stream=False,
    )


def datetime_context() -> str:
    """Matches Agno's add_datetime_to_context=True — a dated header so agents
    know what 'today' means. Identical format to the Astra/Agno helpers."""
    return f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y %H:%M %Z')}\n\n"
