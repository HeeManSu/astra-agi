"""
Example weather agent demonstrating agent execution.

This agent can answer weather-related questions using tool calling.
Includes observability (tracing and metrics) and saves responses to JSON file.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Agent, tool

# Weather tool implementation using @tool decorator
@tool
async def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # Mock weather data for demo
    weather_data = {
        "san francisco": "Sunny, 72°F",
        "new york": "Cloudy, 65°F",
        "london": "Rainy, 55°F",
        "tokyo": "Clear, 75°F",
    }
    
    location_lower = location.lower()
    for city, weather in weather_data.items():
        if city in location_lower or location_lower in city:
            return f"The weather in {location} is {weather}"
    
    return f"Weather data not available for {location}. It's a nice day!"


async def main():
    """Run weather agent example."""
    
    print("=== Weather Agent Example ===\n")
    
    # Initialize agent (this will initialize observability)
    weather_agent = Agent(
        id="weather-agent",
        name="Weather Agent",
        description="An agent that provides weather information",
        instructions=(
            'You are a helpful weather assistant. '
            'When asked about weather, use the get_weather tool to fetch current weather information. '
            'Always be friendly and concise.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": os.getenv("GOOGLE_API_KEY")  # Set GOOGLE_API_KEY in .env file
        },
        tools=[get_weather]
    )
    
    print(f"Created agent: {weather_agent}\n")
    
    await weather_agent.startup()
    
    # Store all responses for JSON export
    responses = []
    
    # Test 1: Simple invoke
    print("1. Testing invoke() method")
    print("-" * 50)
    query1 = "What is the temperature today in San Francisco?"
    print(f"Query: {query1}")
    print("\n📤 Invoking agent...")
    
    response1 = await weather_agent.invoke(query1)
    responses.append({
        "query": query1,
        "response": response1,
        "timestamp": datetime.now().isoformat(),
        "test": "invoke"
    })
    
    print(f"\n✅ Response: {response1['content']}")
    if response1.get('tool_calls'):
        print(f"🔧 Tool calls: {response1['tool_calls']}")
    print(f"📊 Usage: {response1.get('usage', {})}")
    print(f"⏱️  Latency: {response1.get('metadata', {}).get('latency_ms', 0):.2f}ms")
    
    # Test 2: Streaming
    print("\n\n2. Testing stream() method")
    print("-" * 50)
    query2 = "What's the weather like in New York?"
    print(f"Query: {query2}")
    print("\n📤 Streaming response...")
    print("✅ Response: ", end="", flush=True)
    
    streamed_content = ""
    async for chunk in weather_agent.stream(query2):
        content = chunk.get('content', '')
        if content:
            print(content, end="", flush=True)
            streamed_content += content
    
    responses.append({
        "query": query2,
        "response": {"content": streamed_content},
        "timestamp": datetime.now().isoformat(),
        "test": "stream"
    })
    print("\n")
    
    # Test 3: Another query
    print("\n3. Testing with different location")
    print("-" * 50)
    query3 = "Tell me about the weather in Tokyo"
    print(f"Query: {query3}")
    print("\n📤 Invoking agent...")
    
    response3 = await weather_agent.invoke(query3)
    responses.append({
        "query": query3,
        "response": response3,
        "timestamp": datetime.now().isoformat(),
        "test": "invoke"
    })
    print(f"\n✅ Response: {response3['content']}")
    
    # Get metrics
    obs = weather_agent.dependencies.observability
    metrics_text = obs.metrics.get_metrics_text()
    
    # Save responses to JSON file
    output_file = Path(__file__).parent.parent / "jsons" / "weather_agent_responses.json"
    output_data = {
        "agent_id": weather_agent.id,
        "agent_name": weather_agent.name,
        "timestamp": datetime.now().isoformat(),
        "responses": responses,
        "metrics": metrics_text
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"\n💾 Responses saved to: {output_file}")
    print("\n=== Example Complete ===")
    
    # Shutdown observability
    await weather_agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

