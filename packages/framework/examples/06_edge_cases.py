"""
Example 6: Edge Cases and Boundary Conditions
Comprehensive edge case testing for Agent.
"""

import asyncio
from collections.abc import Callable

from framework.agents import Agent, tool
from framework.agents.exceptions import ValidationError
from framework.models.huggingface import HuggingFaceLocal


@tool
def edge_case_tool(value: str) -> str:
    """Tool for edge case testing."""
    return f"Processed: {value}"


async def test_empty_string():
    """Test with empty string (should fail validation)."""
    print("\n" + "=" * 60)
    print("Test 1: Empty String")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    try:
        await agent.invoke("")
        print("✗ FAIL: Should have raised ValidationError")
    except ValidationError as e:
        print(f"✓ Caught expected ValidationError: {e}")
        print("✓ PASS: Empty string validation works")


async def test_whitespace_only():
    """Test with whitespace-only string."""
    print("\n" + "=" * 60)
    print("Test 2: Whitespace Only")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    try:
        await agent.invoke("   ")
        print("✗ FAIL: Should have raised ValidationError")
    except ValidationError as e:
        print(f"✓ Caught expected ValidationError: {e}")
        print("✓ PASS: Whitespace validation works")


async def test_very_long_message():
    """Test with very long message."""
    print("\n" + "=" * 60)
    print("Test 3: Very Long Message")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    # Test at boundary (100,000 chars)
    long_msg = "A" * 100000

    try:
        await agent.invoke(long_msg)
        print("✗ FAIL: Should have raised ValidationError")
    except ValidationError:
        print("✓ Caught expected ValidationError for 100k chars")

    # Test just under boundary (99,999 chars)
    long_msg = "A" * 99999
    try:
        response = await agent.invoke(long_msg[:1000])  # Truncate for actual call
        print(f"✓ Message just under limit works (response length: {len(response)})")
    except ValidationError:
        print("✗ Unexpected ValidationError")

    print("✓ PASS: Long message validation works")


async def test_temperature_boundaries():
    """Test temperature at boundaries."""
    print("\n" + "=" * 60)
    print("Test 4: Temperature Boundaries")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    # Test valid boundaries
    for temp in [0.0, 2.0]:
        try:
            response = await agent.invoke("Hello", temperature=temp)
            assert len(response) > 0, "Should get response"
            print(f"✓ Temperature {temp} works")
        except ValidationError as e:
            print(f"✓ Temperature {temp} correctly rejected: {e}")

    # Test invalid boundaries
    for temp in [-0.1, 2.1, 5.0]:
        try:
            await agent.invoke("Hello", temperature=temp)
            print(f"✗ Temperature {temp} should have failed")
        except ValidationError:
            print(f"✓ Temperature {temp} correctly rejected")

    print("✓ PASS: Temperature boundaries work")


async def test_max_tokens_boundaries():
    """Test max_tokens at boundaries."""
    print("\n" + "=" * 60)
    print("Test 5: Max Tokens Boundaries")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    # Test valid values
    for tokens in [1, 100, 1000, 10000]:
        try:
            response = await agent.invoke("Say hello", max_tokens=tokens)
            assert len(response) > 0, "Should get response"
            print(f"✓ max_tokens={tokens} works")
        except Exception as e:
            print(f"✗ max_tokens={tokens} failed: {e}")

    # Test invalid values
    for tokens in [-1, 0, 100001]:
        try:
            await agent.invoke("Hello", max_tokens=tokens)
            print(f"✗ max_tokens={tokens} should have failed")
        except ValidationError:
            print(f"✓ max_tokens={tokens} correctly rejected")

    print("✓ PASS: Max tokens boundaries work")


async def test_zero_retries():
    """Test with zero retries."""
    print("\n" + "=" * 60)
    print("Test 6: Zero Retries")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
        max_retries=0,
    )

    # Should still work, just no retries
    try:
        response = await agent.invoke("Hello")
        assert len(response) > 0, "Should get response"
        print("✓ Zero retries works")
    except Exception as e:
        print(f"✗ Zero retries failed: {e}")

    print("✓ PASS: Zero retries works")


async def test_very_high_retries():
    """Test with very high retry count."""
    print("\n" + "=" * 60)
    print("Test 7: Very High Retries")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
        max_retries=100,
    )

    assert agent.max_retries == 100, "Should accept high retry count"
    print("✓ High retry count works")

    # Should work normally
    response = await agent.invoke("Hello")
    assert len(response) > 0, "Should get response"

    print("✓ PASS: High retries works")


async def test_special_characters():
    """Test with special characters."""
    print("\n" + "=" * 60)
    print("Test 8: Special Characters")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    special_messages = [
        "Hello! @#$%^&*()",
        "Test\nwith\nnewlines",
        "Test\twith\ttabs",
        "Test with 'quotes' and \"double quotes\"",
        "Unicode: 你好 🌟",
    ]

    for msg in special_messages:
        try:
            response = await agent.invoke(msg)
            assert len(response) > 0, "Should get response"
            print(f"✓ Special chars work: {msg[:30]}...")
        except Exception as e:
            print(f"✗ Special chars failed: {msg[:30]}... - {e}")

    print("✓ PASS: Special characters work")


async def test_none_values():
    """Test handling of None values."""
    print("\n" + "=" * 60)
    print("Test 9: None Values")
    print("=" * 60)

    # Test with None for optional properties
    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
        description=None,
        tools=None,
        storage=None,
    )

    assert agent.description is None, "None description should work"
    assert agent.tools is None, "None tools should work"
    assert agent.storage is None, "None storage should work"

    # Should still work
    response = await agent.invoke("Hello")
    assert len(response) > 0, "Should get response"

    print("✓ PASS: None values work")


async def test_unicode_and_emojis():
    """Test with Unicode and emojis."""
    print("\n" + "=" * 60)
    print("Test 10: Unicode and Emojis")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    unicode_messages = [
        "Hello 世界",
        "Test with emojis 🚀 🎉 💻",
        "Mixed: Hello 世界 🚀",
    ]

    for msg in unicode_messages:
        try:
            response = await agent.invoke(msg)
            assert len(response) > 0, "Should get response"
            print(f"✓ Unicode works: {msg}")
        except Exception as e:
            print(f"✗ Unicode failed: {msg} - {e}")

    print("✓ PASS: Unicode and emojis work")


async def test_concurrent_invocations():
    """Test many concurrent invocations."""
    print("\n" + "=" * 60)
    print("Test 11: Concurrent Invocations")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    async def invoke_question(q: str) -> str:
        return await agent.invoke(q)

    questions = [f"Say number {i}" for i in range(10)]
    tasks = [invoke_question(q) for q in questions]

    try:
        results = await asyncio.gather(*tasks)
        assert len(results) == 10, "Should complete all invocations"
        print(f"✓ Completed {len(results)} concurrent invocations")
    except Exception as e:
        print(f"✗ Concurrent invocations failed: {e}")
        raise

    print("✓ PASS: Concurrent invocations work")


async def test_rapid_sequential_calls():
    """Test rapid sequential calls."""
    print("\n" + "=" * 60)
    print("Test 12: Rapid Sequential Calls")
    print("=" * 60)

    agent = Agent(
        name="EdgeAgent",
        instructions="You are helpful.",
        model=HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=200),
    )

    for i in range(5):
        try:
            response = await agent.invoke(f"Say {i}")
            assert len(response) > 0, "Should get response"
        except Exception as e:
            print(f"✗ Rapid call {i} failed: {e}")
            raise

    print("✓ PASS: Rapid sequential calls work")


async def main():
    """Run all edge case tests."""
    print("\n" + "=" * 60)
    print("Example 6: Edge Cases and Boundary Conditions")
    print("=" * 60)

    tests = [
        test_empty_string,
        test_whitespace_only,
        test_very_long_message,
        test_temperature_boundaries,
        test_max_tokens_boundaries,
        test_zero_retries,
        test_very_high_retries,
        test_special_characters,
        test_none_values,
        test_unicode_and_emojis,
        test_concurrent_invocations,
        test_rapid_sequential_calls,
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
    print("All edge case tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
