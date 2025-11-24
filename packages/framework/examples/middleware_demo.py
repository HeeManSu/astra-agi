"""
Example demonstrating middleware usage in Astra.

Shows input validation, output formatting, and streaming middlewares.
"""
import asyncio
from framework.agents import Agent
from framework.models import Gemini
from framework.middlewares import (
    InputMiddleware,
    OutputMiddleware,
    StreamingOutputMiddleware,
    MiddlewareContext,
    InputValidationError,
    MiddlewareAbortError
)
from framework.middlewares.builtin.validation import InputLengthValidator, EmptyInputValidator
from framework.middlewares.builtin.formatting import TrimWhitespaceMiddleware, OutputLengthLimiter


# Custom input middleware: Add context
class ContextInjectionMiddleware(InputMiddleware):
    """Injects additional context into user messages."""
    
    def __init__(self, context_prefix: str = "[Context: Be concise] "):
        self.context_prefix = context_prefix
    
    async def process(self, messages, context):
        """Add context prefix to user messages."""
        for msg in messages:
            if msg.get('role') == 'user':
                msg['content'] = self.context_prefix + msg['content']
        return messages


# Custom output middleware: Remove markdown
class RemoveMarkdownMiddleware(OutputMiddleware):
    """Removes markdown formatting from output."""
    
    async def process(self, output, context):
        """Remove common markdown patterns."""
        # Simple markdown removal (for demo)
        output = output.replace('**', '')
        output = output.replace('*', '')
        output = output.replace('`', '')
        return output


# Custom streaming middleware: Word counter
class WordCounterMiddleware(StreamingOutputMiddleware):
    """Counts words in streaming output."""
    
    def __init__(self):
        self.word_count = 0
    
    async def on_chunk(self, chunk, context):
        """Count words in each chunk."""
        self.word_count += len(chunk.split())
        return chunk  # Pass through unchanged
    
    async def on_complete(self, context):
        """Report final word count."""
        print(f"\n[Word count: {self.word_count}]")
        self.word_count = 0  # Reset for next use
        return None


async def example_basic_validation():
    """Example 1: Basic input validation."""
    print("=== Example 1: Input Validation ===\n")
    
    agent = Agent(
        name="ValidatedAgent",
        model=Gemini("1.5-flash"),
        input_middlewares=[
            EmptyInputValidator(),
            InputLengthValidator(max_length=100)
        ]
    )
    
    # This should work
    try:
        response = await agent.invoke("Hello!")
        print(f"✓ Short message accepted: {response['content'][:50]}...")
    except InputValidationError as e:
        print(f"✗ Validation failed: {e}")
    
    # This should fail (too long)
    try:
        long_message = "x" * 150
        response = await agent.invoke(long_message)
        print(f"✓ Long message accepted")
    except InputValidationError as e:
        print(f"✗ Validation failed (expected): {e}")
    
    print()


async def example_output_formatting():
    """Example 2: Output formatting."""
    print("=== Example 2: Output Formatting ===\n")
    
    agent = Agent(
        name="FormattedAgent",
        model=Gemini("1.5-flash"),
        output_middlewares=[
            TrimWhitespaceMiddleware(),
            OutputLengthLimiter(max_length=50, suffix="...")
        ]
    )
    
    response = await agent.invoke("Tell me a long story")
    print(f"Formatted output: {response['content']}")
    print(f"Length: {len(response['content'])} chars")
    print()


async def example_custom_middlewares():
    """Example 3: Custom middlewares."""
    print("=== Example 3: Custom Middlewares ===\n")
    
    agent = Agent(
        name="CustomAgent",
        model=Gemini("1.5-flash"),
        input_middlewares=[
            ContextInjectionMiddleware("[Be brief] ")
        ],
        output_middlewares=[
            RemoveMarkdownMiddleware(),
            TrimWhitespaceMiddleware()
        ]
    )
    
    response = await agent.invoke("What is Python?")
    print(f"Response (no markdown): {response['content']}")
    print()


async def example_streaming_middleware():
    """Example 4: Streaming middleware."""
    print("=== Example 4: Streaming Middleware ===\n")
    
    agent = Agent(
        name="StreamingAgent",
        model=Gemini("1.5-flash"),
        output_middlewares=[
            WordCounterMiddleware()
        ]
    )
    
    print("Streaming response:")
    async for chunk in agent.stream("Tell me about AI in 3 sentences"):
        print(chunk['content'], end='', flush=True)
    print("\n")


async def example_dynamic_middlewares():
    """Example 5: Dynamic middleware resolution."""
    print("=== Example 5: Dynamic Middlewares ===\n")
    
    def get_middlewares(context: MiddlewareContext):
        """Return middlewares based on context."""
        # Check user tier from metadata
        user_tier = context.metadata.get("user_tier", "free")
        
        if user_tier == "premium":
            # Premium users get no length limit
            return [TrimWhitespaceMiddleware()]
        else:
            # Free users get limited output
            return [
                TrimWhitespaceMiddleware(),
                OutputLengthLimiter(max_length=30)
            ]
    
    agent = Agent(
        name="DynamicAgent",
        model=Gemini("1.5-flash"),
        output_middlewares=get_middlewares  # Callable!
    )
    
    # Free user
    response = await agent.invoke(
        "Tell me about space",
        metadata={"user_tier": "free"}
    )
    print(f"Free user output: {response['content']}")
    
    # Premium user
    response = await agent.invoke(
        "Tell me about space",
        metadata={"user_tier": "premium"}
    )
    print(f"Premium user output: {response['content']}")
    print()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Middleware System Examples")
    print("=" * 60)
    print()
    
    await example_basic_validation()
    await example_output_formatting()
    await example_custom_middlewares()
    await example_streaming_middleware()
    await example_dynamic_middlewares()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
