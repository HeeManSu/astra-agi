"""RAG Embedders module."""

from framework.rag.embedders.base import Embedder
from framework.rag.embedders.huggingface import HuggingFaceEmbedder


# Conditionally import OpenAI embedder
try:
    from framework.rag.embedders.openai import OpenAIEmbedder

    __all__ = ["Embedder", "HuggingFaceEmbedder", "OpenAIEmbedder"]
except ImportError:
    __all__ = ["Embedder", "HuggingFaceEmbedder"]
