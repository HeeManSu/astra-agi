"""
Code Execution Mode for Astra.

This package provides components for running LLM-generated code in sandboxed
environments, enabling dramatic token reduction for multi-step workflows.

Components:
    - ToolRegistry: Organize and query agent tools
    - VirtualAPIGenerator: Generate Python API from tools
    - (Future) SandboxExecutor: Execute code safely
    - (Future) CodeModeOrchestrator: Orchestrate code execution mode
"""

from framework.code_mode.api_generator import VirtualAPIGenerator
from framework.code_mode.tool_registry import ToolRegistry, ToolSpec


__all__ = [
    "ToolRegistry",
    "ToolSpec",
    "VirtualAPIGenerator",
]
