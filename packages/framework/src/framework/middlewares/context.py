"""
Middleware context passed to each middleware.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MiddlewareContext:
    """
    Context object passed to middlewares.
    
    Provides access to run metadata, tools, and conversation context.
    
    Attributes:
        run_id: Unique run identifier
        agent_id: Agent identifier
        thread_id: Optional thread/conversation ID
        metadata: Additional metadata dict (use for custom IDs like user_id)
        tools: List of available tools
    """
    run_id: str
    agent_id: str
    thread_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tools: List[Any] = field(default_factory=list)
