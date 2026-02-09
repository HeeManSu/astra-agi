"""Wiki recall middleware for Limca.

Prepends relevant wiki pages to user queries for grounded responses.
"""

from typing import Any, ClassVar

from framework.middleware import Middleware, MiddlewareContext, MiddlewareStage


class WikiRecallMiddleware(Middleware):
    """Middleware that retrieves and prepends relevant wiki content.

    This middleware:
    1. Takes the user query
    2. Searches wiki pages for relevant content
    3. Prepends wiki context to the prompt

    Wiki content provides high-level architectural context that complements
    the lower-level code chunks from SemanticRecallMiddleware.
    """

    stages: ClassVar[set[MiddlewareStage]] = {MiddlewareStage.INPUT}

    def __init__(
        self,
        wiki_storage: Any = None,
        max_pages: int = 3,
        max_tokens: int = 1500,
    ) -> None:
        """Initialize wiki recall middleware.

        Args:
            wiki_storage: Storage provider for wiki pages
            max_pages: Maximum number of wiki pages to include
            max_tokens: Max tokens for wiki context
        """
        self.wiki_storage = wiki_storage
        self.max_pages = max_pages
        self.max_tokens = max_tokens

    async def run(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """Retrieve and prepend relevant wiki content."""
        if not self.wiki_storage:
            return ctx

        query = ctx.data
        if not isinstance(query, str):
            return ctx

        # Get relevant wiki pages
        pages = await self._find_relevant_pages(query)
        if not pages:
            return ctx

        # Format wiki context
        context = self._format_wiki_context(pages)

        # Prepend to query
        augmented_query = f"""### Wiki Context

{context}

### User Query

{query}"""

        ctx.data = augmented_query
        return ctx

    async def _find_relevant_pages(self, query: str) -> list[dict]:
        """Find wiki pages relevant to the query.

        Uses simple keyword matching. Can be enhanced with embeddings.
        """
        try:
            # List all wiki pages
            keys = await self.wiki_storage.list_keys()
            if not keys:
                return []

            # Score pages by keyword overlap
            query_words = set(query.lower().split())
            scored_pages = []

            for key in keys[:20]:  # Limit to avoid loading too many
                page = await self.wiki_storage.get(key)
                if not page:
                    continue

                title = page.get("title", key)
                content = page.get("content", "")

                # Simple keyword scoring
                page_words = set(title.lower().split()) | set(content.lower().split()[:100])
                overlap = len(query_words & page_words)

                if overlap > 0:
                    scored_pages.append(
                        {
                            "title": title,
                            "content": content,
                            "score": overlap,
                        }
                    )

            # Sort by score and return top pages
            scored_pages.sort(key=lambda x: x["score"], reverse=True)
            return scored_pages[: self.max_pages]

        except Exception:
            return []

    def _format_wiki_context(self, pages: list[dict]) -> str:
        """Format wiki pages as context."""
        lines = []
        total_tokens = 0

        for page in pages:
            title = page.get("title", "Untitled")
            content = page.get("content", "")

            # Rough token estimate
            tokens = len(content.split())
            if total_tokens + tokens > self.max_tokens:
                # Truncate content
                words = content.split()[: self.max_tokens - total_tokens]
                content = " ".join(words) + "..."

            lines.append(f"## {title}")
            lines.append(content)
            lines.append("")
            total_tokens += len(content.split())

            if total_tokens >= self.max_tokens:
                break

        return "\n".join(lines)
