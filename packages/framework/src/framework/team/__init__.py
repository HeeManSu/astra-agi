"""
Team module for Astra Framework.

Provides multi-agent coordination through team-based delegation.
"""

from framework.team.team import Team
from framework.team.types import (
    DELEGATION_TOOL,
    DelegationError,
    DelegationResultEvent,
    DelegationStartEvent,
    MemberExecutionEvent,
    MemberNotFoundError,
    SynthesisEvent,
    TeamError,
    TeamExecutionContext,
    TeamMember,
    TeamStatusEvent,
    TeamTimeoutError,
)


__all__ = [
    "DELEGATION_TOOL",
    "DelegationError",
    "DelegationResultEvent",
    "DelegationStartEvent",
    "MemberExecutionEvent",
    "MemberNotFoundError",
    "SynthesisEvent",
    "Team",
    "TeamError",
    "TeamExecutionContext",
    "TeamMember",
    "TeamStatusEvent",
    "TeamTimeoutError",
]
