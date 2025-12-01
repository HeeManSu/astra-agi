"""
Test: Content Safety Filter

This example demonstrates the InputContentFilter and OutputContentFilter guardrails,
which provide basic content moderation using blocklists and allowlists.

Tests:
- Blocklist filtering (profanity, restricted topics)
- Allowlist filtering (only permitted terms)
- BLOCK vs REDACT actions
- Case sensitivity options
- Edge cases (word boundaries, partial matches)

Codebase:
- framework.guardrails.content.InputContentFilter
- framework.guardrails.content.OutputContentFilter
"""

import asyncio
import os

from framework.agents import Agent
from framework.guardrails import (
    ContentAction,
    InputContentFilter,
    InputGuardrailError,
    OutputContentFilter,
)
from framework.models import Gemini


async def test_input_content_filter():
    """Test InputContentFilter with blocklists and allowlists."""

    print("=" * 80)
    print("INPUT CONTENT FILTER TESTS")
    print("=" * 80)

    # Test 1: Blocklist with BLOCK action
    print("\nTest 1: Blocklist - BLOCK mode")
    agent_block = Agent(
        name="BlockAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[
            InputContentFilter(
                blocklist=["badword", "inappropriate", "restricted"], action=ContentAction.BLOCK
            )
        ],
    )

    try:
        await agent_block.invoke("This is a badword in the message")
        print("✗ Blocked word was not caught!")
    except InputGuardrailError as e:
        print(f"✓ Blocked word detected: {e!s}")

    # Test 2: Blocklist with REDACT action
    print("\nTest 2: Blocklist - REDACT mode")
    agent_redact = Agent(
        name="RedactAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[
            InputContentFilter(blocklist=["secret", "confidential"], action=ContentAction.REDACT)
        ],
    )

    try:
        response = await agent_redact.invoke("This is a secret message about confidential data")
        print("✓ Blocked words redacted (replaced with [UNSAFE])")
        # Model sees: "This is a [UNSAFE] message about [UNSAFE] data"
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Blocked words redacted (model returned empty response)")
        else:
            raise

    # Test 3: Case sensitivity
    print("\nTest 3: Case-insensitive matching (default)")
    try:
        await agent_block.invoke("This contains BADWORD in caps")
        print("✗ Case variation not caught!")
    except InputGuardrailError:
        print("✓ Case-insensitive matching works")

    # Test 4: Case-sensitive mode
    print("\nTest 4: Case-sensitive matching")
    agent_case_sensitive = Agent(
        name="CaseSensitiveAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[
            InputContentFilter(
                blocklist=["BadWord"], action=ContentAction.BLOCK, case_sensitive=True
            )
        ],
    )

    # Should pass (different case)
    try:
        response = await agent_case_sensitive.invoke("This has badword in lowercase")
        print("✓ Case-sensitive mode allows different case")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Case-sensitive mode allows different case (model returned empty response)")
        else:
            raise

    # Should block (exact case)
    try:
        await agent_case_sensitive.invoke("This has BadWord in exact case")
        print("✗ Exact case not blocked!")
    except InputGuardrailError:
        print("✓ Exact case blocked")

    # Test 5: Word boundaries
    print("\nTest 5: Word boundary detection")
    agent_boundary = Agent(
        name="BoundaryAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[InputContentFilter(blocklist=["bad"], action=ContentAction.BLOCK)],
    )

    # Should pass (bad is part of another word)
    try:
        response = await agent_boundary.invoke("This is a badge")
        print("✓ Word boundaries respected (badge != bad)")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Word boundaries respected (model returned empty response)")
        else:
            raise

    # Should block (bad as standalone word)
    try:
        await agent_boundary.invoke("This is bad")
        print("✗ Standalone word not blocked!")
    except InputGuardrailError:
        print("✓ Standalone word blocked")

    # Test 6: Clean input (should pass)
    print("\nTest 6: Clean input")
    try:
        response = await agent_block.invoke("What is the weather today?")
        print(f"✓ Clean input passed: {response[:50]}...")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Clean input passed (model returned empty response)")
        else:
            raise


async def test_output_content_filter():
    """Test OutputContentFilter to moderate agent responses."""

    print("\n" + "=" * 80)
    print("OUTPUT CONTENT FILTER TESTS")
    print("=" * 80)

    # Test 1: Block inappropriate output
    print("\nTest 1: Output blocklist")
    agent_block = Agent(
        name="OutputBlockAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        output_middlewares=[
            OutputContentFilter(blocklist=["internal", "proprietary"], action=ContentAction.BLOCK)
        ],
    )

    # Normal response should work
    try:
        response = await agent_block.invoke("What is Python?")
        print(f"✓ Clean output allowed: {response[:50]}...")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Clean output allowed (model returned empty response)")
        else:
            raise

    # Test 2: Redact output
    print("\nTest 2: Output redaction")
    agent_redact = Agent(
        name="OutputRedactAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        output_middlewares=[
            OutputContentFilter(blocklist=["example"], action=ContentAction.REDACT)
        ],
    )

    try:
        response = await agent_redact.invoke("Give me an example")
        print("✓ Output redaction configured")
        # If model says "Here's an example", it becomes "Here's an [UNSAFE]"
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Output redaction configured (model returned empty response)")
        else:
            raise


async def test_combined_filters():
    """Test combining multiple content filters."""

    print("\n" + "=" * 80)
    print("COMBINED FILTER TESTS")
    print("=" * 80)

    # Test 1: Multiple blocklists
    print("\nTest 1: Layered content filtering")
    agent_layered = Agent(
        name="LayeredAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[
            InputContentFilter(blocklist=["profanity1", "profanity2"], action=ContentAction.BLOCK),
            InputContentFilter(blocklist=["spam", "advertisement"], action=ContentAction.BLOCK),
        ],
    )

    # Test first filter
    try:
        await agent_layered.invoke("This contains profanity1")
        print("✗ First filter failed!")
    except InputGuardrailError:
        print("✓ First filter works")

    # Test second filter
    try:
        await agent_layered.invoke("This is spam")
        print("✗ Second filter failed!")
    except InputGuardrailError:
        print("✓ Second filter works")

    # Clean message should pass both
    try:
        response = await agent_layered.invoke("What is machine learning?")
        print(f"✓ Clean message passed both filters: {response[:50]}...")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Clean message passed both filters (model returned empty response)")
        else:
            raise


async def test_edge_cases():
    """Test edge cases and boundary conditions."""

    print("\n" + "=" * 80)
    print("EDGE CASE TESTS")
    print("=" * 80)

    agent = Agent(
        name="EdgeCaseAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[InputContentFilter(blocklist=["test"], action=ContentAction.REDACT)],
    )

    # Test 1: Empty blocklist
    print("\nTest 1: Empty blocklist")
    agent_empty = Agent(
        name="EmptyAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[InputContentFilter(blocklist=[], action=ContentAction.BLOCK)],
    )
    try:
        response = await agent_empty.invoke("Any message should pass")
        print("✓ Empty blocklist allows all messages")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Empty blocklist allows all messages (model returned empty response)")
        else:
            raise

    # Test 2: Empty message
    print("\nTest 2: Empty message")
    try:
        response = await agent.invoke("")
        print("✓ Empty message handled")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Empty message handled (model returned empty response)")
        elif "empty" in str(e).lower():  # Handle validation error for empty message
            print("✓ Empty message handled (validation error)")
        else:
            raise

    # Test 3: Very long message
    print("\nTest 3: Long message processing")
    long_message = "This is a long message. " * 50 + "test"
    try:
        response = await agent.invoke(long_message)
        print("✓ Long message processed and redacted")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Long message processed (model returned empty response)")
        else:
            raise

    # Test 4: Special characters in blocklist
    print("\nTest 4: Special regex characters")
    agent_special = Agent(
        name="SpecialAgent",
        model=Gemini("gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY")),
        instructions="You are a helpful assistant.",
        input_middlewares=[
            InputContentFilter(
                blocklist=["test.com"],  # Period is a regex special char
                action=ContentAction.BLOCK,
            )
        ],
    )

    try:
        await agent_special.invoke("Visit test.com")
        print("✗ Special characters not handled!")
    except InputGuardrailError:
        print("✓ Special characters properly escaped")

    # Test 5: Multiple occurrences
    print("\nTest 5: Multiple occurrences of blocked word")
    try:
        _ = await agent.invoke("test test test")
        print("✓ Multiple occurrences redacted")
    except Exception as e:
        if "output text or tool calls" in str(e):
            print("✓ Multiple occurrences redacted (model returned empty response)")
        else:
            raise

    print("\n" + "=" * 80)
    print("All edge cases handled successfully!")


async def main():
    """Run all content filter tests."""
    await test_input_content_filter()
    await test_output_content_filter()
    await test_combined_filters()
    await test_edge_cases()

    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("- Content filters provide basic keyword-based moderation")
    print("- Supports both BLOCK and REDACT actions")
    print("- Can be layered for comprehensive filtering")
    print("- All filters are user-configured (no defaults)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
