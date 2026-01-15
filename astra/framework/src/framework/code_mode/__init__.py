"""
Code Mode for Astra Teams.

This package provides components for Team code execution:
    - Sandbox: Generate and execute LLM code in isolated subprocess
    - SandboxResult: Execution result container
    - generate_stubs: Generate Python stubs from semantic layer
    - build_semantic_layer: Build semantic layer from Team

Flow:
    Team → semantic_layer → generate_stubs() → LLM Prompt → Code → Sandbox.execute()
"""

from framework.code_mode.sandbox import Sandbox, SandboxResult
from framework.code_mode.semantic import TeamSemanticLayer, build_semantic_layer
from framework.code_mode.stub_generator import generate_stubs
from framework.code_mode.tool_registry import ToolRegistry, ToolSpec


__all__ = [
    # Sandbox
    "Sandbox",
    "SandboxResult",
    # Semantic Layer
    "build_semantic_layer",
    "generate_stubs",
    "TeamSemanticLayer",
    # Tool Registry
    "ToolRegistry",
    "ToolSpec",
]
