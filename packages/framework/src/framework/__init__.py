"""
Astra Framework - Main entry point.

Provides Agent and Astra classes for building AI agents.
"""
from .agents import Agent, AgentConfig, ModelConfig, tool, Tool
from .astra import Astra, FrameworkSettings, DependencyContainer

__all__ = [
    "Agent",
    "AgentConfig",
    "ModelConfig",
    "Astra",
    "FrameworkSettings",
    "DependencyContainer",
    "tool",
    "Tool",
]

