"""
Unit tests for middleware system.
"""
import pytest
from framework.middlewares import (
    InputMiddleware,
    OutputMiddleware,
    StreamingOutputMiddleware,
    MiddlewareContext,
    InputValidationError,
    OutputValidationError,
    MiddlewareAbortError
)
from framework.middlewares.builtin.validation import InputLengthValidator, EmptyInputValidator
from framework.middlewares.builtin.formatting import TrimWhitespaceMiddleware, OutputLengthLimiter


@pytest.mark.asyncio
async def test_input_length_validator():
    """Test input length validation."""
    validator = InputLengthValidator(max_length=50)
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    # Short message should pass
    messages = [{"role": "user", "content": "Hello"}]
    result = await validator.process(messages, context)
    assert result == messages
    
    # Long message should fail
    messages = [{"role": "user", "content": "x" * 100}]
    with pytest.raises(InputValidationError):
        await validator.process(messages, context)


@pytest.mark.asyncio
async def test_empty_input_validator():
    """Test empty input validation."""
    validator = EmptyInputValidator()
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    # Valid message should pass
    messages = [{"role": "user", "content": "Hello"}]
    result = await validator.process(messages, context)
    assert result == messages
    
    # Empty list should fail
    with pytest.raises(InputValidationError):
        await validator.process([], context)
    
    # Empty content should fail
    messages = [{"role": "user", "content": ""}]
    with pytest.raises(InputValidationError):
        await validator.process(messages, context)


@pytest.mark.asyncio
async def test_trim_whitespace_middleware():
    """Test whitespace trimming."""
    middleware = TrimWhitespaceMiddleware()
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    output = "  Hello World  \n"
    result = await middleware.process(output, context)
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_output_length_limiter():
    """Test output length limiting."""
    middleware = OutputLengthLimiter(max_length=10, suffix="...")
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    # Short output should pass through
    output = "Hello"
    result = await middleware.process(output, context)
    assert result == "Hello"
    
    # Long output should be truncated
    output = "This is a very long message"
    result = await middleware.process(output, context)
    assert len(result) == 10
    assert result.endswith("...")


@pytest.mark.asyncio
async def test_custom_input_middleware():
    """Test custom input middleware."""
    
    class UpperCaseMiddleware(InputMiddleware):
        async def process(self, messages, context):
            for msg in messages:
                msg['content'] = msg['content'].upper()
            return messages
    
    middleware = UpperCaseMiddleware()
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    messages = [{"role": "user", "content": "hello"}]
    result = await middleware.process(messages, context)
    assert result[0]['content'] == "HELLO"


@pytest.mark.asyncio
async def test_custom_output_middleware():
    """Test custom output middleware."""
    
    class PrefixMiddleware(OutputMiddleware):
        async def process(self, output, context):
            return f"[Agent] {output}"
    
    middleware = PrefixMiddleware()
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    output = "Hello"
    result = await middleware.process(output, context)
    assert result == "[Agent] Hello"


@pytest.mark.asyncio
async def test_streaming_middleware():
    """Test streaming middleware."""
    
    class BufferMiddleware(StreamingOutputMiddleware):
        def __init__(self):
            self.buffer = []
        
        async def on_chunk(self, chunk, context):
            self.buffer.append(chunk)
            return chunk.upper()
        
        async def on_complete(self, context):
            count = len(self.buffer)
            self.buffer = []
            return f"\n[{count} chunks]"
    
    middleware = BufferMiddleware()
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    # Process chunks
    chunk1 = await middleware.on_chunk("hello", context)
    assert chunk1 == "HELLO"
    
    chunk2 = await middleware.on_chunk("world", context)
    assert chunk2 == "WORLD"
    
    # Complete
    final = await middleware.on_complete(context)
    assert final == "\n[2 chunks]"


@pytest.mark.asyncio
async def test_middleware_abort():
    """Test middleware abort mechanism."""
    
    class AbortMiddleware(InputMiddleware):
        async def process(self, messages, context):
            if "abort" in messages[0]['content'].lower():
                raise MiddlewareAbortError("Aborted by middleware")
            return messages
    
    middleware = AbortMiddleware()
    context = MiddlewareContext(run_id="test", agent_id="agent-1")
    
    # Normal message should pass
    messages = [{"role": "user", "content": "Hello"}]
    result = await middleware.process(messages, context)
    assert result == messages
    
    # Abort message should raise
    messages = [{"role": "user", "content": "ABORT"}]
    with pytest.raises(MiddlewareAbortError):
        await middleware.process(messages, context)


@pytest.mark.asyncio
async def test_middleware_context():
    """Test middleware context."""
    context = MiddlewareContext(
        run_id="run-123",
        agent_id="agent-1",
        thread_id="thread-456",
        metadata={"key": "value"},
        tools=[]
    )
    
    assert context.run_id == "run-123"
    assert context.agent_id == "agent-1"
    assert context.thread_id == "thread-456"
    assert context.metadata == {"key": "value"}
