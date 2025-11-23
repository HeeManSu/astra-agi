from .base import Model, ModelResponse

class HuggingFace(Model):
    """Stub implementation for Hugging Face models.

    Provides a deterministic mock response for local testing without external API calls.
    """

    def __init__(self, model_id: str = "meta-llama/Llama-3-8b", api_key: str | None = None, **kwargs):
        super().__init__(model_id=model_id, api_key=api_key, **kwargs)

    async def invoke(self, messages, tools=None, temperature=0.7, max_tokens=None, **kwargs) -> ModelResponse:
        content = "HuggingFace response placeholder"
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict) and last.get("content"):
                content = f"HuggingFace mock reply to: {last['content']}"
        return ModelResponse(content=content)

    async def stream(self, messages, tools=None, temperature=0.7, max_tokens=None, **kwargs):
        response = await self.invoke(messages, tools, temperature, max_tokens, **kwargs)
        class Chunk:
            def __init__(self, content):
                self.content = content
                self.tool_calls = []
                self.usage = {}
                self.metadata = {}
        yield Chunk(response.content)
