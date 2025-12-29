from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Dict, Optional

from observability.core.span import truncate_text
from observability.semantic.conventions import LLMAttributes


def _extract_prompt_text(contents: Any, truncate_limit: int) -> str | None:
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


def _extract_usage_metadata(resp: Any) -> dict[str, Any]:
    meta = getattr(resp, "usage_metadata", None)
    if meta:
        return {
            LLMAttributes.USAGE_PROMPT_TOKENS: getattr(meta, "prompt_token_count", None),
            LLMAttributes.USAGE_COMPLETION_TOKENS: getattr(meta, "candidates_token_count", None),
            LLMAttributes.USAGE_TOTAL_TOKENS: getattr(meta, "total_token_count", None),
            LLMAttributes.USAGE_CACHED_TOKENS: getattr(meta, "cached_content_token_count", None),
        }
    total = getattr(resp, "total_tokens", None)
    if total is not None:
        return {LLMAttributes.USAGE_TOTAL_TOKENS: total}
    tokens_info = getattr(resp, "tokens_info", None)
    if tokens_info is not None:
        try:
            total_ids = 0
            for ti in tokens_info:
                ids = getattr(ti, "token_ids", None)
                if isinstance(ids, Iterable):
                    total_ids += len(list(ids))
            return {LLMAttributes.USAGE_TOTAL_TOKENS: total_ids}
        except Exception:
            return {}
    return {}
__all__ = [
    "_extract_prompt_text",
    "_extract_usage_metadata",
]
