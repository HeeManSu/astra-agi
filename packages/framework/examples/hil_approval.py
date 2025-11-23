"""
Example demonstrating HIL (Human-in-the-Loop) Tool Approval.

Shows how tools can require human approval before execution.
"""
import asyncio
import os
from framework.agents import Agent, tool
from framework.models import Gemini
from framework.storage import SQLiteStorage


# Define a tool that requires approval
@tool(requires_approval=True)
def delete_file(path: str) -> str:
    """
    Delete a file (requires human approval).
    
    This is a sensitive operation that requires approval.
    """
    if os.path.exists(path):
        os.remove(path)
        return f"File {path} deleted successfully"
    return f"File {path} not found"


# Define a tool for external execution
@tool(external_execution=True)
def run_shell_command(command: str) -> str:
    """
    Run a shell command (executed externally for safety).
    
    Shell commands are dangerous and must be executed by humans.
    """
    # This will never execute - it's marked for external execution
    return "Executed externally"


async def main():
    """Demonstrate HIL tool approval flow."""
    print("=== HIL Tool Approval Example ===\n")
    
    # Setup storage (required for HIL)
    storage = SQLiteStorage("hil_demo.db")
    await storage.connect()
    
    # Create agent with HIL-enabled tools
    agent = Agent(
        name="SafetyBot",
        model=Gemini("1.5-flash"),
        instructions="You are a helpful assistant with safety controls.",
        storage=storage,
        tools=[delete_file, run_shell_command]
    )
    
    print("Agent created with HIL-enabled tools:")
    print(f"  - delete_file (requires_approval={delete_file.requires_approval})")
    print(f"  - run_shell_command (external_execution={run_shell_command.external_execution})")
    print()
    
    # Example 1: Tool requiring approval
    print("=" * 60)
    print("Example 1: Tool Requiring Approval")
    print("=" * 60)
    print("Tool metadata:")
    print(f"  Name: {delete_file.name}")
    print(f"  Requires Approval: {delete_file.requires_approval}")
    print(f"  Description: {delete_file.description}")
    print()
    
    # In a real scenario, the agent would:
    # 1. Identify that delete_file needs to be called
    # 2. Pause execution (return run_id)
    # 3. Wait for human approval
    # 4. Resume with decision
    
    # Simulated flow:
    print("Simulated Flow:")
    print("1. Agent wants to call delete_file('/tmp/test.txt')")
    print("2. Tool requires approval → Execution pauses")
    print("3. System returns run_id to user")
    print("4. Human reviews and decides: approve/decline")
    print("5. Call agent.resume(run_id, decision='approve')")
    print("6. Tool executes and agent continues")
    print()
    
    # Example 2: External execution tool
    print("=" * 60)
    print("Example 2: External Execution Tool")
    print("=" * 60)
    print("Tool metadata:")
    print(f"  Name: {run_shell_command.name}")
    print(f"  External Execution: {run_shell_command.external_execution}")
    print(f"  Description: {run_shell_command.description}")
    print()
    
    print("Simulated Flow:")
    print("1. Agent wants to call run_shell_command('ls -la')")
    print("2. Tool requires external execution → Execution pauses")
    print("3. System returns run_id and command details")
    print("4. Human executes command externally")
    print("5. Call agent.resume(run_id, result={'stdout': '...'})")
    print("6. Agent continues with the result")
    print()
    
    # Cleanup
    await storage.disconnect()
    if os.path.exists("hil_demo.db"):
        os.remove("hil_demo.db")
    
    print("=" * 60)
    print("KEY CONCEPTS:")
    print("=" * 60)
    print("✓ requires_approval: Tool needs human approval before execution")
    print("✓ external_execution: Tool must be executed outside the agent")
    print("✓ HIL requires storage: Run state must persist")
    print("✓ Pause/Resume: Agent pauses, human acts, agent resumes")


if __name__ == "__main__":
    asyncio.run(main())
