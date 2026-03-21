"""
Astra Framework — Public API.

Core exports for building compiler-based multi-agent workflows.

Quick start:
    from framework import Agent, Sandbox, build_entity_semantic_layer
"""

from framework.agents import Agent
from framework.astra import Astra, AstraContext, FrameworkSettings
from framework.code_mode import (
    EntitySemanticLayer,
    Sandbox,
    SandboxResult,
    build_domain_schema,
    build_entity_semantic_layer,
    generate_stubs,
)


__all__ = [
    "Agent",
    "Astra",
    "AstraContext",
    "EntitySemanticLayer",
    "FrameworkSettings",
    "Sandbox",
    "SandboxResult",
    "build_domain_schema",
    "build_entity_semantic_layer",
    "generate_stubs",
]

