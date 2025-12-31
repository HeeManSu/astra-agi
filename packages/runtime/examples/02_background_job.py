"""Background job example - simulates processing multiple tasks with an agent."""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal


# Create global agent instance (reused across jobs)
welcome_agent = Agent(
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="Generate personalized, friendly welcome messages",
    name="welcome-generator",
)


async def send_welcome_email(user_name: str, user_role: str) -> str:
    """
    Background job that generates personalized welcome message.

    In a real application, this would be called by a job queue
    (e.g., Celery, RQ, BullMQ) to process user signups.

    Args:
        user_name: Name of the user
        user_role: Role (e.g., "developer", "manager")

    Returns:
        Generated welcome message
    """
    prompt = f"""
    Generate a welcome message for {user_name} who just signed up as a {user_role}.
    Keep it friendly, professional, and under 3 sentences.
    """

    response = await welcome_agent.invoke(prompt)
    return response


async def main():
    """Simulate processing multiple background jobs concurrently."""

    print("=== Background Job Simulation ===\n")
    print("Processing user signups...\n")

    # Simulate multiple users signing up
    users = [
        ("Alice", "developer"),
        ("Bob", "manager"),
        ("Charlie", "designer"),
    ]

    # Process all jobs concurrently (like a job queue would)
    tasks = [send_welcome_email(name, role) for name, role in users]
    results = await asyncio.gather(*tasks)

    # Display results
    for (name, role), message in zip(users, results):
        print(f"User: {name} ({role})")
        print(f"Message: {message}\n")
        print("-" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
