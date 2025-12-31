"""Agent wrapper for Astra SDK.

This is a thin wrapper that re-exports the framework Agent class
for clean imports: from astra.sdk import Agent
"""

from framework.agents.agent import Agent as FrameworkAgent


# Re-export as Agent for SDK usage
Agent = FrameworkAgent

__all__ = ["Agent"]
