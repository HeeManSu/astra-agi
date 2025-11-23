from .base import Model, ModelResponse

class Claude(Model):
    """Stub implementation for Anthropic Claude models.

    This class provides a minimal implementation that satisfies the
    `Model` abstract interface. Real network calls are omitted – the
    methods return a deterministic `ModelResponse` useful for unit tests
    and local execution without external dependencies.
    """

    def __init__(self, model_id: str = "claude-3-5-sonnet", api_key: str | None = None, **kwargs):
        super().__init__(model_id=model_id, api_key=api_key, **kwargs)

    async def invoke(self, messages, tools=None, temperature=0.7, max_tokens=None, **kwargs) -> ModelResponse:
        # Simple deterministic mock response – echo the last user message.
        content = """Claude response placeholder"""
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict) and last.get("content"):
                content = f"Claude mock reply to: {last['content']}"
        return ModelResponse(content=content)

    async def stream(self, messages, tools=None, temperature=0.7, max_tokens=None, **kwargs):
        # Yield a single chunk mirroring `invoke` for simplicity.
        response = await self.invoke(messages, tools, temperature, max_tokens, **kwargs)
        class Chunk:
            def __init__(self, content):
                self.content = content
                self.tool_calls = []
                self.usage = {}
                self.metadata = {}
        yield Chunk(response.content)
