"""
Code Execution Mode for Astra.

This package provides components for running LLM-generated code in sandboxed
environments, enabling dramatic token reduction for multi-step workflows.

Components:
    - ToolRegistry: Organize and query agent tools
    - SandboxExecutor: Execute code safely in isolated subprocess
    - SandboxResult: Execution result container
    - synthesize_response: Synthesize execution results into meaningful responses
    - (Future) VirtualAPIGenerator: Generate Python API from tools
    - (Future) CodeModeOrchestrator: Orchestrate code execution mode
"""

from framework.code_mode.sandbox import SandboxExecutor, SandboxResult, synthesize_response
from framework.code_mode.tool_registry import ToolRegistry, ToolSpec


__all__ = [
    "SandboxExecutor",
    "SandboxResult",
    "ToolRegistry",
    "ToolSpec",
    "synthesize_response",
]
