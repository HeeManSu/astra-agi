"""Hand-authored research graph — LangGraph's StateGraph API.

This is the developer-cost we're measuring: a human sits down and draws
the graph. Nodes, edges, and the final synthesis step are all explicit.

Compare to Astra's side, where the LLM generates this exact shape of
graph from the user's natural-language query automatically.

Sequential: macro -> financial -> valuation -> technical -> synthesize.
Each analyst node passes its output downstream via ResearchState.
The synthesize node has no LLM call — it concatenates the 4 analyst
outputs into a single formatted report (matching the shape returned by
Astra/Agno/CrewAI for apples-to-apples quality comparison).
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from nodes import (
    financial_node,
    macro_node,
    technical_node,
    valuation_node,
)


class ResearchState(TypedDict, total=False):
    query: str
    macro_output: str
    financial_output: str
    valuation_output: str
    technical_output: str
    final_report: str


def synthesize_node(state: ResearchState) -> dict:
    """No-LLM final step: stitch all 4 analyst outputs into the packet."""
    parts = [
        "## 1. MACRO ANALYSIS\n\n" + (state.get("macro_output") or "").strip(),
        "## 2. FINANCIAL ANALYSIS\n\n" + (state.get("financial_output") or "").strip(),
        "## 3. VALUATION ANALYSIS\n\n" + (state.get("valuation_output") or "").strip(),
        "## 4. TECHNICAL ANALYSIS\n\n" + (state.get("technical_output") or "").strip(),
    ]
    return {"final_report": "\n\n---\n\n".join(parts)}


def _build_graph():
    g = StateGraph(ResearchState)
    g.add_node("macro", macro_node)
    g.add_node("financial", financial_node)
    g.add_node("valuation", valuation_node)
    g.add_node("technical", technical_node)
    g.add_node("synthesize", synthesize_node)

    g.set_entry_point("macro")
    g.add_edge("macro", "financial")
    g.add_edge("financial", "valuation")
    g.add_edge("valuation", "technical")
    g.add_edge("technical", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


research_graph = _build_graph()
