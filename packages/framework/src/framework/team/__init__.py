"""
Team module for Astra Framework.

Provides multi-agent coordination through team-based delegation.
"""

from framework.team.team import (
    DELEGATION_TOOL,
    DelegationError,
    MemberNotFoundError,
    Team,
    TeamError,
    TeamExecutionContext,
    TeamMember,
    TeamTimeoutError,
)


__all__ = [
    "DELEGATION_TOOL",
    "DelegationError",
    "MemberNotFoundError",
    "Team",
    "TeamError",
    "TeamExecutionContext",
    "TeamMember",
    "TeamTimeoutError",
]
