from typing import Any

from framework.models.aws.bedrock import Bedrock
from framework.models.base import Model, ModelResponse
from framework.models.google.gemini import Gemini


__all__ = [
    "Bedrock",
    "Gemini",
    "Model",
    "ModelResponse",
    "get_model",
]


def get_model(provider: str, model_id: str) -> Model:
    """
    Factory to create a model instance based on provider.

    This method helps IDEs provide better autocomplete suggestions
    for supported providers and model IDs.

    Args:
        provider: AI model provider name (e.g. "gemini", "google", "bedrock", "aws")
        model_id: Identifier of the model to load
    """
    # Normalize provider value for case-insensitive comparison
    provider = provider.lower()

    # Gemini provider - covers both "google" and "gemini" aliases for convenience
    if provider in ("google", "gemini"):
        return Gemini(model_id)  # type: ignore[arg-type]

    # AWS Bedrock provider - covers "bedrock", "aws", and "amazon-bedrock" aliases
    if provider in ("bedrock", "aws", "amazon-bedrock"):
        return Bedrock(model_id)  # type: ignore[arg-type]

    # If we reach this point, the provider is not supported yet.
    raise ValueError(
        f"Unsupported model provider '{provider}'. "
        "Supported providers: 'google', 'gemini', 'bedrock', 'aws', 'amazon-bedrock'"
    )
