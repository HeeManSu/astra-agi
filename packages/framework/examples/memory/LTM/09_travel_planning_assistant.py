"""
Example 9: Advanced Travel Planning Assistant with LTM

A comprehensive example demonstrating a production-ready travel planning assistant
that uses Long-Term Memory to provide personalized travel recommendations.

Key Features Demonstrated:
1. Multi-session conversations with persistent memory
2. Preference learning and adaptation
3. Travel history tracking
4. Budget and constraint management
5. Fact extraction from natural conversations
6. Context-aware recommendations
7. Progress tracking across sessions

This example shows how LTM enables truly personalized AI assistants that
remember user preferences, past trips, and constraints across sessions.

Uses local HuggingFace model - no API key required.
"""

import asyncio
from datetime import datetime, timezone

from framework.agents import Agent
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Travel Planning Assistant with Long-Term Memory."""
    print("\n" + "✈️ " * 25)
    print("  TRAVEL PLANNING ASSISTANT WITH LONG-TERM MEMORY")
    print("✈️ " * 25 + "\n")

    # Setup persistent storage
    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    print("Loading local model (first time may take a few minutes to download)...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    # Create agent with persistent facts enabled
    agent = Agent(
        name="TravelPlanner",
        instructions=(
            "You are a helpful travel planning assistant. You remember everything about the user: "
            "their travel preferences, past trips, budget constraints, favorite destinations, "
            "and any special requirements. Use this information to provide personalized "
            "recommendations. Always reference past conversations and preferences when making suggestions. "
            "Be friendly, knowledgeable, and considerate of their budget and constraints."
        ),
        model=model,
        storage=storage,
        enable_persistent_facts=True,
    )

    user_id = "user_traveler_001"
    session_1 = "planning_europe_trip"
    session_2 = "post_trip_feedback"
    session_3 = "planning_next_trip"

    # ==================== SESSION 1: Initial Planning ====================
    print("=" * 70)
    print("SESSION 1: Planning First Trip (Europe)")
    print("=" * 70)

    print("\n👤 User: Hi! I'm planning a trip to Europe next month...")
    response1 = await agent.invoke(
        "Hi! I'm planning a trip to Europe next month. I'm Sarah, 28 years old, "
        "and I work as a marketing manager. I have a budget of $3000 and I prefer "
        "budget-friendly accommodations. I love art museums, historical sites, "
        "and trying local food. I'm vegetarian and I prefer walking or public transport. "
        "Can you help me plan a 10-day trip?",
        user_id=user_id,
        thread_id=session_1,
    )
    print(f"\n🤖 Assistant: {response1[:400]}...")

    # Manually store structured facts (simulating fact extraction + manual curation)
    if agent.persistent_facts:
        await agent.persistent_facts.add(
            "profile",
            {"name": "Sarah", "age": 28, "occupation": "Marketing Manager"},
            scope_id=user_id,
        )

        await agent.persistent_facts.add(
            "travel_preferences",
            {
                "accommodation_type": "budget-friendly",
                "transport_preference": ["walking", "public_transport"],
                "interests": ["art_museums", "historical_sites", "local_food"],
            },
            scope_id=user_id,
        )

        await agent.persistent_facts.add("dietary_restrictions", ["vegetarian"], scope_id=user_id)

        await agent.persistent_facts.add(
            "budget_constraints",
            {"total_budget": 3000, "currency": "USD", "preference": "budget-friendly"},
            scope_id=user_id,
        )

    await asyncio.sleep(1)

    print("\n👤 User: I'm thinking about Paris, Amsterdam, and Berlin...")
    response2 = await agent.invoke(
        "I'm thinking about visiting Paris, Amsterdam, and Berlin. What do you think? "
        "Can you suggest a good itinerary?",
        user_id=user_id,
        thread_id=session_1,
    )
    print(f"\n🤖 Assistant: {response2[:400]}...")

    # Store planned trip
    if agent.persistent_facts:
        await agent.persistent_facts.add(
            "planned_trips",
            [
                {
                    "trip_id": "europe_2024_01",
                    "destination": ["Paris", "Amsterdam", "Berlin"],
                    "duration_days": 10,
                    "budget": 3000,
                    "status": "planned",
                    "planned_date": "2024-02-15",
                }
            ],
            scope_id=user_id,
        )

    await asyncio.sleep(1)

    print("\n📝 Stored Facts After Session 1:")
    if agent.persistent_facts:
        all_facts = await agent.persistent_facts.get_all(scope_id=user_id)
        for fact in all_facts:
            print(f"   • {fact.key}: {fact.value}")

    # ==================== SESSION 2: Post-Trip Feedback ====================
    print("\n" + "=" * 70)
    print("SESSION 2: Post-Trip Feedback (2 Weeks Later)")
    print("=" * 70)
    print("\n⏳ [Simulating time passing... User returns from trip]")

    # Simulate session break (reconnect storage)
    await storage.disconnect()
    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    # Recreate agent (simulates app restart)
    agent = Agent(
        name="TravelPlanner",
        instructions=(
            "You are a helpful travel planning assistant. You remember everything about the user. "
            "Reference their past trips and preferences when making recommendations."
        ),
        model=model,
        storage=storage,
        enable_persistent_facts=True,
    )

    print("\n👤 User: I just got back from my Europe trip! It was amazing...")
    response3 = await agent.invoke(
        "I just got back from my Europe trip! It was amazing. I loved Paris the most - "
        "the art museums were incredible. Amsterdam was nice but a bit too touristy for me. "
        "Berlin was interesting but I found the food options limited for vegetarians. "
        "I ended up spending about $2800 total. I'm thinking about my next trip already!",
        user_id=user_id,
        thread_id=session_2,
    )
    print(f"\n🤖 Assistant: {response3[:400]}...")

    # Update facts based on feedback
    if agent.persistent_facts:
        # Update trip status
        planned_trips = await agent.persistent_facts.get("planned_trips", scope_id=user_id)
        if planned_trips:
            trips = (
                planned_trips.value
                if isinstance(planned_trips.value, list)
                else [planned_trips.value]
            )
            if trips:
                trips[0]["status"] = "completed"
                trips[0]["actual_spend"] = 2800
                trips[0]["feedback"] = {
                    "favorite": "Paris",
                    "least_favorite": "Berlin",
                    "reason": "Limited vegetarian options",
                }
                await agent.persistent_facts.update("planned_trips", trips, scope_id=user_id)

        # Update preferences based on experience
        preferences = await agent.persistent_facts.get("travel_preferences", scope_id=user_id)
        if preferences:
            updated_prefs = preferences.value.copy()
            updated_prefs["favorite_destinations"] = ["Paris"]
            updated_prefs["avoid_crowded"] = True  # Learned from Amsterdam feedback
            await agent.persistent_facts.update(
                "travel_preferences", updated_prefs, scope_id=user_id, merge=True
            )

        # Add travel history
        await agent.persistent_facts.add(
            "travel_history",
            [
                {
                    "trip_id": "europe_2024_01",
                    "destinations": ["Paris", "Amsterdam", "Berlin"],
                    "date": datetime.now(timezone.utc).isoformat(),
                    "rating": 4,
                    "notes": "Loved Paris, Berlin had limited vegetarian options",
                }
            ],
            scope_id=user_id,
        )

    await asyncio.sleep(1)

    print("\n📊 Updated Facts After Session 2:")
    if agent.persistent_facts:
        trips = await agent.persistent_facts.get("planned_trips", scope_id=user_id)
        prefs = await agent.persistent_facts.get("travel_preferences", scope_id=user_id)
        print(f"   • Trip Status: {trips.value[0]['status'] if trips and trips.value else 'N/A'}")
        print(f"   • Updated Preferences: {prefs.value if prefs else 'N/A'}")

    # ==================== SESSION 3: Planning Next Trip ====================
    print("\n" + "=" * 70)
    print("SESSION 3: Planning Next Trip (1 Month Later)")
    print("=" * 70)

    print("\n👤 User: I want to plan another trip, maybe to Asia this time...")
    response4 = await agent.invoke(
        "I want to plan another trip, maybe to Asia this time. I have a budget of $2500 "
        "and I want to visit places with good vegetarian food and less crowded than Amsterdam was. "
        "What do you recommend?",
        user_id=user_id,
        thread_id=session_3,
    )
    print(f"\n🤖 Assistant: {response4[:500]}...")
    print("\n✅ Notice: Assistant should remember:")
    print("   - Previous trip feedback (Amsterdam too crowded, Berlin limited vegetarian options)")
    print("   - Budget constraints ($2500 this time)")
    print("   - Preference for art museums and historical sites")
    print("   - Vegetarian dietary requirement")

    await asyncio.sleep(1)

    print("\n👤 User: What about Japan? I've always wanted to visit Tokyo...")
    response5 = await agent.invoke(
        "What about Japan? I've always wanted to visit Tokyo and Kyoto. "
        "Is that feasible with my budget and preferences?",
        user_id=user_id,
        thread_id=session_3,
    )
    print(f"\n🤖 Assistant: {response5[:400]}...")

    # Store new planned trip
    if agent.persistent_facts:
        planned_trips = await agent.persistent_facts.get("planned_trips", scope_id=user_id)
        if planned_trips:
            trips = (
                planned_trips.value
                if isinstance(planned_trips.value, list)
                else [planned_trips.value]
            )
            trips.append(
                {
                    "trip_id": "japan_2024_02",
                    "destination": ["Tokyo", "Kyoto"],
                    "duration_days": 12,
                    "budget": 2500,
                    "status": "planned",
                    "planned_date": "2024-04-10",
                }
            )
            await agent.persistent_facts.update("planned_trips", trips, scope_id=user_id)

    # ==================== Final Summary ====================
    print("\n" + "=" * 70)
    print("SUMMARY: What LTM Enabled")
    print("=" * 70)
    print("""
✅ 1. PERSONALIZATION
   Assistant remembers user's name, age, occupation, and preferences without being reminded.

✅ 2. PREFERENCE LEARNING
   Learned from feedback: Amsterdam too crowded, Berlin limited vegetarian options.
   Updated preferences automatically.

✅ 3. TRAVEL HISTORY
   Tracks past trips, spending, and feedback for future recommendations.

✅ 4. BUDGET AWARENESS
   Remembers budget constraints ($3000 → $2500) and provides budget-appropriate suggestions.

✅ 5. CONTEXTUAL RECOMMENDATIONS
   Uses past experiences to avoid repeating mistakes (crowded places, limited food options).

✅ 6. MULTI-SESSION MEMORY
   All information persists across sessions, enabling seamless conversations.
""")

    print("=" * 70)
    print("ALL STORED FACTS FOR USER")
    print("=" * 70)
    if agent.persistent_facts:
        all_facts = await agent.persistent_facts.get_all(scope_id=user_id)
        for fact in all_facts:
            print(f"   📌 {fact.key}: {fact.value}")

    await storage.disconnect()

    print("\n📁 Data saved in MongoDB database: astra_ltm_test")
    print("   Run this script again to see persistence in action!\n")


if __name__ == "__main__":
    asyncio.run(main())
