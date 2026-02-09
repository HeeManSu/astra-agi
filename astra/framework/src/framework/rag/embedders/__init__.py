"""RAG Embedders module."""

from framework.rag.embedders.base import Embedder
from framework.rag.embedders.huggingface import HuggingFaceEmbedder


__all__ = ["Embedder", "HuggingFaceEmbedder"]

# Conditionally import OpenAI embedder
try:
    from framework.rag.embedders.openai import OpenAIEmbedder

    __all__.append("OpenAIEmbedder")
except ImportError:
    pass

try:
    from framework.rag.embedders.gemini import GeminiEmbedder

    __all__.append("GeminiEmbedder")
except ImportError:
    pass
