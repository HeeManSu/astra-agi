"""Multi-agent team example - CONCEPT DEMONSTRATION

NOTE: This is a concept demonstration showing team collaboration APIs.

Shows:
- Creating specialized agents
- Team composition concept
- Delegation workflow
"""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal


async def main():
    """
    Concept demonstration of multi-agent teams.
    
    Shows how specialized agents can work together.
    """
    
    print("=== Astra Multi-Agent Team (Concept Demo) ===\n")
    
    # Create specialized agents for different roles
    researcher = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a research specialist. Provide factual information.",
        name="researcher",
    )
    
    writer = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a writer. Create engaging content.",
        name="writer",
    )
    
    editor = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are an editor. Review and improve content.",
        name="editor",
    )
    
    # Simulate workflow
    print("📋 Task: Create content about Python programming\n")
    print("=" * 60)
    
    print("\n🔍 Researcher: Gathering information...")
    research = await researcher.invoke("What are the top 3 benefits of Python?")
    print(f"Result: {research[:100]}...\n")
    
    print("✍️  Writer: Creating content...")
    article = await writer.invoke(f"Write a short paragraph about: {research}")
    print(f"Result: {article[:100]}...\n")
    
    print("📝 Editor: Reviewing...")
    final = await editor.invoke(f"Review and improve: {article}")
    print(f"Final: {final}")
    
    print("\n" + "=" * 60)
    print("Team Collaboration Concepts")
    print("=" * 60)
    
    print("\n👥 **Team Structure**:")
    print("  - Specialized agents for different roles")
    print("  - Manager agent for coordination")
    print("  - Delegation between team members")
    
    print("\n📋 **How to create teams**:")
    print("""
    from astra import Team, TeamMember
    
    # Create team with members
    team = Team(
        name="content-team",
        model=model,  # Model for coordination
        members=["researcher", "writer", "editor"],  # Member IDs
    )
    
    # Agents can delegate to team members
    # Manager coordinates the workflow
    """)
    
    print("\n✨ **Benefits**:")
    print("  ✓ Specialized expertise per agent")
    print("  ✓ Complex task decomposition")
    print("  ✓ Higher quality through collaboration")
    print("  ✓ Scalable multi-agent systems")


if __name__ == "__main__":
    asyncio.run(main())
