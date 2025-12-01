"""
Astra Framework - Main entry point.

Provides Agent and Astra classes for building AI agents.
"""

from framework.agents import Agent, Tool, tool
from framework.astra import Astra, AstraContext, FrameworkSettings


__all__ = [
    "Agent",
    "Astra",
    "AstraContext",
    "FrameworkSettings",
    "Tool",
    "tool",
]
