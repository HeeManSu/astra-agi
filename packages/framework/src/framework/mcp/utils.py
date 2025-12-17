import csv
import datetime
import os
from typing import Any

from framework.agents import Agent
from framework.models.base import ModelResponse


class TrackingAgent(Agent):
    """
    Agent that tracks token usage from the last invocation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_usage: dict[str, Any] | None = None

    def _format_response(self, response: ModelResponse) -> str:
        """Capture usage before formatting."""
        self.last_usage = response.usage
        return super()._format_response(response)


def log_to_csv(agent_name: str, usage: dict[str, Any] | None, filename: str = "token_usage.csv"):
    """
    Log token usage to a CSV file.
    """
    if not usage:
        print(f"[WARN] No usage data found for {agent_name}")
        return

    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["Timestamp", "Agent", "Input Tokens", "Output Tokens", "Total Tokens"])

        writer.writerow(
            [
                datetime.datetime.now().isoformat(),
                agent_name,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("total_tokens", 0),
            ]
        )

    print(f"\n[INFO] Token usage logged to {filename}")
    print(f"  - Input: {usage.get('input_tokens', 0)}")
    print(f"  - Output: {usage.get('output_tokens', 0)}")
    print(f"  - Total: {usage.get('total_tokens', 0)}")
