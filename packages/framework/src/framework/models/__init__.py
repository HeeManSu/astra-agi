from .base import Model, ModelResponse
from .google import GeminiFlash, GeminiPro, GeminiModel
from .claude import Claude
from .openai import OpenAI
from .huggingface import HuggingFace

# Alias for better UX
Gemini = GeminiModel

__all__ = [
    "Model",
    "ModelResponse",
    "GeminiFlash",
    "GeminiPro",
    "GeminiModel",
    "Gemini",
    "Claude",
    "OpenAI",
    "HuggingFace",
]

def get_model(provider: str, model_id: str, api_key: str | None = None) -> Model:
    """Factory to create a model instance based on provider.

    Args:
        provider: Provider name (e.g., 'google', 'anthropic', 'openai', 'huggingface').
        model_id: Model identifier specific to the provider.
        api_key: Optional API key for the provider.
    """
    provider = provider.lower()
    if provider == "google":
        # Use existing Gemini classes
        if "flash" in model_id.lower():
            return GeminiFlash(api_key=api_key, model_id=model_id)
        elif "pro" in model_id.lower():
            return GeminiPro(api_key=api_key, model_id=model_id)
        else:
            return GeminiModel(api_key=api_key, model_id=model_id)
    elif provider in {"anthropic", "claude"}:
        return Claude(api_key=api_key, model_id=model_id)
    elif provider == "openai":
        return OpenAI(api_key=api_key, model_id=model_id)
    elif provider == "huggingface":
        return HuggingFace(api_key=api_key, model_id=model_id)
    else:
        raise ValueError(f"Unsupported model provider '{provider}'.")
