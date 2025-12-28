"""
Example 7: Real-World LTM Use Case - Personal Fitness Coach Agent

This example demonstrates a production-ready use case of Long-Term Memory:
A Personal Fitness Coach Agent that remembers user's fitness goals, preferences,
workout history, and injuries across multiple sessions.

This is a PROPER Agent-based example showing how LTM makes AI assistants
genuinely personalized and useful over time.

Key Real-World Features:
1. Agent remembers user profile without being told again
2. Recommendations adapt based on stored preferences
3. Safety considerations (injury tracking) persist across sessions
4. Progress tracking over time

Uses local HuggingFace model - no API key required.
"""

import asyncio
from datetime import datetime, timezone

from framework.agents import Agent
from framework.memory import MemoryScope, PersistentFacts
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Personal Fitness Coach with Long-Term Memory."""
    print("\n" + "🏋️ " * 20)
    print("  PERSONAL FITNESS COACH WITH LONG-TERM MEMORY")
    print("🏋️ " * 20 + "\n")

    # Use persistent database to simulate real production use
    # MongoDB connection

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    print("Loading local model (first time may take a few minutes to download)...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    # Create agent with persistent facts enabled
    agent = Agent(
        name="FitnessCoach",
        instructions=(
            "You are a personal fitness coach AI that provides workout advice "
            "and health guidance. You remember everything the user tells you about: "
            "their fitness goals, any injuries or health conditions, exercise preferences, "
            "and past workout history. Always consider their injuries when recommending "
            "exercises. Be encouraging and supportive. Reference things they've told you before."
        ),
        model=model,
        storage=storage,
        enable_persistent_facts=True,  # This enables LTM!
    )

    user_id = "user_john_fitness"
    session_1 = "onboarding"
    session_2 = "week_later"
    session_3 = "month_later"

    # ==================== SESSION 1: Onboarding ====================
    print("=" * 60)
    print("SESSION 1: Initial Onboarding (Day 1)")
    print("=" * 60)

    print("\n👤 User: Hi! I'm John, 32 years old. I want to lose 20 pounds...")
    response1 = await agent.invoke(
        "Hi! I'm John, 32 years old. I want to lose 20 pounds and build some muscle. "
        "I have an old knee injury from playing basketball so I can't do high-impact exercises. "
        "I prefer working out in the mornings before work.",
        user_id=user_id,
        thread_id=session_1,
    )
    print(f"\n🤖 Coach: {response1[:400]}...")

    # Store additional facts manually (simulating assistant learning)
    if agent.persistent_facts:
        await agent.persistent_facts.add(
            "fitness_goals", {"weight_loss": "20 pounds", "build_muscle": True}, scope_id=user_id
        )
        await agent.persistent_facts.add(
            "injuries",
            [{"type": "knee", "cause": "basketball", "restrictions": ["high-impact exercises"]}],
            scope_id=user_id,
            tags=["important", "safety"],
        )
        await agent.persistent_facts.add(
            "preferences", {"workout_time": "morning", "before_work": True}, scope_id=user_id
        )
        await agent.persistent_facts.add("profile", {"name": "John", "age": 32}, scope_id=user_id)

    print("\n📝 Facts stored about user John:")
    if agent.persistent_facts:
        facts = await agent.persistent_facts.get_all(scope_id=user_id)
        for fact in facts:
            print(f"   • {fact.key}: {fact.value}")

    # ==================== SESSION 2: Week Later ====================
    print("\n" + "=" * 60)
    print("SESSION 2: Follow-up (1 Week Later)")
    print("=" * 60)
    print("\n⏳ [Simulating time passing... New session starts]")

    # Simulate session break
    await storage.disconnect()
    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    # Recreate agent (simulates app restart / new session)
    persistent_facts = PersistentFacts(
        storage=storage,
        scope=MemoryScope.USER,
        auto_extract=True,
        extraction_model=model,
    )

    agent = Agent(
        name="FitnessCoach",
        instructions="""You are a personal fitness coach AI. You remember everything about the user.
Always check their injuries before recommending exercises. Be supportive and reference their goals.""",
        model=model,
        storage=storage,
        persistent_facts=persistent_facts,
    )

    print("\n👤 User: Hey! Can you suggest a leg workout for me?")
    response2 = await agent.invoke(
        "Hey! Can you suggest a leg workout for me?",
        user_id=user_id,
        thread_id=session_2,
    )
    print(f"\n🤖 Coach: {response2[:500]}...")
    print("\n✅ Notice: Coach should remember knee injury and avoid high-impact exercises!")

    # ==================== SESSION 3: Progress Check ====================
    print("\n" + "=" * 60)
    print("SESSION 3: Progress Check (1 Month Later)")
    print("=" * 60)

    # User provides update
    print("\n👤 User: I've lost 5 pounds already! Also my knee is feeling much better...")
    response3 = await agent.invoke(
        "Great news! I've lost 5 pounds already! Also my knee is feeling much better "
        "now after doing the low-impact exercises you suggested. Can we start "
        "adding some more challenging exercises?",
        user_id=user_id,
        thread_id=session_3,
    )
    print(f"\n🤖 Coach: {response3[:500]}...")

    # Update facts based on progress
    if agent.persistent_facts:
        # Record progress
        await agent.persistent_facts.add(
            "progress_log",
            [{"date": datetime.now(timezone.utc).isoformat(), "weight_lost": "5 pounds"}],
            scope_id=user_id,
        )

        # Update injury status
        injuries = await agent.persistent_facts.get("injuries", scope_id=user_id)
        if injuries:
            updated_injuries = injuries.value
            if updated_injuries and len(updated_injuries) > 0:
                updated_injuries[0]["status"] = "improving"
                updated_injuries[0]["can_increase_intensity"] = True
            await agent.persistent_facts.update("injuries", updated_injuries, scope_id=user_id)

    print("\n📊 User's progress tracked in LTM:")
    if agent.persistent_facts:
        progress = await agent.persistent_facts.get("progress_log", scope_id=user_id)
        injuries = await agent.persistent_facts.get("injuries", scope_id=user_id)
        print(f"   • Progress: {progress.value if progress else 'N/A'}")
        print(f"   • Injury Status: {injuries.value if injuries else 'N/A'}")

    # ==================== Final Summary ====================
    print("\n" + "=" * 60)
    print("SUMMARY: What LTM Enabled")
    print("=" * 60)
    print("""
✅ 1. PERSONALIZATION
   The coach knows John's name, age, and goals without being reminded.

✅ 2. SAFETY
   Knee injury is tracked and considered in all workout recommendations.

✅ 3. PREFERENCES
   Morning workout preference is remembered across sessions.

✅ 4. PROGRESS TRACKING
   Weight loss progress is logged and celebrated.

✅ 5. ADAPTIVE BEHAVIOR
   Injury status updated based on feedback, allowing intensity increase.
""")

    # Show all stored facts
    print("=" * 60)
    print("ALL STORED FACTS FOR USER")
    print("=" * 60)
    if agent.persistent_facts:
        all_facts = await agent.persistent_facts.get_all(scope_id=user_id)
        for fact in all_facts:
            print(f"   📌 {fact.key}: {fact.value}")

    await storage.disconnect()

    print("\n📁 Data saved in MongoDB database: astra_ltm_test")
    print("   Run this script again to see persistence in action!\n")


if __name__ == "__main__":
    asyncio.run(main())
