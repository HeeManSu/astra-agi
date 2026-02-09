"""Semantic recall middleware for Limca.

Prepends relevant code context to user queries using vector similarity search.
"""

from typing import Any, ClassVar

from framework.middleware import Middleware, MiddlewareContext, MiddlewareStage


class SemanticRecallMiddleware(Middleware):
    """Middleware that retrieves and prepends semantically similar code chunks.

    This middleware:
    1. Takes the user query
    2. Searches vector store for similar code/docs
    3. Prepends retrieved context to the prompt

    This enables RAG (Retrieval-Augmented Generation) with a single LLM call.
    """

    stages: ClassVar[set[MiddlewareStage]] = {MiddlewareStage.INPUT}

    def __init__(
        self,
        embedder: Any = None,
        vector_store: Any = None,
        top_k: int = 5,
        max_tokens: int = 2000,
    ) -> None:
        """Initialize semantic recall middleware.

        Args:
            embedder: Embedder to convert queries to vectors
            vector_store: Vector store for similarity search
            top_k: Number of results to retrieve
            max_tokens: Max tokens for retrieved context
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k
        self.max_tokens = max_tokens

    async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """Retrieve and prepend relevant context."""
        if not self.embedder or not self.vector_store:
            # Skip if not configured
            return ctx

        query = ctx.data
        if not isinstance(query, str):
            return ctx

        # Get query embedding
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            return ctx

        # Search for similar chunks
        results = await self._search(query_embedding)
        if not results:
            return ctx

        # Format context
        context = self._format_context(results)

        # Prepend to query
        augmented_query = f"""### Retrieved Context

{context}

### User Query

{query}"""

        ctx.data = augmented_query
        return ctx

    async def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text."""
        try:
            if hasattr(self.embedder, "embed"):
                return await self.embedder.embed(text)
            elif hasattr(self.embedder, "embed_query"):
                return await self.embedder.embed_query(text)
            return None
        except Exception:
            return None

    async def _search(self, embedding: list[float]) -> list[dict]:
        """Search vector store for similar documents."""
        try:
            if hasattr(self.vector_store, "search"):
                return await self.vector_store.search(embedding, k=self.top_k)
            elif hasattr(self.vector_store, "similarity_search"):
                return await self.vector_store.similarity_search(embedding, k=self.top_k)
            return []
        except Exception:
            return []

    def _format_context(self, results: list[dict]) -> str:
        """Format search results as context."""
        lines: list[str] = []
        total_tokens = 0

        for result in results:
            content = result.get("content") or result.get("text") or ""
            metadata = result.get("metadata") or {}
            source = result.get("source") or metadata.get("source") or ""

            # Ensure content is a string
            content_str = str(content) if content else ""
            source_str = str(source) if source else ""

            # Rough token estimate
            tokens = len(content_str.split()) if content_str else 0
            if total_tokens + tokens > self.max_tokens:
                break

            if source_str:
                lines.append(f"**Source: {source_str}**")
            if content_str:
                lines.append(content_str)
            lines.append("")
            total_tokens += tokens

        return "\n".join(lines)
