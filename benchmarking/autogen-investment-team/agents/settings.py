"""
Shared agent settings for the AutoGen side.

Single load-bearing helper: `make_model_client()` returns our custom
`GeminiChatCompletionClient` (see gemini_client.py). It routes every LLM
call through `google.genai`'s Async API, which is the exact SDK boundary
the benchmark's `DebugCounter` patches — so AutoGen's calls are counted
the same way Agno, CrewAI, and Astra are.

Thinking tokens are explicitly disabled (matching the rest of the
benchmark) via Gemini's ThinkingConfig.
"""

from datetime import datetime

from google.genai.types import ThinkingConfig

from .gemini_client import GeminiChatCompletionClient


THINKING_OFF = ThinkingConfig(thinking_budget=0, include_thoughts=False)


def make_model_client() -> GeminiChatCompletionClient:
    """One client per agent (the manager_llm gets its own too).

    Kept deterministic: temperature=0.0, thinking disabled. Stream off so the
    benchmark measures the same code path on every framework.
    """
    return GeminiChatCompletionClient(
        model="gemini-2.5-flash",
        temperature=0.0,
        thinking_config=THINKING_OFF,
    )


def datetime_context() -> str:
    """Matches Agno's `add_datetime_to_context=True` — a dated header so agents
    know what 'today' means. Identical format to the Astra/Agno/CrewAI helpers."""
    return f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y %H:%M %Z')}\n\n"


TEAM_CONTEXT = """
TEAM CONTEXT
------------
You are one of four specialists in a research team coordinated by a manager LLM.
The other specialists handle whichever domains you do not. When the user query
spans multiple domains (e.g., "compare AAPL and MSFT" or "rank these three
stocks"), produce your domain-specific section anyway --- the other analysts
will handle the rest. Do NOT refuse the task because it mentions concerns
outside your role. Always produce your assigned section using the OUTPUT FORMAT
below, scoped to whichever symbol(s) the query names.

"""
