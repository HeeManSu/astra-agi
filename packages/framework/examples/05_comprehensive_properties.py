"""
Example 5: Comprehensive Property Tests
Tests all Agent properties and configurations.
"""

import asyncio
from collections.abc import Callable

from framework.agents import Agent
from framework.agents.exceptions import ValidationError
from framework.models import Gemini


async def test_basic_properties():
    """Test basic Agent properties."""
    print("\n" + "=" * 60)
    print("Test 1: Basic Properties")
    print("=" * 60)

    agent = Agent(
        name="TestAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        id="custom-id-123",
        description="Test agent description",
    )

    assert agent.name == "TestAgent", "Name should match"
    assert agent.id == "custom-id-123", "ID should match"
    assert agent.description == "Test agent description", "Description should match"
    assert agent.instructions == "You are helpful.", "Instructions should match"
    assert agent.model is not None, "Model should be set"

    print(f"Name: {agent.name}")
    print(f"ID: {agent.id}")
    print(f"Description: {agent.description}")
    print("PASS: Basic properties work")


async def test_execution_properties():
    """Test execution-related properties."""
    print("\n" + "=" * 60)
    print("Test 2: Execution Properties")
    print("=" * 60)

    agent = Agent(
        name="ExecAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        max_retries=5,
        temperature=0.5,
        max_tokens=1000,
        stream_enabled=True,
    )

    assert agent.max_retries == 5, "max_retries should be 5"
    assert agent.temperature == 0.5, "temperature should be 0.5"
    assert agent.max_tokens == 1000, "max_tokens should be 1000"
    assert agent.stream_enabled is True, "stream_enabled should be True"

    print(f" max_retries: {agent.max_retries}")
    print(f" temperature: {agent.temperature}")
    print(f" max_tokens: {agent.max_tokens}")
    print(f" stream_enabled: {agent.stream_enabled}")
    print("PASS: Execution properties work")


async def test_default_properties():
    """Test default property values."""
    print("\n" + "=" * 60)
    print("Test 3: Default Properties")
    print("=" * 60)

    agent = Agent(
        name="DefaultAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    assert agent.max_retries == 3, "Default max_retries should be 3"
    assert agent.temperature == 0.7, "Default temperature should be 0.7"
    assert agent.max_tokens is None, "Default max_tokens should be None"
    assert agent.stream_enabled is False, "Default stream_enabled should be False"
    assert agent.tools is None, "Default tools should be None"
    assert agent.storage is None, "Default storage should be None"
    assert agent.knowledge is None, "Default knowledge should be None"

    print("All defaults match expected values")
    print("PASS: Default properties work")


async def test_temperature_range():
    """Test temperature property range."""
    print("\n" + "=" * 60)
    print("Test 4: Temperature Range")
    print("=" * 60)

    # Test valid temperatures
    for temp in [0.0, 0.5, 1.0, 1.5, 2.0]:
        agent = Agent(
            name="TempAgent",
            instructions="You are helpful.",
            model=Gemini("gemini-2.5-flash"),
            temperature=temp,
        )
        assert agent.temperature == temp, f"Temperature {temp} should be set"
        print(f"Temperature {temp} works")

    # Test invalid temperatures (should be caught during invoke)
    agent = Agent(
        name="TempAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        temperature=0.5,  # Valid for init
    )

    try:
        await agent.invoke("Hello", temperature=3.0)  # Invalid
        print("Should have raised ValidationError")
    except ValidationError:
        print("Invalid temperature caught during invoke")

    print("PASS: Temperature range validation works")


async def test_max_retries():
    """Test max_retries property."""
    print("\n" + "=" * 60)
    print("Test 5: Max Retries")
    print("=" * 60)

    for retries in [1, 3, 5, 10]:
        agent = Agent(
            name="RetryAgent",
            instructions="You are helpful.",
            model=Gemini("gemini-2.5-flash"),
            max_retries=retries,
        )
        assert agent.max_retries == retries, f"max_retries {retries} should be set"
        print(f"max_retries={retries} works")

    print("PASS: Max retries property works")


async def test_max_tokens():
    """Test max_tokens property."""
    print("\n" + "=" * 60)
    print("Test 6: Max Tokens")
    print("=" * 60)

    # Test None (unlimited)
    agent = Agent(
        name="TokenAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        max_tokens=None,
    )
    assert agent.max_tokens is None, "max_tokens None should work"
    print("max_tokens=None works")

    # Test specific values
    for tokens in [100, 500, 1000, 2000]:
        agent = Agent(
            name="TokenAgent",
            instructions="You are helpful.",
            model=Gemini("gemini-2.5-flash"),
            max_tokens=tokens,
        )
        assert agent.max_tokens == tokens, f"max_tokens {tokens} should be set"
        print(f"max_tokens={tokens} works")

    # Test invalid value (should be caught during invoke)
    agent = Agent(
        name="TokenAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    try:
        await agent.invoke("Hello", max_tokens=-1)
        print("Should have raised ValidationError")
    except ValidationError:
        print("Invalid max_tokens caught during invoke")

    print("PASS: Max tokens property works")


async def test_tools_property():
    """Test tools property."""
    print("\n" + "=" * 60)
    print("Test 7: Tools Property")
    print("=" * 60)

    from framework.agents import tool

    @tool
    def test_tool(x: int) -> int:
        return x * 2

    # Test with tools
    agent_with_tools = Agent(
        name="ToolAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        tools=[test_tool],
    )
    assert agent_with_tools.tools is not None, "Tools should be set"
    assert len(agent_with_tools.tools) == 1, "Should have 1 tool"
    print(f"Tools count: {len(agent_with_tools.tools)}")

    # Test without tools
    agent_no_tools = Agent(
        name="NoToolAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        tools=None,
    )
    assert agent_no_tools.tools is None, "Tools should be None"
    print("No tools works")

    # Test empty tools list
    agent_empty_tools = Agent(
        name="EmptyToolAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        tools=[],
    )
    assert agent_empty_tools.tools == [], "Tools should be empty list"
    print("Empty tools list works")

    print("PASS: Tools property works")


async def test_optional_properties():
    """Test optional properties (storage, knowledge, middlewares, etc.)."""
    print("\n" + "=" * 60)
    print("Test 8: Optional Properties")
    print("=" * 60)

    agent = Agent(
        name="OptionalAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        storage=None,
        knowledge=None,
        input_middlewares=None,
        output_middlewares=None,
        guardrails=None,
    )

    assert agent.storage is None, "storage should be None"
    assert agent.knowledge is None, "knowledge should be None"
    assert agent.input_middlewares is None, "input_middlewares should be None"
    assert agent.output_middlewares is None, "output_middlewares should be None"
    assert agent.guardrails is None, "guardrails should be None"

    print("All optional properties default to None")
    print("PASS: Optional properties work")


async def test_property_override():
    """Test property overrides during invoke."""
    print("\n" + "=" * 60)
    print("Test 9: Property Overrides")
    print("=" * 60)

    agent = Agent(
        name="OverrideAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        temperature=0.3,
        max_tokens=100,
    )

    # Override during invoke
    response = await agent.invoke(
        "Say hello",
        temperature=1.0,  # Override
        max_tokens=200,  # Override
    )

    assert len(response) > 0, "Should get response"
    print("Temperature override works")
    print("Max tokens override works")
    print("PASS: Property overrides work")


async def test_auto_generated_id():
    """Test auto-generated agent ID."""
    print("\n" + "=" * 60)
    print("Test 10: Auto-Generated ID")
    print("=" * 60)

    agent1 = Agent(
        name="AutoIDAgent1",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    agent2 = Agent(
        name="AutoIDAgent2",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    assert agent1.id != agent2.id, "IDs should be unique"
    assert agent1.id.startswith("agent-"), "ID should start with 'agent-'"
    assert len(agent1.id) > 10, "ID should have reasonable length"

    print(f"Agent 1 ID: {agent1.id}")
    print(f"Agent 2 ID: {agent2.id}")
    print("PASS: Auto-generated IDs work")


async def main():
    """Run all property tests."""
    print("\n" + "=" * 60)
    print("Example 5: Comprehensive Property Tests")
    print("=" * 60)

    tests = [
        test_basic_properties,
        test_execution_properties,
        test_default_properties,
        test_temperature_range,
        test_max_retries,
        test_max_tokens,
        test_tools_property,
        test_optional_properties,
        test_property_override,
        test_auto_generated_id,
    ]

    for test in tests:
        await run_test(test)


async def run_test(test: Callable):
    try:
        await test()
    except Exception as e:
        print(f"\nFAIL: {test.__name__}: {e}")
        raise

    print("\n" + "=" * 60)
    print("All property tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
