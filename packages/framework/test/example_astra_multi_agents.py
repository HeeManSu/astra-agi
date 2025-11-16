"""
Example demonstrating Astra framework with multiple agents.

This example shows:
1. Creating multiple agents with different capabilities
2. Registering them with Astra instance
3. Calling agents through Astra
4. Observability and metrics collection
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Agent, Astra, tool

# Tool implementations using @tool decorator
@tool
async def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    weather_data = {
        "san francisco": "Sunny, 72°F",
        "new york": "Cloudy, 65°F",
        "london": "Rainy, 55°F",
        "tokyo": "Clear, 75°F",
        "paris": "Partly cloudy, 68°F",
    }
    
    location_lower = location.lower()
    for city, weather in weather_data.items():
        if city in location_lower or location_lower in city:
            return f"The weather in {location} is {weather}"
    
    return f"Weather data not available for {location}. It's a nice day!"


@tool
async def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        # Simple eval for demo (in production, use a safer math parser)
        result = eval(expression)
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"


@tool
async def get_time(timezone: str = "UTC") -> str:
    """Get the current time in a timezone."""
    from datetime import datetime
    
    # Simple timezone handling for demo (in production, use pytz or zoneinfo)
    timezone_offsets = {
        "UTC": 0,
        "America/New_York": -5,
        "Europe/London": 0,
        "Asia/Tokyo": 9,
        "America/Los_Angeles": -8,
    }
    
    try:
        offset = timezone_offsets.get(timezone, 0)
        from datetime import timedelta
        current_time = datetime.utcnow() + timedelta(hours=offset)
        return f"Current time in {timezone} (UTC{offset:+d}) is {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return f"Error getting time for {timezone}: {str(e)}"


@tool
async def translate_text(text: str, target_language: str) -> str:
    """Translate text to target language (mock implementation)."""
    translations = {
        "hello": {"spanish": "hola", "french": "bonjour", "german": "hallo"},
        "thank you": {"spanish": "gracias", "french": "merci", "german": "danke"},
    }
    
    text_lower = text.lower()
    if text_lower in translations and target_language.lower() in translations[text_lower]:
        return f"'{text}' in {target_language} is '{translations[text_lower][target_language.lower()]}'"
    
    return f"Translation: '{text}' would be translated to {target_language} (mock translation)"


async def main():
    """Run Astra multi-agent example."""
    
    print("=== Astra Multi-Agent Example ===\n")
    
    # Create 4 different agents
    print("Creating agents...")
    
    # Agent 1: Weather Agent
    weather_agent = Agent(
        id="weather-agent",
        name="Weather Agent",
        description="Provides weather information for locations",
        instructions=(
            'You are a helpful weather assistant. '
            'When asked about weather, use the get_weather tool to fetch current weather information. '
            'Always be friendly and concise.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyBdlhWIITmvhQLunWUTv9t9-V4nwvo90I8"
        },
        tools=[get_weather]
    )
    
    # Agent 2: Calculator Agent
    calculator_agent = Agent(
        id="calculator-agent",
        name="Calculator Agent",
        description="Performs mathematical calculations",
        instructions=(
            'You are a helpful calculator assistant. '
            'When asked to calculate something, use the calculate tool. '
            'Be precise and show your work.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyBdlhWIITmvhQLunWUTv9t9-V4nwvo90I8"
        },
        tools=[calculate]
    )
    
    # Agent 3: Time Agent
    time_agent = Agent(
        id="time-agent",
        name="Time Agent",
        description="Provides current time information",
        instructions=(
            'You are a helpful time assistant. '
            'When asked about time, use the get_time tool to fetch current time in different timezones. '
            'Be accurate and mention the timezone clearly.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyBdlhWIITmvhQLunWUTv9t9-V4nwvo90I8"
        },
        tools=[get_time]
    )
    
    # Agent 4: Translator Agent
    translator_agent = Agent(
        id="translator-agent",
        name="Translator Agent",
        description="Translates text between languages",
        instructions=(
            'You are a helpful translation assistant. '
            'When asked to translate text, use the translate_text tool. '
            'Always confirm the source and target languages.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyBdlhWIITmvhQLunWUTv9t9-V4nwvo90I8"
        },
        tools=[translate_text]
    )
    
    # Initialize Astra with all agents (using list format - more user-friendly)
    print("Initializing Astra with agents...\n")
    astra = Astra({
        'agents': [
            weather_agent,
            calculator_agent,
            time_agent,
            translator_agent
        ]
    })
    
    print(f"✅ Astra instance created: {astra}")
    print(f"📋 Registered agents: {[agent.id for agent in astra.list_agents()]}\n")
    
    # Note: Observability is automatically initialized in __init__
    # Agents will initialize themselves lazily when invoke() is called
    
    # Store all responses
    responses = []
    
    # Test 1: Weather Agent
    print("=" * 60)
    print("1. Testing Weather Agent")
    print("=" * 60)
    weather_query = "What's the weather in San Francisco?"
    print(f"Query: {weather_query}\n")
    
    # Get agent by its ID (since we used list format)
    weather_agent_instance = astra.get_agent('weather-agent')
    weather_response = await weather_agent_instance.invoke(weather_query)
    responses.append({
        "agent": "weather",
        "query": weather_query,
        "response": weather_response,
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"✅ Response: {weather_response['content']}")
    if weather_response.get('tool_calls'):
        print(f"🔧 Tool calls: {weather_response['tool_calls']}")
    print()
    
    # Test 2: Calculator Agent
    print("=" * 60)
    print("2. Testing Calculator Agent")
    print("=" * 60)
    calc_query = "What is 25 multiplied by 17?"
    print(f"Query: {calc_query}\n")
    
    calc_agent_instance = astra.get_agent('calculator-agent')
    calc_response = await calc_agent_instance.invoke(calc_query)
    responses.append({
        "agent": "calculator",
        "query": calc_query,
        "response": calc_response,
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"✅ Response: {calc_response['content']}")
    if calc_response.get('tool_calls'):
        print(f"🔧 Tool calls: {calc_response['tool_calls']}")
    print()
    
    # Test 3: Time Agent
    print("=" * 60)
    print("3. Testing Time Agent")
    print("=" * 60)
    time_query = "What time is it in Tokyo?"
    print(f"Query: {time_query}\n")
    
    time_agent_instance = astra.get_agent('time-agent')
    time_response = await time_agent_instance.invoke(time_query)
    responses.append({
        "agent": "time",
        "query": time_query,
        "response": time_response,
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"✅ Response: {time_response['content']}")
    if time_response.get('tool_calls'):
        print(f"🔧 Tool calls: {time_response['tool_calls']}")
    print()
    
    # Test 4: Translator Agent
    print("=" * 60)
    print("4. Testing Translator Agent")
    print("=" * 60)
    translate_query = "Translate 'hello' to Spanish"
    print(f"Query: {translate_query}\n")
    
    translator_agent_instance = astra.get_agent('translator-agent')
    translator_response = await translator_agent_instance.invoke(translate_query)
    responses.append({
        "agent": "translator",
        "query": translate_query,
        "response": translator_response,
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"✅ Response: {translator_response['content']}")
    if translator_response.get('tool_calls'):
        print(f"🔧 Tool calls: {translator_response['tool_calls']}")
    print()
    
    # Test 5: List all agents
    print("=" * 60)
    print("5. Listing All Agents")
    print("=" * 60)
    all_agents = astra.list_agents()
    print(f"Total agents: {len(all_agents)}")
    for agent in all_agents:
        print(f"  - {agent.id}: {agent.name}")
    print()
    
    # Get metrics from observability
    obs = astra.dependencies.observability
    metrics_text = obs.metrics.get_metrics_text()
    
    # Save responses to JSON file
    output_file = Path(__file__).parent.parent / "jsons" / "astra_multi_agent_responses.json"
    output_data = {
        "astra_instance": str(astra),
        "total_agents": len(all_agents),
        "agent_ids": [agent.id for agent in all_agents],
        "timestamp": datetime.now().isoformat(),
        "responses": responses,
        "metrics": metrics_text
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print("=" * 60)
    print(f"💾 Responses saved to: {output_file}")
    print("=" * 60)
    print("\n=== Example Complete ===")
    
    # Shutdown Astra
    await astra.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

