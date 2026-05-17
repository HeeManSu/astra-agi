"""Benchmark-only config: disabled memory shared by every agent and team."""

from framework.memory import Memory


DISABLED_MEMORY = Memory(add_history_to_messages=False, num_history_turns=0)
