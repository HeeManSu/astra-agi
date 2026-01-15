"""Type stubs for models package - enables IDE autocomplete for provider names."""

from framework.models.base import Model, ModelResponse
from framework.models.google.gemini import Gemini

# Export model catalogs
GEMINI_MODELS: list[str]

# Export all providers and utilities
__all__ = [
    "GEMINI_MODELS",
    "Gemini",
    "Model",
    "ModelResponse",
    "get_model",
]

def get_model(provider: str, model_id: str) -> Model: ...
