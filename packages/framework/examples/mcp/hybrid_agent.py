import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents import tool
from framework.mcp import MCPManager
from framework.mcp.utils import TrackingAgent, log_to_csv
from framework.models.google.gemini import Gemini


# Define a normal tool
@tool
def calculate_roi(investment: float, return_amount: float) -> float:
    """
    Calculate Return on Investment (ROI).

    Args:
        investment: Initial investment amount
        return_amount: Total return amount

    Returns:
        ROI percentage
    """
    return ((return_amount - investment) / investment) * 100


async def main():
    manager = MCPManager()
    await manager.add_server("filesystem", {"path": "."})

    try:
        mcp_tools = await manager.get_tools()
    except Exception as e:
        print(f"Failed to load MCP tools: {e}")
        return

    all_tools = [calculate_roi, *mcp_tools]

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[WARN] GOOGLE_API_KEY not found.")
        return

    agent = TrackingAgent(
        name="HybridAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="You are a financial analyst. Calculate ROI and save reports.",
        tools=all_tools,
    )

    print("\n--- Calculating ROI and Saving Report ---")
    try:
        response = await agent.invoke(
            "I invested $5000 and got back $7500. Calculate the ROI and save a report to 'roi_report.txt'."
        )
        print("\nResponse:")
        print(response)

        # Log Usage
        log_to_csv(agent.name, agent.last_usage)

    except Exception as e:
        print(f"Agent invocation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
