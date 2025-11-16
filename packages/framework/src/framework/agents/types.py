"""
Type definitions for Agent configuration.
"""
from typing import Any, Dict, Optional, Union, Callable, Protocol
from typing_extensions import TypedDict


class ModelConfig(TypedDict, total=False):
    """Model configuration."""
    provider: str  # e.g., 'openai', 'google', 'anthropic'
    model: str  # e.g., 'gpt-4', 'gemini-1.5-flash'
    api_key: Optional[str]
    # Additional model-specific settings can be added here


class AgentConfig(TypedDict, total=False):
    """
    Configuration for creating an Agent.
    
    """
    # Required fields
    name: str
    instructions: str
    
    # Optional fields
    id: Optional[str]  # Defaults to name if not provided
    description: Optional[str]
    model: Union[ModelConfig, str]  # Can be a config dict or model string
    max_retries: Optional[int]  # Defaults to 0
    tools: Optional[Dict[str, Any]]  # Dictionary of tools
    # For MVP, we'll keep tools simple - can be extended later
    # workflows: Optional[Dict[str, Any]]  # Future: workflows
    # memory: Optional[Any]  # Future: memory configuration
    # agents: Optional[Dict[str, 'Agent']]  # Future: sub-agents

