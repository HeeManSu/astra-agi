"""Shared tool-calling loop for each analyst node.

LangGraph nodes are plain functions. Each analyst node needs to call its
tools, observe results, and synthesize a final text output. We run this
loop inside the node — the LLM decides which tools to call, we execute
them, feed results back, and stop when the LLM emits a final message
with no `tool_calls`.

This is LangGraph's standard "node with tool loop" pattern. It keeps the
tool-calling cost scoped to the node (each analyst's 2-3 LLM calls),
unlike a single-agent ReAct loop where every step pays for the full
accumulated context.
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI


MAX_ITERATIONS = 15  # mirror Agno/CrewAI's max_iter to bound worst case


def run_analyst(
    llm: ChatGoogleGenerativeAI,
    system_prompt: str,
    user_prompt: str,
    tools: list[Any],
) -> str:
    """Run an analyst's tool-calling loop and return the final text.

    Args:
        llm: the analyst's LLM (already has thinking off, temp=0).
        system_prompt: byte-identical instruction text from the Agno side.
        user_prompt: the query + context from upstream nodes.
        tools: the analyst's tool list (langchain @tool decorated functions).

    Returns:
        Final text response from the analyst (no tool_calls attached).
    """
    # bind_tools returns a new runnable that knows the tool schemas.
    llm_with_tools = llm.bind_tools(tools)

    # tool name -> callable lookup for result execution
    tool_map: dict[str, Callable] = {t.name: t for t in tools}

    messages: list[Any] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    for _ in range(MAX_ITERATIONS):
        response: AIMessage = llm_with_tools.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            # No tools requested → final synthesis text. Return it.
            return response.content or ""

        # Execute each requested tool and append ToolMessage results.
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args") or {}
            if tool_name not in tool_map:
                result = f"Error: tool '{tool_name}' not found"
            else:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                except Exception as e:
                    result = f"Error: {type(e).__name__}: {e}"
            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tc.get("id", ""),
                    name=tool_name,
                )
            )

    # Exhausted iterations — return whatever the last AIMessage said.
    last = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage) and (m.content or "")),
        None,
    )
    if last is None:
        return "(exceeded max iterations with no text output)"
    return last.content or "(exceeded max iterations)"
