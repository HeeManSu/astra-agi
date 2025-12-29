from __future__ import annotations

from typing import Any, Dict, Optional, Iterable

from observability.semantic.conventions import GenAIAttributes
from observability.core.span import truncate_text


def _extract_prompt_text(contents: Any, truncate_limit: int) -> Optional[str]:
    try:
        if isinstance(contents, str):
            return truncate_text(contents, truncate_limit)
        if isinstance(contents, bytes):
            return None
        if isinstance(contents, Iterable):
            for item in contents:
                if isinstance(item, str):
                    return truncate_text(item, truncate_limit)
                text = getattr(item, "text", None)
                if isinstance(text, str) and text:
                    return truncate_text(text, truncate_limit)
            return None
        parts = getattr(contents, "parts", None)
        if parts and isinstance(parts, Iterable):
            for p in parts:
                text = getattr(p, "text", None)
                if isinstance(text, str) and text:
                    return truncate_text(text, truncate_limit)
        return None
    except Exception:
        return None


def _extract_usage_metadata(resp: Any) -> Dict[str, Any]:
    meta = getattr(resp, "usage_metadata", None)
    if meta:
        return {
            GenAIAttributes.USAGE_INPUT_TOKENS: getattr(meta, "prompt_token_count", None),
            GenAIAttributes.USAGE_OUTPUT_TOKENS: getattr(meta, "candidates_token_count", None),
            GenAIAttributes.USAGE_TOTAL_TOKENS: getattr(meta, "total_token_count", None),
            GenAIAttributes.USAGE_CACHED_TOKENS: getattr(meta, "cached_content_token_count", None),
        }
    total = getattr(resp, "total_tokens", None)
    if total is not None:
        return {"genai.usage.total_tokens": total}
    tokens_info = getattr(resp, "tokens_info", None)
    if tokens_info is not None:
        try:
            total_ids = 0
            for ti in tokens_info:
                ids = getattr(ti, "token_ids", None)
                if isinstance(ids, Iterable):
                    total_ids += len(list(ids))
            return {"genai.usage.total_tokens": total_ids}
        except Exception:
            return {}
    return {}
__all__ = [
    "_extract_prompt_text",
    "_extract_usage_metadata",
]
